"""
OpenWhisk action entry point for similarity service
"""
import json
from models import SimilarityRequest
from service import SimilarityService


def main(args):
    """
    OpenWhisk action entry point for similarity service
    Expected input: {"question": "user question", "threshold": 0.7, "algorithm": "cosine"}
    """
    try:
        # Parse request
        question = args.get('question')
        if not question:
            return {
                'error': 'Missing required parameter: question'
            }
        
        # Get optional parameters
        threshold = args.get('threshold', 0.7)
        algorithm = args.get('algorithm', 'cosine')
        
        # Create request
        request = SimilarityRequest(question=question)
        
        # Process similarity search
        service = SimilarityService(threshold=threshold, algorithm=algorithm)
        response = service.find_similar(request)
        
        return response.to_dict()
        
    except ValueError as e:
        return {
            'error': f'Invalid request: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Internal server error: {str(e)}'
        }