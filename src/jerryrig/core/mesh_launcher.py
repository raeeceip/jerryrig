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
import json
import websockets
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import logging
from dotenv import load_dotenv

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MeshLauncher:
    """Launches and manages the Solace Agent Mesh"""
    
    def __init__(self, config_path: str, web_port: int = 8000, websocket_port: int = 8001):
        self.config_path = config_path
        self.web_port = web_port
        self.websocket_port = websocket_port
        self.processes = []
        self.sam_gateway = None
        self.config = self._load_config()
        self.environment = self._load_environment()
        self._setup_signal_handlers()
        
        # WebSocket for real-time status updates
        self.status_websocket_thread = None
        self.websocket_server = None
        self.websocket_clients = set()
    
    def _load_environment(self) -> Dict[str, Any]:
        """Load and validate environment variables for Solace Cloud"""
        # Load environment variables
        load_dotenv()
        
        # Validate required environment variables for Solace Cloud
        required_vars = ['SOLACE_API_KEY', 'OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info(f"Loaded environment variables for Solace Cloud: {required_vars}")
        
        return {
            'SOLACE_API_KEY': os.getenv('SOLACE_API_KEY'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'SOLACE_BASE_URL': os.getenv('SOLACE_BASE_URL', 'https://api.solace.dev'),
            'SOLACE_VPN_NAME': os.getenv('SOLACE_VPN_NAME', 'jerryrig-mesh'),
            'SOLACE_USERNAME': os.getenv('SOLACE_USERNAME', 'jerryrig-user'),
            'SOLACE_PASSWORD': os.getenv('SOLACE_PASSWORD', ''),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
        }
    
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
    
    def _start_websocket_server(self):
        """Start WebSocket server for real-time status updates"""
        try:
            async def handle_websocket(websocket, path):
                """Handle WebSocket connections"""
                self.websocket_clients.add(websocket)
                logger.info(f"WebSocket client connected from {websocket.remote_address}")
                
                try:
                    # Send initial status
                    await websocket.send(json.dumps({
                        "type": "connection_status",
                        "status": "connected",
                        "timestamp": time.time()
                    }))
                    
                    # Keep connection alive
                    await websocket.wait_closed()
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    self.websocket_clients.discard(websocket)
                    logger.info("WebSocket client disconnected")
            
            def run_websocket_server():
                """Run WebSocket server in event loop"""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                start_server = websockets.serve(
                    handle_websocket,
                    "localhost",
                    self.websocket_port
                )
                
                self.websocket_server = loop.run_until_complete(start_server)
                logger.info(f"WebSocket server started on ws://localhost:{self.websocket_port}")
                
                try:
                    loop.run_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    self.websocket_server.close()
                    loop.run_until_complete(self.websocket_server.wait_closed())
                    loop.close()
            
            # Start WebSocket server in separate thread
            self.status_websocket_thread = threading.Thread(
                target=run_websocket_server,
                daemon=True
            )
            self.status_websocket_thread.start()
            
            # Give server time to start
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
    
    def _broadcast_status(self, status_data: Dict[str, Any]):
        """Broadcast status update to all WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message = json.dumps(status_data)
        
        # Send to all connected clients
        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                asyncio.run(client.send(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                logger.warning(f"Error sending WebSocket message: {e}")
                disconnected_clients.append(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            self.websocket_clients.discard(client)
        sys.exit(0)
    
    def start_mesh(self):
        """Start the agent mesh with real-time WebSocket support"""
        logger.info("Starting Solace Agent Mesh...")
        
        try:
            # Start WebSocket server for real-time updates
            self._start_websocket_server()
            
            # Check if Solace Agent Mesh is available
            self._check_sam_availability()
            
            # Start Solace broker (if configured)
            self._start_broker()
            
            # Start the mesh using the configuration
            self._start_sam_mesh()
            
            # Start web interface
            self._start_web_interface()
            
            # Send status update via WebSocket
            self._broadcast_status({
                "type": "mesh_status",
                "status": "running",
                "gateway_active": self.sam_gateway is not None,
                "web_port": self.web_port,
                "websocket_port": self.websocket_port,
                "timestamp": time.time()
            })
            
            logger.info(f"WebSocket status updates: ws://localhost:{self.websocket_port}")
            
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
        """Configure connection to Solace Cloud broker"""
        solace_config = self.config.get('solace', {})
        
        if solace_config.get('broker_type') == 'solace_cloud':
            api_key = solace_config.get('api_key')
            base_url = solace_config.get('base_url', 'https://api.solace.dev')
            
            if api_key:
                logger.info(f"Using Solace Cloud at: {base_url}")
                logger.info("Solace Cloud broker configured with API key")
            else:
                logger.warning("Solace Cloud API key not found in configuration")
        else:
            broker_url = solace_config.get('broker_url', 'tcp://localhost:55555')
            logger.info(f"Using local Solace broker at: {broker_url}")
    
    def _start_sam_mesh(self):
        """Start the SAM mesh using Python API"""
        try:
            # Use the SAM Gateway API directly
            sam_gateway = self._start_sam_gateway()
            if sam_gateway:
                logger.info("Started Solace Agent Mesh via Python API")
                # Store the gateway for later cleanup
                self.sam_gateway = sam_gateway
                return
        except Exception as e:
            logger.warning(f"Could not start SAM Gateway: {e}")
        
        # Fallback: Start our coordinator agent
        logger.info("Starting JerryRig mesh coordinator...")
        self._start_coordinator_agent()
    
    def _start_sam_gateway(self):
        """Start the SAM Gateway using Solace Cloud"""
        try:
            from solace_agent_mesh.gateway import SAMGateway
            
            solace_config = self.config.get('solace', {})
            
            # Create gateway configuration for Solace Cloud
            gateway_config = {
                "gateway_id": "jerryrig-mesh-gateway",
                "solace_cloud": {
                    "api_key": solace_config.get('api_key'),
                    "base_url": solace_config.get('base_url', 'https://api.solace.dev')
                },
                "flows": self.config.get("flows", [])
            }
            
            logger.info("Initializing SAM Gateway with Solace Cloud...")
            gateway = SAMGateway(gateway_config)
            
            # Start the gateway in a separate thread
            gateway_thread = threading.Thread(
                target=self._run_sam_gateway,
                args=(gateway,),
                daemon=True
            )
            gateway_thread.start()
            
            logger.info("SAM Gateway started with Solace Cloud")
            return gateway
            
        except ImportError as e:
            logger.warning(f"SAM Gateway not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error starting SAM Gateway: {e}")
            return None
    
    def _run_sam_gateway(self, gateway):
        """Run the SAM Gateway"""
        try:
            # Start the gateway
            gateway.start()
            logger.info("SAM Gateway is running")
            
            # Keep it running
            while True:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"SAM Gateway error: {e}")
    
    
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
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>JerryRig Agent Mesh - Code Migration Platform</title>
                        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                        <style>
                            .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                            .card-hover { transition: all 0.3s ease; }
                            .card-hover:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
                            .pulse-animation { animation: pulse 2s infinite; }
                            @keyframes pulse {
                                0%, 100% { opacity: 1; }
                                50% { opacity: 0.5; }
                            }
                            .status-indicator {
                                width: 12px; height: 12px;
                                border-radius: 50%;
                                display: inline-block;
                                margin-right: 8px;
                            }
                            .status-online { background-color: #10b981; }
                            .status-processing { background-color: #f59e0b; }
                            .status-offline { background-color: #ef4444; }
                        </style>
                    </head>
                    <body class="bg-gray-50 min-h-screen">
                        <!-- Header -->
                        <nav class="gradient-bg text-white shadow-lg">
                            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                                <div class="flex justify-between items-center py-4">
                                    <div class="flex items-center space-x-3">
                                        <i class="fas fa-sitemap text-2xl"></i>
                                        <h1 class="text-2xl font-bold">JerryRig Agent Mesh</h1>
                                    </div>
                                    <div class="flex items-center space-x-4">
                                        <div class="flex items-center space-x-2">
                                            <span class="text-sm">Mesh:</span>
                                            <span id="meshStatus" class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">running</span>
                                        </div>
                                        <div class="flex items-center space-x-2">
                                            <span class="text-sm">WebSocket:</span>
                                            <span id="connectionStatus" class="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">connecting</span>
                                        </div>
                                        <button onclick="refreshStatus()" class="bg-white bg-opacity-20 hover:bg-opacity-30 px-3 py-2 rounded-lg transition-all">
                                            <i class="fas fa-sync-alt"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </nav>

                        <!-- Main Content -->
                        <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
                            <!-- Stats Cards -->
                            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                                <div class="bg-white rounded-xl shadow-md card-hover p-6">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0">
                                            <i class="fas fa-code-branch text-3xl text-blue-600"></i>
                                        </div>
                                        <div class="ml-4">
                                            <p class="text-sm font-medium text-gray-500">Active Agents</p>
                                            <p class="text-2xl font-semibold text-gray-900" id="activeAgents">6</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="bg-white rounded-xl shadow-md card-hover p-6">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0">
                                            <i class="fas fa-tasks text-3xl text-green-600"></i>
                                        </div>
                                        <div class="ml-4">
                                            <p class="text-sm font-medium text-gray-500">Migrations Today</p>
                                            <p class="text-2xl font-semibold text-gray-900" id="migrationsToday">42</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="bg-white rounded-xl shadow-md card-hover p-6">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0">
                                            <i class="fas fa-clock text-3xl text-yellow-600"></i>
                                        </div>
                                        <div class="ml-4">
                                            <p class="text-sm font-medium text-gray-500">Avg. Process Time</p>
                                            <p class="text-2xl font-semibold text-gray-900">2.3m</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="bg-white rounded-xl shadow-md card-hover p-6">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0">
                                            <i class="fas fa-check-circle text-3xl text-purple-600"></i>
                                        </div>
                                        <div class="ml-4">
                                            <p class="text-sm font-medium text-gray-500">Success Rate</p>
                                            <p class="text-2xl font-semibold text-gray-900">94.2%</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                <!-- Migration Form -->
                                <div class="bg-white rounded-xl shadow-lg card-hover p-8">
                                    <div class="flex items-center mb-6">
                                        <i class="fas fa-rocket text-2xl text-blue-600 mr-3"></i>
                                        <h2 class="text-2xl font-bold text-gray-900">Start Migration</h2>
                                    </div>
                                    
                                    <form id="migrationForm" class="space-y-6">
                                        <div>
                                            <label for="repo_url" class="block text-sm font-medium text-gray-700 mb-2">
                                                <i class="fab fa-github mr-2"></i>Repository URL
                                            </label>
                                            <input type="url" id="repo_url" name="repo_url" required 
                                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                                   placeholder="https://github.com/user/repository">
                                        </div>
                                        
                                        <div>
                                            <label for="target_language" class="block text-sm font-medium text-gray-700 mb-2">
                                                <i class="fas fa-code mr-2"></i>Target Language
                                            </label>
                                            <select id="target_language" name="target_language" required 
                                                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all">
                                                <option value="">Select target language</option>
                                                <option value="python">🐍 Python</option>
                                                <option value="javascript">🟨 JavaScript</option>
                                                <option value="typescript">🔷 TypeScript</option>
                                                <option value="java">☕ Java</option>
                                                <option value="go">🟢 Go</option>
                                                <option value="rust">🦀 Rust</option>
                                                <option value="cpp">⚡ C++</option>
                                                <option value="csharp">🔵 C#</option>
                                            </select>
                                        </div>
                                        
                                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label for="source_language" class="block text-sm font-medium text-gray-700 mb-2">
                                                    Source Language (Optional)
                                                </label>
                                                <select id="source_language" name="source_language" 
                                                        class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all">
                                                    <option value="">Auto-detect</option>
                                                    <option value="python">🐍 Python</option>
                                                    <option value="javascript">🟨 JavaScript</option>
                                                    <option value="typescript">🔷 TypeScript</option>
                                                    <option value="java">☕ Java</option>
                                                    <option value="go">🟢 Go</option>
                                                    <option value="rust">🦀 Rust</option>
                                                    <option value="cpp">⚡ C++</option>
                                                    <option value="csharp">🔵 C#</option>
                                                </select>
                                            </div>
                                            
                                            <div>
                                                <label for="priority" class="block text-sm font-medium text-gray-700 mb-2">
                                                    Priority
                                                </label>
                                                <select id="priority" name="priority" 
                                                        class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all">
                                                    <option value="normal">Normal</option>
                                                    <option value="high">High</option>
                                                    <option value="urgent">Urgent</option>
                                                </select>
                                            </div>
                                        </div>
                                        
                                        <button type="submit" 
                                                class="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-purple-700 transform hover:scale-105 transition-all duration-200 shadow-lg">
                                            <i class="fas fa-rocket mr-2"></i>
                                            Start Migration
                                        </button>
                                    </form>
                                </div>

                                <!-- Status Panel -->
                                <div class="bg-white rounded-xl shadow-lg card-hover p-8">
                                    <div class="flex items-center justify-between mb-6">
                                        <div class="flex items-center">
                                            <i class="fas fa-list-alt text-2xl text-green-600 mr-3"></i>
                                            <h2 class="text-2xl font-bold text-gray-900">Migration Status</h2>
                                        </div>
                                        <button onclick="clearStatus()" class="text-gray-400 hover:text-red-500 transition-colors">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                    
                                    <div id="status" class="space-y-4">
                                        <div class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
                                            <i class="fas fa-info-circle text-3xl mb-2"></i>
                                            <p>No active migrations</p>
                                            <p class="text-sm">Submit a repository to get started</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Recent Migrations -->
                            <div class="mt-8 bg-white rounded-xl shadow-lg card-hover p-8">
                                <div class="flex items-center justify-between mb-6">
                                    <div class="flex items-center">
                                        <i class="fas fa-history text-2xl text-indigo-600 mr-3"></i>
                                        <h2 class="text-2xl font-bold text-gray-900">Recent Migrations</h2>
                                    </div>
                                    <button onclick="refreshHistory()" class="text-indigo-600 hover:text-indigo-800 transition-colors">
                                        <i class="fas fa-sync-alt"></i>
                                    </button>
                                </div>
                                
                                <div class="overflow-x-auto">
                                    <table class="min-w-full divide-y divide-gray-200">
                                        <thead class="bg-gray-50">
                                            <tr>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Repository</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source → Target</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="migrationHistory" class="bg-white divide-y divide-gray-200">
                                            <!-- Dynamic content will be inserted here -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <script>
                            let migrationCount = 0;
                            let migrationHistory = [];
                            
                            document.getElementById('migrationForm').addEventListener('submit', async function(e) {
                                e.preventDefault();
                                
                                const formData = new FormData(e.target);
                                const request = {
                                    repository_url: formData.get('repo_url'),
                                    target_language: formData.get('target_language'),
                                    source_language: formData.get('source_language') || null,
                                    priority: formData.get('priority') || 'normal'
                                };
                                
                                updateStatus('submitting', 'Submitting migration request...', request);
                                
                                try {
                                    const response = await fetch('/migrate', {
                                        method: 'POST',
                                        headers: {'Content-Type': 'application/json'},
                                        body: JSON.stringify(request)
                                    });
                                    
                                    const result = await response.json();
                                    
                                    if (response.ok) {
                                        updateStatus('success', 'Migration request submitted successfully!', result);
                                        addToHistory(request, result, 'completed');
                                        updateStats();
                                    } else {
                                        updateStatus('error', `Error: ${result.error}`, result);
                                        addToHistory(request, result, 'failed');
                                    }
                                } catch (error) {
                                    updateStatus('error', `Network error: ${error.message}`, {error: error.message});
                                    addToHistory(request, {error: error.message}, 'failed');
                                }
                            });
                            
                            function updateStatus(type, message, data) {
                                const statusDiv = document.getElementById('status');
                                const timestamp = new Date().toLocaleTimeString();
                                
                                let iconClass, bgClass, textClass;
                                switch(type) {
                                    case 'submitting':
                                        iconClass = 'fas fa-spinner fa-spin';
                                        bgClass = 'bg-blue-50 border-blue-200';
                                        textClass = 'text-blue-800';
                                        break;
                                    case 'success':
                                        iconClass = 'fas fa-check-circle';
                                        bgClass = 'bg-green-50 border-green-200';
                                        textClass = 'text-green-800';
                                        break;
                                    case 'error':
                                        iconClass = 'fas fa-exclamation-triangle';
                                        bgClass = 'bg-red-50 border-red-200';
                                        textClass = 'text-red-800';
                                        break;
                                }
                                
                                statusDiv.innerHTML = `
                                    <div class="border-l-4 p-4 rounded-lg ${bgClass}">
                                        <div class="flex items-start">
                                            <div class="flex-shrink-0">
                                                <i class="${iconClass} text-xl ${textClass}"></i>
                                            </div>
                                            <div class="ml-3 flex-1">
                                                <p class="text-sm font-medium ${textClass}">${message}</p>
                                                <p class="text-xs ${textClass} opacity-75 mt-1">${timestamp}</p>
                                                ${data.request_id ? `<p class="text-xs ${textClass} opacity-75">Request ID: ${data.request_id}</p>` : ''}
                                            </div>
                                        </div>
                                    </div>
                                `;
                            }
                            
                            function addToHistory(request, result, status) {
                                migrationHistory.unshift({
                                    repository: request.repository_url,
                                    source: request.source_language || 'Auto',
                                    target: request.target_language,
                                    status: status,
                                    time: new Date().toLocaleString(),
                                    id: result.request_id || Date.now()
                                });
                                
                                if (migrationHistory.length > 10) {
                                    migrationHistory.pop();
                                }
                                
                                renderHistory();
                            }
                            
                            function renderHistory() {
                                const tbody = document.getElementById('migrationHistory');
                                tbody.innerHTML = migrationHistory.map(item => `
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="flex items-center">
                                                <i class="fab fa-github text-gray-400 mr-2"></i>
                                                <span class="text-sm text-gray-900">${item.repository.split('/').slice(-2).join('/')}</span>
                                            </div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            ${item.source} → ${item.target}
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                item.status === 'completed' ? 'bg-green-100 text-green-800' : 
                                                item.status === 'failed' ? 'bg-red-100 text-red-800' : 
                                                'bg-yellow-100 text-yellow-800'
                                            }">
                                                ${item.status}
                                            </span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            ${item.time}
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                            <button class="text-indigo-600 hover:text-indigo-900 mr-2">View</button>
                                            <button class="text-green-600 hover:text-green-900">Download</button>
                                        </td>
                                    </tr>
                                `).join('');
                            }
                            
                            function updateStats() {
                                migrationCount++;
                                document.getElementById('migrationsToday').textContent = migrationCount;
                            }
                            
                            function clearStatus() {
                                document.getElementById('status').innerHTML = `
                                    <div class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
                                        <i class="fas fa-info-circle text-3xl mb-2"></i>
                                        <p>No active migrations</p>
                                        <p class="text-sm">Submit a repository to get started</p>
                                    </div>
                                `;
                            }
                            
                            function refreshStatus() {
                                // Simulate refresh
                                const button = event.target.closest('button');
                                button.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
                                setTimeout(() => {
                                    button.innerHTML = '<i class="fas fa-sync-alt"></i>';
                                }, 1000);
                            }
                            
                            function refreshHistory() {
                                // Simulate refresh
                                const button = event.target;
                                button.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
                                setTimeout(() => {
                                    button.innerHTML = '<i class="fas fa-sync-alt"></i>';
                                }, 1000);
                            }
                            
                            // Initialize with some demo data
                            migrationHistory = [
                                {
                                    repository: 'https://github.com/octocat/Hello-World',
                                    source: 'JavaScript',
                                    target: 'Python',
                                    status: 'completed',
                                    time: new Date(Date.now() - 300000).toLocaleString(),
                                    id: 'demo-1'
                                },
                                {
                                    repository: 'https://github.com/example/demo-repo',
                                    source: 'Java',
                                    target: 'Go',
                                    status: 'completed',
                                    time: new Date(Date.now() - 600000).toLocaleString(),
                                    id: 'demo-2'
                                }
                            ];
                            renderHistory();
                            
                            // WebSocket connection for real-time updates
                            let websocket;
                            let reconnectInterval = 5000; // 5 seconds
                            let maxReconnectAttempts = 10;
                            let reconnectAttempts = 0;
                            
                            function connectWebSocket() {
                                try {
                                    websocket = new WebSocket(`ws://localhost:${window.location.port == 8000 ? 8001 : parseInt(window.location.port) + 1}`);
                                    
                                    websocket.onopen = function(event) {
                                        console.log('WebSocket connected');
                                        reconnectAttempts = 0;
                                        updateConnectionStatus('connected');
                                    };
                                    
                                    websocket.onmessage = function(event) {
                                        const data = JSON.parse(event.data);
                                        handleWebSocketMessage(data);
                                    };
                                    
                                    websocket.onclose = function(event) {
                                        console.log('WebSocket disconnected');
                                        updateConnectionStatus('disconnected');
                                        
                                        // Attempt to reconnect
                                        if (reconnectAttempts < maxReconnectAttempts) {
                                            setTimeout(() => {
                                                reconnectAttempts++;
                                                console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
                                                connectWebSocket();
                                            }, reconnectInterval);
                                        }
                                    };
                                    
                                    websocket.onerror = function(error) {
                                        console.error('WebSocket error:', error);
                                        updateConnectionStatus('error');
                                    };
                                } catch (error) {
                                    console.error('Failed to create WebSocket connection:', error);
                                }
                            }
                            
                            function handleWebSocketMessage(data) {
                                console.log('WebSocket message:', data);
                                
                                if (data.type === 'mesh_status') {
                                    updateMeshStatus(data);
                                } else if (data.type === 'migration_update') {
                                    updateMigrationStatus(data);
                                } else if (data.type === 'connection_status') {
                                    updateConnectionStatus(data.status);
                                }
                            }
                            
                            function updateConnectionStatus(status) {
                                const statusElement = document.getElementById('connectionStatus');
                                if (statusElement) {
                                    statusElement.textContent = status;
                                    statusElement.className = `px-2 py-1 text-xs rounded-full ${
                                        status === 'connected' ? 'bg-green-100 text-green-800' :
                                        status === 'disconnected' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-red-100 text-red-800'
                                    }`;
                                }
                            }
                            
                            function updateMeshStatus(data) {
                                const meshStatusElement = document.getElementById('meshStatus');
                                if (meshStatusElement) {
                                    meshStatusElement.textContent = data.status;
                                    meshStatusElement.className = `px-2 py-1 text-xs rounded-full ${
                                        data.status === 'running' ? 'bg-green-100 text-green-800' :
                                        'bg-red-100 text-red-800'
                                    }`;
                                }
                            }
                            
                            function updateMigrationStatus(data) {
                                // Update migration progress in real-time
                                if (data.request_id) {
                                    const row = document.querySelector(`[data-request-id="${data.request_id}"]`);
                                    if (row) {
                                        const statusCell = row.querySelector('.status-cell');
                                        if (statusCell) {
                                            statusCell.textContent = data.status;
                                            statusCell.className = `status-cell px-2 py-1 text-xs rounded-full ${
                                                data.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                data.status === 'in-progress' ? 'bg-blue-100 text-blue-800' :
                                                data.status === 'failed' ? 'bg-red-100 text-red-800' :
                                                'bg-yellow-100 text-yellow-800'
                                            }`;
                                        }
                                    }
                                }
                            }
                            
                            // Connect WebSocket on page load
                            connectWebSocket();
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
        
        # Broadcast shutdown status
        self._broadcast_status({
            "type": "mesh_status",
            "status": "stopping",
            "timestamp": time.time()
        })
        
        # Stop WebSocket server
        if self.websocket_server:
            try:
                self.websocket_server.close()
                logger.info("WebSocket server stopped")
            except Exception as e:
                logger.warning(f"Error stopping WebSocket server: {e}")
        
        # Stop WebSocket thread
        if self.status_websocket_thread and self.status_websocket_thread.is_alive():
            try:
                # Give WebSocket clients time to disconnect gracefully
                time.sleep(1)
                logger.info("WebSocket thread stopped")
            except Exception as e:
                logger.warning(f"Error stopping WebSocket thread: {e}")
        
        # Stop SAM Gateway if running
        if self.sam_gateway:
            try:
                if hasattr(self.sam_gateway, 'stop'):
                    self.sam_gateway.stop()
                logger.info("SAM Gateway stopped")
            except Exception as e:
                logger.warning(f"Error stopping SAM Gateway: {e}")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")
        
        logger.info("Agent mesh stopped")