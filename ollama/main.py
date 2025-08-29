"""
OpenWhisk action entry point for Ollama service
"""
import json
import os
import sys

# Add libs directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

import yaml


def load_config():
    """Load configuration from YAML file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'helpdesk-config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        # Fallback to defaults if config file not found
        return {
            'ollama': {
                'endpoint_url': 'http://172.31.17.101:11434',
                'model': 'nemotron-mini:latest',
                'temperature': 0.5,
                'max_tokens': 512,
                'timeout': 30
            }
        }


def main(args):
    """
    OpenWhisk action entry point - Using configuration file
    """
    try:
        # Load configuration
        config = load_config()
        ollama_config = config.get('ollama', {})
        
        question = args.get('question', 'test question')
        
        # Get configuration from YAML file
        base_url = ollama_config.get('endpoint_url', 'http://172.31.17.101:11434')
        model = ollama_config.get('model', 'mistral')
        temperature = ollama_config.get('temperature', 0.5)
        max_tokens = ollama_config.get('max_tokens', 512)
        timeout = ollama_config.get('timeout', 30)
        
        # Simple HTTP call without complex imports
        import urllib.request
        import urllib.parse
        
        url = f'{base_url}/v1/chat/completions'
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": question}
            ]
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode())
        
        answer = result['choices'][0]['message']['content']
        
        return {
            'question': question,
            'answer': answer,
            'model': model,
            'source': 'ollama'
        }
        
    except Exception as e:
        return {
            'error': f'Error: {str(e)}',
            'answer': 'Sorry, I encountered an error processing your request.'
        }


# Health check action
def health(args):
    """
    Health check action for Ollama service
    """
    try:
        config = load_config()
        ollama_config = config.get('ollama', {})
        base_url = args.get('base_url', ollama_config.get('endpoint_url', 'http://172.31.17.101:11434'))
        
        client = OllamaClient(base_url=base_url)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            is_healthy = loop.run_until_complete(client.health_check())
        finally:
            loop.close()
        
        return {
            'healthy': is_healthy,
            'service': 'ollama',
            'base_url': base_url
        }
    except Exception as e:
        return {
            'healthy': False,
            'service': 'ollama',
            'error': str(e)
        }