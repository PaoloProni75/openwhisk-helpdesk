"""
Custom exceptions for Ollama client
"""


class OllamaException(Exception):
    """Base exception for Ollama client"""
    pass


class OllamaConnectionError(OllamaException):
    """Exception raised when connection to Ollama fails"""
    pass


class OllamaTimeoutError(OllamaException):
    """Exception raised when request to Ollama times out"""
    pass


class OllamaModelError(OllamaException):
    """Exception raised when there's an issue with the model"""
    pass


class OllamaInvalidRequestError(OllamaException):
    """Exception raised when request format is invalid"""
    pass