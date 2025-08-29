# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/test_orchestrator.py
pytest tests/test_similarity.py
pytest tests/test_ollama.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy .
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Test individual modules locally
python orchestrator/main.py
python similarity/main.py
python ollama/main.py

# Or use console scripts from setup.py
test-orchestrator
test-similarity
test-ollama
```

### OpenWhisk Deployment
```bash
# Deploy individual actions
wsk action create helpdesk-orchestrator orchestrator/main.py --kind python:3.9
wsk action create helpdesk-similarity similarity/main.py --kind python:3.9
wsk action create helpdesk-ollama ollama/main.py --kind python:3.9

# Deploy as package
wsk package create helpdesk
wsk action create helpdesk/orchestrator orchestrator/main.py --kind python:3.9
wsk action create helpdesk/similarity similarity/main.py --kind python:3.9
wsk action create helpdesk/ollama ollama/main.py --kind python:3.9

# Test deployed actions
wsk action invoke helpdesk/orchestrator -p question "How do I reset my password?"
```

## Architecture Overview

### Microservices Design
This is an OpenWhisk-based helpdesk system with three independent services:

1. **Orchestrator** (`orchestrator/`) - Main coordination service that manages request flow
2. **Similarity** (`similarity/`) - Text similarity matching against knowledge base using cosine similarity
3. **Ollama** (`ollama/`) - LLM service integration with OpenAI-compatible API

### Request Flow
1. User question → Orchestrator (`orchestrator/main.py`)
2. Orchestrator → Similarity service to find KB matches
3. If confidence < threshold → Orchestrator → Ollama LLM service
4. Response processing checks for escalation phrases
5. Structured response returned to user

### Key Components
- **Models**: Each service has its own models in `models/` directories
- **Configuration**: Centralized YAML config in `config/helpdesk-config.yaml`
- **Async Architecture**: Full async/await implementation using `aiohttp`
- **Knowledge Base**: JSON file at `config/knowledge-base.json`

### Service Communication
- Services communicate via HTTP (service-to-service calls from orchestrator)
- Orchestrator acts as API gateway, similarity and ollama services are called internally
- Each service has OpenWhisk action entry point at `main.py`

### Configuration Management
- Main config: `config/helpdesk-config.yaml`
- Test config: `config/test-config.yaml`
- Knowledge base: `config/knowledge-base.json`
- ConfigManager class loads and validates YAML configuration

### Testing Strategy
- Unit tests for each service in `tests/`
- Async test support with `pytest-asyncio`
- Mock-based testing for external service calls
- Coverage reporting available

## Development Notes

### Module Structure
Each service follows the same pattern:
- `main.py` - OpenWhisk action entry point
- `models/` - Data models specific to the service
- Service-specific logic in separate modules (e.g., `engine.py`, `service.py`, `client.py`)

### Dependencies
- Core: `aiohttp`, `PyYAML`
- Testing: `pytest`, `pytest-asyncio`, `pytest-mock`
- Code quality: `black`, `flake8`, `mypy`

### Error Handling
- Graceful degradation with fallback responses
- Timeout management for external calls
- Input validation on all user inputs
- Sanitized error messages (no sensitive data exposure)