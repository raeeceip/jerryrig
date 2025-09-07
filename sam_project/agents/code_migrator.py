"""
Code Migrator Agent for Solace Agent Mesh
Performs actual code migration using AI models
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai
import os

def process(input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Migrate code from source language to target language using AI
    
    Args:
        input_data: Input data containing migration request
        **kwargs: Additional configuration including shared_config
        
    Returns:
        Migration results
    """
    logger = logging.getLogger(__name__)
    shared_config = kwargs.get('shared_config', {})
    openai_config = shared_config.get('openai', {})
    
    try:
        session_id = input_data.get('session_id')
        correlation_id = input_data.get('correlation_id')
        chunk_id = input_data.get('chunk_id')
        chunk_index = input_data.get('chunk_index', 0)
        total_chunks = input_data.get('total_chunks', 1)
        
        # Get analysis data from previous step
        analysis = input_data.get('analysis', {})
        source_language = analysis.get('source_language')
        file_analyses = analysis.get('file_analyses', [])
        
        # Get target language from metadata
        metadata = input_data.get('metadata', {})
        target_language = metadata.get('target_language', 'javascript')
        
        logger.info(f"Migrating chunk {chunk_id} from {source_language} to {target_language}")
        
        # Initialize OpenAI client
        api_key = openai_config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        client = openai.OpenAI(api_key=api_key)
        
        # Migrate each file in the chunk
        migrated_files = []
        migration_errors = []
        
        for file_analysis in file_analyses:
            try:
                migrated_file = _migrate_file(
                    file_analysis,
                    source_language,
                    target_language,
                    openai_config,
                    client,
                    logger
                )
                migrated_files.append(migrated_file)
                
            except Exception as e:
                error_info = {
                    'file_path': file_analysis.get('path', 'unknown'),
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                migration_errors.append(error_info)
                logger.error(f"Failed to migrate file {file_analysis.get('path')}: {e}")
        
        # Calculate success metrics
        total_files = len(file_analyses)
        successful_migrations = len(migrated_files)
        failed_migrations = len(migration_errors)
        
        success_rate = successful_migrations / total_files if total_files > 0 else 0.0
        
        # Create migration result
        migration_result = {
            'session_id': session_id,
            'correlation_id': correlation_id,
            'chunk_id': chunk_id,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'source_language': source_language,
            'target_language': target_language,
            'migrated_files': migrated_files,
            'errors': migration_errors,
            'metrics': {
                'total_files': total_files,
                'successful_migrations': successful_migrations,
                'failed_migrations': failed_migrations,
                'success_rate': success_rate
            },
            'timestamp': datetime.now().isoformat(),
            'status': 'migrated'
        }
        
        logger.info(f"Completed migration for chunk {chunk_id}: {successful_migrations}/{total_files} files")
        
        return {
            'migrated_code': migration_result,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Code migration failed: {e}")
        return {
            'error': str(e),
            'status': 'failed',
            'session_id': input_data.get('session_id'),
            'correlation_id': input_data.get('correlation_id'),
            'chunk_id': input_data.get('chunk_id')
        }

def _migrate_file(file_analysis: Dict[str, Any], source_language: str, target_language: str, openai_config: Dict[str, Any], client, logger: logging.Logger) -> Dict[str, Any]:
    """Migrate a single file using OpenAI"""
    file_path = file_analysis.get('path', '')
    original_content = file_analysis.get('content', '')
    
    logger.info(f"Migrating file: {file_path}")
    
    # Prepare migration prompt
    migration_prompt = _create_migration_prompt(
        original_content,
        source_language,
        target_language,
        file_analysis,
        logger
    )
    
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model=openai_config.get('model', 'gpt-4'),
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert code migration specialist. Migrate the following {source_language} code to {target_language}. Preserve functionality, add appropriate comments, and follow {target_language} best practices. Return only the migrated code without explanation."
                },
                {
                    "role": "user",
                    "content": migration_prompt
                }
            ],
            temperature=openai_config.get('temperature', 0.1),
            max_tokens=openai_config.get('max_tokens', 4000)
        )
        
        migrated_content = response.choices[0].message.content.strip()
        
        # Clean up the response (remove code block markers if present)
        migrated_content = _clean_migrated_code(migrated_content, target_language)
        
        # Validate migration
        validation_result = _validate_migration(
            original_content,
            migrated_content,
            source_language,
            target_language,
            file_analysis,
            logger
        )
        
        # Determine target file extension
        target_extension = _get_target_extension(target_language)
        target_path = _convert_file_path(file_path, target_extension)
        
        return {
            'original_path': file_path,
            'target_path': target_path,
            'original_content': original_content,
            'migrated_content': migrated_content,
            'source_language': source_language,
            'target_language': target_language,
            'validation': validation_result,
            'metrics': {
                'original_lines': len(original_content.splitlines()),
                'migrated_lines': len(migrated_content.splitlines()),
                'original_size': len(original_content),
                'migrated_size': len(migrated_content)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"OpenAI migration failed for {file_path}: {e}")
        raise Exception(f"AI migration failed: {e}")

def _create_migration_prompt(content: str, source_language: str, target_language: str, file_analysis: Dict[str, Any], logger: logging.Logger) -> str:
    """Create a detailed migration prompt for the AI"""
    
    # Get file context
    functions = file_analysis.get('functions', [])
    classes = file_analysis.get('classes', [])
    dependencies = file_analysis.get('dependencies', [])
    patterns = file_analysis.get('patterns', [])
    
    prompt_parts = [
        f"Migrate this {source_language} code to {target_language}:",
        "",
        "ORIGINAL CODE:",
        "```" + source_language,
        content,
        "```",
        "",
        "MIGRATION REQUIREMENTS:",
        f"- Convert from {source_language} to {target_language}",
        f"- Preserve all functionality and behavior",
        f"- Follow {target_language} best practices and conventions",
        f"- Use appropriate {target_language} libraries and patterns",
        f"- Add helpful comments where the translation is not obvious",
    ]
    
    # Add context-specific requirements
    if functions:
        prompt_parts.append(f"- Preserve {len(functions)} functions with equivalent behavior")
    
    if classes:
        prompt_parts.append(f"- Convert {len(classes)} classes using {target_language} class syntax")
    
    if dependencies:
        prompt_parts.append(f"- Map dependencies to {target_language} equivalents where possible")
    
    if 'async_programming' in patterns:
        prompt_parts.append(f"- Preserve asynchronous programming patterns")
    
    if 'unit_testing' in patterns:
        prompt_parts.append(f"- Convert test code to {target_language} testing framework")
    
    # Add language-specific guidance
    if target_language == 'javascript':
        prompt_parts.extend([
            "- Use modern ES6+ syntax",
            "- Use const/let instead of var",
            "- Use arrow functions where appropriate",
            "- Use async/await for asynchronous operations"
        ])
    elif target_language == 'typescript':
        prompt_parts.extend([
            "- Add appropriate TypeScript type annotations",
            "- Use interfaces for object types",
            "- Add proper return type annotations",
            "- Use generics where beneficial"
        ])
    elif target_language == 'python':
        prompt_parts.extend([
            "- Follow PEP 8 style guidelines",
            "- Use type hints where appropriate",
            "- Use proper Python idioms and patterns",
            "- Handle exceptions appropriately"
        ])
    
    prompt_parts.extend([
        "",
        "MIGRATED CODE:"
    ])
    
    return "\n".join(prompt_parts)

def _clean_migrated_code(content: str, target_language: str) -> str:
    """Clean up AI-generated code"""
    lines = content.split('\n')
    cleaned_lines = []
    
    skip_line = False
    for line in lines:
        stripped = line.strip()
        
        # Skip code block markers
        if stripped.startswith('```'):
            skip_line = not skip_line
            continue
        
        if skip_line:
            continue
            
        # Skip explanatory text that might be at the beginning or end
        if stripped.startswith('Here') and ('code' in stripped or 'migrated' in stripped):
            continue
        if stripped.startswith('This') and ('migrated' in stripped or 'converted' in stripped):
            continue
        
        cleaned_lines.append(line)
    
    # Remove empty lines at start and end
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def _validate_migration(original: str, migrated: str, source_lang: str, target_lang: str, file_analysis: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Validate the migrated code"""
    validation = {
        'is_valid': True,
        'warnings': [],
        'errors': [],
        'confidence': 0.8,  # Default confidence
        'checks_performed': []
    }
    
    # Basic checks
    if not migrated.strip():
        validation['is_valid'] = False
        validation['errors'].append('Migration produced empty result')
        validation['confidence'] = 0.0
        return validation
    
    # Length ratio check
    original_lines = len(original.splitlines())
    migrated_lines = len(migrated.splitlines())
    ratio = migrated_lines / original_lines if original_lines > 0 else 0
    
    validation['checks_performed'].append('length_ratio')
    if ratio < 0.3 or ratio > 3.0:
        validation['warnings'].append(f'Significant size change: {ratio:.1f}x')
        validation['confidence'] -= 0.1
    
    # Function preservation check
    original_functions = file_analysis.get('functions', [])
    if original_functions:
        validation['checks_performed'].append('function_preservation')
        # Simple heuristic: check if we have similar number of function-like patterns
        if target_lang in ['javascript', 'typescript']:
            function_patterns = ['function ', '=>', ': function']
        elif target_lang == 'python':
            function_patterns = ['def ']
        elif target_lang == 'java':
            function_patterns = [') {', 'public ', 'private ']
        else:
            function_patterns = []
        
        migrated_function_count = sum(
            migrated.count(pattern) for pattern in function_patterns
        )
        
        if migrated_function_count < len(original_functions) * 0.7:
            validation['warnings'].append('Some functions may not have been migrated')
            validation['confidence'] -= 0.2
    
    # Syntax validation (basic)
    validation['checks_performed'].append('syntax_check')
    try:
        if target_lang == 'python':
            compile(migrated, '<migrated>', 'exec')
        # Note: For JS/TS we'd need a JS parser, for now just check basic syntax
        elif target_lang in ['javascript', 'typescript']:
            # Basic brace matching
            if migrated.count('{') != migrated.count('}'):
                validation['warnings'].append('Mismatched braces detected')
                validation['confidence'] -= 0.1
    except SyntaxError as e:
        validation['errors'].append(f'Syntax error: {e}')
        validation['is_valid'] = False
        validation['confidence'] = 0.2
    
    # Comment preservation check
    original_comment_lines = len([line for line in original.splitlines() if line.strip().startswith('#')])
    migrated_comment_lines = len([line for line in migrated.splitlines() if line.strip().startswith('//')])
    
    if original_comment_lines > 0 and migrated_comment_lines == 0:
        validation['warnings'].append('Comments may not have been preserved')
        validation['confidence'] -= 0.1
    
    validation['confidence'] = max(0.0, min(1.0, validation['confidence']))
    
    return validation

def _get_target_extension(target_language: str) -> str:
    """Get file extension for target language"""
    extensions = {
        'python': '.py',
        'javascript': '.js',
        'typescript': '.ts',
        'java': '.java',
        'cpp': '.cpp',
        'go': '.go',
        'rust': '.rs'
    }
    return extensions.get(target_language, '.txt')

def _convert_file_path(original_path: str, target_extension: str) -> str:
    """Convert file path to target language"""
    from pathlib import Path
    
    path = Path(original_path)
    # Keep the same directory structure, just change extension
    return str(path.with_suffix(target_extension))