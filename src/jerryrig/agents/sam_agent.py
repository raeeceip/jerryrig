"""
JerryRig SAM Agent - Code Migration Agent for Solace Agent Mesh
Integrates JerryRig's migration capabilities with SAM's A2A protocol
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

try:
    from a2a_sdk import Agent, Tool, ToolResult
    from a2a_sdk.models import AgentInfo, ToolInfo
except ImportError:
    # Fallback if A2A SDK is not available
    print("A2A SDK not available, using mock classes")
    
    class Agent:
        def __init__(self, agent_id: str, **kwargs):
            self.agent_id = agent_id
            
        async def register_tool(self, tool):
            pass
            
        async def start(self):
            pass
    
    class Tool:
        def __init__(self, name: str, description: str, **kwargs):
            self.name = name
            self.description = description
    
    class ToolResult:
        def __init__(self, success: bool, result: Any, error: Optional[str] = None):
            self.success = success
            self.result = result
            self.error = error

from jerryrig.core.migrator import CodeMigrator
from jerryrig.core.analyzer import CodeAnalyzer
from jerryrig.utils.logger import get_logger

logger = get_logger(__name__)


class JerryRigSAMAgent:
    """
    SAM-compatible agent for code migration using A2A protocol
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.agent_id = self.config.get('agent_id', 'jerryrig-code-migrator')
        self.migrator = CodeMigrator()
        self.analyzer = CodeAnalyzer()
        
        # Initialize A2A Agent
        self.agent = Agent(
            agent_id=self.agent_id,
            name=self.config.get('name', 'JerryRig Code Migrator'),
            description=self.config.get('description', 'AI-powered code migration agent')
        )
        
        # Register tools
        self._register_tools()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load agent configuration from YAML file"""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "agents" / "jerryrig_migrator.yaml")
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {
                'agent_id': 'jerryrig-code-migrator',
                'name': 'JerryRig Code Migrator',
                'description': 'AI-powered code migration agent'
            }
    
    def _register_tools(self):
        """Register tools with the A2A agent"""
        
        # Tool 1: Migrate Code
        migrate_tool = Tool(
            name="migrate_code",
            description="Migrate source code from one programming language to another",
            handler=self._migrate_code_handler
        )
        
        # Tool 2: Analyze Repository  
        analyze_tool = Tool(
            name="analyze_repository",
            description="Analyze code repository structure and dependencies",
            handler=self._analyze_repository_handler
        )
        
        # Tool 3: Generate Migration Plan
        plan_tool = Tool(
            name="generate_migration_plan", 
            description="Create a detailed migration plan for a codebase",
            handler=self._generate_plan_handler
        )
        
        # Register tools with agent
        asyncio.create_task(self.agent.register_tool(migrate_tool))
        asyncio.create_task(self.agent.register_tool(analyze_tool))
        asyncio.create_task(self.agent.register_tool(plan_tool))
    
    async def _migrate_code_handler(self, request: Dict[str, Any]) -> ToolResult:
        """Handle code migration requests via A2A protocol"""
        try:
            source_code = request.get('source_code')
            source_language = request.get('source_language')
            target_language = request.get('target_language')
            
            if not all([source_code, source_language, target_language]):
                return ToolResult(
                    success=False,
                    result=None,
                    error="Missing required parameters: source_code, source_language, target_language"
                )
            
            # Use the migrator to perform the migration
            result = await self.migrator.migrate_code_async(
                source_code=source_code,
                source_language=source_language, 
                target_language=target_language
            )
            
            return ToolResult(
                success=True,
                result={
                    'migrated_code': result.get('migrated_code'),
                    'source_language': source_language,
                    'target_language': target_language,
                    'migration_notes': result.get('notes', [])
                }
            )
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return ToolResult(
                success=False,
                result=None,
                error=f"Migration failed: {str(e)}"
            )
    
    async def _analyze_repository_handler(self, request: Dict[str, Any]) -> ToolResult:
        """Handle repository analysis requests"""
        try:
            repo_path = request.get('repository_url') or request.get('repository_path')
            
            if not repo_path:
                return ToolResult(
                    success=False,
                    result=None,
                    error="Missing repository_url or repository_path parameter"
                )
            
            # Use the analyzer to analyze the repository
            analysis = await self.analyzer.analyze_repository_async(repo_path)
            
            return ToolResult(
                success=True,
                result=analysis
            )
            
        except Exception as e:
            logger.error(f"Repository analysis failed: {str(e)}")
            return ToolResult(
                success=False,
                result=None,
                error=f"Analysis failed: {str(e)}"
            )
    
    async def _generate_plan_handler(self, request: Dict[str, Any]) -> ToolResult:
        """Handle migration plan generation requests"""
        try:
            source_files = request.get('source_files', [])
            target_language = request.get('target_language')
            
            if not source_files or not target_language:
                return ToolResult(
                    success=False,
                    result=None,
                    error="Missing required parameters: source_files, target_language"
                )
            
            # Generate migration plan
            plan = await self.migrator.generate_migration_plan_async(
                source_files=source_files,
                target_language=target_language
            )
            
            return ToolResult(
                success=True,
                result=plan
            )
            
        except Exception as e:
            logger.error(f"Plan generation failed: {str(e)}")
            return ToolResult(
                success=False,
                result=None,
                error=f"Plan generation failed: {str(e)}"
            )
    
    async def start(self):
        """Start the SAM agent and connect to the event mesh"""
        try:
            logger.info(f"Starting JerryRig SAM Agent: {self.agent_id}")
            await self.agent.start()
            logger.info("JerryRig SAM Agent started successfully")
        except Exception as e:
            logger.error(f"Failed to start agent: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the SAM agent gracefully"""
        try:
            logger.info("Stopping JerryRig SAM Agent")
            # Add cleanup logic here if needed
            logger.info("JerryRig SAM Agent stopped")
        except Exception as e:
            logger.error(f"Failed to stop agent: {str(e)}")


async def main():
    """Main entry point for running the JerryRig SAM agent"""
    agent = JerryRigSAMAgent()
    
    try:
        await agent.start()
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())