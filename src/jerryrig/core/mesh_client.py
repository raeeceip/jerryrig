"""
Mesh Client for interacting with the Solace Agent Mesh
"""

import requests
import time
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MeshClient:
    """Client for interacting with the agent mesh"""
    
    def __init__(self, mesh_url: str = "http://localhost:8000"):
        self.mesh_url = mesh_url.rstrip('/')
        self.session = requests.Session()
    
    def submit_migration_request(self, repository_url: str, target_language: str, **options) -> str:
        """Submit a migration request to the mesh"""
        
        request_data = {
            'repository_url': repository_url,
            'target_language': target_language,
            'operation_type': 'migration',
            **options
        }
        
        try:
            response = self.session.post(
                f"{self.mesh_url}/migrate",
                json=request_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            request_id = result.get('request_id')
            
            if not request_id:
                raise Exception("No request ID returned from mesh")
            
            logger.info(f"Migration request submitted: {request_id}")
            return request_id
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to submit request to mesh: {e}")
    
    def submit_analysis_request(self, repository_url: str, **options) -> str:
        """Submit an analysis request to the mesh"""
        
        request_data = {
            'repository_url': repository_url,
            'operation_type': 'analysis',
            **options
        }
        
        try:
            response = self.session.post(
                f"{self.mesh_url}/analyze",
                json=request_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            request_id = result.get('request_id')
            
            if not request_id:
                raise Exception("No request ID returned from mesh")
            
            logger.info(f"Analysis request submitted: {request_id}")
            return request_id
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to submit request to mesh: {e}")
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get the status of a request"""
        
        try:
            response = self.session.get(
                f"{self.mesh_url}/status/{request_id}",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get request status: {e}")
    
    def monitor_migration_progress(self, request_id: str, timeout: int = 1800) -> Dict[str, Any]:
        """Monitor migration progress until completion"""
        
        start_time = time.time()
        last_status = None
        
        logger.info(f"Monitoring migration progress: {request_id}")
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_request_status(request_id)
                current_status = status.get('status', 'unknown')
                
                # Log status changes
                if current_status != last_status:
                    logger.info(f"Status update: {current_status}")
                    last_status = current_status
                
                # Check if completed
                if current_status in ['completed', 'failed', 'error']:
                    return status
                
                # Wait before next check
                time.sleep(5)
                
            except Exception as e:
                logger.warning(f"Error checking status: {e}")
                time.sleep(10)
        
        raise Exception(f"Migration timed out after {timeout} seconds")
    
    def download_migration_results(self, request_id: str, output_dir: str) -> str:
        """Download migration results"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get download URL
            response = self.session.get(
                f"{self.mesh_url}/download/{request_id}",
                timeout=60
            )
            response.raise_for_status()
            
            # Save the downloaded file
            filename = f"migration_results_{request_id}.zip"
            file_path = output_path / filename
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded migration results to: {file_path}")
            return str(file_path)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download results: {e}")
    
    def get_mesh_status(self) -> Dict[str, Any]:
        """Get the overall status of the mesh"""
        
        try:
            response = self.session.get(
                f"{self.mesh_url}/status",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get mesh status: {e}")
    
    def list_active_requests(self) -> List[Dict[str, Any]]:
        """List all active requests in the mesh"""
        
        try:
            response = self.session.get(
                f"{self.mesh_url}/requests",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json().get('requests', [])
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to list requests: {e}")
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel an active request"""
        
        try:
            response = self.session.delete(
                f"{self.mesh_url}/requests/{request_id}",
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('cancelled', False)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel request: {e}")
            return False
    
    def wait_for_mesh(self, timeout: int = 60) -> bool:
        """Wait for the mesh to become available"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_mesh_status()
                if status.get('status') == 'running':
                    logger.info("Mesh is available")
                    return True
            except Exception:
                pass
            
            time.sleep(2)
        
        logger.error(f"Mesh did not become available within {timeout} seconds")
        return False