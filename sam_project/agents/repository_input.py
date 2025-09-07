"""
Repository Input Agent for Solace Agent Mesh
Handles incoming repository analysis and migration requests
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

def process(input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Process incoming repository requests and validate them
    
    Args:
        input_data: Input data containing repository request
        **kwargs: Additional configuration
        
    Returns:
        Validated and enriched repository request
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Extract request from input
        if 'request' not in input_data:
            raise ValueError("No request found in input data")
        
        request = input_data['request']
        
        # Validate required fields
        required_fields = ['repository_url', 'target_language']
        for field in required_fields:
            if field not in request:
                raise ValueError(f"Missing required field: {field}")
        
        # Enrich request with metadata
        enriched_request = {
            **request,
            'correlation_id': request.get('correlation_id', f"req_{int(time.time())}"),
            'timestamp': datetime.now().isoformat(),
            'status': 'received',
            'processing_steps': []
        }
        
        # Determine operation type
        operation_type = 'migration' if 'target_language' in request else 'analysis'
        enriched_request['operation_type'] = operation_type
        
        # Auto-detect source language if not provided
        if 'source_language' not in enriched_request:
            enriched_request['source_language'] = 'auto-detect'
        
        # Set default options
        default_options = {
            'preserve_structure': True,
            'include_tests': True,
            'include_docs': False,
            'chunk_size': 50,
            'max_file_size': 1048576
        }
        
        if 'options' not in enriched_request:
            enriched_request['options'] = default_options
        else:
            # Merge with defaults
            enriched_request['options'] = {**default_options, **enriched_request['options']}
        
        logger.info(f"Processed {operation_type} request for {request['repository_url']}")
        
        return {
            'request': enriched_request,
            'operation_type': operation_type,
            'status': 'validated'
        }
        
    except Exception as e:
        logger.error(f"Failed to process repository input: {e}")
        return {
            'request': input_data.get('request', {}),
            'error': str(e),
            'status': 'failed'
        }

# Required imports for the agent
import time
from datetime import datetime