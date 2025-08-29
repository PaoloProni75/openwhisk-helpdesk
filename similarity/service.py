"""
Similarity service implementation
"""
import json
from typing import List, Optional
from models import SimilarityRequest, SimilarityResult, SimilarityResponse
from algorithms import SimilarityAlgorithms


class KnowledgeStore:
    """
    Simple in-memory knowledge base store
    In production, this would connect to a real database or storage service
    """
    
    def __init__(self):
        # Sample knowledge base - in production this would be loaded from external storage
        self.knowledge_base = [
            {
                "id": "kb001",
                "question": "How do I reset my password?",
                "answer": "To reset your password, go to the login page and click 'Forgot Password'. Enter your email address and follow the instructions sent to your email."
            },
            {
                "id": "kb002", 
                "question": "How can I change my email address?",
                "answer": "You can change your email address in your account settings. Go to Profile > Account Settings > Email and enter your new email address."
            },
            {
                "id": "kb003",
                "question": "Where can I find my order history?",
                "answer": "Your order history is available in your account dashboard. Log in and click on 'My Orders' to view all your past purchases."
            },
            {
                "id": "kb004",
                "question": "How do I cancel my subscription?",
                "answer": "To cancel your subscription, go to Account Settings > Billing > Manage Subscription and click 'Cancel Subscription'. You'll continue to have access until the current billing period ends."
            },
            {
                "id": "kb005",
                "question": "What payment methods do you accept?",
                "answer": "We accept all major credit cards (Visa, Mastercard, American Express), PayPal, and bank transfers for enterprise accounts."
            }
        ]
    
    def get_all_entries(self) -> List[dict]:
        """Get all knowledge base entries"""
        return self.knowledge_base
    
    def load_from_file(self, file_path: str):
        """Load knowledge base from JSON file"""
        try:
            with open(file_path, 'r') as f:
                self.knowledge_base = json.load(f)
        except FileNotFoundError:
            print(f"Knowledge file not found: {file_path}. Using default knowledge base.")
        except json.JSONDecodeError as e:
            print(f"Error parsing knowledge file: {e}. Using default knowledge base.")


class SimilarityService:
    """
    Service for finding similar questions in the knowledge base
    """
    
    def __init__(self, threshold: float = 0.7, algorithm: str = "cosine"):
        self.threshold = threshold
        self.algorithm = algorithm
        self.knowledge_store = KnowledgeStore()
        
        # Try to load knowledge from file if available
        try:
            self.knowledge_store.load_from_file("config/knowledge-base.json")
        except:
            pass  # Use default knowledge base
    
    def find_similar(self, request: SimilarityRequest) -> SimilarityResponse:
        """
        Find similar questions in the knowledge base
        """
        query = request.question
        all_matches = []
        
        # Calculate similarity with all knowledge base entries
        for entry in self.knowledge_store.get_all_entries():
            similarity = SimilarityAlgorithms.calculate_similarity(
                query, 
                entry["question"], 
                self.algorithm
            )
            
            # Convert similarity to confidence (could apply different logic here)
            confidence = similarity
            
            if similarity > 0.0:  # Include all matches with some similarity
                result = SimilarityResult(
                    entry_id=entry["id"],
                    question=entry["question"],
                    answer=entry["answer"],
                    similarity_score=similarity,
                    confidence=confidence
                )
                all_matches.append(result)
        
        # Sort by similarity score descending
        all_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Determine best match (highest scoring match above threshold)
        best_match = None
        if all_matches and all_matches[0].confidence >= self.threshold:
            best_match = all_matches[0]
        
        return SimilarityResponse(
            best_match=best_match,
            all_matches=all_matches
        )