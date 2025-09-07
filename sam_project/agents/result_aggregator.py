"""
Result Aggregator Agent for Solace Agent Mesh
Aggregates analysis and migration results from multiple chunks
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import zipfile
import tempfile
import os

def process(input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Aggregate results from multiple chunks into final repository structure
    
    Args:
        input_data: Input data containing aggregate request
        **kwargs: Additional configuration including shared_config
        
    Returns:
        Aggregated results
    """
    logger = logging.getLogger(__name__)
    shared_config = kwargs.get('shared_config', {})
    
    try:
        session_id = input_data.get('session_id')
        correlation_id = input_data.get('correlation_id')
        operation_type = input_data.get('operation_type', 'analysis')
        
        # Determine if this is analysis or migration aggregation
        if operation_type == 'analysis':
            return _aggregate_analysis_results(input_data, shared_config, logger)
        elif operation_type == 'migration':
            return _aggregate_migration_results(input_data, shared_config, logger)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
            
    except Exception as e:
        logger.error(f"Result aggregation failed: {e}")
        return {
            'error': str(e),
            'status': 'failed',
            'session_id': input_data.get('session_id'),
            'correlation_id': input_data.get('correlation_id')
        }

def _aggregate_analysis_results(input_data: Dict[str, Any], config: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Aggregate repository analysis results"""
    session_id = input_data.get('session_id')
    correlation_id = input_data.get('correlation_id')
    
    # Collect all analysis results (would come from message queue in real implementation)
    analysis_results = input_data.get('analysis_results', [])
    
    if not analysis_results:
        # In real implementation, this would wait for all chunks to complete
        logger.warning("No analysis results found for aggregation")
        return {
            'result': {
                'session_id': session_id,
                'correlation_id': correlation_id,
                'operation_type': 'analysis',
                'status': 'no_results',
                'message': 'No analysis results to aggregate'
            }
        }
    
    # Aggregate data from all chunks
    total_files = 0
    total_complexity = 0
    all_dependencies = set()
    all_patterns = set()
    file_summaries = []
    chunk_summaries = []
    
    source_language = None
    repository_url = None
    
    for result in analysis_results:
        analysis = result.get('analysis', {})
        
        # Extract metadata
        if not source_language:
            source_language = analysis.get('source_language')
        if not repository_url:
            metadata = analysis.get('metadata', {})
            repository_url = metadata.get('repository_url')
        
        # Aggregate file analyses
        file_analyses = analysis.get('file_analyses', [])
        for file_analysis in file_analyses:
            file_summaries.append({
                'path': file_analysis.get('path'),
                'complexity_score': file_analysis.get('complexity_score', 0),
                'dependencies': file_analysis.get('dependencies', []),
                'patterns': file_analysis.get('patterns', []),
                'lines': file_analysis.get('lines', 0)
            })
            
            total_complexity += file_analysis.get('complexity_score', 0)
            all_dependencies.update(file_analysis.get('dependencies', []))
            all_patterns.update(file_analysis.get('patterns', []))
        
        # Aggregate chunk summaries
        chunk_summary = analysis.get('chunk_summary', {})
        chunk_summaries.append({
            'chunk_id': analysis.get('chunk_id'),
            'file_count': chunk_summary.get('total_files', 0),
            'complexity_score': chunk_summary.get('complexity_score', 0),
            'migration_readiness': chunk_summary.get('migration_readiness', {})
        })
        
        total_files += chunk_summary.get('total_files', 0)
    
    # Calculate overall metrics
    avg_complexity = total_complexity / total_files if total_files > 0 else 0
    
    # Calculate overall migration readiness
    readiness_scores = [
        chunk['migration_readiness'].get('score', 0.5) 
        for chunk in chunk_summaries 
        if 'migration_readiness' in chunk
    ]
    overall_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0.5
    
    # Generate recommendations
    recommendations = _generate_analysis_recommendations(
        total_files, 
        avg_complexity, 
        overall_readiness, 
        all_dependencies, 
        all_patterns,
        logger
    )
    
    aggregated_result = {
        'session_id': session_id,
        'correlation_id': correlation_id,
        'operation_type': 'analysis',
        'repository_url': repository_url,
        'source_language': source_language,
        'summary': {
            'total_files': total_files,
            'total_chunks': len(analysis_results),
            'average_complexity': avg_complexity,
            'total_dependencies': len(all_dependencies),
            'common_patterns': list(all_patterns),
            'migration_readiness_score': overall_readiness
        },
        'dependencies': list(all_dependencies),
        'patterns': list(all_patterns),
        'chunk_summaries': chunk_summaries,
        'file_summaries': file_summaries,
        'recommendations': recommendations,
        'timestamp': datetime.now().isoformat(),
        'status': 'completed'
    }
    
    logger.info(f"Aggregated analysis for {total_files} files across {len(analysis_results)} chunks")
    
    return {
        'result': aggregated_result,
        'status': 'completed'
    }

def _aggregate_migration_results(input_data: Dict[str, Any], config: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Aggregate repository migration results"""
    session_id = input_data.get('session_id')
    correlation_id = input_data.get('correlation_id')
    
    # Collect all migration results
    migration_results = input_data.get('migration_results', [])
    
    if not migration_results:
        logger.warning("No migration results found for aggregation")
        return {
            'result': {
                'session_id': session_id,
                'correlation_id': correlation_id,
                'operation_type': 'migration',
                'status': 'no_results',
                'message': 'No migration results to aggregate'
            }
        }
    
    # Aggregate migration data
    all_migrated_files = []
    all_errors = []
    total_original_files = 0
    total_successful_migrations = 0
    total_failed_migrations = 0
    
    source_language = None
    target_language = None
    repository_url = None
    
    for result in migration_results:
        migration = result.get('migrated_code', {})
        
        # Extract metadata
        if not source_language:
            source_language = migration.get('source_language')
        if not target_language:
            target_language = migration.get('target_language')
        
        # Aggregate migrated files
        migrated_files = migration.get('migrated_files', [])
        all_migrated_files.extend(migrated_files)
        
        # Aggregate errors
        errors = migration.get('errors', [])
        all_errors.extend(errors)
        
        # Aggregate metrics
        metrics = migration.get('metrics', {})
        total_original_files += metrics.get('total_files', 0)
        total_successful_migrations += metrics.get('successful_migrations', 0)
        total_failed_migrations += metrics.get('failed_migrations', 0)
    
    # Calculate success rate
    success_rate = total_successful_migrations / total_original_files if total_original_files > 0 else 0.0
    
    # Create repository structure
    repository_structure = _create_migrated_repository_structure(
        all_migrated_files, 
        target_language,
        logger
    )
    
    # Generate migration report
    migration_report = _generate_migration_report(
        all_migrated_files,
        all_errors,
        source_language,
        target_language,
        success_rate,
        logger
    )
    
    # Package migrated repository (create downloadable archive)
    archive_path = _package_migrated_repository(
        session_id,
        all_migrated_files,
        target_language,
        logger
    )
    
    aggregated_result = {
        'session_id': session_id,
        'correlation_id': correlation_id,
        'operation_type': 'migration',
        'source_language': source_language,
        'target_language': target_language,
        'summary': {
            'total_original_files': total_original_files,
            'successful_migrations': total_successful_migrations,
            'failed_migrations': total_failed_migrations,
            'success_rate': success_rate,
            'total_chunks': len(migration_results)
        },
        'migrated_files': all_migrated_files,
        'errors': all_errors,
        'repository_structure': repository_structure,
        'migration_report': migration_report,
        'archive_path': archive_path,
        'timestamp': datetime.now().isoformat(),
        'status': 'completed'
    }
    
    logger.info(f"Aggregated migration: {total_successful_migrations}/{total_original_files} files successfully migrated")
    
    return {
        'result': aggregated_result,
        'status': 'completed'
    }

def _generate_analysis_recommendations(total_files: int, avg_complexity: float, readiness_score: float, dependencies: set, patterns: set, logger: logging.Logger) -> List[str]:
    """Generate recommendations based on analysis"""
    recommendations = []
    
    # File count recommendations
    if total_files > 100:
        recommendations.append("Large repository - consider phased migration approach")
    elif total_files < 10:
        recommendations.append("Small repository - suitable for complete migration")
    
    # Complexity recommendations
    if avg_complexity > 30:
        recommendations.append("High complexity code - manual review recommended")
    elif avg_complexity < 10:
        recommendations.append("Low complexity code - good candidate for automated migration")
    
    # Readiness recommendations
    if readiness_score > 0.8:
        recommendations.append("Repository is ready for automated migration")
    elif readiness_score > 0.6:
        recommendations.append("Repository suitable for migration with review")
    else:
        recommendations.append("Repository needs preprocessing before migration")
    
    # Dependency recommendations
    if len(dependencies) > 20:
        recommendations.append("Many external dependencies - create dependency mapping plan")
    
    # Pattern recommendations
    if 'async_programming' in patterns:
        recommendations.append("Contains async patterns - ensure target language equivalents")
    if 'unit_testing' in patterns:
        recommendations.append("Contains tests - migrate test framework")
    
    return recommendations

def _create_migrated_repository_structure(migrated_files: List[Dict[str, Any]], target_language: str, logger: logging.Logger) -> Dict[str, Any]:
    """Create directory structure for migrated repository"""
    structure = {
        'directories': set(),
        'files': [],
        'total_size': 0
    }
    
    for file_info in migrated_files:
        target_path = file_info.get('target_path', '')
        migrated_content = file_info.get('migrated_content', '')
        
        # Add directory to structure
        dir_path = str(Path(target_path).parent)
        if dir_path != '.':
            structure['directories'].add(dir_path)
        
        # Add file info
        structure['files'].append({
            'path': target_path,
            'size': len(migrated_content),
            'lines': len(migrated_content.splitlines())
        })
        
        structure['total_size'] += len(migrated_content)
    
    structure['directories'] = sorted(list(structure['directories']))
    
    return structure

def _generate_migration_report(migrated_files: List[Dict[str, Any]], errors: List[Dict[str, Any]], source_lang: str, target_lang: str, success_rate: float, logger: logging.Logger) -> Dict[str, Any]:
    """Generate comprehensive migration report"""
    
    # Analyze validation results
    validation_summary = {
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'total_warnings': 0,
        'total_errors': 0
    }
    
    for file_info in migrated_files:
        validation = file_info.get('validation', {})
        confidence = validation.get('confidence', 0.5)
        
        if confidence > 0.8:
            validation_summary['high_confidence'] += 1
        elif confidence > 0.5:
            validation_summary['medium_confidence'] += 1
        else:
            validation_summary['low_confidence'] += 1
        
        validation_summary['total_warnings'] += len(validation.get('warnings', []))
        validation_summary['total_errors'] += len(validation.get('errors', []))
    
    # Calculate average confidence
    confidences = [
        file_info.get('validation', {}).get('confidence', 0.5)
        for file_info in migrated_files
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
    
    report = {
        'migration_summary': {
            'source_language': source_lang,
            'target_language': target_lang,
            'success_rate': success_rate,
            'average_confidence': avg_confidence
        },
        'validation_summary': validation_summary,
        'error_summary': {
            'total_errors': len(errors),
            'error_types': _categorize_errors(errors)
        },
        'recommendations': _generate_migration_recommendations(
            success_rate, avg_confidence, validation_summary, errors
        ),
        'next_steps': _generate_next_steps(success_rate, avg_confidence)
    }
    
    return report

def _categorize_errors(errors: List[Dict[str, Any]]) -> Dict[str, int]:
    """Categorize migration errors"""
    categories = {
        'api_errors': 0,
        'syntax_errors': 0,
        'timeout_errors': 0,
        'validation_errors': 0,
        'other_errors': 0
    }
    
    for error in errors:
        error_msg = error.get('error', '').lower()
        
        if 'api' in error_msg or 'openai' in error_msg:
            categories['api_errors'] += 1
        elif 'syntax' in error_msg:
            categories['syntax_errors'] += 1
        elif 'timeout' in error_msg:
            categories['timeout_errors'] += 1
        elif 'validation' in error_msg:
            categories['validation_errors'] += 1
        else:
            categories['other_errors'] += 1
    
    return categories

def _generate_migration_recommendations(success_rate: float, avg_confidence: float, validation_summary: Dict[str, Any], errors: List[Dict[str, Any]]) -> List[str]:
    """Generate migration-specific recommendations"""
    recommendations = []
    
    if success_rate > 0.9:
        recommendations.append("Excellent migration success rate - review and deploy")
    elif success_rate > 0.7:
        recommendations.append("Good migration success rate - review failed files")
    else:
        recommendations.append("Low migration success rate - investigate errors and retry")
    
    if avg_confidence > 0.8:
        recommendations.append("High confidence in migration quality")
    elif avg_confidence > 0.6:
        recommendations.append("Moderate confidence - manual review recommended")
    else:
        recommendations.append("Low confidence - thorough manual review required")
    
    if validation_summary['low_confidence'] > 0:
        recommendations.append(f"Review {validation_summary['low_confidence']} low-confidence migrations")
    
    if len(errors) > 0:
        recommendations.append(f"Address {len(errors)} migration errors")
    
    return recommendations

def _generate_next_steps(success_rate: float, avg_confidence: float) -> List[str]:
    """Generate next steps for the user"""
    steps = []
    
    if success_rate > 0.8 and avg_confidence > 0.7:
        steps.extend([
            "Download migrated repository archive",
            "Set up build environment for target language",
            "Run tests to verify functionality",
            "Deploy to target environment"
        ])
    else:
        steps.extend([
            "Review migration report and errors",
            "Address high-priority issues",
            "Re-run migration for failed files",
            "Manual review of low-confidence migrations"
        ])
    
    return steps

def _package_migrated_repository(session_id: str, migrated_files: List[Dict[str, Any]], target_language: str, logger: logging.Logger) -> Optional[str]:
    """Package migrated repository into downloadable archive"""
    try:
        # Create temporary directory for the archive
        temp_dir = tempfile.mkdtemp(prefix=f"jerryrig_migration_{session_id}_")
        archive_name = f"migrated_repository_{session_id}.zip"
        archive_path = os.path.join(temp_dir, archive_name)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in migrated_files:
                target_path = file_info.get('target_path', '')
                migrated_content = file_info.get('migrated_content', '')
                
                # Add file to archive
                zipf.writestr(target_path, migrated_content)
            
            # Add migration report
            report = {
                'session_id': session_id,
                'target_language': target_language,
                'total_files': len(migrated_files),
                'timestamp': datetime.now().isoformat()
            }
            zipf.writestr('MIGRATION_REPORT.json', json.dumps(report, indent=2))
        
        logger.info(f"Created migration archive: {archive_path}")
        return archive_path
        
    except Exception as e:
        logger.error(f"Failed to create migration archive: {e}")
        return None