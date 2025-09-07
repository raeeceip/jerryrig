"""Fast parallel repository migration using existing SAM agents."""

import asyncio
import json
import os
import time
from typing import Dict, List, Any
from pathlib import Path
import tempfile
import shutil

from .repository_agent import RepositoryMigrationAgent
from ..agents.chunking_agents import RepositoryChunkerAgent, CodeMigratorAgent
from ..agents.solace_agent import SolaceAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FastRepositoryMigrator:
    """Fast parallel repository migration using existing SAM agent mesh."""
    
    def __init__(self, max_workers: int = 10, use_sam: bool = True):
        self.max_workers = max_workers
        self.use_sam = use_sam
        
        # Use existing repository agent instead of reinventing SAM integration
        self.repository_agent = RepositoryMigrationAgent()
        self.chunker_agent = RepositoryChunkerAgent(max_chunk_size=max_workers)
        self.migrator_agent = CodeMigratorAgent()
        self.fallback_agent = SolaceAgent()
        
        logger.info(f"FastRepositoryMigrator initialized with SAM: {use_sam}")
        
    def migrate_repository_fast(self, repo_url: str, target_language: str, output_dir: str) -> Dict[str, Any]:
        """Fast migration using GitHub API + parallel processing.
        
        Args:
            repo_url: GitHub repository URL
            target_language: Target programming language
            output_dir: Output directory
            
        Returns:
            Migration results
        """
        logger.info(f"Starting fast migration: {repo_url} -> {target_language}")
        
        # Step 1: Get repository info via GitHub API (much faster than GitIngest)
        repo_info = self._get_repo_info_fast(repo_url)
        
        # Step 2: Get file list via GitHub API (no cloning needed)
        source_files = self._get_source_files_fast(repo_url)
        
        # Step 3: Process files in parallel batches
        migration_results = self._migrate_files_parallel(
            repo_url, source_files, target_language, output_dir
        )
        
        return {
            "repository_url": repo_url,
            "target_language": target_language,
            "total_files": len(source_files),
            "migrated_files": len(migration_results["successful"]),
            "failed_files": len(migration_results["failed"]),
            "output_directory": output_dir,
            "processing_time": migration_results["processing_time"],
            "results": migration_results
        }
        
    def _get_repo_info_fast(self, repo_url: str) -> Dict[str, Any]:
        """Get repository info via GitHub API (much faster than GitIngest)."""
        import requests
        
        # Convert GitHub URL to API URL
        if 'github.com' in repo_url:
            parts = repo_url.rstrip('/').replace('https://github.com/', '').split('/')
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "name": data.get("name"),
                        "full_name": data.get("full_name"),
                        "language": data.get("language"),
                        "size": data.get("size"),
                        "default_branch": data.get("default_branch", "main")
                    }
        
        return {"name": "unknown", "language": "unknown", "default_branch": "main"}
        
    def _get_source_files_fast(self, repo_url: str) -> List[Dict[str, Any]]:
        """Get source files via GitHub API (no cloning needed)."""
        import requests
        
        # Convert to API URL
        if 'github.com' in repo_url:
            parts = repo_url.rstrip('/').replace('https://github.com/', '').split('/')
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                
                # Get repository tree (all files)
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
                
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    
                    source_files = []
                    for item in data.get("tree", []):
                        if item["type"] == "blob":  # It's a file, not a directory
                            file_path = item["path"]
                            
                            # Filter for source code files
                            if self._is_source_file(file_path):
                                source_files.append({
                                    "path": file_path,
                                    "sha": item["sha"],
                                    "size": item.get("size", 0),
                                    "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{file_path}"
                                })
                    
                    logger.info(f"Found {len(source_files)} source files via API")
                    return source_files
        
        return []
        
    def _is_source_file(self, file_path: str) -> bool:
        """Check if file is a source code file."""
        code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go', 
            '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext in code_extensions and not any(ignore in file_path for ignore in [
            '__pycache__', 'node_modules', '.git', 'venv', 'target', 'build'
        ])
        
    def _migrate_files_parallel(self, repo_url: str, source_files: List[Dict], 
                               target_language: str, output_dir: str) -> Dict[str, Any]:
        """Migrate files using SAM agent mesh instead of ThreadPoolExecutor."""
        import time
        start_time = time.time()
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Use existing SAM agents for distributed processing
        if self.use_sam:
            logger.info("Using SAM agent mesh for distributed migration")
            return self._migrate_with_sam_agents(source_files, target_language, output_dir)
        else:
            logger.info("Using fallback sequential processing")
            return self._migrate_sequential_fallback(source_files, target_language, output_dir)
            
    def _migrate_with_sam_agents(self, source_files: List[Dict], 
                                target_language: str, output_dir: str) -> Dict[str, Any]:
        """Migrate files using existing SAM agent mesh."""
        import asyncio
        start_time = time.time()
        
        # Step 1: Chunk the files using existing chunker agent
        chunk_request = {
            'repository_data': {'source_files': source_files},
            'chunk_config': {'max_chunk_size': self.max_workers},
            'correlation_id': f"fast_migration_{int(time.time())}"
        }
        
        try:
            # Use the existing chunker agent (already has SAM integration)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            chunking_result = loop.run_until_complete(
                self.chunker_agent.process_chunking_request(chunk_request)
            )
            
            if not chunking_result.get('success', False):
                logger.error("Chunking failed, falling back to sequential processing")
                return self._migrate_sequential_fallback(source_files, target_language, output_dir)
            
            # Step 2: Process chunks with migration agents
            chunks = chunking_result.get('chunks', [])
            migration_tasks = []
            
            for chunk in chunks:
                migration_request = {
                    'files': chunk.get('files', []),
                    'target_language': target_language,
                    'output_dir': output_dir,
                    'correlation_id': chunk_request['correlation_id']
                }
                
                # Use the existing migration agent (already has SAM integration)
                task = self.migrator_agent.process_migration_request(migration_request)
                migration_tasks.append(task)
            
            # Wait for all migrations to complete
            migration_results = loop.run_until_complete(
                asyncio.gather(*migration_tasks, return_exceptions=True)
            )
            
            loop.close()
            
            # Aggregate results
            successful = []
            failed = []
            
            for result in migration_results:
                if isinstance(result, Exception):
                    failed.append({"error": str(result), "success": False})
                elif isinstance(result, dict) and result.get('success', False):
                    successful.extend(result.get('migrated_files', []))
                elif isinstance(result, dict):
                    failed.extend(result.get('failed_files', []))
            
            processing_time = time.time() - start_time
            logger.info(f"SAM agent mesh processing completed in {processing_time:.2f} seconds")
            
            return {
                "successful": successful,
                "failed": failed,
                "processing_time": processing_time,
                "processing_method": "sam_agent_mesh"
            }
            
        except Exception as e:
            logger.error(f"SAM agent mesh failed: {e}. Falling back to sequential processing.")
            return self._migrate_sequential_fallback(source_files, target_language, output_dir)
            
    def _migrate_sequential_fallback(self, source_files: List[Dict], 
                                   target_language: str, output_dir: str) -> Dict[str, Any]:
        """Fallback sequential processing when SAM is not available."""
        start_time = time.time()
        successful = []
        failed = []
        
        # Process files sequentially using fallback agent
        for file_info in source_files[:50]:  # Limit to first 50 files for demo
            try:
                result = self._migrate_single_file(file_info, target_language, output_dir)
                if result["success"]:
                    successful.append(result)
                    logger.info(f"✅ Migrated: {file_info['path']}")
                else:
                    failed.append(result)
                    logger.warning(f"❌ Failed: {file_info['path']} - {result['error']}")
            except Exception as e:
                failed.append({
                    "file_path": file_info['path'],
                    "success": False,
                    "error": str(e)
                })
                logger.error(f"❌ Exception migrating {file_info['path']}: {e}")
        
        processing_time = time.time() - start_time
        logger.info(f"Sequential fallback processing completed in {processing_time:.2f} seconds")
        
        return {
            "successful": successful,
            "failed": failed,
            "processing_time": processing_time,
            "processing_method": "sequential_fallback"
        }
        
    def _migrate_single_file(self, file_info: Dict, target_language: str, output_dir: str) -> Dict[str, Any]:
        """Migrate a single file."""
        import requests
        
        try:
            # Download file content
            response = requests.get(file_info["download_url"])
            response.raise_for_status()
            content = response.text
            
            # Detect source language
            file_path = file_info["path"]
            source_language = self._detect_language(file_path)
            
            if source_language == "unknown":
                return {
                    "file_path": file_path,
                    "success": False,
                    "error": "Unknown source language"
                }
            
            # Migrate using fallback Solace agent
            migration_result = self.fallback_agent.migrate_code(content, source_language, target_language)
            
            if migration_result["success"]:
                # Save migrated file
                output_file = os.path.join(output_dir, self._get_target_filename(file_path, target_language))
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(migration_result["migrated_code"])
                
                return {
                    "file_path": file_path,
                    "output_path": output_file,
                    "source_language": source_language,
                    "target_language": target_language,
                    "success": True,
                    "confidence": migration_result.get("confidence", 0.0),
                    "warnings": migration_result.get("warnings", [])
                }
            else:
                return {
                    "file_path": file_path,
                    "success": False,
                    "error": "Migration failed"
                }
                
        except Exception as e:
            return {
                "file_path": file_info["path"],
                "success": False,
                "error": str(e)
            }
            
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
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
            '.php': 'php'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_to_lang.get(ext, "unknown")
        
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
            "php": ".php"
        }
        
        new_extension = extension_map.get(target_language.lower(), f".{target_language}")
        return str(path.parent / f"{stem}{new_extension}")


# For backwards compatibility
class AgentMeshMigrator(FastRepositoryMigrator):
    """Alias for FastRepositoryMigrator."""
    pass