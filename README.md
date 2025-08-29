# OpenWhisk Helpdesk

A modular helpdesk backend system built for OpenWhisk with Python, designed to provide AI-powered support responses using Ollama LLM. The system uses a microservices architecture with three independent modules.

## Architecture

The system consists of three OpenWhisk actions:

1. **Orchestrator** - Main coordination service that manages the request flow
2. **Similarity** - Text similarity service for knowledge base matching  
3. **Ollama** - LLM service integration for AI-powered responses

## Project Structure

```
openwhisk-helpdesk/
├── orchestrator/           # Main orchestration service
│   ├── main.py            # OpenWhisk action entry point
│   ├── engine.py          # Core helpdesk logic
│   ├── config.py          # Configuration management
│   └── models/            # Data models
├── similarity/            # Text similarity service
│   ├── main.py           # OpenWhisk action entry point
│   ├── service.py        # Similarity service implementation
│   ├── algorithms.py     # Cosine similarity algorithm
│   └── models.py         # Similarity models
├── ollama/               # Ollama LLM integration
│   ├── main.py          # OpenWhisk action entry point
│   ├── client.py        # Ollama API client
│   ├── models.py        # LLM models
│   └── exceptions.py    # Custom exceptions
├── config/              # Configuration files
├── tests/              # Test suite
└── requirements.txt    # Python dependencies
```

## Features

- **Modular Design**: Three independent microservices
- **Knowledge Base Matching**: Cosine similarity algorithm for question matching
- **LLM Integration**: Ollama support with OpenAI-compatible API
- **Configurable Thresholds**: Customizable confidence levels
- **Escalation Detection**: Automatic detection of requests requiring human intervention
- **Async Processing**: Full async/await support for performance
- **Comprehensive Testing**: Unit tests for all modules

## Setup

### Prerequisites

- Python 3.9+
- OpenWhisk CLI
- Ollama service running (for LLM functionality)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the system:
   ```bash
   cp config/helpdesk-config.yaml config/my-config.yaml
   # Edit config/my-config.yaml with your settings
   ```

### Configuration

Edit `config/helpdesk-config.yaml`:

```yaml
# Ollama Configuration
ollama:
  endpoint_url: "http://localhost:11434"
  model: "llama2"
  temperature: 0.1
  max_tokens: 500

# Similarity Configuration  
similarity:
  threshold: 0.7
  algorithm: "cosine"

# Prompts Configuration
prompts:
  escalation_phrases:
    - "contact support"
    - "speak to human"
```

## Deployment to OpenWhisk

### Deploy Individual Actions

```bash
# Deploy orchestrator
wsk action create helpdesk-orchestrator orchestrator/main.py --kind python:3.9

# Deploy similarity service
wsk action create helpdesk-similarity similarity/main.py --kind python:3.9

# Deploy Ollama service  
wsk action create helpdesk-ollama ollama/main.py --kind python:3.9
```

### Deploy as Package

```bash
# Create package
wsk package create helpdesk

# Deploy actions to package
wsk action create helpdesk/orchestrator orchestrator/main.py --kind python:3.9
wsk action create helpdesk/similarity similarity/main.py --kind python:3.9  
wsk action create helpdesk/ollama ollama/main.py --kind python:3.9
```

## Usage

### Orchestrator Service

Main entry point for helpdesk requests:

```bash
wsk action invoke helpdesk/orchestrator -p question "How do I reset my password?"
```

Expected response:
```json
{
  "answer": "To reset your password, go to the login page...",
  "source": "kb",
  "confidence": 0.85,
  "escalate_to_human": false
}
```

### Similarity Service  

Direct similarity matching:

```bash
wsk action invoke helpdesk/similarity -p question "How can I reset my password?" -p threshold 0.7
```

### Ollama Service

Direct LLM interaction:

```bash
wsk action invoke helpdesk/ollama -p question "How do I reset my password?" -p model "llama2"
```

## Request Flow

1. **User Question** → Orchestrator receives request
2. **Knowledge Base Search** → Orchestrator calls Similarity service
3. **Decision Logic**:
   - If similarity confidence ≥ threshold → Return KB answer
   - If similarity confidence < threshold → Call Ollama LLM
4. **Response Processing** → Check for escalation phrases
5. **Final Response** → Return structured response to user

## Development

### Running Tests

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

### Local Testing

Each module can be tested locally:

```bash
# Test orchestrator
python orchestrator/main.py

# Test similarity  
python similarity/main.py

# Test Ollama
python ollama/main.py
```

### Adding New Knowledge

Edit `config/knowledge-base.json` to add new questions and answers:

```json
{
  "id": "kb009",
  "question": "How do I schedule maintenance?",
  "answer": "Maintenance can be scheduled through...",
  "category": "Equipment",
  "tags": ["maintenance", "schedule"]
}
```

## Configuration Options

### Ollama Configuration

- `endpoint_url`: Ollama service URL
- `model`: Model to use (llama2, mistral, etc.)
- `temperature`: Response randomness (0.0-1.0)
- `max_tokens`: Maximum response length
- `timeout`: Request timeout in seconds

### Similarity Configuration

- `threshold`: Confidence threshold for KB answers (0.0-1.0)
- `algorithm`: Similarity algorithm ("cosine")
- `endpoint_url`: Similarity service URL (for microservice communication)

### Prompts Configuration

- `system_prompt`: System prompt for LLM
- `escalation_phrases`: Phrases that trigger human escalation

## Performance Considerations

- **Async Operations**: All network calls use async/await
- **Connection Pooling**: HTTP clients use connection pooling
- **Timeout Management**: Configurable timeouts prevent hanging requests
- **Error Handling**: Graceful degradation with fallback responses
- **Memory Efficiency**: Minimal memory footprint for serverless deployment

## Security

- Input validation on all user inputs
- No sensitive data logging
- Configurable timeout limits
- Error message sanitization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License