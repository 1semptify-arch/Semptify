"""
Fix Vertex AI session ID collision by ensuring unique session IDs.
This addresses the "Session with user-provided ID already exists" error.
"""

import secrets
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_unique_session_id() -> str:
    """
    Generate a truly unique session ID for Vertex AI to avoid collisions.
    
    The error occurs because the same session ID is being reused.
    This function combines timestamp and random components to ensure uniqueness.
    """
    # Get current timestamp in microseconds
    timestamp = int(time.time() * 1000000)
    
    # Generate random component
    random_part = secrets.token_hex(8)
    
    # Combine to create unique ID
    session_id = f"{timestamp}-{random_part}"
    
    logger.info(f"Generated unique session ID: {session_id}")
    return session_id

def patch_vertex_session_creation():
    """
    Monkey-patch any Vertex AI session creation to use unique IDs.
    This is a temporary fix until the root cause is identified.
    """
    try:
        # Import any potential Vertex AI modules
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        # Store original methods if they exist
        original_init = None
        if hasattr(GenerativeModel, '__init__'):
            original_init = GenerativeModel.__init__
            
        def patched_init(self, *args, **kwargs):
            # Add unique session ID if not present
            if 'session_id' not in kwargs:
                kwargs['session_id'] = generate_unique_session_id()
            
            return original_init(self, *args, **kwargs)
        
        # Apply patch
        if original_init:
            GenerativeModel.__init__ = patched_init
            logger.info("Applied Vertex AI session ID patch")
            
    except ImportError:
        logger.info("Vertex AI not available, no patch needed")
    except Exception as e:
        logger.error(f"Failed to patch Vertex AI: {e}")

# Apply the patch immediately when imported
patch_vertex_session_creation()
