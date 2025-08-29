"""
Tests for Ollama module
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from aiohttp import ClientResponse, ClientSession
from ollama.models import OllamaRequest, OllamaResponse, OllamaChatRequest, OllamaChatMessage
from ollama.client import OllamaClient
from ollama.exceptions import (
    OllamaConnectionError, 
    OllamaTimeoutError, 
    OllamaModelError, 
    OllamaInvalidRequestError
)


@pytest.fixture
def ollama_client():
    """Create Ollama client for testing"""
    return OllamaClient(
        base_url="http://localhost:11434",
        model="llama2",
        temperature=0.1,
        max_tokens=100,
        timeout=10
    )


class TestOllamaModels:
    """Test Ollama models"""
    
    def test_ollama_request_validation(self):
        """Test request validation"""
        # Valid request
        request = OllamaRequest(question="How do I reset my password?")
        assert request.question == "How do I reset my password?"
        assert request.context is None
        
        # Valid request with context
        request_with_context = OllamaRequest(
            question="Help me reset password",
            context="User account management"
        )
        assert request_with_context.context == "User account management"
        
        # Invalid request - empty question
        with pytest.raises(ValueError):
            OllamaRequest(question="")
        
        with pytest.raises(ValueError):
            OllamaRequest(question="   ")
    
    def test_ollama_response_serialization(self):
        """Test response serialization"""
        response = OllamaResponse(
            answer="To reset your password, go to login page.",
            model="llama2",
            tokens_used=25,
            processing_time=1.5
        )
        
        data = response.to_dict()
        
        assert data == {
            'answer': 'To reset your password, go to login page.',
            'model': 'llama2',
            'tokens_used': 25,
            'processing_time': 1.5
        }
    
    def test_chat_request_creation(self):
        """Test chat request creation"""
        messages = [
            OllamaChatMessage(role="system", content="You are helpful"),
            OllamaChatMessage(role="user", content="Hello")
        ]
        
        chat_request = OllamaChatRequest(
            model="llama2",
            messages=messages,
            temperature=0.1,
            max_tokens=100
        )
        
        data = chat_request.to_dict()
        
        assert data["model"] == "llama2"
        assert data["temperature"] == 0.1
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "system"
        assert data["options"]["num_predict"] == 100


class TestOllamaClient:
    """Test Ollama client"""
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, ollama_client):
        """Test successful response generation"""
        # Mock successful API response
        mock_response_data = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "To reset your password, visit the login page."
                }
            }],
            "model": "llama2"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            request = OllamaRequest(question="How do I reset my password?")
            response = await ollama_client.generate_response(request)
            
            assert response.answer == "To reset your password, visit the login page."
            assert response.model == "llama2"
            assert response.processing_time is not None
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, ollama_client):
        """Test response generation with context"""
        mock_response_data = {
            "choices": [{
                "message": {
                    "role": "assistant", 
                    "content": "Based on the context, here's how to reset your password."
                }
            }],
            "model": "llama2"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            request = OllamaRequest(
                question="How do I reset my password?",
                context="User is locked out of account"
            )
            response = await ollama_client.generate_response(request)
            
            assert "context" in response.answer.lower()
    
    @pytest.mark.asyncio
    async def test_generate_response_empty_question(self, ollama_client):
        """Test response generation with empty question"""
        with pytest.raises(ValueError):
            request = OllamaRequest(question="   ")
    
    @pytest.mark.asyncio
    async def test_generate_response_model_not_found(self, ollama_client):
        """Test response when model is not found"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_post.return_value.__aenter__.return_value = mock_response
            
            request = OllamaRequest(question="Test question")
            
            with pytest.raises(OllamaModelError):
                await ollama_client.generate_response(request)
    
    @pytest.mark.asyncio
    async def test_generate_response_invalid_request_format(self, ollama_client):
        """Test response with invalid request format"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value="Invalid request format")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            request = OllamaRequest(question="Test question")
            
            with pytest.raises(OllamaInvalidRequestError):
                await ollama_client.generate_response(request)
    
    @pytest.mark.asyncio
    async def test_generate_response_connection_error(self, ollama_client):
        """Test response when connection fails"""
        import aiohttp
        
        with patch('ollama.client.OllamaClient._call_chat_api') as mock_call:
            mock_call.side_effect = aiohttp.ClientError("Connection failed")
            
            request = OllamaRequest(question="Test question")
            
            with pytest.raises(OllamaConnectionError):
                await ollama_client.generate_response(request)
    
    @pytest.mark.asyncio
    async def test_generate_response_timeout(self, ollama_client):
        """Test response when request times out"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            request = OllamaRequest(question="Test question")
            
            with pytest.raises(OllamaTimeoutError):
                await ollama_client.generate_response(request)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, ollama_client):
        """Test health check when service is healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await ollama_client.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, ollama_client):
        """Test health check when service is unhealthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            is_healthy = await ollama_client.health_check()
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, ollama_client):
        """Test health check when connection fails"""
        from aiohttp import ClientError
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = ClientError()
            
            is_healthy = await ollama_client.health_check()
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_client):
        """Test listing models successfully"""
        mock_models_response = {
            "models": [
                {"name": "llama2:latest"},
                {"name": "mistral:latest"},
                {"name": "nemotron-mini:latest"}
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_models_response)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await ollama_client.list_models()
            
            assert len(models) == 3
            assert "llama2:latest" in models
            assert "mistral:latest" in models
    
    @pytest.mark.asyncio
    async def test_list_models_error(self, ollama_client):
        """Test listing models when API fails"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await ollama_client.list_models()
            assert models == []