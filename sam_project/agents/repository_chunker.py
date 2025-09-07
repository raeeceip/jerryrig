"""
Repository Chunker Agent for Solace Agent Mesh
Breaks large repositories into manageable chunks for processing
"""

import json
import logging
import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import subprocess
import git
from urllib.parse import urlparse

def process(input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Chunk a repository into manageable pieces for analysis/migration
    
    Args:
        input_data: Input data containing chunk request
        **kwargs: Additional configuration including shared_config
        
    Returns:
        Repository chunks ready for processing
    """
    logger = logging.getLogger(__name__)
    shared_config = kwargs.get('shared_config', {})
    jerryrig_config = shared_config.get('jerryrig', {})
    
    try:
        session_id = input_data.get('session_id')
        correlation_id = input_data.get('correlation_id')
        repository_url = input_data.get('repository_url')
        source_language = input_data.get('source_language')
        options = input_data.get('options', {})
        operation_type = input_data.get('operation_type', 'analysis')
        
        logger.info(f"Chunking repository {repository_url} for session {session_id}")
        
        # Clone repository to temporary directory
        temp_dir = _clone_repository(repository_url, logger)
        
        try:
            # Analyze repository structure
            repo_analysis = _analyze_repository_structure(temp_dir, jerryrig_config, logger)
            
            # Detect source language if needed
            if source_language == 'auto-detect':
                source_language = _detect_primary_language(repo_analysis['files'], jerryrig_config, logger)
                logger.info(f"Auto-detected source language: {source_language}")
            
            # Create chunks based on configuration
            chunks = _create_chunks(
                repo_analysis, 
                source_language,
                options.get('chunk_size', jerryrig_config.get('max_chunk_size', 50)),
                options.get('max_file_size', jerryrig_config.get('max_file_size', 1048576)),
                logger
            )
            
            # Prepare chunk requests for downstream processing
            chunk_requests = []
            for i, chunk in enumerate(chunks):
                chunk_request = {
                    'session_id': session_id,
                    'correlation_id': correlation_id,
                    'chunk_id': f"{session_id}_chunk_{i:03d}",
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'source_language': source_language,
                    'operation_type': operation_type,
                    'files': chunk['files'],
                    'dependencies': chunk['dependencies'],
                    'metadata': {
                        'repository_url': repository_url,
                        'chunk_size': len(chunk['files']),
                        'estimated_complexity': chunk['complexity'],
                        'primary_patterns': chunk['patterns']
                    },
                    'timestamp': datetime.now().isoformat()
                }
                chunk_requests.append(chunk_request)
            
            logger.info(f"Created {len(chunks)} chunks for repository {repository_url}")
            
            return {
                'chunks': chunk_requests,
                'repository_metadata': {
                    'session_id': session_id,
                    'correlation_id': correlation_id,
                    'repository_url': repository_url,
                    'source_language': source_language,
                    'total_files': len(repo_analysis['files']),
                    'total_chunks': len(chunks),
                    'structure': repo_analysis['structure'],
                    'dependencies': repo_analysis['dependencies']
                },
                'status': 'chunked'
            }
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        logger.error(f"Repository chunking failed: {e}")
        return {
            'error': str(e),
            'status': 'failed',
            'session_id': input_data.get('session_id'),
            'correlation_id': input_data.get('correlation_id')
        }

def _clone_repository(repository_url: str, logger: logging.Logger) -> str:
    """Clone repository to temporary directory"""
    temp_dir = tempfile.mkdtemp(prefix="jerryrig_repo_")
    
    try:
        # Clone using git
        git.Repo.clone_from(repository_url, temp_dir, depth=1)
        logger.info(f"Cloned repository to {temp_dir}")
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to clone repository {repository_url}: {e}")

def _analyze_repository_structure(repo_path: str, config: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Analyze repository structure and collect files"""
    supported_languages = config.get('supported_languages', ['python', 'javascript', 'typescript', 'java'])
    max_file_size = config.get('max_file_size', 1048576)
    
    # Language file extensions mapping
    language_extensions = {
        'python': ['.py', '.pyw'],
        'javascript': ['.js', '.jsx', '.mjs'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'cpp': ['.cpp', '.cxx', '.cc', '.hpp', '.h'],
        'go': ['.go'],
        'rust': ['.rs']
    }
    
    files = []
    structure = {'directories': [], 'total_files': 0}
    dependencies = {'imports': [], 'packages': []}
    
    repo_root = Path(repo_path)
    
    # Walk through repository
    for file_path in repo_root.rglob('*'):
        if file_path.is_file():
            structure['total_files'] += 1
            
            # Check if file is supported and within size limit
            file_extension = file_path.suffix.lower()
            file_size = file_path.stat().st_size
            
            if file_size > max_file_size:
                continue
                
            # Check if it's a source code file
            is_source = any(
                file_extension in extensions 
                for extensions in language_extensions.values()
            )
            
            if is_source:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    relative_path = file_path.relative_to(repo_root)
                    
                    files.append({
                        'path': str(relative_path),
                        'absolute_path': str(file_path),
                        'size': file_size,
                        'extension': file_extension,
                        'content': content,
                        'lines': len(content.splitlines())
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not read file {file_path}: {e}")
    
    # Collect directory structure
    for dir_path in repo_root.rglob('*'):
        if dir_path.is_dir():
            relative_dir = dir_path.relative_to(repo_root)
            if str(relative_dir) != '.':
                structure['directories'].append(str(relative_dir))
    
    logger.info(f"Analyzed repository: {len(files)} source files, {len(structure['directories'])} directories")
    
    return {
        'files': files,
        'structure': structure,
        'dependencies': dependencies
    }

def _detect_primary_language(files: List[Dict[str, Any]], config: Dict[str, Any], logger: logging.Logger) -> str:
    """Detect the primary programming language in the repository"""
    language_extensions = {
        'python': ['.py', '.pyw'],
        'javascript': ['.js', '.jsx', '.mjs'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'cpp': ['.cpp', '.cxx', '.cc', '.hpp', '.h'],
        'go': ['.go'],
        'rust': ['.rs']
    }
    
    language_counts = {}
    
    for file_info in files:
        extension = file_info['extension']
        for language, extensions in language_extensions.items():
            if extension in extensions:
                language_counts[language] = language_counts.get(language, 0) + 1
                break
    
    if not language_counts:
        return 'unknown'
    
    # Return the language with the most files
    primary_language = max(language_counts, key=language_counts.get)
    logger.info(f"Language detection: {language_counts}, primary: {primary_language}")
    
    return primary_language

def _create_chunks(repo_analysis: Dict[str, Any], source_language: str, chunk_size: int, max_file_size: int, logger: logging.Logger) -> List[Dict[str, Any]]:
    """Create file chunks for processing"""
    files = repo_analysis['files']
    chunks = []
    current_chunk = []
    current_chunk_size = 0
    
    # Sort files by size and dependencies for optimal chunking
    sorted_files = sorted(files, key=lambda f: (f['size'], f['path']))
    
    for file_info in sorted_files:
        # Skip files that are too large
        if file_info['size'] > max_file_size:
            logger.warning(f"Skipping large file: {file_info['path']} ({file_info['size']} bytes)")
            continue
        
        # Check if adding this file would exceed chunk size
        if len(current_chunk) >= chunk_size and current_chunk:
            # Finalize current chunk
            chunks.append(_finalize_chunk(current_chunk, source_language))
            current_chunk = []
            current_chunk_size = 0
        
        current_chunk.append(file_info)
        current_chunk_size += file_info['size']
    
    # Add remaining files as final chunk
    if current_chunk:
        chunks.append(_finalize_chunk(current_chunk, source_language))
    
    logger.info(f"Created {len(chunks)} chunks from {len(files)} files")
    return chunks

def _finalize_chunk(files: List[Dict[str, Any]], source_language: str) -> Dict[str, Any]:
    """Finalize a chunk with metadata"""
    total_lines = sum(f['lines'] for f in files)
    total_size = sum(f['size'] for f in files)
    
    # Estimate complexity based on file count and size
    complexity = 'low'
    if len(files) > 20 or total_lines > 5000:
        complexity = 'medium'
    if len(files) > 40 or total_lines > 10000:
        complexity = 'high'
    
    # Identify common patterns
    extensions = set(f['extension'] for f in files)
    patterns = list(extensions)
    
    return {
        'files': files,
        'dependencies': [],  # TODO: Analyze dependencies within chunk
        'complexity': complexity,
        'patterns': patterns,
        'metadata': {
            'file_count': len(files),
            'total_lines': total_lines,
            'total_size': total_size,
            'source_language': source_language
        }
    }