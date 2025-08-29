"""
Helpdesk request models
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HelpdeskRequest:
    """Request model for helpdesk queries"""
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.question or not self.question.strip():
            raise ValueError("Question cannot be empty")