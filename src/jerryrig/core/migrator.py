"""Code migration engine using AI agents."""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

from ..agents.solace_agent import SolaceAgent
from ..core.analyzer import RepositoryParser, GitIngestAnalysis
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MigrationPlan:
    """Plan for migrating code from one language to another."""
    source_language: str
    target_language: str
    files_to_migrate: List[str]
    dependency_order: List[str]
    estimated_complexity: float
    migration_strategy: str


@dataclass
class MigrationResult:
    """Result of a code migration operation."""
    source_file: str
    target_file: str
    source_language: str
    target_language: str
    migration_success: bool
    confidence_score: float
    warnings: List[str]
    errors: List[str]


class CodeMigrator:
    """Migrates code between programming languages using AI agents."""
    
    # Language extension mapping
    LANGUAGE_EXTENSIONS = {
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
    
    SUPPORTED_LANGUAGES = {
        'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 
        'csharp', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin'
    }
    
    def __init__(self):
        self.analyzer = RepositoryParser()
        self.solace_agent = SolaceAgent()
        
    def migrate_code(self, source_path: str, target_language: str, output_dir: str = "./migrated") -> str:
        """Migrate code from source to target language.
        
        Args:
            source_path: Path to source code (file or directory)
            target_language: Target programming language
            output_dir: Output directory for migrated code
            
        Returns:
            Path to the migrated code directory
        """
        logger.info(f"Starting code migration to {target_language}")
        
        if target_language.lower() not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported target language: {target_language}")
            
        source_path_obj = Path(source_path)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if source_path_obj.is_file():
                # Migrate single file
                result = self._migrate_single_file(source_path_obj, target_language, output_path)
                logger.info(f"Single file migration complete: {result.target_file}")
                
            else:
                # Migrate entire repository/directory
                migration_plan = self._create_migration_plan(source_path_obj, target_language)
                results = self._execute_migration_plan(migration_plan, output_path)
                logger.info(f"Repository migration complete: {len(results)} files migrated")
                
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            raise
            
    def _create_migration_plan(self, source_path: Path, target_language: str) -> MigrationPlan:
        """Create a migration plan for the source code."""
        logger.info("Creating migration plan...")
        
        # Analyze the source repository
        analysis = self.analyzer.analyze_repository(str(source_path))
        
        # Determine primary source language
        if not analysis.languages:
            raise ValueError("No source code files found")
            
        primary_language = max(analysis.languages.keys(), key=lambda k: analysis.languages[k])
        logger.info(f"Primary source language detected: {primary_language}")
        
        # Get files to migrate (filter by primary language)
        files_to_migrate = [
            fa.path for fa in analysis.file_analyses 
            if fa.language == primary_language
        ]
        
        # Create dependency order based on complexity and dependencies
        dependency_order = self._calculate_migration_order(analysis.file_analyses, files_to_migrate)
        
        # Estimate complexity
        total_complexity = sum(fa.complexity_score for fa in analysis.file_analyses if fa.path in files_to_migrate)
        estimated_complexity = total_complexity / len(files_to_migrate) if files_to_migrate else 0
        
        # Determine migration strategy
        migration_strategy = self._determine_migration_strategy(primary_language, target_language, analysis)
        
        return MigrationPlan(
            source_language=primary_language,
            target_language=target_language,
            files_to_migrate=files_to_migrate,
            dependency_order=dependency_order,
            estimated_complexity=estimated_complexity,
            migration_strategy=migration_strategy
        )
        
    def _calculate_migration_order(self, file_analyses: List, files_to_migrate: List[str]) -> List[str]:
        """Calculate the optimal order for migrating files based on dependencies."""
        # Simple approach: migrate files with fewer dependencies first
        file_complexity = {}
        
        for fa in file_analyses:
            if fa.path in files_to_migrate:
                # Lower complexity = fewer dependencies + lower complexity score
                complexity = len(fa.dependencies) + fa.complexity_score
                file_complexity[fa.path] = complexity
                
        # Sort by complexity (ascending)
        sorted_files = sorted(file_complexity.items(), key=lambda x: x[1])
        return [file_path for file_path, _ in sorted_files]
        
    def _determine_migration_strategy(self, source_lang: str, target_lang: str, analysis) -> str:
        """Determine the best migration strategy based on languages and code structure."""
        # Simple strategy selection based on language pairs
        if source_lang == 'python' and target_lang == 'javascript':
            return 'syntax_mapping_with_async_conversion'
        elif source_lang == 'javascript' and target_lang == 'python':
            return 'callback_to_coroutine_conversion'
        elif source_lang in ['c', 'cpp'] and target_lang in ['rust', 'go']:
            return 'memory_safe_conversion'
        elif source_lang == 'java' and target_lang in ['kotlin', 'scala']:
            return 'jvm_compatible_conversion'
        else:
            return 'generic_syntax_mapping'
            
    def _execute_migration_plan(self, plan: MigrationPlan, output_path: Path) -> List[MigrationResult]:
        """Execute the migration plan."""
        logger.info(f"Executing migration plan: {len(plan.files_to_migrate)} files to migrate")
        
        results = []
        
        for file_path in plan.dependency_order:
            try:
                source_file = Path(file_path)
                result = self._migrate_single_file(source_file, plan.target_language, output_path)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error migrating file {file_path}: {e}")
                error_result = MigrationResult(
                    source_file=file_path,
                    target_file="",
                    source_language=plan.source_language,
                    target_language=plan.target_language,
                    migration_success=False,
                    confidence_score=0.0,
                    warnings=[],
                    errors=[str(e)]
                )
                results.append(error_result)
                
        return results
        
    def _migrate_single_file(self, source_file: Path, target_language: str, output_path: Path) -> MigrationResult:
        """Migrate a single source file to the target language."""
        logger.info(f"Migrating file: {source_file.name}")
        
        try:
            # Read source code
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
                
            # Determine source language
            source_language = self.LANGUAGE_EXTENSIONS.get(source_file.suffix.lower(), 'unknown')
            
            # Use Solace agent to perform migration
            migration_result = self.solace_agent.migrate_code(
                source_code=source_code,
                source_language=source_language,
                target_language=target_language
            )
            
            # Generate target file name
            target_extension = self._get_file_extension(target_language)
            target_file_name = source_file.stem + target_extension
            target_file_path = output_path / target_file_name
            
            # Save migrated code
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(migration_result['migrated_code'])
                
            return MigrationResult(
                source_file=str(source_file),
                target_file=str(target_file_path),
                source_language=source_language,
                target_language=target_language,
                migration_success=migration_result['success'],
                confidence_score=migration_result['confidence'],
                warnings=migration_result.get('warnings', []),
                errors=migration_result.get('errors', [])
            )
            
        except Exception as e:
            logger.error(f"Error migrating file {source_file}: {e}")
            return MigrationResult(
                source_file=str(source_file),
                target_file="",
                source_language="unknown",
                target_language=target_language,
                migration_success=False,
                confidence_score=0.0,
                warnings=[],
                errors=[str(e)]
            )
            
    def _get_file_extension(self, language: str) -> str:
        """Get the appropriate file extension for a programming language."""
        extension_map = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'java': '.java',
            'cpp': '.cpp',
            'c': '.c',
            'csharp': '.cs',
            'go': '.go',
            'rust': '.rs',
            'ruby': '.rb',
            'php': '.php',
            'swift': '.swift',
            'kotlin': '.kt',
            'scala': '.scala'
        }
        return extension_map.get(language.lower(), '.txt')
        
    def save_migration_report(self, results: List[MigrationResult], output_path: str) -> None:
        """Save a detailed migration report."""
        report = {
            "migration_summary": {
                "total_files": len(results),
                "successful_migrations": sum(1 for r in results if r.migration_success),
                "failed_migrations": sum(1 for r in results if not r.migration_success),
                "average_confidence": sum(r.confidence_score for r in results) / len(results) if results else 0
            },
            "detailed_results": [
                {
                    "source_file": r.source_file,
                    "target_file": r.target_file,
                    "success": r.migration_success,
                    "confidence": r.confidence_score,
                    "warnings": r.warnings,
                    "errors": r.errors
                }
                for r in results
            ]
        }
        
        report_path = Path(output_path)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Migration report saved to: {report_path}")
        
    async def migrate_code_async(self, source_code: str, source_language: str, target_language: str) -> Dict[str, Any]:
        """
        Async version of migrate_code for SAM integration - migrates just the code string
        """
        import asyncio
        
        def _migrate_code_string():
            try:
                logger.info(f"Migrating code from {source_language} to {target_language}")
                
                if target_language.lower() not in self.SUPPORTED_LANGUAGES:
                    raise ValueError(f"Unsupported target language: {target_language}")
                
                # Use SolaceAgent for AI-powered migration
                migration_result = self.solace_agent.migrate_code(
                    source_code=source_code,
                    source_language=source_language,
                    target_language=target_language
                )
                
                return {
                    'success': True,
                    'migrated_code': migration_result['migrated_code'],
                    'source_language': source_language,
                    'target_language': target_language,
                    'confidence': migration_result.get('confidence', 0.8),
                    'warnings': migration_result.get('warnings', []),
                    'errors': migration_result.get('errors', [])
                }
                
            except Exception as e:
                logger.error(f"Migration failed: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'migrated_code': '',
                    'confidence': 0.0
                }
        
        return await asyncio.to_thread(_migrate_code_string)
    
    async def generate_migration_plan_async(self, source_files: List[str], target_language: str) -> Dict[str, Any]:
        """
        Generate a migration plan for multiple source files (async version for SAM)
        """
        import asyncio
        
        def _generate_plan():
            try:
                if target_language.lower() not in self.SUPPORTED_LANGUAGES:
                    raise ValueError(f"Unsupported target language: {target_language}")
                
                plan = {
                    'source_files': source_files,
                    'target_language': target_language,
                    'migration_steps': [],
                    'estimated_time_minutes': 0,
                    'complexity': 'medium',
                    'total_files': len(source_files)
                }
                
                for file_path in source_files:
                    # Determine source language from file extension
                    file_ext = Path(file_path).suffix.lower()
                    source_lang = self.LANGUAGE_EXTENSIONS.get(file_ext, 'unknown')
                    
                    # Generate target filename
                    target_ext = self._get_file_extension(target_language)
                    target_file = str(Path(file_path).with_suffix(target_ext))
                    
                    step = {
                        'source_file': file_path,
                        'target_file': target_file,
                        'source_language': source_lang,
                        'target_language': target_language,
                        'action': 'migrate',
                        'estimated_time_minutes': 5,
                        'complexity': 'medium'
                    }
                    plan['migration_steps'].append(step)
                    plan['estimated_time_minutes'] += 5
                
                # Determine overall complexity
                if len(source_files) > 20:
                    plan['complexity'] = 'high'
                elif len(source_files) < 5:
                    plan['complexity'] = 'low'
                
                return plan
                
            except Exception as e:
                logger.error(f"Plan generation failed: {str(e)}")
                return {
                    'error': str(e),
                    'source_files': source_files,
                    'target_language': target_language,
                    'migration_steps': []
                }
        
        return await asyncio.to_thread(_generate_plan)