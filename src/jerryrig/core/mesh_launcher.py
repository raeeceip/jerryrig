"""
Mesh Launcher for Solace Agent Mesh
Manages the lifecycle of the agent mesh
"""

import os
import sys
import subprocess
import time
import signal
import threading
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import logging

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MeshLauncher:
    """Launches and manages the Solace Agent Mesh"""
    
    def __init__(self, config_path: str, web_port: int = 8000):
        self.config_path = config_path
        self.web_port = web_port
        self.processes = []
        self.config = self._load_config()
        self._setup_signal_handlers()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load SAM configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Failed to load config from {self.config_path}: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping mesh...")
        self.stop_mesh()
        sys.exit(0)
    
    def start_mesh(self):
        """Start the agent mesh"""
        logger.info("Starting Solace Agent Mesh...")
        
        try:
            # Check if Solace Agent Mesh is available
            self._check_sam_availability()
            
            # Start Solace broker (if configured)
            self._start_broker()
            
            # Start the mesh using the configuration
            self._start_sam_mesh()
            
            # Start web interface
            self._start_web_interface()
            
            # Keep the mesh running
            self._monitor_mesh()
            
        except Exception as e:
            logger.error(f"Failed to start mesh: {e}")
            self.stop_mesh()
            raise
    
    def _check_sam_availability(self):
        """Check if Solace Agent Mesh is available"""
        try:
            import solace_agent_mesh
            logger.info("Solace Agent Mesh is available")
        except ImportError:
            logger.warning("Solace Agent Mesh not available, using simulation mode")
            # In simulation mode, we'll start our custom agents
    
    def _start_broker(self):
        """Start Solace broker if needed"""
        solace_config = self.config.get('solace', {})
        broker_url = solace_config.get('broker_url', 'tcp://localhost:55555')
        
        # For development, we can skip starting an actual broker
        # In production, this would start/connect to a Solace PubSub+ broker
        logger.info(f"Using Solace broker at: {broker_url}")
    
    def _start_sam_mesh(self):
        """Start the SAM mesh using the SAM CLI"""
        try:
            # Use the SAM CLI to start the mesh
            sam_process = self._start_sam_cli()
            if sam_process:
                self.processes.append(sam_process)
                logger.info("Started Solace Agent Mesh via SAM CLI")
                return
        except Exception as e:
            logger.warning(f"Could not start SAM CLI: {e}")
        
        # Fallback: Start our coordinator agent
        logger.info("Starting JerryRig mesh coordinator...")
        self._start_coordinator_agent()
    
    def _start_sam_cli(self) -> Optional[subprocess.Popen]:
        """Try to start the SAM CLI"""
        try:
            # Check if sam CLI is available
            result = subprocess.run(['sam', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning("SAM CLI not found")
                return None
            
            logger.info(f"Found SAM CLI: {result.stdout.strip()}")
            
            # Start SAM with our configuration
            sam_dir = Path(self.config_path).parent
            logger.info(f"Starting SAM in directory: {sam_dir}")
            
            process = subprocess.Popen(
                ['sam', 'run', '-c', self.config_path],
                cwd=sam_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                logger.info("SAM CLI mesh started successfully")
                return process
            else:
                stdout, stderr = process.communicate()
                logger.error(f"SAM CLI failed to start: {stderr}")
                return None
            
        except FileNotFoundError:
            logger.warning("SAM CLI executable not found")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("SAM CLI version check timed out")
            return None
        except Exception as e:
            logger.warning(f"Error starting SAM CLI: {e}")
            return None
    
    def _start_coordinator_agent(self):
        """Start our coordinator agent"""
        # Start the coordinator agent in a separate thread
        agent_thread = threading.Thread(
            target=self._run_mesh_agent,
            daemon=True
        )
        agent_thread.start()
        
        logger.info("Started JerryRig mesh coordinator")
    
    def _run_mesh_agent(self):
        """Run the mesh agent in async loop"""
        from ..agents.event_mesh_agent import JerryRigEventMeshAgent
        
        async def run_agent():
            agent = JerryRigEventMeshAgent(self.config_path)
            await agent.start_agent()
            
            # Keep the agent running
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                await agent.stop_agent()
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(run_agent())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    
    def _start_web_interface(self):
        """Start the web interface for the mesh"""
        try:
            # Try to start a simple web interface for migration requests
            web_thread = threading.Thread(
                target=self._run_web_server,
                daemon=True
            )
            web_thread.start()
            
            logger.info(f"Web interface started at http://localhost:{self.web_port}")
            
        except Exception as e:
            logger.warning(f"Could not start web interface: {e}")
    
    def _run_web_server(self):
        """Run a simple web server for the mesh interface"""
        try:
            from http.server import HTTPServer, SimpleHTTPRequestHandler
            import json
            
            class MeshHandler(SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        
                        html = self._get_mesh_interface_html()
                        self.wfile.write(html.encode())
                    elif self.path == '/status':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        
                        status = {'status': 'running', 'agents': ['jerryrig-mesh']}
                        self.wfile.write(json.dumps(status).encode())
                    else:
                        super().do_GET()
                
                def do_POST(self):
                    if self.path == '/migrate':
                        # Handle migration request
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        
                        try:
                            request_data = json.loads(post_data.decode())
                            response = self._handle_migration_request(request_data)
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(response).encode())
                            
                        except Exception as e:
                            self.send_response(500)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            error_response = {'error': str(e)}
                            self.wfile.write(json.dumps(error_response).encode())
                
                def _get_mesh_interface_html(self):
                    return '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>JerryRig Agent Mesh</title>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 40px; }
                            .container { max-width: 800px; margin: 0 auto; }
                            .form-group { margin: 20px 0; }
                            label { display: block; margin-bottom: 5px; font-weight: bold; }
                            input, select { width: 100%; padding: 10px; margin-bottom: 10px; }
                            button { background: #007cba; color: white; padding: 12px 24px; border: none; cursor: pointer; }
                            button:hover { background: #005a8a; }
                            .status { margin-top: 20px; padding: 15px; border-radius: 5px; }
                            .success { background: #d4edda; color: #155724; }
                            .error { background: #f8d7da; color: #721c24; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>🕸️ JerryRig Agent Mesh</h1>
                            <p>Submit repository migration requests to the distributed agent mesh.</p>
                            
                            <form id="migrationForm">
                                <div class="form-group">
                                    <label for="repo_url">Repository URL:</label>
                                    <input type="url" id="repo_url" name="repo_url" required 
                                           placeholder="https://github.com/user/repository">
                                </div>
                                
                                <div class="form-group">
                                    <label for="target_language">Target Language:</label>
                                    <select id="target_language" name="target_language" required>
                                        <option value="">Select target language</option>
                                        <option value="python">Python</option>
                                        <option value="javascript">JavaScript</option>
                                        <option value="typescript">TypeScript</option>
                                        <option value="java">Java</option>
                                        <option value="go">Go</option>
                                        <option value="rust">Rust</option>
                                    </select>
                                </div>
                                
                                <button type="submit">🚀 Start Migration</button>
                            </form>
                            
                            <div id="status"></div>
                        </div>
                        
                        <script>
                            document.getElementById('migrationForm').addEventListener('submit', async function(e) {
                                e.preventDefault();
                                
                                const formData = new FormData(e.target);
                                const request = {
                                    repository_url: formData.get('repo_url'),
                                    target_language: formData.get('target_language')
                                };
                                
                                const statusDiv = document.getElementById('status');
                                statusDiv.innerHTML = '<div class="status">⏳ Submitting migration request...</div>';
                                
                                try {
                                    const response = await fetch('/migrate', {
                                        method: 'POST',
                                        headers: {'Content-Type': 'application/json'},
                                        body: JSON.stringify(request)
                                    });
                                    
                                    const result = await response.json();
                                    
                                    if (response.ok) {
                                        statusDiv.innerHTML = `
                                            <div class="status success">
                                                ✅ Migration request submitted successfully!<br>
                                                Request ID: ${result.request_id}<br>
                                                Status: ${result.status}
                                            </div>
                                        `;
                                    } else {
                                        statusDiv.innerHTML = `<div class="status error">❌ Error: ${result.error}</div>`;
                                    }
                                } catch (error) {
                                    statusDiv.innerHTML = `<div class="status error">❌ Network error: ${error.message}</div>`;
                                }
                            });
                        </script>
                    </body>
                    </html>
                    '''
                
                def _handle_migration_request(self, request_data):
                    """Handle incoming migration request"""
                    import uuid
                    
                    request_id = str(uuid.uuid4())
                    
                    # In a real implementation, this would submit to the agent mesh
                    # For now, return a success response
                    return {
                        'request_id': request_id,
                        'status': 'submitted',
                        'message': 'Migration request submitted to agent mesh',
                        'repository_url': request_data.get('repository_url'),
                        'target_language': request_data.get('target_language')
                    }
            
            server = HTTPServer(('localhost', self.web_port), MeshHandler)
            server.serve_forever()
            
        except Exception as e:
            logger.error(f"Web server error: {e}")
    
    def _monitor_mesh(self):
        """Monitor the mesh and keep it running"""
        logger.info("Agent mesh is running. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
                
                # Check if any processes have died
                for process in self.processes:
                    if process.poll() is not None:
                        logger.warning("A mesh process has stopped")
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_mesh()
    
    def stop_mesh(self):
        """Stop the agent mesh"""
        logger.info("Stopping agent mesh...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
        
        logger.info("Agent mesh stopped")