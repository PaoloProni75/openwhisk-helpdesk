"""
Configuration management for orchestrator
"""
import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SimilarityConfig:
    """Configuration for similarity service"""
    threshold: float = 0.7
    algorithm: str = "cosine"
    endpoint_url: str = "http://localhost:3001"


@dataclass
class OllamaConfig:
    """Configuration for Ollama LLM"""
    endpoint_url: str = "http://localhost:11434"
    model: str = "llama2"
    temperature: float = 0.1
    max_tokens: int = 500
    timeout: int = 30


@dataclass
class PromptsConfig:
    """Configuration for prompts"""
    system_prompt: str = "You are a helpful customer service assistant."
    escalation_phrases: list = None
    
    def __post_init__(self):
        if self.escalation_phrases is None:
            self.escalation_phrases = ["contact support", "speak to human"]


@dataclass
class AppConfig:
    """Main application configuration"""
    similarity: SimilarityConfig
    ollama: OllamaConfig
    prompts: PromptsConfig
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'AppConfig':
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            similarity=SimilarityConfig(**data.get('similarity', {})),
            ollama=OllamaConfig(**data.get('ollama', {})),
            prompts=PromptsConfig(**data.get('prompts', {}))
        )


class ConfigManager:
    """Singleton configuration manager"""
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """Load configuration from file or environment"""
        if self._config is not None:
            return self._config
            
        if config_path is None:
            config_path = os.getenv('APP_CONFIG_PATH', 'config/helpdesk-config.yaml')
        
        self._config = AppConfig.from_yaml(config_path)
        return self._config
    
    @property
    def config(self) -> AppConfig:
        """Get current configuration"""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config