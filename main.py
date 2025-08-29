"""
OpenWhisk action entry point for orchestrator
"""
import json
import asyncio
from .models.request import HelpdeskRequest
from .engine import HelpdeskEngine
from .config import ConfigManager


def main(args):
    """
    OpenWhisk action entry point
    Expected input: {"question": "user question", "session_id": "optional", "user_id": "optional"}
    """
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        config_manager.load_config()
        
        # Parse request
        question = args.get('question')
        if not question:
            return {
                'error': 'Missing required parameter: question'
            }
        
        request = HelpdeskRequest(
            question=question,
            session_id=args.get('session_id'),
            user_id=args.get('user_id')
        )
        
        # Process request
        engine = HelpdeskEngine()
        
        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(engine.process_question(request))
        finally:
            loop.close()
        
        return response.to_dict()
        
    except Exception as e:
        return {
            'error': f'Internal server error: {str(e)}',
            'answer': 'Sorry, I encountered an error processing your request.',
            'source': 'error',
            'escalate_to_human': True
        }


# For local testing
if __name__ == '__main__':
    import sys
    
    # Test input
    test_args = {
        'question': 'How do I reset my password?'
    }
    
    result = main(test_args)
    print(json.dumps(result, indent=2))