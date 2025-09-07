"""
Code Analyzer Agent for Solace Agent Mesh
Analyzes code structure, dependencies, and patterns within chunks
"""

import json
import logging
import re
import ast
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path

def process(input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Analyze code structure and dependencies within a chunk
    
    Args:
        input_data: Input data containing analyze request
        **kwargs: Additional configuration including shared_config
        
    Returns:
        Code analysis results
    """
    logger = logging.getLogger(__name__)
    shared_config = kwargs.get('shared_config', {})
    
    try:
        session_id = input_data.get('session_id')
        correlation_id = input_data.get('correlation_id')
        chunk_id = input_data.get('chunk_id')
        chunk_index = input_data.get('chunk_index', 0)
        total_chunks = input_data.get('total_chunks', 1)
        source_language = input_data.get('source_language')
        operation_type = input_data.get('operation_type', 'analysis')
        files = input_data.get('files', [])
        
        logger.info(f"Analyzing chunk {chunk_id} ({len(files)} files)")
        
        # Analyze each file in the chunk
        file_analyses = []
        chunk_dependencies = set()
        chunk_complexity_score = 0
        
        for file_info in files:
            file_analysis = _analyze_file(
                file_info, 
                source_language, 
                shared_config, 
                logger
            )
            file_analyses.append(file_analysis)
            
            # Aggregate dependencies
            chunk_dependencies.update(file_analysis.get('dependencies', []))
            chunk_complexity_score += file_analysis.get('complexity_score', 0)
        
        # Analyze inter-file relationships within chunk
        relationships = _analyze_relationships(file_analyses, source_language, logger)
        
        # Generate migration readiness assessment
        migration_readiness = _assess_migration_readiness(
            file_analyses, 
            source_language, 
            relationships, 
            logger
        )
        
        # Create comprehensive analysis result
        analysis_result = {
            'session_id': session_id,
            'correlation_id': correlation_id,
            'chunk_id': chunk_id,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'operation_type': operation_type,
            'source_language': source_language,
            'file_analyses': file_analyses,
            'chunk_summary': {
                'total_files': len(files),
                'total_lines': sum(f.get('lines', 0) for f in file_analyses),
                'complexity_score': chunk_complexity_score,
                'dependencies': list(chunk_dependencies),
                'relationships': relationships,
                'migration_readiness': migration_readiness
            },
            'timestamp': datetime.now().isoformat(),
            'status': 'analyzed'
        }
        
        logger.info(f"Completed analysis for chunk {chunk_id}")
        
        return {
            'analysis': analysis_result,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Code analysis failed: {e}")
        return {
            'error': str(e),
            'status': 'failed',
            'session_id': input_data.get('session_id'),
            'correlation_id': input_data.get('correlation_id'),
            'chunk_id': input_data.get('chunk_id')
        }

def _analyze_file(file_info: Dict[str, Any], source_language: str, config: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Analyze individual file structure and patterns"""
    file_path = file_info.get('path', '')
    content = file_info.get('content', '')
    extension = file_info.get('extension', '')
    
    analysis = {
        'path': file_path,
        'extension': extension,
        'size': len(content),
        'lines': len(content.splitlines()),
        'complexity_score': 0,
        'dependencies': [],
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': [],
        'issues': []
    }
    
    try:
        if source_language == 'python':
            analysis.update(_analyze_python_file(content, logger))
        elif source_language in ['javascript', 'typescript']:
            analysis.update(_analyze_javascript_file(content, logger))
        elif source_language == 'java':
            analysis.update(_analyze_java_file(content, logger))
        else:
            # Generic analysis for unsupported languages
            analysis.update(_analyze_generic_file(content, logger))
            
    except Exception as e:
        logger.warning(f"Failed to analyze file {file_path}: {e}")
        analysis['issues'].append(f"Analysis failed: {e}")
    
    return analysis

def _analyze_python_file(content: str, logger: logging.Logger) -> Dict[str, Any]:
    """Analyze Python file using AST"""
    analysis = {
        'complexity_score': 0,
        'dependencies': [],
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': []
    }
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis['imports'].append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname
                    })
                    analysis['dependencies'].append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    analysis['imports'].append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname
                    })
                    if module:
                        analysis['dependencies'].append(module)
            
            elif isinstance(node, ast.FunctionDef):
                analysis['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': len(node.args.args),
                    'decorators': len(node.decorator_list),
                    'is_async': isinstance(node, ast.AsyncFunctionDef)
                })
                analysis['complexity_score'] += 2  # Base complexity per function
            
            elif isinstance(node, ast.ClassDef):
                analysis['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'bases': len(node.bases),
                    'decorators': len(node.decorator_list),
                    'methods': len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                })
                analysis['complexity_score'] += 5  # Base complexity per class
            
            elif isinstance(node, (ast.For, ast.While, ast.If)):
                analysis['complexity_score'] += 1  # Control flow complexity
    
        # Detect patterns
        if any('async' in imp['name'] for imp in analysis['imports'] if 'name' in imp):
            analysis['patterns'].append('async_programming')
        
        if any('test' in func['name'].lower() for func in analysis['functions']):
            analysis['patterns'].append('unit_testing')
            
    except SyntaxError as e:
        logger.warning(f"Python syntax error: {e}")
        analysis['issues'] = [f"Syntax error: {e}"]
    
    return analysis

