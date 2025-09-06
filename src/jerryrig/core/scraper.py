import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitingestScraper:
    def __init__(self, headless=False):
        """
        Initialize the scraper with Chrome WebDriver

        Args:
            headless (bool): Whether to run browser in headless mode
        """
        self.driver = None
        self.setup_driver(headless)

    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless")

        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def fill_and_submit_form(self, github_url, pattern_type="exclude", pattern="", max_file_size=50, token=""):
        """
        Fill out the Gitingest form and submit it

        Args:
            github_url (str): GitHub repository URL
            pattern_type (str): "exclude" or "include"
            pattern (str): File pattern (e.g., "*.md, src/")
            max_file_size (int): Maximum file size in KB
            token (str): Personal Access Token (if needed for private repos)
        """
        try:
            # Navigate to Gitingest
            logger.info("Navigating to Gitingest...")
            self.driver.get("https://gitingest.com/")

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "input_text"))
            )

            # Fill in the GitHub URL
            logger.info(f"Filling GitHub URL: {github_url}")
            url_input = self.driver.find_element(By.ID, "input_text")
            url_input.clear()
            url_input.send_keys(github_url)

            # Set pattern type if different from default
            if pattern_type != "exclude":
                logger.info(f"Setting pattern type to: {pattern_type}")
                pattern_select = self.driver.find_element(By.ID, "pattern_type")
                pattern_select.send_keys(pattern_type)

            # Fill pattern if provided
            if pattern:
                logger.info(f"Setting pattern: {pattern}")
                pattern_input = self.driver.find_element(By.ID, "pattern")
                pattern_input.clear()
                pattern_input.send_keys(pattern)

            # Set file size slider
            if max_file_size != 50:
                logger.info(f"Setting max file size: {max_file_size}KB")
                file_size_slider = self.driver.find_element(By.ID, "file_size")
                # Calculate slider value (assuming range 1-500)
                slider_value = min(max(max_file_size, 1), 500)
                self.driver.execute_script(f"arguments[0].value = {slider_value};", file_size_slider)

            # Handle private repository token if provided
            if token:
                logger.info("Setting up private repository access...")
                # Check the private repository checkbox
                private_repo_checkbox = self.driver.find_element(By.ID, "showAccessSettings")
                if not private_repo_checkbox.is_selected():
                    private_repo_checkbox.click()

                # Wait for token field to appear and fill it
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "token"))
                )
                token_input = self.driver.find_element(By.ID, "token")
                token_input.clear()
                token_input.send_keys(token)

            # Submit the form
            logger.info("Submitting form...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()

            logger.info("Form submitted successfully")
            return True

        except Exception as e:
            logger.error(f"Error filling and submitting form: {e}")
            return False

    def wait_for_results(self, timeout=30):
        """
        Wait for the results to appear on the page

        Args:
            timeout (int): Maximum time to wait in seconds
        """
        try:
            logger.info(f"Waiting for results (timeout: {timeout}s)...")

            # Wait for either results or error
            WebDriverWait(self.driver, timeout).until(
                lambda driver: (
                    driver.find_element(By.ID, "results-section").is_displayed() or
                    driver.find_element(By.ID, "results-error").is_displayed()
                )
            )

            # Check if there's an error
            try:
                error_element = self.driver.find_element(By.ID, "results-error")
                if error_element.is_displayed():
                    error_text = error_element.text
                    logger.error(f"Error occurred: {error_text}")
                    return False
            except NoSuchElementException:
                pass

            # Check if results are available
            try:
                results_section = self.driver.find_element(By.ID, "results-section")
                if results_section.is_displayed():
                    logger.info("Results are now available")
                    return True
            except NoSuchElementException:
                pass

            return False

        except TimeoutException:
            logger.warning(f"Timeout waiting for results after {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Error waiting for results: {e}")
            return False

    def extract_file_contents(self):
        """
        Extract the file contents from the results section

        Returns:
            dict: Dictionary containing summary, directory structure, and file contents
        """
        try:
            logger.info("Extracting file contents...")

            results = {
                'summary': '',
                'directory_structure': '',
                'file_contents': ''
            }

            # Extract summary
            try:
                summary_element = self.driver.find_element(By.ID, "result-summary")
                results['summary'] = summary_element.get_attribute('value') or summary_element.text
                logger.info("Summary extracted successfully")
            except NoSuchElementException:
                logger.warning("Summary element not found")

            # Extract directory structure
            try:
                # Try to get from the hidden input first
                dir_structure_input = self.driver.find_element(By.ID, "directory-structure-content")
                results['directory_structure'] = dir_structure_input.get_attribute('value')

                # If empty, try to get from the pre element
                if not results['directory_structure']:
                    dir_structure_pre = self.driver.find_element(By.ID, "directory-structure-pre")
                    results['directory_structure'] = dir_structure_pre.text

                logger.info("Directory structure extracted successfully")
            except NoSuchElementException:
                logger.warning("Directory structure element not found")

            # Extract file contents
            try:
                content_element = self.driver.find_element(By.ID, "result-content")
                results['file_contents'] = content_element.get_attribute('value') or content_element.text
                logger.info("File contents extracted successfully")
            except NoSuchElementException:
                logger.warning("File contents element not found")

            return results

        except Exception as e:
            logger.error(f"Error extracting file contents: {e}")
            return None

    def save_to_file(self, results, output_filename="gitingest_output.txt"):
        """
        Save the extracted results to a text file

        Args:
            results (dict): Results dictionary from extract_file_contents
            output_filename (str): Output filename
        """
        try:
            logger.info(f"Saving results to {output_filename}...")

            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("GITINGEST RESULTS\n")
                f.write("=" * 80 + "\n\n")

                if results['summary']:
                    f.write("SUMMARY:\n")
                    f.write("-" * 40 + "\n")
                    f.write(results['summary'])
                    f.write("\n\n")

                if results['directory_structure']:
                    f.write("DIRECTORY STRUCTURE:\n")
                    f.write("-" * 40 + "\n")
                    f.write(results['directory_structure'])
                    f.write("\n\n")

                if results['file_contents']:
                    f.write("FILE CONTENTS:\n")
                    f.write("-" * 40 + "\n")
                    f.write(results['file_contents'])
                    f.write("\n")

            logger.info(f"Results saved successfully to {output_filename}")
            return True

        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return False

    def scrape_repository(self, github_url, pattern_type="exclude", pattern="",
                         max_file_size=50, token="", output_filename="file.txt",
                         wait_timeout=30):
        """
        Complete scraping workflow

        Args:
            github_url (str): GitHub repository URL
            pattern_type (str): "exclude" or "include"
            pattern (str): File pattern
            max_file_size (int): Maximum file size in KB
            token (str): Personal Access Token
            output_filename (str): Output filename (auto-generated if None)
            wait_timeout (int): Timeout for waiting for results

        Returns:
            bool: Success status
        """
        try:
            # Generate output filename if not provided
            if output_filename is None:
                repo_name = github_url.split('/')[-1].replace('.git', '')
                output_filename = f"gitingest_{repo_name}_{int(time.time())}.txt"

            logger.info(f"Starting scraping workflow for: {github_url}")

            # Step 1: Fill and submit form
            if not self.fill_and_submit_form(github_url, pattern_type, pattern, max_file_size, token):
                return False

            # Step 2: Wait for results
            if not self.wait_for_results(wait_timeout):
                return False

            # Step 3: Extract file contents
            results = self.extract_file_contents()
            if not results:
                return False

            # Step 4: Save to file
            if not self.save_to_file(results, output_filename):
                return False

            logger.info("Scraping completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Error in scraping workflow: {e}")
            return False

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")


def run(url):
    """Example usage of the GitingestScraper"""

    # Configuration
    #GITHUB_URL = "https://github.com/coderamp-labs/gitingest"  # Example repository
    PATTERN_TYPE = "exclude"  # or "include"
    PATTERN = "*.md, tests/"  # Example pattern
    MAX_FILE_SIZE = 50  # KB
    TOKEN = ""  # Leave empty for public repos
    WAIT_TIMEOUT = 30  # seconds
    HEADLESS = True  # Set to True to run without GUI

    # Initialize scraper
    scraper = GitingestScraper(headless=HEADLESS)

    try:
        # Run the scraping workflow
        success = scraper.scrape_repository(
            github_url=url,
            pattern_type=PATTERN_TYPE,
            pattern=PATTERN,
            max_file_size=MAX_FILE_SIZE,
            token=TOKEN,
            wait_timeout=WAIT_TIMEOUT
        )

        if success:
            print("✅ Scraping completed successfully!")
        else:
            print("❌ Scraping failed!")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Always close the browser
        scraper.close()


class RepositoryScraper:
    """Wrapper class for GitingestScraper to match CLI interface expectations."""
    
    def __init__(self, headless=True):
        self.headless = headless
        
    def scrape_repository(self, repo_url, output_dir):
        """Scrape a repository using the run function."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            output_filename = os.path.join(output_dir, f"gitingest_{repo_name}.txt")
            
            # Use the existing GitingestScraper with modifications
            PATTERN_TYPE = "exclude"
            PATTERN = "*.md, tests/"
            MAX_FILE_SIZE = 50
            TOKEN = ""
            WAIT_TIMEOUT = 30
            
            # Initialize scraper
            scraper = GitingestScraper(headless=self.headless)
            
            try:
                # Run the scraping workflow
                success = scraper.scrape_repository(
                    github_url=repo_url,
                    pattern_type=PATTERN_TYPE,
                    pattern=PATTERN,
                    max_file_size=MAX_FILE_SIZE,
                    token=TOKEN,
                    output_filename=output_filename,
                    wait_timeout=WAIT_TIMEOUT
                )
                
                if success:
                    logger.info(f"✅ Scraping completed successfully! Output: {output_filename}")
                    return output_filename
                else:
                    raise Exception("Scraping failed")
                    
            finally:
                # Always close the browser
                scraper.close()
                
        except Exception as e:
            logger.error(f"Error in RepositoryScraper: {e}")
            raise
