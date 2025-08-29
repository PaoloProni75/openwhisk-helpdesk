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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'answer': self.answer,
            'source': self.source,
            'confidence': self.confidence,
            'escalate_to_human': self.escalate_to_human
        }