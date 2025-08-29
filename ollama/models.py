"""
Ollama service models
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class OllamaRequest:
    """Request to Ollama LLM service"""
    question: str
    context: Optional[str] = None
    
    def __post_init__(self):
        if not self.question or not self.question.strip():
            raise ValueError("Question cannot be empty")


@dataclass
class OllamaResponse:
    """Response from Ollama LLM service"""
    answer: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'answer': self.answer,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'processing_time': self.processing_time
        }


@dataclass  
class OllamaChatMessage:
    """Chat message for Ollama API"""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class OllamaChatRequest:
    """Chat completion request for Ollama API"""
    model: str
    messages: List[OllamaChatMessage]
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    stream: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API call"""
        data = {
            'model': self.model,
            'messages': [
                {'role': msg.role, 'content': msg.content}
                for msg in self.messages
            ],
            'temperature': self.temperature,
            'stream': self.stream
        }
        
        if self.max_tokens:
            data['options'] = {'num_predict': self.max_tokens}
            
        return data


@dataclass
class OllamaChatResponse:
    """Chat completion response from Ollama API"""
    message: Dict[str, Any]
    model: str
    created_at: str
    done: bool = True
    
    @property
    def content(self) -> str:
        """Get the response content"""
        return self.message.get('content', '')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OllamaChatResponse':
        """Create from API response dictionary"""
        return cls(
            message=data.get('message', {}),
            model=data.get('model', ''),
            created_at=data.get('created_at', ''),
            done=data.get('done', True)
        )