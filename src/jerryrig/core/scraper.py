"""Repository scraper using gitingest and web scraping techniques."""

import os
import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import aiohttp
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    PLAYWRIGHT_AVAILABLE = False

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryScraper:
    """Scrapes repositories using gitingest and other techniques."""
    
    def __init__(self, base_url: str = "https://gitingest.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.use_browser = PLAYWRIGHT_AVAILABLE
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available. Using basic HTTP requests (may not work with interactive sites)")
        else:
            logger.info("Playwright available. Using browser automation for gitingest")
        
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
        """Get repository analysis from gitingest.com.
        
        Args:
            repo_url: URL of the repository
            
        Returns:
            Dictionary containing repository analysis
        """
        logger.info(f"Requesting gitingest analysis for: {repo_url}")
        
        if self.use_browser and PLAYWRIGHT_AVAILABLE:
            return self._get_gitingest_with_browser(repo_url)
        else:
            return self._get_gitingest_fallback(repo_url)
            
    def _get_gitingest_with_browser(self, repo_url: str) -> Dict[str, Any]:
        """Get repository content using browser automation to click Ingest button.
        
        Args:
            repo_url: URL of the repository
            
        Returns:
            Dictionary containing repository analysis
        """
        logger.info(f"Using browser automation for gitingest: {repo_url}")
        
        try:
            # Format the gitingest URL
            if "github.com" in repo_url:
                parts = repo_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    owner = parts[-2]
                    repo = parts[-1]
                    gitingest_url = f"{self.base_url}/{owner}/{repo}"
                else:
                    raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            else:
                logger.warning(f"Non-GitHub repository detected: {repo_url}")
                gitingest_url = f"{self.base_url}?url={repo_url}"
            
            logger.info(f"Navigating to gitingest: {gitingest_url}")
            
            if not sync_playwright:
                raise ImportError("Playwright not available")
            
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=True)  # Set to False for debugging
                context = browser.new_context()
                page = context.new_page()
                
                try:
                    # Navigate to gitingest page
                    page.goto(gitingest_url, timeout=30000)
                    
                    # Wait for page to load
                    page.wait_for_load_state("networkidle")
                    
                    # Look for the Ingest button and click it
                    ingest_button = page.locator('button[type="submit"]:has-text("Ingest")')
                    
                    if ingest_button.count() > 0:
                        logger.info("Found Ingest button, clicking...")
                        ingest_button.click()
                        
                        # Wait for the result content to be generated
                        result_textarea = page.locator('#result-content')
                        
                        # Wait for content to appear (up to 30 seconds)
                        logger.info("Waiting for gitingest to generate content...")
                        
                        # Poll for content generation
                        max_wait_time = 30  # seconds
                        wait_interval = 2   # seconds
                        elapsed_time = 0
                        
                        while elapsed_time < max_wait_time:
                            if result_textarea.count() > 0:
                                content = result_textarea.input_value()
                                if content and len(content.strip()) > 100:  # Has substantial content
                                    logger.info(f"Content generated! Length: {len(content)} characters")
                                    break
                            
                            time.sleep(wait_interval)
                            elapsed_time += wait_interval
                            logger.info(f"Still waiting for content... ({elapsed_time}s)")
                        
                        # Get the final content
                        if result_textarea.count() > 0:
                            content = result_textarea.input_value()
                            if content and len(content.strip()) > 50:
                                logger.info(f"Successfully extracted {len(content)} characters from gitingest")
                                return self._parse_gitingest_content(content, repo_url)
                            else:
                                logger.warning("Generated content is too short or empty")
                        else:
                            logger.warning("Could not find result textarea")
                    else:
                        logger.warning("Could not find Ingest button")
                        # Try to get any existing content on the page
                        page_content = page.content()
                        return self._parse_gitingest_content(page_content, repo_url)
                
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"Error using browser automation: {e}")
            return self._get_gitingest_fallback(repo_url)
        
        # If we get here, something went wrong
        logger.warning("Browser automation completed but no content extracted")
        return self._get_mock_analysis(repo_url)
        
    def _get_gitingest_fallback(self, repo_url: str) -> Dict[str, Any]:
        """Fallback method using simple HTTP requests.
        
        Args:
            repo_url: URL of the repository
            
        Returns:
            Dictionary containing repository analysis
        """
        logger.info(f"Using fallback HTTP method for: {repo_url}")
        
        try:
            # Format the gitingest URL
            # gitingest.com typically works with GitHub URLs
            if "github.com" in repo_url:
                # Extract owner/repo from GitHub URL
                parts = repo_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    owner = parts[-2]
                    repo = parts[-1]
                    gitingest_url = f"{self.base_url}/{owner}/{repo}"
                else:
                    raise ValueError(f"Invalid GitHub URL format: {repo_url}")
            else:
                # For non-GitHub repos, we might need different handling
                logger.warning(f"Non-GitHub repository detected: {repo_url}")
                gitingest_url = f"{self.base_url}?url={repo_url}"
            
            logger.info(f"Fetching from gitingest: {gitingest_url}")
            
            # Make request to gitingest.com
            headers = {
                'User-Agent': 'JerryRig/1.0 (https://github.com/raeeceip/jerryrig)',
                'Accept': 'text/plain, text/html, application/json'
            }
            
            response = self.session.get(gitingest_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse the response
            content_type = response.headers.get('content-type', '').lower()

            #
            
            if 'application/json' in content_type:
                # If gitingest returns JSON, parse it directly
                data = response.json()
            else:
                # If gitingest returns plain text, parse it
                content = response.text
                data = self._parse_gitingest_content(content, repo_url)
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching from gitingest: {e}")
            # Return mock data as fallback
            return self._get_mock_analysis(repo_url)
        except Exception as e:
            logger.error(f"Error processing gitingest response: {e}")
            return self._get_mock_analysis(repo_url)
            
    def _parse_gitingest_content(self, content: str, repo_url: str) -> Dict[str, Any]:
        """Parse gitingest plain text content into structured data.
        
        Args:
            content: Raw content from gitingest
            repo_url: Original repository URL
            
        Returns:
            Structured repository analysis
        """
        lines = content.split('\n')
        
        # Initialize analysis structure
        analysis = {
            "repository_url": repo_url,
            "analysis_timestamp": "2025-09-06T00:00:00Z",
            "summary": "",
            "language_breakdown": {
                "primary_language": "Unknown",
                "languages": []
            },
            "file_structure": [],
            "dependencies": [],
            "readme_content": "",
            "license": "Unknown",
            "contributors": 0,
            "last_updated": "Unknown",
            "raw_content": content[:1000] + "..." if len(content) > 1000 else content  # Truncated for storage
        }
        
        # Extract basic information from content
        current_section = ""
        for line in lines[:50]:  # Analyze first 50 lines for metadata
            line = line.strip()
            if not line:
                continue
                
            # Look for common patterns
            if line.startswith('#') or line.startswith('Repository:'):
                analysis["summary"] = line.replace('#', '').replace('Repository:', '').strip()
            elif 'language:' in line.lower() or 'primary language:' in line.lower():
                # Try to extract language information
                if ':' in line:
                    lang = line.split(':')[1].strip()
                    analysis["language_breakdown"]["primary_language"] = lang
                    analysis["language_breakdown"]["languages"] = [lang]
        
        # If we have content, consider it a successful analysis
        if content.strip():
            analysis["status"] = "success"
            analysis["file_count"] = len([l for l in lines if l.strip() and not l.startswith('#')])
        else:
            analysis["status"] = "empty"
            
        return analysis
        
    def _get_mock_analysis(self, repo_url: str) -> Dict[str, Any]:
        """Return mock analysis data when gitingest is not available.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Mock repository analysis
        """
        logger.warning(f"Using mock analysis for: {repo_url}")
        
        return {
            "repository_url": repo_url,
            "analysis_timestamp": "2025-09-06T00:00:00Z",
            "summary": f"Mock analysis for {repo_url} - gitingest not available",
            "language_breakdown": {
                "primary_language": "Unknown",
                "languages": []
            },
            "file_structure": [],
            "dependencies": [],
            "readme_content": "Mock README content",
            "license": "Unknown",
            "contributors": 0,
            "last_updated": "Unknown",
            "status": "mock",
            "warning": "This is mock data - gitingest service was not available"
        }
            
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