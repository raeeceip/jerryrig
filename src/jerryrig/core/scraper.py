"""Repository scraper using gitingest and web scraping techniques."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import aiohttp
from bs4 import BeautifulSoup

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryScraper:
    """Scrapes repositories using gitingest and other techniques."""
    
    def __init__(self, base_url: str = "https://gitingest.com"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def scrape_repository(self, repo_url: str, output_dir: str = "./scraped") -> str:
        """Scrape a repository and save the analysis.
        
        Args:
            repo_url: URL of the repository to scrape
            output_dir: Directory to save scraped data
            
        Returns:
            Path to the scraped data directory
        """
        logger.info(f"Starting repository scrape: {repo_url}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Use gitingest to get repository analysis
            analysis = self._get_gitingest_analysis(repo_url)
            
            # Save analysis to file
            analysis_file = output_path / "repository_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Repository analysis saved to: {analysis_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error scraping repository: {e}")
            raise
            
    def _get_gitingest_analysis(self, repo_url: str) -> Dict[str, Any]:
        """Get repository analysis from gitingest.
        
        Args:
            repo_url: URL of the repository
            
        Returns:
            Dictionary containing repository analysis
        """
        logger.info(f"Requesting gitingest analysis for: {repo_url}")
        
        try:
            # TODO: Implement actual gitingest API integration
            # For now, return a mock structure
            return {
                "repository_url": repo_url,
                "analysis_timestamp": "2025-09-06T00:00:00Z",
                "summary": f"Repository analysis for {repo_url}",
                "language_breakdown": {
                    "primary_language": "Unknown",
                    "languages": []
                },
                "file_structure": [],
                "dependencies": [],
                "readme_content": "",
                "license": "Unknown",
                "contributors": 0,
                "last_updated": "Unknown"
            }
            
        except Exception as e:
            logger.error(f"Error getting gitingest analysis: {e}")
            raise
            
    async def scrape_multiple_repositories(self, repo_urls: List[str], output_dir: str = "./scraped") -> List[str]:
        """Scrape multiple repositories concurrently.
        
        Args:
            repo_urls: List of repository URLs
            output_dir: Base directory for scraped data
            
        Returns:
            List of paths to scraped data directories
        """
        logger.info(f"Starting concurrent scrape of {len(repo_urls)} repositories")
        
        tasks = []
        for i, repo_url in enumerate(repo_urls):
            repo_output_dir = f"{output_dir}/repo_{i:03d}"
            task = asyncio.create_task(
                self._async_scrape_repository(repo_url, repo_output_dir)
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping repository {repo_urls[i]}: {result}")
            else:
                successful_results.append(result)
                
        logger.info(f"Successfully scraped {len(successful_results)} repositories")
        return successful_results
        
    async def _async_scrape_repository(self, repo_url: str, output_dir: str) -> str:
        """Async version of repository scraping."""
        # For now, just call the sync version
        # TODO: Implement proper async scraping
        return self.scrape_repository(repo_url, output_dir)