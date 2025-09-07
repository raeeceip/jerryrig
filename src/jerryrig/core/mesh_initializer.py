"""
Mesh Initializer for creating SAM project structures
"""

import os
import shutil
from typing import Dict, Any, List
from pathlib import Path
import yaml

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MeshInitializer:
    """Initializes new Solace Agent Mesh projects"""
    
    def create_sam_project(self, output_dir: str) -> Dict[str, Any]:
        """Create a complete SAM project structure"""
        project_path = Path(output_dir)
        
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating SAM project in {project_path}")
        
        # Copy the existing SAM project structure
        source_sam_dir = Path(__file__).parent.parent.parent.parent / "sam_project"
        
        if source_sam_dir.exists():
            # Copy existing structure
            self._copy_sam_structure(source_sam_dir, project_path)
        else:
            # Create structure from scratch
            self._create_sam_structure(project_path)
        
        # Create additional project files
        self._create_project_files(project_path)
        
        result = {
            'project_dir': str(project_path),
            'config_file': str(project_path / 'config.yaml'),
            'agents': self._list_agents(project_path),
            'status': 'created'
        }
        
        logger.info(f"SAM project created successfully at {project_path}")
        return result
    
    def _copy_sam_structure(self, source_dir: Path, target_dir: Path):
        """Copy existing SAM structure"""
        for item in source_dir.iterdir():
            if item.name in ['.git', '__pycache__', '.venv']:
                continue
                
            target_item = target_dir / item.name
            
            if item.is_dir():
                shutil.copytree(item, target_item, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target_item)
        
        logger.info("Copied existing SAM project structure")
    
    def _create_sam_structure(self, project_path: Path):
        """Create SAM structure from scratch"""
        
        # Create directories
        directories = [
            'agents',
            'logs',
            'config',
            'temp'
        ]
        
        for dir_name in directories:
            (project_path / dir_name).mkdir(exist_ok=True)
        
        # Create main config.yaml
        config = self._get_default_config()
        with open(project_path / 'config.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        # Create agent files
        self._create_agent_files(project_path / 'agents')
        
        logger.info("Created SAM project structure from scratch")
    
    def _create_agent_files(self, agents_dir: Path):
        """Create basic agent files"""
        
        # Repository input agent
        repository_input = '''"""
Repository Input Agent
Handles incoming repository requests
"""

def process(input_data, **kwargs):
    """Process repository input"""
    return {
        'status': 'processed',
        'request': input_data
    }
'''
        
        # Repository orchestrator
        repository_orchestrator = '''"""
Repository Orchestrator Agent
Coordinates migration workflows
"""

def process(input_data, **kwargs):
    """Orchestrate repository processing"""
    return {
        'status': 'orchestrated',
        'workflow_id': 'workflow_001'
    }
'''
        
        # Simple agents
        agents = {
            'repository_input.py': repository_input,
            'repository_orchestrator.py': repository_orchestrator
        }
        
        for filename, content in agents.items():
            with open(agents_dir / filename, 'w') as f:
                f.write(content)
    
    def _create_project_files(self, project_path: Path):
        """Create additional project files"""
        
        # Create .env file
        env_content = '''# Solace Agent Mesh Environment Variables

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Solace Broker Configuration
SOLACE_BROKER_URL=tcp://localhost:55555
SOLACE_USERNAME=default
SOLACE_PASSWORD=default
SOLACE_VPN=default

# JerryRig Configuration
JERRYRIG_LOG_LEVEL=INFO
JERRYRIG_MAX_WORKERS=10
'''
        
        with open(project_path / '.env', 'w') as f:
            f.write(env_content)
        
        # Create README
        readme_content = '''# JerryRig Solace Agent Mesh Project

This is a Solace Agent Mesh project for distributed code migration.

## Setup

1. Install dependencies:
   ```bash
   pip install solace-agent-mesh jerryrig
   ```

2. Configure environment variables in `.env`

3. Start the mesh:
   ```bash
   jerryrig start-mesh
   ```

4. Access the web interface at http://localhost:8000

## Structure

- `config.yaml` - Main SAM configuration
- `agents/` - Agent implementation modules
- `logs/` - Agent mesh logs
- `.env` - Environment variables

## Usage

Submit migration requests via:
- Web interface at http://localhost:8000
- CLI: `jerryrig mesh-migration <repo_url> <target_language>`
- REST API: POST to `/migrate`

## Agents

- **Repository Input**: Validates and enriches migration requests
- **Repository Orchestrator**: Coordinates migration workflows
- **Repository Chunker**: Breaks large repos into manageable chunks
- **Code Analyzer**: Analyzes code structure and dependencies
- **Code Migrator**: Performs AI-powered code migration
- **Result Aggregator**: Assembles final migration results
'''
        
        with open(project_path / 'README.md', 'w') as f:
            f.write(readme_content)
        
        # Create requirements.txt
        requirements = '''solace-agent-mesh>=1.1.0
openai>=1.0.0
gitpython>=3.1.0
pyyaml>=6.0
requests>=2.28.0
rich>=13.0.0
click>=8.0.0
python-dotenv>=1.0.0
'''
        
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write(requirements)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default SAM configuration"""
        return {
            'instance_name': 'jerryrig-mesh',
            'log': {
                'stdout_log_level': 'INFO',
                'log_file_level': 'DEBUG',
                'log_file': 'logs/jerryrig-mesh.log'
            },
            'solace': {
                'broker_type': 'solace',
                'broker_url': '${SOLACE_BROKER_URL:tcp://localhost:55555}',
                'broker_username': '${SOLACE_USERNAME:default}',
                'broker_password': '${SOLACE_PASSWORD:default}',
                'broker_vpn': '${SOLACE_VPN:default}'
            },
            'shared_config': {
                'openai': {
                    'api_key': '${OPENAI_API_KEY}',
                    'model': 'gpt-4',
                    'temperature': 0.1,
                    'max_tokens': 4000
                },
                'jerryrig': {
                    'supported_languages': ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust'],
                    'max_file_size': 1048576,
                    'max_chunk_size': 50,
                    'timeout_seconds': 300
                }
            },
            'flows': [
                {
                    'name': 'repository_migration',
                    'components': [
                        {
                            'component_name': 'repository_input',
                            'component_module': 'repository_input'
                        },
                        {
                            'component_name': 'repository_orchestrator',
                            'component_module': 'repository_orchestrator'
                        }
                    ]
                }
            ]
        }
    
    def _list_agents(self, project_path: Path) -> List[str]:
        """List available agents in the project"""
        agents_dir = project_path / 'agents'
        if not agents_dir.exists():
            return []
        
        agents = []
        for file_path in agents_dir.glob('*.py'):
            if not file_path.name.startswith('__'):
                agents.append(file_path.stem)
        
        return agents