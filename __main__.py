"""
OpenWhisk entry point for helpdesk orchestrator
"""
import sys
import os
import json
import urllib.request
import urllib.parse

# Add current directory and libs to Python path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

def load_config():
    """Load configuration from YAML file"""
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'helpdesk-config.yaml')
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if config:
            return config
        else:
            raise ValueError("Empty config file")
            
    except Exception as e:
        print(f"Error loading config: {e}")
        # Fallback defaults that match the YAML structure
        return {
            'ollama': {
                'endpoint_url': 'http://172.31.17.101:11434',
                'model': 'nemotron-mini:latest',
                'temperature': 0.5,
                'max_tokens': 512,
                'timeout': 30
            },
            'similarity': {
                'threshold': 0.7,
                'algorithm': 'cosine'
            },
            'prompts': {
                'escalation_phrases': [
                    'contact support',
                    'speak to human', 
                    'human assistance'
                ]
            }
        }

def main(args):
    """
    Entry point for OpenWhisk - Orchestrator logic
    """
    try:
        # Load configuration
        config = load_config()
        
        # Extract configuration values
        similarity_config = config.get('similarity', {})
        ollama_config = config.get('ollama', {})
        prompts_config = config.get('prompts', {})
        
        threshold = similarity_config.get('threshold', 0.7)
        escalation_phrases = prompts_config.get('escalation_phrases', ['contact support'])
        
        question = args.get('question', '')
        if not question:
            return {'error': 'Missing required parameter: question'}
        
        # Check ALWAYS_CALL_LLM from args or environment variable
        always_call_llm_arg = args.get("ALWAYS_CALL_LLM", "")
        always_call_llm_env = os.getenv("ALWAYS_CALL_LLM", "")
        
        # Handle both string and boolean values
        if isinstance(always_call_llm_arg, bool):
            always_call_llm = always_call_llm_arg
        elif isinstance(always_call_llm_arg, str):
            always_call_llm = always_call_llm_arg.lower() == "true"
        elif isinstance(always_call_llm_env, str):
            always_call_llm = always_call_llm_env.lower() == "true"
        else:
            always_call_llm = True  # Changed default to True
        
        # Step 1: Call similarity service
        similarity_result = None
        confidence = 0.0
        
        try:
            # Call similarity service directly via HTTP (OpenWhisk API)
            # For now, use the similarity logic directly
            
            # Load knowledge base from JSON file  
            kb_path = os.path.join(os.path.dirname(__file__), 'config', 'knowledge-base.json')
            try:
                with open(kb_path, 'r') as f:
                    knowledge_base = json.load(f)
                
                # Simple similarity matching (same as similarity service)
                question_words = set(question.lower().split())
                best_match = None
                best_score = 0
                
                for entry in knowledge_base:
                    entry_words = set(entry["question"].lower().split())
                    common_words = question_words.intersection(entry_words)
                    score = len(common_words) / len(entry_words) if entry_words else 0
                    
                    if score > best_score and score >= 0.3:  # 30% threshold
                        best_match = entry
                        best_score = score
                
                if best_match and best_score >= threshold:
                    similarity_result = best_match
                    confidence = best_score
                    
            except Exception as kb_error:
                print(f"KB loading error: {kb_error}")
                
        except Exception as e:
            print(f"Similarity service error: {e}")
        
        # Step 2: Decide whether to use KB answer or call LLM
        if not always_call_llm and similarity_result and confidence >= threshold:
            return {
                'question': question,
                'answer': similarity_result['answer'],
                'source': 'kb',
                'confidence': confidence,
                'escalate_to_human': similarity_result.get('escalation', False)
            }
        
        # Step 3: Call Ollama LLM service
        try:
            # Get Ollama configuration
            base_url = ollama_config.get('endpoint_url', 'http://172.31.17.101:11434')
            model = ollama_config.get('model', 'mistral')
            temperature = ollama_config.get('temperature', 0.5)
            max_tokens = ollama_config.get('max_tokens', 512)
            timeout = ollama_config.get('timeout', 30)
            
            # Call Ollama directly with HTTP using config
            url = f'{base_url}/v1/chat/completions'
            
            # Build system prompt with context if available
            system_content = prompts_config.get('system_prompt', 
                "You are a helpful assistant for an agricultural subcontractor management software. Answer clearly and helpfully only if the question is relevant to the software. If it is not, state that you cannot answer. If the user needs human intervention, include EXACTLY the phrase 'contact support' once in the answer. If no human is required, DO NOT include that phrase.")
            
            if similarity_result:
                system_content += f" Context: {similarity_result['answer']}"
            
            payload = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": question}
                ]
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode())
            
            answer = result['choices'][0]['message']['content']
            
            # Check for escalation phrases from config
            escalate = any(phrase.lower() in answer.lower() for phrase in escalation_phrases)
            
            return {
                'question': question,
                'answer': answer,
                'source': 'llm',
                'confidence': 0.9,
                'escalate_to_human': escalate,
                'always_call_llm': always_call_llm,
                'kb_match_found': similarity_result is not None
            }
            
        except Exception as e:
            print(f"Ollama service error: {e}")
        
        # Fallback if both services fail
        return {
            'question': question,
            'answer': 'Sorry, I encountered an error processing your request.',
            'source': 'error',
            'escalate_to_human': True
        }
        
    except Exception as e:
        return {
            'error': f'System error: {str(e)}',
            'answer': 'Sorry, system error occurred',
            'source': 'error',
            'escalate_to_human': True
        }

    # """
    # Entry point for OpenWhisk - simplified helpdesk logic
    # """
    # try:
    #     question = args.get('question', '')
    #     if not question:
    #         return {'error': 'Missing required parameter: question'}
    #     
    #     # Load knowledge base directly from JSON file
    #     import json
    #     kb_path = os.path.join(os.path.dirname(__file__), 'config', 'knowledge-base.json')
    #     
    #     try:
    #         with open(kb_path, 'r') as f:
    #             knowledge_base = json.load(f)
    #     except Exception as e:
    #         return {
    #             'error': f'Cannot load knowledge base: {str(e)}',
    #             'answer': 'Sorry, system configuration error',
    #             'source': 'error',
    #             'escalate_to_human': True
    #         }
    #     
    #     # Simple similarity matching (keyword matching)
    #     def find_best_match(question, kb):
    #         question_words = set(question.lower().split())
    #         best_match = None
    #         best_score = 0
    #         
    #         for entry in kb:
    #             entry_words = set(entry["question"].lower().split())
    #             common_words = question_words.intersection(entry_words)
    #             score = len(common_words) / len(entry_words) if entry_words else 0
    #             
    #             if score > best_score and score >= 0.3:  # 30% threshold
    #                 best_match = entry
    #                 best_score = score
    #         
    #         return best_match, best_score
    #     
    #     # Check ALWAYS_CALL_LLM environment variable
    #     always_call_llm = os.getenv("ALWAYS_CALL_LLM", "").lower() == "true"
    #     
    #     # Find best KB match
    #     best_match, confidence = find_best_match(question, knowledge_base)
    #     
    #     # If we have a good match and not forced to call LLM, use KB
    #     if not always_call_llm and best_match and confidence >= 0.7:
    #         return {
    #             'question': question,
    #             'answer': best_match["answer"],
    #             'source': 'kb',
    #             'confidence': confidence,
    #             'escalate_to_human': best_match.get("escalation", False)
    #         }
    #     
    #     # Otherwise call LLM (Ollama)
    #     try:
    #         import urllib.request
    #         import urllib.parse
    #         
    #         url = 'http://172.31.17.101:11434/v1/chat/completions'
    #         
    #         # Build system prompt with context if available
    #         system_content = "You are a helpful assistant for an agricultural subcontractor management software. Answer clearly and helpfully only if the question is relevant to the software. If it is not, state that you cannot answer. If the user needs human intervention, include EXACTLY the phrase 'contact support' once in the answer. If no human is required, DO NOT include that phrase."
    #         
    #         if best_match:
    #             system_content += f" Context: {best_match['answer']}"
    #         
    #         payload = {
    #             "model": "gpt-oss:20b",
    #             "messages": [
    #                 {"role": "system", "content": system_content},
    #                 {"role": "user", "content": question}
    #             ]
    #         }
    #         
    #         data = json.dumps(payload).encode('utf-8')
    #         req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    #         
    #         with urllib.request.urlopen(req, timeout=60) as response:
    #             result = json.loads(response.read().decode())
    #         
    #         answer = result['choices'][0]['message']['content']
    #         
    #         # Check for escalation phrases in LLM response
    #         escalation_phrases = ["contact support", "speak to human", "human assistance"]
    #         escalate = any(phrase.lower() in answer.lower() for phrase in escalation_phrases)
    #         
    #         return {
    #             'question': question,
    #             'answer': answer,
    #             'source': 'llm',
    #             'confidence': 0.9,
    #             'escalate_to_human': escalate,
    #             'always_call_llm': always_call_llm,
    #             'kb_match_found': best_match is not None
    #         }
    #         
    #     except Exception as e:
    #         return {
    #             'question': question,
    #             'answer': f'Sorry, I encountered an error: {str(e)}',
    #             'source': 'error',
    #             'escalate_to_human': True
    #         }
    #     
    # except Exception as e:
    #     return {
    #         'error': f'System error: {str(e)}',
    #         'answer': 'Sorry, system error occurred',
    #         'source': 'error',
    #         'escalate_to_human': True
    #     }