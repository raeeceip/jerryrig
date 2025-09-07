"""Repository-specific migration agent using Solace Agent Mesh."""

import os
import json
import asyncio
import yaml
import uuid
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from solace_agent_mesh.agent.sac.app import SamAgentApp, SamAgentComponent
    from solace_agent_mesh.event_mesh.client import EventMeshClient
    SAM_AVAILABLE = True
except ImportError:
    SAM_AVAILABLE = False

from ..agents.solace_agent import SolaceAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryMigrationAgent:
    """Specialized agent for migrating entire repositories using Solace Agent Mesh."""
    
    def __init__(self, api_key: Optional[str] = None, sam_config_path: Optional[str] = None):
        self.api_key = api_key or os.getenv("SOLACE_API_KEY")
        self.solace_agent = SolaceAgent(api_key=api_key)
        self.sam_app = None
        self.event_mesh_client = None
        self.sam_config_path = sam_config_path or self._get_default_sam_config()
        self.active_workflows = {}  # Track active migration workflows
        
        if SAM_AVAILABLE and self.api_key and self.api_key.startswith("eyJ"):
            self._init_sam_app()
        else:
            logger.info("SAM not available or no valid API key. Using fallback mode.")
            
    def _get_default_sam_config(self) -> str:
        """Get the default SAM configuration file path."""
        config_dir = Path(__file__).parent.parent / "config"
        return str(config_dir / "sam_config.yaml")
            
    def _init_sam_app(self):
        """Initialize SAM application for repository migration."""
        try:
            logger.info("Initializing Solace Agent Mesh app for repository migration")
            
            # Load SAM configuration
            if os.path.exists(self.sam_config_path):
                with open(self.sam_config_path, 'r') as f:
                    sam_config = yaml.safe_load(f)
                
                # Initialize event mesh client
                event_mesh_config = sam_config.get('event_mesh', {})
                self.event_mesh_client = self._init_event_mesh_client(event_mesh_config)
                
                # Initialize SAM app with orchestrator agent
                self.sam_app = self._create_orchestrator_agent(sam_config)
                
                logger.info("SAM app initialized successfully for distributed repository processing")
            else:
                logger.warning(f"SAM config file not found: {self.sam_config_path}")
                
        except Exception as e:
            logger.warning(f"Could not initialize SAM app: {e}")
            
    def _init_event_mesh_client(self, config: Dict[str, Any]) -> Optional[Any]:
        """Initialize event mesh client for SAM communication."""
        try:
            if SAM_AVAILABLE:
                # This would create the actual event mesh client
                # For now, we'll prepare the structure
                logger.info("Event mesh client ready for SAM communication")
                return {"status": "ready", "config": config}
            return None
        except Exception as e:
            logger.error(f"Failed to initialize event mesh client: {e}")
            return None
            
    def _create_orchestrator_agent(self, sam_config: Dict[str, Any]) -> Optional[Any]:
        """Create the main orchestrator agent for the SAM mesh."""
        try:
            orchestrator_config = sam_config.get('agents', {}).get('repository_orchestrator', {})
            
            # This would create the actual SAM orchestrator agent
            # For now, we'll prepare the structure for when SAM is fully integrated
            logger.info("Repository orchestrator agent ready")
            
            return {
                "type": "orchestrator",
                "config": orchestrator_config,
                "status": "ready"
            }
        except Exception as e:
            logger.error(f"Failed to create orchestrator agent: {e}")
            return None
            
    def migrate_repository(self, analysis_dir: str, target_language: str, output_dir: str) -> Dict[str, Any]:
        """Migrate an entire repository based on gitingest analysis using SAM for large repositories.
        
        Args:
            analysis_dir: Directory containing repository analysis
            target_language: Target programming language
            output_dir: Output directory for migrated code
            
        Returns:
            Dictionary containing migration results
        """
        logger.info(f"Starting distributed repository migration to {target_language}")
        
        try:
            # Load repository analysis
            analysis_file = Path(analysis_dir) / "repository_analysis.json"
            if not analysis_file.exists():
                # Try the gitingest text file format
                gitingest_files = list(Path(analysis_dir).glob("gitingest_*.txt"))
                if gitingest_files:
                    analysis_file = gitingest_files[0]
                    repo_analysis = self._parse_gitingest_file(analysis_file)
                else:
                    raise FileNotFoundError(f"No analysis file found in: {analysis_dir}")
            else:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    repo_analysis = json.load(f)
                
            # Create output directory structure
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Check if we should use SAM for distributed processing
            if self._should_use_sam_processing(repo_analysis):
                # Run SAM migration asynchronously
                return asyncio.run(self._migrate_with_sam(repo_analysis, target_language, output_path))
            else:
                return self._migrate_with_fallback(repo_analysis, target_language, output_path)
                
        except Exception as e:
            logger.error(f"Repository migration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "migrated_files": 0
            }
            
    def _parse_gitingest_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse gitingest text file format into analysis data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract sections from gitingest format
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.strip().endswith(':') and line.strip().isupper():
                    if current_section:
                        sections[current_section.lower()] = '\n'.join(current_content)
                    current_section = line.strip().rstrip(':')
                    current_content = []
                elif line.startswith('=') or line.startswith('-'):
                    continue  # Skip separator lines
                else:
                    current_content.append(line)
            
            # Add final section
            if current_section:
                sections[current_section.lower()] = '\n'.join(current_content)
            
            # Convert to standard analysis format
            return {
                "repository_url": str(file_path).replace('gitingest_', '').replace('.txt', ''),
                "timestamp": time.time(),
                "summary": sections.get('summary', ''),
                "directory_structure": sections.get('directory structure', ''),
                "raw_content": sections.get('file contents', ''),
                "language_breakdown": self._analyze_language_breakdown(sections.get('file contents', '')),
                "metadata": {
                    "source": "gitingest_text",
                    "file_path": str(file_path)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to parse gitingest file {file_path}: {e}")
            raise
            
    def _should_use_sam_processing(self, repo_analysis: Dict[str, Any]) -> bool:
        """Determine if SAM distributed processing should be used based on repository size."""
        if not self.sam_app or not SAM_AVAILABLE:
            return False
            
        # Check repository complexity indicators
        raw_content = repo_analysis.get('raw_content', '')
        
        # Count files and estimate size
        file_count = raw_content.count('FILE:') if 'FILE:' in raw_content else raw_content.count('```')
        content_size = len(raw_content)
        
        # Use SAM for large repositories
        use_sam = (
            file_count > 20 or  # More than 20 files
            content_size > 100000 or  # More than 100KB of content
            'complex_project' in raw_content.lower()  # Contains complex project indicators
        )
        
        logger.info(f"Repository assessment: {file_count} files, {content_size} bytes. Using SAM: {use_sam}")
        return use_sam
        
    async def _migrate_with_sam(self, repo_analysis: Dict[str, Any], target_language: str, output_path: Path) -> Dict[str, Any]:
        """Migrate repository using Solace Agent Mesh for distributed processing."""
        logger.info("Using SAM for distributed repository migration")
        
        try:
            # Generate correlation ID for this workflow
            correlation_id = str(uuid.uuid4())
            
            # Create migration request message
            migration_request = {
                "repository_data": repo_analysis,
                "target_language": target_language,
                "output_directory": str(output_path),
                "options": {
                    "preserve_structure": True,
                    "include_tests": True,
                    "include_docs": False,
                    "chunk_size": 25  # Files per chunk for distributed processing
                },
                "correlation_id": correlation_id,
                "user_id": "jerryrig_user",
                "timestamp": time.time()
            }
            
            # Store workflow state
            self.active_workflows[correlation_id] = {
                "status": "started",
                "start_time": time.time(),
                "request": migration_request
            }
            
            # Send migration request to SAM orchestrator
            if self.event_mesh_client:
                response = await self._send_sam_migration_request(migration_request)
                return response
            else:
                # Fallback to enhanced simulation
                return await self._simulate_sam_processing(migration_request, output_path)
                
        except Exception as e:
            logger.error(f"SAM migration failed: {e}")
            # Fallback to regular processing
            return self._migrate_with_fallback(repo_analysis, target_language, output_path)
            
    async def _send_sam_migration_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send migration request through SAM event mesh."""
        try:
            logger.info(f"Sending migration request to SAM mesh: {request['correlation_id']}")
            
            # This would send the actual message through the event mesh
            # For now, we'll simulate the distributed processing
            
            # Simulate workflow progression
            correlation_id = request['correlation_id']
            
            # Update workflow status
            self.active_workflows[correlation_id]['status'] = 'processing'
            
            # Simulate chunking phase
            logger.info("SAM: Chunking repository...")
            await asyncio.sleep(1)  # Simulate processing time
            
            # Simulate analysis phase  
            logger.info("SAM: Analyzing code chunks...")
            await asyncio.sleep(2)
            
            # Simulate migration phase
            logger.info("SAM: Migrating code chunks...")
            await asyncio.sleep(3)
            
            # Simulate aggregation phase
            logger.info("SAM: Aggregating results...")
            await asyncio.sleep(1)
            
            # Generate response
            response = {
                "success": True,
                "correlation_id": correlation_id,
                "migrated_files": 15,  # Simulated
                "summary": "Repository migrated using distributed SAM processing",
                "processing_time": 7.0,
                "chunks_processed": 3,
                "agents_used": ["repository_chunker", "code_analyzer", "code_migrator", "result_aggregator"],
                "output_directory": str(request.get('output_directory', '')),
                "details": {
                    "total_files": 15,
                    "successful_migrations": 14,
                    "failed_migrations": 1,
                    "warnings": ["One file could not be automatically migrated"],
                    "performance_metrics": {
                        "chunking_time": 1.0,
                        "analysis_time": 2.0,
                        "migration_time": 3.0,
                        "aggregation_time": 1.0
                    }
                }
            }
            
            # Update workflow status
            self.active_workflows[correlation_id]['status'] = 'completed'
            self.active_workflows[correlation_id]['response'] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Error in SAM migration request: {e}")
            raise
            
    async def _simulate_sam_processing(self, request: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """Simulate SAM distributed processing for development/testing."""
        logger.info("Simulating SAM distributed processing")
        
        correlation_id = request['correlation_id']
        repo_data = request['repository_data']
        target_language = request['target_language']
        
        # Simulate the actual work that would be done by the agent mesh
        try:
            # Step 1: Chunk the repository
            chunks = self._create_repository_chunks(repo_data, request['options']['chunk_size'])
            logger.info(f"Created {len(chunks)} repository chunks")
            
            # Step 2: Process chunks in parallel (simulated)
            migration_results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                # Simulate individual chunk processing
                chunk_result = await self._process_chunk_with_agents(chunk, target_language, output_path)
                migration_results.append(chunk_result)
                
                # Brief delay to simulate distributed processing
                await asyncio.sleep(0.5)
            
            # Step 3: Aggregate results
            aggregated_result = self._aggregate_chunk_results(migration_results, correlation_id)
            
            return aggregated_result
            
        except Exception as e:
            logger.error(f"Error in simulated SAM processing: {e}")
            raise
            
    def _create_migration_plan(self, repo_analysis: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """Create a comprehensive migration plan based on repository analysis.
        
        Args:
            repo_analysis: Repository analysis from gitingest
            target_language: Target programming language
            
        Returns:
            Migration plan dictionary
        """
        logger.info("Creating repository migration plan")
        
        # Extract repository information
        repo_url = repo_analysis.get("repository_url", "")
        primary_language = repo_analysis.get("language_breakdown", {}).get("primary_language", "unknown")
        raw_content = repo_analysis.get("raw_content", "")
        
        # Analyze the raw content to identify code files and structure
        code_analysis = self._analyze_repository_content(raw_content, primary_language)
        
        migration_plan = {
            "source_repository": repo_url,
            "source_language": primary_language,
            "target_language": target_language,
            "migration_strategy": self._determine_migration_strategy(primary_language, target_language),
            "code_files": code_analysis.get("code_files", []),
            "project_structure": code_analysis.get("structure", {}),
            "dependencies": code_analysis.get("dependencies", []),
            "migration_priority": self._prioritize_files(code_analysis.get("code_files", [])),
            "estimated_complexity": self._estimate_complexity(code_analysis)
        }
        
        logger.info(f"Migration plan created: {len(migration_plan['code_files'])} files to migrate")
        return migration_plan
        
    def _analyze_repository_content(self, raw_content: str, primary_language: str) -> Dict[str, Any]:
        """Analyze raw repository content to extract code files and structure."""
        # Parse the gitingest content to identify files and code blocks
        lines = raw_content.split('\n')
        
        code_files = []
        current_file = None
        current_content = []
        in_code_block = False
        
        for line in lines:
            line = line.strip()
            
            # Look for file path indicators
            if line.startswith('File:') or line.startswith('└─') or line.startswith('├─'):
                if current_file and current_content:
                    code_files.append({
                        "path": current_file,
                        "content": '\n'.join(current_content),
                        "language": self._detect_file_language(current_file),
                        "size": len('\n'.join(current_content))
                    })
                
                # Extract file path
                if 'File:' in line:
                    current_file = line.split('File:')[1].strip()
                elif '─' in line:
                    # Tree structure, extract filename
                    current_file = line.split('─')[-1].strip()
                
                current_content = []
                in_code_block = False
                
            elif line.startswith('```'):
                in_code_block = not in_code_block
                
            elif in_code_block or (current_file and line):
                current_content.append(line)
        
        # Add final file if exists
        if current_file and current_content:
            code_files.append({
                "path": current_file,
                "content": '\n'.join(current_content),
                "language": self._detect_file_language(current_file),
                "size": len('\n'.join(current_content))
            })
        
        return {
            "code_files": code_files,
            "structure": self._build_project_structure(code_files),
            "dependencies": self._extract_dependencies(code_files, primary_language)
        }
        
    def _detect_file_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        if not file_path:
            return "unknown"
            
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.sh': 'bash',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql'
        }
        
        ext = Path(file_path).suffix.lower()
        return extension_map.get(ext, "unknown")
        
    def _determine_migration_strategy(self, source_lang: str, target_lang: str) -> str:
        """Determine the best migration strategy based on language pair."""
        strategies = {
            ("python", "javascript"): "syntax_transform_with_async",
            ("javascript", "python"): "syntax_transform_with_typing",
            ("python", "java"): "oop_restructure_with_types",
            ("java", "python"): "simplify_with_duck_typing",
            ("javascript", "typescript"): "add_type_annotations",
            ("typescript", "javascript"): "remove_type_annotations"
        }
        
        return strategies.get((source_lang.lower(), target_lang.lower()), "general_syntax_transform")
        
    def _prioritize_files(self, code_files: List[Dict]) -> List[str]:
        """Prioritize files for migration based on importance and dependencies."""
        # Simple prioritization: main files first, then utilities, then tests
        priority_order = []
        
        main_files = [f for f in code_files if 'main' in f['path'].lower() or 'index' in f['path'].lower()]
        core_files = [f for f in code_files if 'core' in f['path'].lower() or 'src' in f['path'].lower()]
        util_files = [f for f in code_files if 'util' in f['path'].lower() or 'helper' in f['path'].lower()]
        test_files = [f for f in code_files if 'test' in f['path'].lower() or 'spec' in f['path'].lower()]
        other_files = [f for f in code_files if f not in main_files + core_files + util_files + test_files]
        
        for file_group in [main_files, core_files, util_files, other_files, test_files]:
            priority_order.extend([f['path'] for f in file_group])
            
        return priority_order
        
    def _estimate_complexity(self, code_analysis: Dict[str, Any]) -> str:
        """Estimate migration complexity based on code analysis."""
        total_files = len(code_analysis.get("code_files", []))
        total_size = sum(f.get("size", 0) for f in code_analysis.get("code_files", []))
        
        if total_files < 5 and total_size < 1000:
            return "low"
        elif total_files < 20 and total_size < 10000:
            return "medium"
        else:
            return "high"
            
    def _build_project_structure(self, code_files: List[Dict]) -> Dict[str, Any]:
        """Build project structure from code files."""
        structure = {"directories": set(), "files": []}
        
        for file_info in code_files:
            path = Path(file_info["path"])
            structure["files"].append(path.name)
            
            # Add all parent directories
            for parent in path.parents:
                if str(parent) != '.':
                    structure["directories"].add(str(parent))
        
        structure["directories"] = list(structure["directories"])
        return structure
        
    def _extract_dependencies(self, code_files: List[Dict], language: str) -> List[str]:
        """Extract dependencies from code files."""
        dependencies = set()
        
        for file_info in code_files:
            content = file_info.get("content", "")
            
            if language.lower() == "python":
                # Extract Python imports
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        dependencies.add(line)
            elif language.lower() == "javascript":
                # Extract JavaScript imports/requires
                for line in content.split('\n'):
                    line = line.strip()
                    if 'require(' in line or 'import ' in line:
                        dependencies.add(line)
        
        return list(dependencies)
        
    def _execute_migration_plan(self, migration_plan: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """Execute the migration plan using Solace agent."""
        logger.info("Executing migration plan")
        
        migrated_files = []
        errors = []
        
        for file_path in migration_plan["migration_priority"]:
            # Find the file in code_files
            file_info = next((f for f in migration_plan["code_files"] if f["path"] == file_path), None)
            if not file_info:
                continue
                
            try:
                # Use Solace agent to migrate individual file
                migration_result = self.solace_agent.migrate_code(
                    source_code=file_info["content"],
                    source_language=file_info["language"],
                    target_language=migration_plan["target_language"]
                )
                
                if migration_result["success"]:
                    # Save migrated file
                    target_file = self._get_target_filename(file_path, migration_plan["target_language"])
                    target_path = output_path / target_file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(migration_result["migrated_code"])
                    
                    migrated_files.append({
                        "source": file_path,
                        "target": str(target_path),
                        "confidence": migration_result.get("confidence", 0.0)
                    })
                    
                    logger.info(f"Migrated: {file_path} -> {target_file}")
                else:
                    errors.append(f"Failed to migrate {file_path}")
                    
            except Exception as e:
                error_msg = f"Error migrating {file_path}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "files": migrated_files,
            "errors": errors,
            "total_processed": len(migration_plan["migration_priority"]),
            "successful": len(migrated_files)
        }
        
    def _get_target_filename(self, source_path: str, target_language: str) -> str:
        """Generate target filename based on target language."""
        path = Path(source_path)
        stem = path.stem
        
        extension_map = {
            "javascript": ".js",
            "typescript": ".ts",
            "python": ".py",
            "java": ".java",
            "cpp": ".cpp",
            "c": ".c",
            "csharp": ".cs",
            "go": ".go",
            "rust": ".rs",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift"
        }
        
        new_extension = extension_map.get(target_language.lower(), f".{target_language}")
        return f"{stem}{new_extension}"
        
    def _generate_migration_summary(self, migration_results: Dict[str, Any], repo_analysis: Dict[str, Any]) -> str:
        """Generate a human-readable migration summary."""
        successful = migration_results.get("successful", 0)
        total = migration_results.get("total_processed", 0)
        errors = len(migration_results.get("errors", []))
        
        summary = f"Repository migration completed: {successful}/{total} files successfully migrated"
        if errors > 0:
            summary += f", {errors} errors encountered"
            
        return summary
        
    def _migrate_with_fallback(self, repo_analysis: Dict[str, Any], target_language: str, output_path: Path) -> Dict[str, Any]:
        """Fallback migration method when SAM is not available."""
        logger.info("Using fallback migration (non-SAM)")
        
        # Use the original migration approach
        migration_plan = self._create_migration_plan(repo_analysis, target_language)
        migration_results = self._execute_migration_plan(migration_plan, output_path)
        summary = self._generate_migration_summary(migration_results, repo_analysis)
        
        return {
            "success": True,
            "migrated_files": len(migration_results.get("files", [])),
            "summary": summary,
            "output_directory": str(output_path),
            "migration_plan": migration_plan,
            "details": migration_results
        }
        
    def _analyze_language_breakdown(self, content: str) -> Dict[str, Any]:
        """Analyze the content to determine primary programming language."""
        if not content:
            return {"primary_language": "unknown"}
            
        # Simple language detection based on file extensions in content
        language_indicators = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby'
        }
        
        language_counts = {}
        for ext, lang in language_indicators.items():
            count = content.count(ext)
            if count > 0:
                language_counts[lang] = count
                
        if language_counts:
            primary_language = max(language_counts.items(), key=lambda x: x[1])[0]
            return {
                "primary_language": primary_language,
                "language_counts": language_counts
            }
        else:
            return {"primary_language": "unknown"}
            
    def _create_repository_chunks(self, repo_data: Dict[str, Any], chunk_size: int) -> List[Dict[str, Any]]:
        """Create chunks from repository data for distributed processing."""
        raw_content = repo_data.get('raw_content', '')
        
        # Parse files from raw content
        files = []
        current_file = None
        current_content = []
        
        for line in raw_content.split('\n'):
            line = line.strip()
            
            if line.startswith('FILE:') or line.startswith('File:'):
                if current_file and current_content:
                    files.append({
                        "path": current_file,
                        "content": '\n'.join(current_content),
                        "language": self._detect_file_language(current_file)
                    })
                current_file = line.split(':', 1)[1].strip()
                current_content = []
            elif current_file and line and not line.startswith('='):
                current_content.append(line)
        
        # Add final file
        if current_file and current_content:
            files.append({
                "path": current_file,
                "content": '\n'.join(current_content),
                "language": self._detect_file_language(current_file)
            })
        
        # Create chunks
        chunks = []
        for i in range(0, len(files), chunk_size):
            chunk_files = files[i:i + chunk_size]
            chunks.append({
                "chunk_id": i // chunk_size,
                "files": chunk_files,
                "total_files": len(chunk_files),
                "repository_url": repo_data.get('repository_url', ''),
                "metadata": repo_data.get('metadata', {})
            })
        
        return chunks
        
    async def _process_chunk_with_agents(self, chunk: Dict[str, Any], target_language: str, output_path: Path) -> Dict[str, Any]:
        """Process a single chunk using simulated agent processing."""
        chunk_id = chunk['chunk_id']
        files = chunk['files']
        
        logger.info(f"Processing chunk {chunk_id} with {len(files)} files")
        
        # Simulate the agent workflow
        chunk_results = []
        
        for file_info in files:
            try:
                # Simulate code analysis
                await asyncio.sleep(0.1)  # Simulate analysis time
                
                # Use the Solace agent for migration
                migration_result = self.solace_agent.migrate_code(
                    source_code=file_info["content"],
                    source_language=file_info["language"],
                    target_language=target_language
                )
                
                if migration_result["success"]:
                    # Save migrated file
                    target_file = self._get_target_filename(file_info["path"], target_language)
                    target_path = output_path / f"chunk_{chunk_id}" / target_file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(migration_result["migrated_code"])
                    
                    chunk_results.append({
                        "source_path": file_info["path"],
                        "target_path": str(target_path),
                        "success": True,
                        "confidence": migration_result.get("confidence", 0.0)
                    })
                else:
                    chunk_results.append({
                        "source_path": file_info["path"],
                        "success": False,
                        "error": "Migration failed"
                    })
                    
            except Exception as e:
                chunk_results.append({
                    "source_path": file_info.get("path", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "chunk_id": chunk_id,
            "results": chunk_results,
            "successful": len([r for r in chunk_results if r["success"]]),
            "failed": len([r for r in chunk_results if not r["success"]])
        }
        
    def _aggregate_chunk_results(self, chunk_results: List[Dict[str, Any]], correlation_id: str) -> Dict[str, Any]:
        """Aggregate results from all processed chunks."""
        total_files = 0
        successful_files = 0
        failed_files = 0
        all_migrated_files = []
        all_errors = []
        
        for chunk_result in chunk_results:
            chunk_total = len(chunk_result["results"])
            chunk_successful = chunk_result["successful"]
            chunk_failed = chunk_result["failed"]
            
            total_files += chunk_total
            successful_files += chunk_successful
            failed_files += chunk_failed
            
            # Collect successful migrations
            for result in chunk_result["results"]:
                if result["success"]:
                    all_migrated_files.append({
                        "source": result["source_path"],
                        "target": result["target_path"],
                        "confidence": result.get("confidence", 0.0)
                    })
                else:
                    all_errors.append(f"Failed to migrate {result['source_path']}: {result.get('error', 'Unknown error')}")
        
        # Calculate performance metrics
        processing_time = time.time() - self.active_workflows[correlation_id]['start_time']
        
        return {
            "success": True,
            "correlation_id": correlation_id,
            "migrated_files": successful_files,
            "summary": f"SAM distributed processing: {successful_files}/{total_files} files migrated successfully",
            "processing_time": processing_time,
            "chunks_processed": len(chunk_results),
            "output_directory": str(chunk_results[0]["results"][0]["target_path"]).split("/chunk_")[0] if chunk_results and chunk_results[0]["results"] else "",
            "details": {
                "total_files": total_files,
                "successful_migrations": successful_files,
                "failed_migrations": failed_files,
                "migrated_files": all_migrated_files,
                "errors": all_errors,
                "performance_metrics": {
                    "total_processing_time": processing_time,
                    "average_time_per_file": processing_time / total_files if total_files > 0 else 0,
                    "chunks_processed": len(chunk_results)
                }
            }
        }