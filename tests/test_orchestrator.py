"""
Tests for orchestrator module
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from orchestrator.models.request import HelpdeskRequest
from orchestrator.models.response import HelpdeskResponse
from orchestrator.models.knowledge import KnowledgeEntry, KnowledgeBestMatch
from orchestrator.engine import HelpdeskEngine
from orchestrator.config import ConfigManager


@pytest.fixture
def config_manager():
    """Mock configuration manager"""
    config_manager = Mock()
    config_manager.config.similarity.threshold = 0.7
    config_manager.config.similarity.endpoint_url = "http://localhost:3001"
    config_manager.config.ollama.endpoint_url = "http://localhost:11434"
    config_manager.config.prompts.escalation_phrases = ["contact support"]
    return config_manager


@pytest.fixture
def engine(config_manager):
    """Create engine with mocked config"""
    with patch('orchestrator.engine.ConfigManager', return_value=config_manager):
        return HelpdeskEngine()


@pytest.mark.asyncio
async def test_process_question_with_high_confidence_kb_match(engine):
    """Test processing question with high confidence KB match"""
    # Mock similarity service response
    mock_best_match = KnowledgeBestMatch(
        entry=KnowledgeEntry(
            id="kb001",
            question="How do I reset my password?",
            answer="Go to login page and click 'Forgot Password'.",
            escalation=False
        ),
        similarity_score=0.9,
        confidence=0.8
    )
    
    with patch.object(engine, '_find_best_match', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_best_match
        
        request = HelpdeskRequest(question="How can I reset my password?")
        response = await engine.process_question(request)
        
        # Verify the mock was called
        mock_find.assert_called_once_with("How can I reset my password?")
        
        assert response.source == "kb"
        assert response.confidence == 0.8
        assert "Forgot Password" in response.answer
        assert not response.escalate_to_human


@pytest.mark.asyncio
async def test_process_question_with_low_confidence_calls_llm(engine):
    """Test processing question with low confidence calls LLM"""
    # Mock similarity service response with low confidence
    mock_best_match = KnowledgeBestMatch(
        entry=KnowledgeEntry(
            id="kb001",
            question="How do I reset my password?",
            answer="Go to login page and click 'Forgot Password'.",
            escalation=False
        ),
        similarity_score=0.5,
        confidence=0.5  # Below threshold
    )
    
    mock_llm_response = HelpdeskResponse(
        answer="I can help you with that. Please contact support for password assistance.",
        source="llm"
    )
    
    with patch.object(engine, '_find_best_match', new_callable=AsyncMock) as mock_find, \
         patch.object(engine, '_get_llm_response', new_callable=AsyncMock) as mock_llm:
        
        mock_find.return_value = mock_best_match
        mock_llm.return_value = mock_llm_response
        
        request = HelpdeskRequest(question="How can I reset my password?")
        response = await engine.process_question(request)
        
        assert response.source == "llm"
        assert response.escalate_to_human == True  # Due to "contact support" phrase


@pytest.mark.asyncio
async def test_process_question_no_kb_match_calls_llm(engine):
    """Test processing question with no KB match calls LLM"""
    mock_llm_response = HelpdeskResponse(
        answer="I can help you with general questions.",
        source="llm"
    )
    
    with patch.object(engine, '_find_best_match', new_callable=AsyncMock) as mock_find, \
         patch.object(engine, '_get_llm_response', new_callable=AsyncMock) as mock_llm:
        
        mock_find.return_value = None
        mock_llm.return_value = mock_llm_response
        
        request = HelpdeskRequest(question="What is the meaning of life?")
        response = await engine.process_question(request)
        
        assert response.source == "llm"
        assert not response.escalate_to_human


@pytest.mark.asyncio
async def test_kb_escalation_detection(engine):
    """Test escalation detection from knowledge base"""
    # Mock similarity service response with escalation=True
    mock_best_match = KnowledgeBestMatch(
        entry=KnowledgeEntry(
            id="kb001",
            question="System error 500",
            answer="This is a server error that requires technical support.",
            escalation=True
        ),
        similarity_score=0.9,
        confidence=0.8
    )
    
    with patch.object(engine, '_find_best_match', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_best_match
        
        request = HelpdeskRequest(question="I'm getting error 500")
        response = await engine.process_question(request)
        
        assert response.source == "kb"
        assert response.escalate_to_human is True


@pytest.mark.asyncio
async def test_always_call_llm_behavior(config_manager):
    """Test ALWAYS_CALL_LLM environment variable behavior"""
    import os
    
    # Mock high confidence KB match
    mock_best_match = KnowledgeBestMatch(
        entry=KnowledgeEntry(
            id="kb001",
            question="How do I register a new job?",
            answer="Go to Jobs - Activities, click 'New Job', fill in the main details and save.",
            escalation=False
        ),
        similarity_score=0.9,
        confidence=0.8  # High confidence
    )
    
    # Test 1: Without ALWAYS_CALL_LLM - should use KB
    os.environ.pop("ALWAYS_CALL_LLM", None)
    with patch('orchestrator.engine.ConfigManager', return_value=config_manager):
        engine1 = HelpdeskEngine()
        
        with patch.object(engine1, '_find_best_match', new_callable=AsyncMock) as mock_find1:
            mock_find1.return_value = mock_best_match
            
            request = HelpdeskRequest(question="How do I register a new job?")
            response1 = await engine1.process_question(request)
            
            assert response1.source == "kb"
            assert "New Job" in response1.answer
    
    # Test 2: With ALWAYS_CALL_LLM=true - should call LLM even with high confidence
    os.environ["ALWAYS_CALL_LLM"] = "true"
    with patch('orchestrator.engine.ConfigManager', return_value=config_manager):
        engine2 = HelpdeskEngine()
        
        mock_llm_response = HelpdeskResponse(
            answer="I can help you register a new job using the system.",
            source="llm"
        )
        
        with patch.object(engine2, '_find_best_match', new_callable=AsyncMock) as mock_find2, \
             patch.object(engine2, '_get_llm_response', new_callable=AsyncMock) as mock_llm2:
            mock_find2.return_value = mock_best_match
            mock_llm2.return_value = mock_llm_response
            
            request = HelpdeskRequest(question="How do I register a new job?")
            response2 = await engine2.process_question(request)
            
            assert response2.source == "llm"
            assert "help you register" in response2.answer
            mock_llm2.assert_called_once()
    
    # Cleanup
    os.environ.pop("ALWAYS_CALL_LLM", None)


@pytest.mark.asyncio  
async def test_escalation_detection(engine):
    """Test escalation phrase detection"""
    # Test phrase detection
    assert engine._should_escalate("Please contact support for help")
    assert engine._should_escalate("You need to CONTACT SUPPORT")
    assert not engine._should_escalate("I can help you with that")


def test_helpdesk_request_validation():
    """Test request validation"""
    # Valid request
    request = HelpdeskRequest(question="How do I reset my password?")
    assert request.question == "How do I reset my password?"
    
    # Invalid request - empty question
    with pytest.raises(ValueError):
        HelpdeskRequest(question="")
    
    with pytest.raises(ValueError):
        HelpdeskRequest(question="   ")


def test_helpdesk_response_serialization():
    """Test response serialization"""
    response = HelpdeskResponse(
        answer="Test answer",
        source="kb",
        confidence=0.8,
        escalate_to_human=False
    )
    
    result = response.to_dict()
    
    assert result == {
        'answer': 'Test answer',
        'source': 'kb', 
        'confidence': 0.8,
        'escalate_to_human': False
    }