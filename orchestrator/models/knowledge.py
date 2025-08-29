"""
Knowledge base models
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class KnowledgeEntry:
    """Single knowledge base entry"""
    id: str
    question: str
    answer: str
    escalation: bool = False
    category: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class KnowledgeBestMatch:
    """Best match from knowledge base with similarity score"""
    entry: KnowledgeEntry
    similarity_score: float
    confidence: float
    
    def is_confident_match(self, threshold: float = 0.7) -> bool:
        """Check if this match exceeds confidence threshold"""
        return self.confidence >= threshold