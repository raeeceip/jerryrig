"""Repository parser for GitIngest output and zip file handling."""

import os
import json
import zipfile
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import requests

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GitIngestAnalysis:
    """Parsed GitIngest analysis results."""
    repository_url: str
    summary: str
    directory_structure: str
    file_contents: str
    language_breakdown: Dict[str, Any]
    total_files: int
    estimated_tokens: int


@dataclass
class RepositoryPackage:
    """Complete repository package with analysis and source code."""
    gitingest_analysis: GitIngestAnalysis
    zip_path: str
    extracted_path: str
    source_files: List[str]


class RepositoryParser:
    """Parses GitIngest output and handles repository zip files."""
    
    def __init__(self):
        self.temp_dir = None
        
    def parse_gitingest_output(self, gitingest_file_path: str) -> GitIngestAnalysis:
        """Parse GitIngest text output file into structured data.
        
        Args:
            gitingest_file_path: Path to GitIngest output text file
            
        Returns:
            GitIngestAnalysis object with parsed data
        """
        logger.info(f"Parsing GitIngest output: {gitingest_file_path}")
        
        with open(gitingest_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse the GitIngest structured output
        sections = self._split_gitingest_sections(content)
        
        # Extract summary information
        summary = sections.get('summary', '')
        repository_url = self._extract_repository_url(summary)
        total_files = self._extract_file_count(summary)
        estimated_tokens = self._extract_token_count(summary)
        
        # Get directory structure and file contents
        directory_structure = sections.get('directory_structure', '')
        file_contents = sections.get('file_contents', '')
        
        # Analyze language breakdown from file contents
        language_breakdown = self._analyze_languages_from_content(file_contents)
        
        return GitIngestAnalysis(
            repository_url=repository_url,
            summary=summary,
            directory_structure=directory_structure,
            file_contents=file_contents,
            language_breakdown=language_breakdown,
            total_files=total_files,
            estimated_tokens=estimated_tokens
        )
        
    def download_repository_zip(self, repo_url: str, output_dir: str) -> str:
        """Download repository as zip file from GitHub.
        
        Args:
            repo_url: GitHub repository URL
            output_dir: Directory to save zip file
            
        Returns:
            Path to downloaded zip file
        """
        logger.info(f"Downloading repository zip: {repo_url}")
        
        # Convert GitHub URL to zip download URL
        if 'github.com' in repo_url:
            # Convert https://github.com/user/repo to https://github.com/user/repo/archive/refs/heads/main.zip
            repo_url = repo_url.rstrip('/')
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            # Try main branch first, then master
            for branch in ['main', 'master']:
                zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"
                try:
                    response = requests.head(zip_url)
                    if response.status_code == 200:
                        break
                except:
                    continue
            else:
                # Fallback to default zip endpoint
                zip_url = f"{repo_url}/archive/refs/heads/master.zip"
        else:
            raise ValueError(f"Unsupported repository host: {repo_url}")
            
        # Download the zip file
        os.makedirs(output_dir, exist_ok=True)
        repo_name = repo_url.split('/')[-1]
        zip_path = os.path.join(output_dir, f"{repo_name}.zip")
        
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Repository downloaded: {zip_path}")
        return zip_path
        
    def extract_repository_zip(self, zip_path: str, extract_dir: Optional[str] = None) -> str:
        """Extract repository zip file.
        
        Args:
            zip_path: Path to zip file
            extract_dir: Directory to extract to (temp dir if None)
            
        Returns:
            Path to extracted directory
        """
        if extract_dir is None:
            if self.temp_dir is None:
                self.temp_dir = tempfile.mkdtemp(prefix="jerryrig_")
            extract_dir = self.temp_dir
            
        logger.info(f"Extracting repository zip to: {extract_dir}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Find the extracted repository directory (GitHub adds a suffix)
        extracted_dirs = [d for d in os.listdir(extract_dir) 
                         if os.path.isdir(os.path.join(extract_dir, d))]
        
        if len(extracted_dirs) == 1:
            repo_dir = os.path.join(extract_dir, extracted_dirs[0])
        else:
            repo_dir = extract_dir
            
        logger.info(f"Repository extracted to: {repo_dir}")
        return repo_dir
        
    def get_source_files(self, repo_dir: str) -> List[str]:
        """Get list of all source files in the extracted repository.
        
        Args:
            repo_dir: Path to extracted repository directory
            
        Returns:
            List of source file paths
        """
        source_files = []
        ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target', 'build', 'dist'}
        
        for root, dirs, files in os.walk(repo_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_patterns]
            
            for file in files:
                file_path = os.path.join(root, file)
                # Get relative path from repo root
                rel_path = os.path.relpath(file_path, repo_dir)
                source_files.append(rel_path)
                
        logger.info(f"Found {len(source_files)} source files")
        return source_files
        
    def create_repository_package(self, gitingest_file: str, repo_url: str, output_dir: str) -> RepositoryPackage:
        """Create complete repository package with analysis and source code.
        
        Args:
            gitingest_file: Path to GitIngest output file
            repo_url: Repository URL
            output_dir: Output directory
            
        Returns:
            RepositoryPackage with all repository data
        """
        logger.info("Creating complete repository package")
        
        # Parse GitIngest analysis
        gitingest_analysis = self.parse_gitingest_output(gitingest_file)
        
        # Download repository zip
        zip_path = self.download_repository_zip(repo_url, output_dir)
        
        # Extract repository
        extracted_path = self.extract_repository_zip(zip_path)
        
        # Get source files
        source_files = self.get_source_files(extracted_path)
        
        return RepositoryPackage(
            gitingest_analysis=gitingest_analysis,
            zip_path=zip_path,
            extracted_path=extracted_path,
            source_files=source_files
        )
        
    def _split_gitingest_sections(self, content: str) -> Dict[str, str]:
        """Split GitIngest output into sections."""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('SUMMARY:'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'summary'
                current_content = []
            elif line.startswith('DIRECTORY STRUCTURE:'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'directory_structure'
                current_content = []
            elif line.startswith('FILE CONTENTS:'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'file_contents'
                current_content = []
            elif current_section and not line.startswith('-' * 40):
                current_content.append(line)
                
        # Add the last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
            
        return sections
        
    def _extract_repository_url(self, summary: str) -> str:
        """Extract repository URL from summary."""
        for line in summary.split('\n'):
            if 'Repository:' in line:
                return line.split('Repository:')[1].strip()
        return ""
        
    def _extract_file_count(self, summary: str) -> int:
        """Extract file count from summary."""
        for line in summary.split('\n'):
            if 'Files analyzed:' in line:
                try:
                    return int(line.split('Files analyzed:')[1].strip())
                except ValueError:
                    pass
        return 0
        
    def _extract_token_count(self, summary: str) -> int:
        """Extract estimated token count from summary."""
        for line in summary.split('\n'):
            if 'Estimated tokens:' in line:
                try:
                    return int(line.split('Estimated tokens:')[1].strip())
                except ValueError:
                    pass
        return 0
        
    def _analyze_languages_from_content(self, file_contents: str) -> Dict[str, Any]:
        """Analyze programming languages from file contents."""
        language_counts = {}
        
        # Look for file extensions in the content
        import re
        file_pattern = r'FILE: ([^\n]+)'
        files = re.findall(file_pattern, file_contents)
        
        for file_path in files:
            if '.' in file_path:
                ext = '.' + file_path.split('.')[-1].lower()
                
                # Map extensions to languages
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
                
                lang = ext_to_lang.get(ext, 'other')
                language_counts[lang] = language_counts.get(lang, 0) + 1
                
        # Determine primary language
        primary_language = 'unknown'
        if language_counts:
            primary_language = max(language_counts.keys(), key=lambda k: language_counts[k])
            
        return {
            'primary_language': primary_language,
            'language_counts': language_counts
        }
        
    async def analyze_repository_async(self, repo_path: str) -> Dict[str, Any]:
        """
        Async version of repository analysis for SAM integration
        """
        import asyncio
        
        def _analyze_repo():
            try:
                # If it's a URL, try to analyze using GitIngest
                if repo_path.startswith(('http://', 'https://', 'git://')):
                    # For now, return a placeholder analysis for URLs
                    return {
                        'repository_url': repo_path,
                        'type': 'remote_repository',
                        'status': 'analysis_not_implemented',
                        'message': 'Remote repository analysis requires GitIngest integration'
                    }
                
                # If it's a local path, analyze the directory structure
                repo_path_obj = Path(repo_path)
                if not repo_path_obj.exists():
                    raise ValueError(f"Repository path does not exist: {repo_path}")
                
                analysis = self.analyze_repository(repo_path)
                
                return {
                    'repository_path': repo_path,
                    'type': 'local_repository',
                    'total_files': analysis.total_files,
                    'languages': analysis.languages,
                    'file_analyses': [
                        {
                            'path': fa.path,
                            'language': fa.language,
                            'size_bytes': fa.size_bytes,
                            'line_count': fa.line_count,
                            'complexity_score': fa.complexity_score,
                            'dependencies': fa.dependencies
                        }
                        for fa in analysis.file_analyses
                    ],
                    'summary': f"Analyzed {analysis.total_files} files across {len(analysis.languages)} languages"
                }
                
            except Exception as e:
                logger.error(f"Repository analysis failed: {str(e)}")
                return {
                    'repository_path': repo_path,
                    'type': 'unknown',
                    'error': str(e),
                    'total_files': 0,
                    'languages': {},
                    'file_analyses': []
                }
        
        return await asyncio.to_thread(_analyze_repo)
        
    def cleanup(self):
        """Clean up temporary files and directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")


# For backwards compatibility
CodeAnalyzer = RepositoryParser