"""
Tests for similarity module
"""
import pytest
from similarity.algorithms import CosineSequenceMatcher, SimilarityAlgorithms
from similarity.models import SimilarityRequest, SimilarityResponse
from similarity.service import SimilarityService


class TestCosineSequenceMatcher:
    """Test cosine similarity algorithm"""
    
    def test_identical_texts(self):
        """Test similarity of identical texts"""
        text = "How do I reset my password?"
        similarity = CosineSequenceMatcher.compute_cosine_similarity(text, text)
        assert abs(similarity - 1.0) < 1e-10
    
    def test_similar_texts(self):
        """Test similarity of similar texts"""
        text1 = "How do I reset my password?"
        text2 = "How can I reset my password?"
        similarity = CosineSequenceMatcher.compute_cosine_similarity(text1, text2)
        assert 0.8 < similarity < 1.0
    
    def test_different_texts(self):
        """Test similarity of different texts"""
        text1 = "How do I reset my password?"
        text2 = "What is the weather today?"
        similarity = CosineSequenceMatcher.compute_cosine_similarity(text1, text2)
        assert similarity < 0.3
    
    def test_empty_texts(self):
        """Test similarity with empty texts"""
        similarity = CosineSequenceMatcher.compute_cosine_similarity("", "test")
        assert similarity == 0.0
        
        similarity = CosineSequenceMatcher.compute_cosine_similarity("test", "")
        assert similarity == 0.0
        
        similarity = CosineSequenceMatcher.compute_cosine_similarity("", "")
        assert similarity == 0.0
    
    def test_preprocessing(self):
        """Test text preprocessing"""
        text = "How do I reset my PASSWORD?!!"
        processed = CosineSequenceMatcher.preprocess_text(text)
        assert processed == "how do i reset my password"
    
    def test_tokenization(self):
        """Test text tokenization"""
        text = "How do I reset my password?"
        tokens = CosineSequenceMatcher.tokenize(text)
        assert tokens == ["how", "do", "i", "reset", "my", "password"]


class TestSimilarityAlgorithms:
    """Test similarity algorithms wrapper"""
    
    def test_cosine_algorithm(self):
        """Test cosine algorithm through wrapper"""
        text1 = "reset password"
        text2 = "password reset"
        similarity = SimilarityAlgorithms.calculate_similarity(text1, text2, "cosine")
        assert similarity > 0.8
    
    def test_unknown_algorithm(self):
        """Test unknown algorithm raises error"""
        with pytest.raises(ValueError):
            SimilarityAlgorithms.calculate_similarity("test", "test", "unknown")
    
    def test_available_algorithms(self):
        """Test getting available algorithms"""
        algorithms = SimilarityAlgorithms.get_available_algorithms()
        assert "cosine" in algorithms


class TestSimilarityModels:
    """Test similarity models"""
    
    def test_similarity_request_validation(self):
        """Test request validation"""
        # Valid request
        request = SimilarityRequest(question="How do I reset my password?")
        assert request.question == "How do I reset my password?"
        
        # Invalid request - empty question
        with pytest.raises(ValueError):
            SimilarityRequest(question="")
        
        with pytest.raises(ValueError):
            SimilarityRequest(question="   ")
    
    def test_similarity_response_serialization(self):
        """Test response serialization"""
        from similarity.models import SimilarityResult
        
        result = SimilarityResult(
            entry_id="kb001",
            question="How do I reset my password?", 
            answer="Go to login page",
            similarity_score=0.9,
            confidence=0.9
        )
        
        response = SimilarityResponse(best_match=result)
        data = response.to_dict()
        
        assert data["best_match"]["entry"]["id"] == "kb001"
        assert data["best_match"]["similarity_score"] == 0.9


class TestSimilarityService:
    """Test similarity service"""
    
    def test_find_similar_high_confidence(self):
        """Test finding similar question with high confidence"""
        service = SimilarityService(threshold=0.5)
        request = SimilarityRequest(question="How can I register a new job?")
        
        response = service.find_similar(request)
        
        # Should find the job registration question
        assert response.best_match is not None
        assert "job" in response.best_match.answer.lower()
        assert response.best_match.confidence > 0.5
    
    def test_find_similar_low_confidence(self):
        """Test finding similar question with low confidence"""
        service = SimilarityService(threshold=0.9)  # Very high threshold
        request = SimilarityRequest(question="What is the weather?")
        
        response = service.find_similar(request)
        
        # Should not find confident match
        assert response.best_match is None
        # But should still have some matches with low scores
        assert len(response.all_matches) > 0
    
    def test_similarity_threshold_behavior(self):
        """Test threshold behavior"""
        # Low threshold - should find match
        service_low = SimilarityService(threshold=0.3)
        request = SimilarityRequest(question="new job registration")
        
        response_low = service_low.find_similar(request)
        assert response_low.best_match is not None
        
        # High threshold - should not find match
        service_high = SimilarityService(threshold=0.95)
        response_high = service_high.find_similar(request)
        assert response_high.best_match is None
    
    def test_all_matches_sorted(self):
        """Test that all matches are sorted by similarity"""
        service = SimilarityService(threshold=0.1)  # Low threshold to get matches
        request = SimilarityRequest(question="account settings")
        
        response = service.find_similar(request)
        
        # Check that matches are sorted descending
        scores = [match.similarity_score for match in response.all_matches]
        assert scores == sorted(scores, reverse=True)