"""
Ollama client implementation
"""
import asyncio
import aiohttp
import time
from typing import Optional
from models import OllamaRequest, OllamaResponse, OllamaChatRequest, OllamaChatResponse, OllamaChatMessage
from exceptions import OllamaConnectionError, OllamaTimeoutError, OllamaModelError, OllamaInvalidRequestError


class OllamaClient:
    """
    Async client for Ollama API
    Supports OpenAI-compatible chat completions endpoint
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model: str = "llama2",
                 temperature: float = 0.1,
                 max_tokens: Optional[int] = 500,
                 timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Default system prompt for helpdesk
        self.system_prompt = (
            "You are a helpful customer service assistant. "
            "Provide clear, concise, and professional responses. "
            "If you cannot answer a question based on the available information, "
            "politely suggest that the user should contact support for further assistance."
        )
    
    async def generate_response(self, request: OllamaRequest) -> OllamaResponse:
        """
        Generate response using Ollama API
        """
        if not request.question.strip():
            raise OllamaInvalidRequestError("Question cannot be empty")
        
        # Build messages for chat completion
        messages = [
            OllamaChatMessage(role="system", content=self.system_prompt)
        ]
        
        # Add context if available
        if request.context and request.context.strip():
            context_message = f"Context information: {request.context}"
            messages.append(OllamaChatMessage(role="system", content=context_message))
        
        # Add user question
        messages.append(OllamaChatMessage(role="user", content=request.question))
        
        # Create chat request
        chat_request = OllamaChatRequest(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Call API
        start_time = time.time()
        try:
            chat_response = await self._call_chat_api(chat_request)
            processing_time = time.time() - start_time
            
            return OllamaResponse(
                answer=chat_response.content,
                model=chat_response.model,
                processing_time=processing_time
            )
            
        except asyncio.TimeoutError:
            raise OllamaTimeoutError(f"Request timed out after {self.timeout} seconds")
        except aiohttp.ClientError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {str(e)}")
    
    async def _call_chat_api(self, chat_request: OllamaChatRequest) -> OllamaChatResponse:
        """
        Call Ollama chat completions API
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(
                url,
                json=chat_request.to_dict(),
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 404:
                    raise OllamaModelError(f"Model '{self.model}' not found")
                elif response.status == 400:
                    error_text = await response.text()
                    raise OllamaInvalidRequestError(f"Invalid request: {error_text}")
                elif response.status != 200:
                    error_text = await response.text()
                    raise OllamaConnectionError(f"API error {response.status}: {error_text}")
                
                try:
                    data = await response.json()
                    
                    # Handle OpenAI-compatible response format
                    if 'choices' in data and len(data['choices']) > 0:
                        choice = data['choices'][0]
                        message = choice.get('message', {})
                        
                        return OllamaChatResponse(
                            message=message,
                            model=data.get('model', self.model),
                            created_at=str(int(time.time())),
                            done=True
                        )
                    
                    # Handle native Ollama response format (fallback)
                    elif 'message' in data:
                        return OllamaChatResponse.from_dict(data)
                    
                    else:
                        raise OllamaModelError("Invalid response format from Ollama API")
                        
                except ValueError as e:
                    raise OllamaModelError(f"Failed to parse response JSON: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy
        """
        try:
            url = f"{self.base_url}/api/tags"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(url) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def list_models(self) -> list:
        """
        Get list of available models
        """
        try:
            url = f"{self.base_url}/api/tags"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['name'] for model in data.get('models', [])]
                    else:
                        return []
                        
        except Exception:
            return []