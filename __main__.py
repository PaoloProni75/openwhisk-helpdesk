"""
OpenWhisk entry point that delegates to orchestrator
"""
import sys
import os

# Add libs directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

from orchestrator.main import main

# Export main function for OpenWhisk
__all__ = ['main']