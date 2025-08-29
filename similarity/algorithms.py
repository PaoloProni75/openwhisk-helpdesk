"""
Similarity algorithms implementation
"""
import re
import math
from collections import Counter
from typing import List, Dict


class CosineSequenceMatcher:
    """
    Cosine similarity algorithm for text comparison
    Based on the Java implementation in the original project
    """
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """Preprocess text by removing punctuation and converting to lowercase"""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into words"""
        return CosineSequenceMatcher.preprocess_text(text).split()
    
    @staticmethod
    def compute_term_frequency(tokens: List[str]) -> Dict[str, int]:
        """Compute term frequency for tokens"""
        return Counter(tokens)
    
    @staticmethod
    def compute_cosine_similarity(text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        Returns value between 0 (no similarity) and 1 (identical)
        """
        # Tokenize both texts
        tokens1 = CosineSequenceMatcher.tokenize(text1)
        tokens2 = CosineSequenceMatcher.tokenize(text2)
        
        # Handle empty texts
        if not tokens1 or not tokens2:
            return 0.0
        
        # Compute term frequencies
        tf1 = CosineSequenceMatcher.compute_term_frequency(tokens1)
        tf2 = CosineSequenceMatcher.compute_term_frequency(tokens2)
        
        # Get all unique terms
        all_terms = set(tf1.keys()) | set(tf2.keys())
        
        # Compute dot product
        dot_product = sum(tf1.get(term, 0) * tf2.get(term, 0) for term in all_terms)
        
        # Compute magnitudes
        magnitude1 = math.sqrt(sum(count ** 2 for count in tf1.values()))
        magnitude2 = math.sqrt(sum(count ** 2 for count in tf2.values()))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Compute cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity


class SimilarityAlgorithms:
    """
    Collection of similarity algorithms
    """
    
    ALGORITHM_COSINE = "cosine"
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str, algorithm: str = ALGORITHM_COSINE) -> float:
        """
        Calculate similarity between two texts using specified algorithm
        """
        if algorithm == SimilarityAlgorithms.ALGORITHM_COSINE:
            return CosineSequenceMatcher.compute_cosine_similarity(text1, text2)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    @staticmethod
    def get_available_algorithms() -> List[str]:
        """Get list of available similarity algorithms"""
        return [SimilarityAlgorithms.ALGORITHM_COSINE]