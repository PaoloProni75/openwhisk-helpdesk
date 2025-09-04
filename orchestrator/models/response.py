"""
Helpdesk response models
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HelpdeskResponse:
    """Response model for helpdesk queries"""
    answer: str
    source: str  # 'kb' or 'llm'
    confidence: Optional[float] = None
    escalate_to_human: bool = False
    response_time_ms: Optional[float] = None
    
    def to_dict(self, question: str = None) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'question': question,
            'answer': self.answer,
            'escalation': self.escalate_to_human,
            'confidence': self.confidence,
            'source': self.source,
            'response_time_ms': self.response_time_ms
        }