"""
OpenWhisk action entry point for orchestrator
"""
import json
from orchestrator.models.request import HelpdeskRequest
from orchestrator.engine import HelpdeskEngine
from orchestrator.config import ConfigManager


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
        engine = HelpdeskEngine(args)
        
        # Process request synchronously
        response = engine.process_question(request)
        
        return response.to_dict(question=request.question)
        
    except Exception as e:
        return {
            'error': f'Internal server error: {str(e)}',
            'answer': 'Sorry, I encountered an error processing your request.',
            'source': 'error',
            'escalate_to_human': True,
            'response_time_ms': 0
        }

    # """
    # OpenWhisk action entry point
    # Expected input: {"question": "user question", "session_id": "optional", "user_id": "optional"}
    # """
    # try:
    #     # Initialize configuration
    #     config_manager = ConfigManager()
    #     config_manager.load_config()
    #     
    #     # Parse request
    #     question = args.get('question')
    #     if not question:
    #         return {
    #             'error': 'Missing required parameter: question'
    #         }
    #     
    #     request = HelpdeskRequest(
    #         question=question,
    #         session_id=args.get('session_id'),
    #         user_id=args.get('user_id')
    #     )
    #     
    #     # Process request
    #     engine = HelpdeskEngine()
    #     
    #     # Run async processing
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     try:
    #         response = loop.run_until_complete(engine.process_question(request))
    #     finally:
    #         loop.close()
    #     
    #     return response.to_dict()
    #     
    # except Exception as e:
    #     return {
    #         'error': f'Internal server error: {str(e)}',
    #         'answer': 'Sorry, I encountered an error processing your request.',
    #         'source': 'error',
    #         'escalate_to_human': True
    #     }