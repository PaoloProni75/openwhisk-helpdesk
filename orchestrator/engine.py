"""
Helpdesk engine - core orchestration logic
"""
import json
import os
import urllib.request
import urllib.parse
import time
from typing import List, Optional
from orchestrator.models.request import HelpdeskRequest
from orchestrator.models.response import HelpdeskResponse
from orchestrator.models.knowledge import KnowledgeEntry, KnowledgeBestMatch
from orchestrator.config import ConfigManager


class HelpdeskEngine:
    """
    Core helpdesk engine that orchestrates similarity matching and LLM interactions
    """
    
    FALLBACK_ANSWER = "Sorry, I don't know the answer to that question."
    
    def __init__(self, openwhisk_args=None):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        # Check ALWAYS_CALL_LLM from OpenWhisk parameters first, then environment variable
        always_call_llm_param = False
        if openwhisk_args:
            always_call_llm_param = openwhisk_args.get("ALWAYS_CALL_LLM", False)
            if isinstance(always_call_llm_param, str):
                always_call_llm_param = always_call_llm_param.lower() == "true"
        
        self.always_call_llm = always_call_llm_param or os.getenv("ALWAYS_CALL_LLM", "").lower() == "true"
    
    def process_question(self, request: HelpdeskRequest) -> HelpdeskResponse:
        """
        Main processing method that coordinates similarity and LLM services
        """
        import time
        total_start = time.time()
        
        try:
            # Step 1: Find best match from knowledge base using similarity service
            best_match = self._find_best_match(request.question)
            
            # Step 2: Decide whether to use KB answer or call LLM
            # If ALWAYS_CALL_LLM is true, skip KB and always call LLM (same logic as Java version)
            if not self.always_call_llm and best_match and best_match.is_confident_match(self.config.similarity.threshold):
                total_time = (time.time() - total_start) * 1000
                return HelpdeskResponse(
                    answer=best_match.entry.answer,
                    source="kb",
                    confidence=best_match.confidence,
                    escalate_to_human=best_match.entry.escalation,
                    response_time_ms=0  # KB response is instant
                )
            
            # Step 3: Call LLM with context from KB if available
            context = best_match.entry.answer if best_match else None
            llm_response, response_time = self._get_llm_response(request.question, context)
            
            # Step 4: Check if response indicates need for human escalation
            escalate = self._should_escalate(llm_response.answer)
            
            total_time = (time.time() - total_start) * 1000
            return HelpdeskResponse(
                answer=llm_response.answer,
                source="llm",
                confidence=best_match.confidence if best_match else None,
                escalate_to_human=escalate,
                response_time_ms=response_time
            )
            
        except Exception as e:
            # Return fallback response on error
            total_time = (time.time() - total_start) * 1000
            return HelpdeskResponse(
                answer=self.FALLBACK_ANSWER,
                source="fallback",
                escalate_to_human=True,
                response_time_ms=0
            )
    
    def _find_best_match(self, question: str) -> Optional[KnowledgeBestMatch]:
        """Call similarity OpenWhisk action to find best knowledge base match"""
        try:
            # OpenWhisk API call to similarity action
            openwhisk_url = "http://18.102.51.160:32209/api/v1/namespaces/guest/actions/helpdesk/similarity"
            payload = {
                "question": question,
                "threshold": self.config.similarity.threshold,
                "algorithm": self.config.similarity.algorithm
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{openwhisk_url}?blocking=true&result=true", 
                data=data, 
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A='
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    
                    if data.get('best_match'):
                        match_data = data['best_match']
                        entry = KnowledgeEntry(
                            id=match_data['entry']['id'],
                            question=match_data['entry']['question'],
                            answer=match_data['entry']['answer'],
                            escalation=match_data['entry'].get('escalation', False)
                        )
                        
                        return KnowledgeBestMatch(
                            entry=entry,
                            similarity_score=match_data['similarity_score'],
                            confidence=match_data['confidence']
                        )
            return None
            
        except Exception as e:
            print(f"Error calling similarity service: {e}")
            return None
    
    def _get_llm_response(self, question: str, context: Optional[str] = None) -> tuple[HelpdeskResponse, float]:
        """Call Ollama service to get LLM response"""
        import time
        try:
            llm_start = time.time()
            
            # OpenWhisk API call to ollama action
            openwhisk_url = "http://18.102.51.160:32209/api/v1/namespaces/guest/actions/helpdesk/ollama"
            
            # Build question with context
            full_question = question
            if context:
                full_question = f"Context: {context}\n\nQuestion: {question}"
            
            payload = {"question": full_question}
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{openwhisk_url}?blocking=true&result=true", 
                data=data, 
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A='
                }
            )
            
            with urllib.request.urlopen(req, timeout=self.config.ollama.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    llm_time = (time.time() - llm_start) * 1000
                    
                    return HelpdeskResponse(
                        answer=data.get('answer', self.FALLBACK_ANSWER),
                        source="llm"
                    ), llm_time
            
            llm_time = (time.time() - llm_start) * 1000
            return HelpdeskResponse(answer=self.FALLBACK_ANSWER, source="fallback"), llm_time
            
        except Exception as e:
            print(f"Error calling Ollama service: {e}")
            return HelpdeskResponse(answer=self.FALLBACK_ANSWER, source="fallback"), 0
    
    def _should_escalate(self, answer: str) -> bool:
        """Check if the answer contains escalation phrases"""
        answer_lower = answer.lower()
        for phrase in self.config.prompts.escalation_phrases:
            if phrase.lower() in answer_lower:
                return True
        return False