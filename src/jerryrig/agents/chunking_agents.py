"""Agent classes for distributed repository processing using Solace Agent Mesh."""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..utils.logger import get_logger
from ..agents.solace_agent import SolaceAgent

logger = get_logger(__name__)


class RepositoryChunkerAgent:
    """Agent responsible for chunking large repositories into manageable pieces."""
    
    def __init__(self, max_chunk_size: int = 50, max_file_size: int = 1048576):
        self.max_chunk_size = max_chunk_size
        self.max_file_size = max_file_size
        self.agent_id = f"chunker_{uuid.uuid4().hex[:8]}"
        
    async def process_chunking_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a repository chunking request."""
        logger.info(f"Agent {self.agent_id}: Processing chunking request")
        
        repository_data = request.get('repository_data', {})
        chunk_config = request.get('chunk_config', {})
        correlation_id = request.get('correlation_id', str(uuid.uuid4()))
        
        # Override default settings with request configuration
        chunk_size = chunk_config.get('chunk_size', self.max_chunk_size)
        
        try:
            # Extract files from repository data
            files = self._extract_files_from_repository(repository_data)
            
            # Filter files by size and type
            valid_files = self._filter_valid_files(files)
            
            # Create chunks
            chunks = self._create_file_chunks(valid_files, chunk_size)
            
            # Add metadata to chunks
            enriched_chunks = self._enrich_chunks_with_metadata(chunks, repository_data)
            
            response = {
                "success": True,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "chunks": enriched_chunks,
                "total_chunks": len(enriched_chunks),
                "total_files": len(valid_files),
                "filtered_files": len(files) - len(valid_files),
                "processing_time": time.time() - request.get('timestamp', time.time())
            }
            
            logger.info(f"Agent {self.agent_id}: Created {len(enriched_chunks)} chunks from {len(valid_files)} files")
            return response
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Chunking failed: {e}")
            return {
                "success": False,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    def _extract_files_from_repository(self, repository_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract file information from repository data."""
        raw_content = repository_data.get('raw_content', '')
        files = []
        
        current_file = None
        current_content = []
        in_file_section = False
        
        for line in raw_content.split('\n'):
            line_stripped = line.strip()
            
            # Detect file headers
            if line_stripped.startswith('FILE:') or line_stripped.startswith('File:'):
                # Save previous file if exists
                if current_file and current_content:
                    files.append({
                        "path": current_file,
                        "content": '\n'.join(current_content),
                        "size": len('\n'.join(current_content)),
                        "language": self._detect_language(current_file)
                    })
                
                # Start new file
                current_file = line_stripped.split(':', 1)[1].strip()
                current_content = []
                in_file_section = True
                
            elif line_stripped.startswith('=') and len(line_stripped) > 10:
                # End of file section
                in_file_section = False
                
            elif in_file_section and current_file:
                current_content.append(line)
        
        # Add final file
        if current_file and current_content:
            files.append({
                "path": current_file,
                "content": '\n'.join(current_content),
                "size": len('\n'.join(current_content)),
                "language": self._detect_language(current_file)
            })
        
        return files
    
    def _filter_valid_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter files based on size and type criteria."""
        valid_files = []
        
        for file_info in files:
            # Skip if file is too large
            if file_info['size'] > self.max_file_size:
                logger.debug(f"Skipping large file: {file_info['path']} ({file_info['size']} bytes)")
                continue
                
            # Skip binary files and certain file types
            if self._is_binary_file(file_info['path']):
                logger.debug(f"Skipping binary file: {file_info['path']}")
                continue
                
            # Skip empty files
            if file_info['size'] == 0:
                logger.debug(f"Skipping empty file: {file_info['path']}")
                continue
                
            valid_files.append(file_info)
        
        return valid_files
    
    def _create_file_chunks(self, files: List[Dict[str, Any]], chunk_size: int) -> List[Dict[str, Any]]:
        """Create chunks from the file list."""
        chunks = []
        
        for i in range(0, len(files), chunk_size):
            chunk_files = files[i:i + chunk_size]
            
            chunk = {
                "chunk_id": len(chunks),
                "files": chunk_files,
                "file_count": len(chunk_files),
                "total_size": sum(f['size'] for f in chunk_files),
                "languages": list(set(f['language'] for f in chunk_files)),
                "created_at": time.time()
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _enrich_chunks_with_metadata(self, chunks: List[Dict[str, Any]], repository_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add repository metadata to chunks."""
        for chunk in chunks:
            chunk.update({
                "repository_url": repository_data.get('repository_url', ''),
                "source_language": repository_data.get('language_breakdown', {}).get('primary_language', 'unknown'),
                "complexity_estimate": self._estimate_chunk_complexity(chunk),
                "priority": self._calculate_chunk_priority(chunk)
            })
        
        return chunks
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file path."""
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
            '.php': 'php'
        }
        
        ext = Path(file_path).suffix.lower()
        return extension_map.get(ext, "unknown")
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is likely binary based on extension."""
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.o',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.mp4', '.wav', '.avi', '.mov',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext in binary_extensions
    
    def _estimate_chunk_complexity(self, chunk: Dict[str, Any]) -> str:
        """Estimate the complexity of migrating this chunk."""
        total_size = chunk['total_size']
        file_count = chunk['file_count']
        languages = chunk['languages']
        
        # Simple complexity heuristic
        if total_size > 50000 or file_count > 20 or len(languages) > 3:
            return "high"
        elif total_size > 10000 or file_count > 10 or len(languages) > 1:
            return "medium"
        else:
            return "low"
    
    def _calculate_chunk_priority(self, chunk: Dict[str, Any]) -> int:
        """Calculate processing priority for the chunk (1=highest, 10=lowest)."""
        # Prioritize chunks with main/core files
        main_file_keywords = ['main', 'index', 'app', 'core', 'init']
        has_main_files = any(
            any(keyword in file_info['path'].lower() for keyword in main_file_keywords)
            for file_info in chunk['files']
        )
        
        if has_main_files:
            return 1
        elif 'test' in str(chunk['files']).lower():
            return 8  # Tests lower priority
        else:
            return 5  # Medium priority


