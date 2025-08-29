"""
Helpdesk engine - core orchestration logic
"""
import json
import asyncio
import aiohttp
import os
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
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        # Check ALWAYS_CALL_LLM environment variable (same logic as Java version)
        self.always_call_llm = os.getenv("ALWAYS_CALL_LLM", "").lower() == "true"
    
    async def process_question(self, request: HelpdeskRequest) -> HelpdeskResponse:
        """
        Main processing method that coordinates similarity and LLM services
        """
        try:
            # Step 1: Find best match from knowledge base using similarity service
            best_match = await self._find_best_match(request.question)
            
            # Step 2: Decide whether to use KB answer or call LLM
            # If ALWAYS_CALL_LLM is true, skip KB and always call LLM (same logic as Java version)
            if not self.always_call_llm and best_match and best_match.is_confident_match(self.config.similarity.threshold):
                return HelpdeskResponse(
                    answer=best_match.entry.answer,
                    source="kb",
                    confidence=best_match.confidence,
                    escalate_to_human=best_match.entry.escalation
                )
            
            # Step 3: Call LLM with context from KB if available
            context = best_match.entry.answer if best_match else None
            llm_response = await self._get_llm_response(request.question, context)
            
            # Step 4: Check if response indicates need for human escalation
            escalate = self._should_escalate(llm_response.answer)
            
            return HelpdeskResponse(
                answer=llm_response.answer,
                source="llm",
                confidence=best_match.confidence if best_match else None,
                escalate_to_human=escalate
            )
            
        except Exception as e:
            # Return fallback response on error
            return HelpdeskResponse(
                answer=self.FALLBACK_ANSWER,
                source="fallback",
                escalate_to_human=True
            )
    
    async def _find_best_match(self, question: str) -> Optional[KnowledgeBestMatch]:
        """Call similarity service to find best knowledge base match"""
        try:
            similarity_url = f"{self.config.similarity.endpoint_url}/similarity"
            payload = {"question": question}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(similarity_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
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
    
    async def _get_llm_response(self, question: str, context: Optional[str] = None) -> HelpdeskResponse:
        """Call Ollama service to get LLM response"""
        try:
            ollama_url = f"{self.config.ollama.endpoint_url}/chat"
            payload = {
                "question": question,
                "context": context
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(ollama_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return HelpdeskResponse(
                            answer=data.get('answer', self.FALLBACK_ANSWER),
                            source="llm"
                        )
            
            return HelpdeskResponse(answer=self.FALLBACK_ANSWER, source="fallback")
            
        except Exception as e:
            print(f"Error calling Ollama service: {e}")
            return HelpdeskResponse(answer=self.FALLBACK_ANSWER, source="fallback")
    
    def _should_escalate(self, answer: str) -> bool:
        """Check if the answer contains escalation phrases"""
        answer_lower = answer.lower()
        for phrase in self.config.prompts.escalation_phrases:
            if phrase.lower() in answer_lower:
                return True
        return False