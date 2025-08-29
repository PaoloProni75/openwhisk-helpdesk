"""
Similarity service models
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SimilarityRequest:
    """Request for similarity calculation"""
    question: str
    
    def __post_init__(self):
        if not self.question or not self.question.strip():
            raise ValueError("Question cannot be empty")


@dataclass
class SimilarityResult:
    """Result of similarity calculation"""
    entry_id: str
    question: str
    answer: str
    similarity_score: float
    confidence: float


@dataclass
class SimilarityResponse:
    """Response from similarity service"""
    best_match: Optional[SimilarityResult] = None
    all_matches: List[SimilarityResult] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {}
        
        if self.best_match:
            result['best_match'] = {
                'entry': {
                    'id': self.best_match.entry_id,
                    'question': self.best_match.question,
                    'answer': self.best_match.answer
                },
                'similarity_score': self.best_match.similarity_score,
                'confidence': self.best_match.confidence
            }
        
        if self.all_matches:
            result['all_matches'] = [
                {
                    'entry': {
                        'id': match.entry_id,
                        'question': match.question,
                        'answer': match.answer
                    },
                    'similarity_score': match.similarity_score,
                    'confidence': match.confidence
                }
                for match in self.all_matches
            ]
        
        return result