class CodeAnalyzerAgent:
    """Agent responsible for analyzing code structure and dependencies."""
    
    def __init__(self):
        self.agent_id = f"analyzer_{uuid.uuid4().hex[:8]}"
        
    async def process_analysis_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a code analysis request for a chunk."""
        logger.info(f"Agent {self.agent_id}: Processing analysis request")
        
        chunk_data = request.get('chunk_data', {})
        correlation_id = request.get('correlation_id', str(uuid.uuid4()))
        
        try:
            analysis_results = []
            
            for file_info in chunk_data.get('files', []):
                file_analysis = await self._analyze_file(file_info)
                analysis_results.append(file_analysis)
            
            # Aggregate chunk-level analysis
            chunk_analysis = self._aggregate_chunk_analysis(analysis_results, chunk_data)
            
            response = {
                "success": True,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "chunk_id": chunk_data.get('chunk_id', 0),
                "file_analyses": analysis_results,
                "chunk_analysis": chunk_analysis,
                "processing_time": time.time() - request.get('timestamp', time.time())
            }
            
            logger.info(f"Agent {self.agent_id}: Analyzed {len(analysis_results)} files")
            return response
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Analysis failed: {e}")
            return {
                "success": False,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    async def _analyze_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file."""
        await asyncio.sleep(0.05)  # Simulate analysis time
        
        content = file_info.get('content', '')
        language = file_info.get('language', 'unknown')
        
        analysis = {
            "file_path": file_info.get('path', ''),
            "language": language,
            "size": file_info.get('size', 0),
            "line_count": len(content.split('\n')) if content else 0,
            "complexity": self._estimate_file_complexity(content, language),
            "dependencies": self._extract_dependencies(content, language),
            "functions": self._extract_functions(content, language),
            "classes": self._extract_classes(content, language),
            "migration_notes": self._generate_migration_notes(content, language)
        }
        
        return analysis
    
    def _estimate_file_complexity(self, content: str, language: str) -> str:
        """Estimate file complexity based on content analysis."""
        if not content:
            return "low"
            
        lines = content.split('\n')
        line_count = len(lines)
        
        # Count complexity indicators
        complexity_indicators = 0
        
        if language == 'python':
            complexity_indicators += content.count('class ')
            complexity_indicators += content.count('def ')
            complexity_indicators += content.count('if ')
            complexity_indicators += content.count('for ')
            complexity_indicators += content.count('while ')
        elif language == 'javascript':
            complexity_indicators += content.count('function ')
            complexity_indicators += content.count('class ')
            complexity_indicators += content.count('if (')
            complexity_indicators += content.count('for (')
            complexity_indicators += content.count('while (')
        
        # Simple heuristic
        if line_count > 200 or complexity_indicators > 20:
            return "high"
        elif line_count > 50 or complexity_indicators > 5:
            return "medium"
        else:
            return "low"
    
    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """Extract dependencies from file content."""
        dependencies = []
        
        if language == 'python':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    dependencies.append(line)
        elif language == 'javascript':
            for line in content.split('\n'):
                line = line.strip()
                if 'require(' in line or line.startswith('import '):
                    dependencies.append(line)
        
        return dependencies
    
    def _extract_functions(self, content: str, language: str) -> List[str]:
        """Extract function names from file content."""
        functions = []
        
        if language == 'python':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('def '):
                    func_name = line.split('(')[0].replace('def ', '').strip()
                    functions.append(func_name)
        elif language == 'javascript':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('function '):
                    func_name = line.split('(')[0].replace('function ', '').strip()
                    functions.append(func_name)
        
        return functions
    
    def _extract_classes(self, content: str, language: str) -> List[str]:
        """Extract class names from file content."""
        classes = []
        
        if language == 'python':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('class '):
                    class_name = line.split(':')[0].replace('class ', '').strip()
                    classes.append(class_name)
        elif language == 'javascript':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('class '):
                    class_name = line.split(' ')[1].split('{')[0].strip()
                    classes.append(class_name)
        
        return classes
    
    def _generate_migration_notes(self, content: str, language: str) -> List[str]:
        """Generate migration-specific notes for the file."""
        notes = []
        
        if language == 'python':
            if 'async def' in content:
                notes.append("Contains async functions - may need Promise handling in JavaScript")
            if '__init__' in content:
                notes.append("Contains constructor - will need JavaScript constructor syntax")
            if 'self.' in content:
                notes.append("Uses instance variables - translate to 'this.' in JavaScript")
        
        elif language == 'javascript':
            if 'async function' in content or 'await ' in content:
                notes.append("Contains async/await - may translate to Python asyncio")
            if 'this.' in content:
                notes.append("Uses 'this' - will translate to 'self' in Python")
            if 'prototype.' in content:
                notes.append("Uses prototype - will need class methods in Python")
        
        return notes
    
    def _aggregate_chunk_analysis(self, file_analyses: List[Dict[str, Any]], chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate file analyses into chunk-level insights."""
        total_lines = sum(analysis['line_count'] for analysis in file_analyses)
        languages = list(set(analysis['language'] for analysis in file_analyses))
        
        all_dependencies = []
        all_functions = []
        all_classes = []
        
        for analysis in file_analyses:
            all_dependencies.extend(analysis['dependencies'])
            all_functions.extend(analysis['functions'])
            all_classes.extend(analysis['classes'])
        
        complexity_counts = {}
        for analysis in file_analyses:
            complexity = analysis['complexity']
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        return {
            "total_files": len(file_analyses),
            "total_lines": total_lines,
            "languages": languages,
            "unique_dependencies": list(set(all_dependencies)),
            "total_functions": len(all_functions),
            "total_classes": len(all_classes),
            "complexity_distribution": complexity_counts,
            "estimated_migration_time": self._estimate_migration_time(file_analyses),
            "migration_complexity": chunk_data.get('complexity_estimate', 'medium')
        }
    
    def _estimate_migration_time(self, file_analyses: List[Dict[str, Any]]) -> float:
        """Estimate migration time in minutes based on analysis."""
        base_time_per_file = 2.0  # minutes
        
        total_time = 0
        for analysis in file_analyses:
            file_time = base_time_per_file
            
            # Adjust based on complexity
            if analysis['complexity'] == 'high':
                file_time *= 3
            elif analysis['complexity'] == 'medium':
                file_time *= 1.5
            
            # Adjust based on size
            if analysis['line_count'] > 100:
                file_time *= 1.5
            
            total_time += file_time
        
        return round(total_time, 1)


class CodeMigratorAgent:
    """Agent responsible for migrating code using AI models."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.agent_id = f"migrator_{uuid.uuid4().hex[:8]}"
        self.solace_agent = SolaceAgent(api_key=api_key)
        
    async def process_migration_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a code migration request for analyzed chunks."""
        logger.info(f"Agent {self.agent_id}: Processing migration request")
        
        chunk_analysis = request.get('chunk_analysis', {})
        target_language = request.get('target_language', 'javascript')
        correlation_id = request.get('correlation_id', str(uuid.uuid4()))
        
        try:
            migration_results = []
            
            file_analyses = chunk_analysis.get('file_analyses', [])
            for file_analysis in file_analyses:
                migration_result = await self._migrate_file(file_analysis, target_language)
                migration_results.append(migration_result)
            
            # Aggregate migration results
            chunk_migration = self._aggregate_migration_results(migration_results, chunk_analysis)
            
            response = {
                "success": True,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "chunk_id": chunk_analysis.get('chunk_id', 0),
                "file_migrations": migration_results,
                "chunk_migration": chunk_migration,
                "processing_time": time.time() - request.get('timestamp', time.time())
            }
            
            logger.info(f"Agent {self.agent_id}: Migrated {len(migration_results)} files")
            return response
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Migration failed: {e}")
            return {
                "success": False,
                "correlation_id": correlation_id,
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    async def _migrate_file(self, file_analysis: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """Migrate a single file based on its analysis."""
        file_path = file_analysis.get('file_path', '')
        source_language = file_analysis.get('language', 'unknown')
        
        # Get the original content (this would need to be passed in the request)
        # For now, we'll simulate based on the analysis
        simulated_content = self._generate_content_from_analysis(file_analysis)
        
        try:
            # Use the Solace agent for migration
            migration_result = self.solace_agent.migrate_code(
                source_code=simulated_content,
                source_language=source_language,
                target_language=target_language
            )
            
            return {
                "file_path": file_path,
                "source_language": source_language,
                "target_language": target_language,
                "success": migration_result["success"],
                "migrated_code": migration_result.get("migrated_code", ""),
                "confidence": migration_result.get("confidence", 0.0),
                "warnings": migration_result.get("warnings", []),
                "suggestions": migration_result.get("suggestions", []),
                "migration_notes": file_analysis.get('migration_notes', [])
            }
            
        except Exception as e:
            return {
                "file_path": file_path,
                "success": False,
                "error": str(e)
            }
    
    def _generate_content_from_analysis(self, file_analysis: Dict[str, Any]) -> str:
        """Generate simulated content based on file analysis."""
        # This is a simplified approach for demonstration
        # In a real implementation, the original content would be passed through
        
        language = file_analysis.get('language', 'python')
        functions = file_analysis.get('functions', [])
        classes = file_analysis.get('classes', [])
        
        if language == 'python':
            content = "# Python code\n"
            for class_name in classes:
                content += f"class {class_name}:\n    pass\n\n"
            for func_name in functions:
                content += f"def {func_name}():\n    pass\n\n"
        else:
            content = "// Generated content\n"
            for class_name in classes:
                content += f"class {class_name} {{}}\n\n"
            for func_name in functions:
                content += f"function {func_name}() {{}}\n\n"
        
        return content
    
    def _aggregate_migration_results(self, migration_results: List[Dict[str, Any]], chunk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate migration results for the chunk."""
        total_files = len(migration_results)
        successful_migrations = len([r for r in migration_results if r['success']])
        failed_migrations = total_files - successful_migrations
        
        all_warnings = []
        all_suggestions = []
        
        for result in migration_results:
            all_warnings.extend(result.get('warnings', []))
            all_suggestions.extend(result.get('suggestions', []))
        
        average_confidence = sum(r.get('confidence', 0) for r in migration_results) / total_files if total_files > 0 else 0
        
        return {
            "total_files": total_files,
            "successful_migrations": successful_migrations,
            "failed_migrations": failed_migrations,
            "success_rate": successful_migrations / total_files if total_files > 0 else 0,
            "average_confidence": round(average_confidence, 2),
            "unique_warnings": list(set(all_warnings)),
            "unique_suggestions": list(set(all_suggestions)),
            "chunk_complexity": chunk_analysis.get('migration_complexity', 'medium'),
            "estimated_vs_actual_time": {
                "estimated": chunk_analysis.get('estimated_migration_time', 0),
                "actual": time.time() - chunk_analysis.get('start_time', time.time())
            }
        }