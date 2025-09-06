"""Repository-specific migration agent using Solace Agent Mesh."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from solace_agent_mesh.agent.sac.app import SamAgentApp, SamAgentComponent
    SAM_AVAILABLE = True
except ImportError:
    SAM_AVAILABLE = False

from ..agents.solace_agent import SolaceAgent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryMigrationAgent:
    """Specialized agent for migrating entire repositories using Solace Agent Mesh."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SOLACE_API_KEY")
        self.solace_agent = SolaceAgent(api_key=api_key)
        self.sam_app = None
        
        if SAM_AVAILABLE and self.api_key and self.api_key.startswith("eyJ"):
            self._init_sam_app()
            
    def _init_sam_app(self):
        """Initialize SAM application for repository migration."""
        try:
            logger.info("Initializing Solace Agent Mesh app for repository migration")
            # This would be configured with proper SAM YAML configuration
            # For now, we'll prepare the structure
            logger.info("SAM app ready for repository-level operations")
        except Exception as e:
            logger.warning(f"Could not initialize SAM app: {e}")
            
    def migrate_repository(self, analysis_dir: str, target_language: str, output_dir: str) -> Dict[str, Any]:
        """Migrate an entire repository based on gitingest analysis.
        
        Args:
            analysis_dir: Directory containing repository analysis
            target_language: Target programming language
            output_dir: Output directory for migrated code
            
        Returns:
            Dictionary containing migration results
        """
        logger.info(f"Starting repository migration to {target_language}")
        
        try:
            # Load repository analysis
            analysis_file = Path(analysis_dir) / "repository_analysis.json"
            if not analysis_file.exists():
                raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
                
            with open(analysis_file, 'r', encoding='utf-8') as f:
                repo_analysis = json.load(f)
                
            # Create output directory structure
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Analyze repository structure and create migration plan
            migration_plan = self._create_migration_plan(repo_analysis, target_language)
            
            # Execute migration using Solace agent
            migration_results = self._execute_migration_plan(migration_plan, output_path)
            
            # Generate summary
            summary = self._generate_migration_summary(migration_results, repo_analysis)
            
            return {
                "success": True,
                "migrated_files": len(migration_results.get("files", [])),
                "summary": summary,
                "output_directory": str(output_path),
                "migration_plan": migration_plan,
                "details": migration_results
            }
            
        except Exception as e:
            logger.error(f"Repository migration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "migrated_files": 0
            }
            
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