"""Code analysis module for understanding repository structure and content."""

import os
import ast
import json
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, asdict

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    path: str
    language: str
    lines_of_code: int
    complexity_score: float
    functions: List[str]
    classes: List[str]
    imports: List[str]
    dependencies: List[str]


@dataclass
class RepositoryAnalysis:
    """Complete analysis of a repository."""
    repo_path: str
    total_files: int
    total_lines: int
    languages: Dict[str, int]
    file_analyses: List[FileAnalysis]
    dependency_graph: Dict[str, List[str]]
    architecture_patterns: List[str]


class CodeAnalyzer:
    """Analyzes code structure and patterns for migration planning."""
    
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
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.m': 'matlab',
        '.sh': 'bash',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml'
    }
    
    def __init__(self):
        self.ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        
    def analyze_repository(self, repo_path: str) -> RepositoryAnalysis:
        """Analyze the complete repository structure and content.
        
        Args:
            repo_path: Path to the repository directory
            
        Returns:
            RepositoryAnalysis object with complete analysis
        """
        logger.info(f"Starting repository analysis: {repo_path}")
        
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
            
        file_analyses = []
        language_counts = {}
        total_lines = 0
        
        # Walk through all files in the repository
        for file_path in self._get_source_files(repo_path_obj):
            try:
                file_analysis = self._analyze_file(file_path)
                file_analyses.append(file_analysis)
                
                # Update statistics
                language = file_analysis.language
                language_counts[language] = language_counts.get(language, 0) + 1
                total_lines += file_analysis.lines_of_code
                
            except Exception as e:
                logger.warning(f"Error analyzing file {file_path}: {e}")
                
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(file_analyses)
        
        # Detect architecture patterns
        architecture_patterns = self._detect_architecture_patterns(file_analyses)
        
        analysis = RepositoryAnalysis(
            repo_path=str(repo_path),
            total_files=len(file_analyses),
            total_lines=total_lines,
            languages=language_counts,
            file_analyses=file_analyses,
            dependency_graph=dependency_graph,
            architecture_patterns=architecture_patterns
        )
        
        logger.info(f"Repository analysis complete. Found {len(file_analyses)} files in {len(language_counts)} languages")
        return analysis
        
    def _get_source_files(self, repo_path: Path) -> List[Path]:
        """Get all source code files in the repository."""
        source_files = []
        
        for file_path in repo_path.rglob('*'):
            # Skip directories and ignored patterns
            if file_path.is_dir():
                continue
                
            if any(ignore in str(file_path) for ignore in self.ignore_patterns):
                continue
                
            # Check if it's a source code file
            if file_path.suffix.lower() in self.LANGUAGE_EXTENSIONS:
                source_files.append(file_path)
                
        return source_files
        
    def _analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single source code file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            content = ""
            
        language = self.LANGUAGE_EXTENSIONS.get(file_path.suffix.lower(), 'unknown')
        lines_of_code = len([line for line in content.splitlines() if line.strip()])
        
        # Language-specific analysis
        if language == 'python':
            return self._analyze_python_file(file_path, content, lines_of_code)
        else:
            return self._analyze_generic_file(file_path, content, language, lines_of_code)
            
    def _analyze_python_file(self, file_path: Path, content: str, lines_of_code: int) -> FileAnalysis:
        """Detailed analysis for Python files."""
        functions = []
        classes = []
        imports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except SyntaxError:
            logger.warning(f"Syntax error in Python file: {file_path}")
            
        complexity_score = self._calculate_complexity_score(content, functions, classes)
        
        return FileAnalysis(
            path=str(file_path),
            language='python',
            lines_of_code=lines_of_code,
            complexity_score=complexity_score,
            functions=functions,
            classes=classes,
            imports=imports,
            dependencies=imports
        )
        
    def _analyze_generic_file(self, file_path: Path, content: str, language: str, lines_of_code: int) -> FileAnalysis:
        """Generic analysis for non-Python files."""
        # Basic pattern matching for common constructs
        functions = []
        classes = []
        imports = []
        
        # TODO: Implement language-specific parsers
        # For now, just return basic info
        
        complexity_score = min(lines_of_code / 50.0, 10.0)  # Simple heuristic
        
        return FileAnalysis(
            path=str(file_path),
            language=language,
            lines_of_code=lines_of_code,
            complexity_score=complexity_score,
            functions=functions,
            classes=classes,
            imports=imports,
            dependencies=imports
        )
        
    def _calculate_complexity_score(self, content: str, functions: List[str], classes: List[str]) -> float:
        """Calculate a complexity score for the file."""
        # Simple complexity metrics
        cyclomatic_complexity = content.count('if ') + content.count('for ') + content.count('while ')
        function_complexity = len(functions) * 0.5
        class_complexity = len(classes) * 1.0
        
        return min(cyclomatic_complexity + function_complexity + class_complexity, 10.0)
        
    def _build_dependency_graph(self, file_analyses: List[FileAnalysis]) -> Dict[str, List[str]]:
        """Build a dependency graph from file analyses."""
        dependency_graph = {}
        
        for analysis in file_analyses:
            file_name = Path(analysis.path).name
            dependency_graph[file_name] = analysis.dependencies
            
        return dependency_graph
        
    def _detect_architecture_patterns(self, file_analyses: List[FileAnalysis]) -> List[str]:
        """Detect common architecture patterns in the codebase."""
        patterns = []
        
        # Check for common patterns based on file structure and naming
        file_names = [Path(analysis.path).name.lower() for analysis in file_analyses]
        
        if any('model' in name for name in file_names):
            patterns.append('MVC Pattern')
            
        if any('controller' in name for name in file_names):
            patterns.append('Controller Pattern')
            
        if any('service' in name for name in file_names):
            patterns.append('Service Layer Pattern')
            
        if any('factory' in name for name in file_names):
            patterns.append('Factory Pattern')
            
        # Check for framework patterns
        languages = [analysis.language for analysis in file_analyses]
        if 'python' in languages:
            if any('views.py' in analysis.path for analysis in file_analyses):
                patterns.append('Django Framework')
            if any('app.py' in analysis.path for analysis in file_analyses):
                patterns.append('Flask Framework')
                
        return patterns
        
    def save_analysis(self, analysis: RepositoryAnalysis, output_path: str) -> None:
        """Save analysis results to a JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(analysis), f, indent=2)
            
        logger.info(f"Analysis saved to: {output_file}")