def _analyze_javascript_file(content: str, logger: logging.Logger) -> Dict[str, Any]:
    """Analyze JavaScript/TypeScript file using regex patterns"""
    analysis = {
        'complexity_score': 0,
        'dependencies': [],
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': []
    }
    
    # Find imports/requires
    import_patterns = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',  # ES6 imports
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',      # CommonJS requires
        r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'        # Dynamic imports
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            analysis['dependencies'].append(match)
            analysis['imports'].append({
                'type': 'import',
                'module': match
            })
    
    # Find functions
    function_patterns = [
        r'function\s+(\w+)\s*\(',                    # Function declarations
        r'(\w+)\s*:\s*function\s*\(',               # Object method definitions
        r'(\w+)\s*=>\s*',                           # Arrow functions
        r'async\s+function\s+(\w+)\s*\('            # Async functions
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match[0] else match[1]
            analysis['functions'].append({
                'name': match,
                'type': 'function'
            })
            analysis['complexity_score'] += 2
    
    # Find classes
    class_matches = re.findall(r'class\s+(\w+)', content)
    for class_name in class_matches:
        analysis['classes'].append({
            'name': class_name,
            'type': 'class'
        })
        analysis['complexity_score'] += 5
    
    # Detect patterns
    if 'async' in content or 'await' in content:
        analysis['patterns'].append('async_programming')
    
    if 'React' in content or 'jsx' in analysis.get('extension', ''):
        analysis['patterns'].append('react_component')
    
    if 'test(' in content or 'describe(' in content:
        analysis['patterns'].append('unit_testing')
    
    return analysis

def _analyze_java_file(content: str, logger: logging.Logger) -> Dict[str, Any]:
    """Analyze Java file using regex patterns"""
    analysis = {
        'complexity_score': 0,
        'dependencies': [],
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': []
    }
    
    # Find imports
    import_matches = re.findall(r'import\s+([^;]+);', content)
    for imp in import_matches:
        analysis['imports'].append({
            'type': 'import',
            'module': imp.strip()
        })
        analysis['dependencies'].append(imp.strip().split('.')[-1])
    
    # Find classes
    class_matches = re.findall(r'(?:public|private|protected)?\s*class\s+(\w+)', content)
    for class_name in class_matches:
        analysis['classes'].append({
            'name': class_name,
            'type': 'class'
        })
        analysis['complexity_score'] += 5
    
    # Find methods
    method_matches = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', content)
    for method_name in method_matches:
        analysis['functions'].append({
            'name': method_name,
            'type': 'method'
        })
        analysis['complexity_score'] += 2
    
    # Detect patterns
    if '@Test' in content or 'junit' in content.lower():
        analysis['patterns'].append('unit_testing')
    
    if '@Override' in content:
        analysis['patterns'].append('inheritance')
    
    return analysis

def _analyze_generic_file(content: str, logger: logging.Logger) -> Dict[str, Any]:
    """Generic analysis for unsupported languages"""
    lines = content.splitlines()
    
    analysis = {
        'complexity_score': len(lines) // 10,  # Simple line-based complexity
        'dependencies': [],
        'functions': [],
        'classes': [],
        'imports': [],
        'patterns': []
    }
    
    # Basic pattern detection
    if any('test' in line.lower() for line in lines[:10]):
        analysis['patterns'].append('testing')
    
    return analysis

def _analyze_relationships(file_analyses: List[Dict[str, Any]], source_language: str, logger: logging.Logger) -> Dict[str, Any]:
    """Analyze relationships between files in the chunk"""
    relationships = {
        'internal_dependencies': [],
        'external_dependencies': set(),
        'shared_patterns': []
    }
    
    # Get all file names in the chunk
    file_names = {Path(fa['path']).stem for fa in file_analyses}
    
    # Find internal dependencies
    for file_analysis in file_analyses:
        file_path = file_analysis['path']
        dependencies = file_analysis.get('dependencies', [])
        
        for dep in dependencies:
            # Check if dependency refers to another file in the chunk
            dep_name = dep.split('.')[-1]  # Get last part of module path
            if dep_name in file_names:
                relationships['internal_dependencies'].append({
                    'from': file_path,
                    'to': dep_name,
                    'type': 'import'
                })
            else:
                relationships['external_dependencies'].add(dep)
    
    # Find shared patterns
    all_patterns = [pattern for fa in file_analyses for pattern in fa.get('patterns', [])]
    pattern_counts = {}
    for pattern in all_patterns:
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    
    # Patterns that appear in multiple files
    relationships['shared_patterns'] = [
        pattern for pattern, count in pattern_counts.items() 
        if count > 1
    ]
    
    return relationships

def _assess_migration_readiness(file_analyses: List[Dict[str, Any]], source_language: str, relationships: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Assess how ready the code chunk is for migration"""
    readiness = {
        'score': 0.0,  # 0.0 to 1.0
        'factors': [],
        'warnings': [],
        'recommendations': []
    }
    
    total_complexity = sum(fa.get('complexity_score', 0) for fa in file_analyses)
    avg_complexity = total_complexity / len(file_analyses) if file_analyses else 0
    
    # Complexity factor (lower complexity = higher readiness)
    if avg_complexity < 10:
        readiness['score'] += 0.3
        readiness['factors'].append('Low complexity code')
    elif avg_complexity < 30:
        readiness['score'] += 0.2
        readiness['factors'].append('Medium complexity code')
    else:
        readiness['score'] += 0.1
        readiness['warnings'].append('High complexity code may need manual review')
    
    # Dependencies factor
    external_deps = len(relationships.get('external_dependencies', []))
    if external_deps < 5:
        readiness['score'] += 0.3
        readiness['factors'].append('Few external dependencies')
    elif external_deps < 15:
        readiness['score'] += 0.2
        readiness['factors'].append('Moderate external dependencies')
    else:
        readiness['score'] += 0.1
        readiness['warnings'].append('Many external dependencies may need mapping')
    
    # Pattern consistency factor
    shared_patterns = relationships.get('shared_patterns', [])
    if shared_patterns:
        readiness['score'] += 0.2
        readiness['factors'].append('Consistent coding patterns detected')
    
    # Language-specific factors
    if source_language in ['python', 'javascript', 'typescript', 'java']:
        readiness['score'] += 0.2
        readiness['factors'].append(f'Well-supported source language: {source_language}')
    else:
        readiness['warnings'].append(f'Limited support for {source_language}')
    
    # Ensure score is between 0 and 1
    readiness['score'] = min(1.0, max(0.0, readiness['score']))
    
    # Generate recommendations
    if readiness['score'] > 0.8:
        readiness['recommendations'].append('Chunk is ready for automatic migration')
    elif readiness['score'] > 0.6:
        readiness['recommendations'].append('Chunk suitable for migration with minimal review')
    elif readiness['score'] > 0.4:
        readiness['recommendations'].append('Chunk needs careful review during migration')
    else:
        readiness['recommendations'].append('Chunk may require manual migration or preprocessing')
    
    return readiness