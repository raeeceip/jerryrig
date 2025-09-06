"""Command line interface for JerryRig."""

import os
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .core.scraper import RepositoryScraper
from .core.migrator import CodeMigrator

# Load environment variables from .env file
load_dotenv()

console = Console()


@click.group()
@click.version_option()
def main():
    """JerryRig - Code Migration Tool
    
    A web scraper and code migrator that converts open source repositories 
    between programming languages using AI agents.
    """
    console.print(
        Panel(
            Text("JerryRig Code Migration Tool", style="bold blue"),
            subtitle="Convert repositories between programming languages",
        )
    )


@main.command()
@click.argument("repo_url")
@click.option(
    "--output-dir", 
    "-o", 
    default="./output", 
    help="Output directory for scraped repository"
)
def scrape(repo_url: str, output_dir: str):
    """Scrape a repository using gitingest."""
    console.print(f"🔍 Scraping repository: {repo_url}")
    
    scraper = RepositoryScraper()
    try:
        result = scraper.scrape_repository(repo_url, output_dir)
        console.print(f"✅ Repository scraped successfully to: {result}")
    except Exception as e:
        console.print(f"❌ Error scraping repository: {e}", style="red")


@main.command()
@click.argument("source_path")
@click.argument("target_language")
@click.option(
    "--output-dir", 
    "-o", 
    default="./migrated", 
    help="Output directory for migrated code"
)
def migrate(source_path: str, target_language: str, output_dir: str):
    """Migrate code from one language to another."""
    console.print(f"🔄 Migrating code to {target_language}")
    
    migrator = CodeMigrator()
    try:
        result = migrator.migrate_code(source_path, target_language, output_dir)
        console.print(f"✅ Code migrated successfully to: {result}")
    except Exception as e:
        console.print(f"❌ Error migrating code: {e}", style="red")


@main.command()
@click.argument("repo_url")
def test_scraper(repo_url: str):
    """Test the repository scraper using the built-in run function."""
    console.print(f"🧪 Testing scraper with: {repo_url}")
    
    try:
        # Import and use the run function directly
        from .core.scraper import run
        run(repo_url)
        console.print(f"✅ Test completed successfully!")
    except Exception as e:
        console.print(f"❌ Error testing scraper: {e}", style="red")


@main.command()
@click.argument("repo_url")
@click.argument("target_language")
@click.option(
    "--output-dir", 
    "-o", 
    default="./jerryrig_output", 
    help="Output directory for the complete migration"
)
def full_migration(repo_url: str, target_language: str, output_dir: str):
    """Complete migration pipeline: scrape repository and migrate to target language."""
    console.print(f"🚀 Starting full migration pipeline")
    console.print(f"📥 Source: {repo_url}")
    console.print(f"🎯 Target Language: {target_language}")
    console.print(f"📁 Output: {output_dir}")
    
    try:
        # Step 1: Scrape repository using gitingest
        console.print("\n📡 Step 1: Analyzing repository with gitingest...")
        from .core.scraper import RepositoryScraper
        scraper = RepositoryScraper()
        
        # Create temporary analysis directory
        analysis_dir = f"{output_dir}/analysis"
        scrape_result = scraper.scrape_repository(repo_url, analysis_dir)
        console.print(f"✅ Repository analysis complete: {scrape_result}")
        
        # Step 2: Initialize custom Solace coding agent
        console.print("\n🤖 Step 2: Spawning custom Solace coding agent...")
        from .agents.solace_agent import SolaceAgent
        try:
            from .core.repository_agent import RepositoryMigrationAgent
        except ImportError:
            from .utils.logger import get_logger
            logger = get_logger(__name__)
            logger.error("Repository agent not available. Using basic migration.")
            RepositoryMigrationAgent = None
        
        if RepositoryMigrationAgent is not None:
            migration_agent = RepositoryMigrationAgent()
            migration_result = migration_agent.migrate_repository(
                analysis_dir=analysis_dir,
                target_language=target_language,
                output_dir=output_dir
            )
            if migration_result["success"]:
                console.print(f"✅ Repository migration complete!")
                console.print(f"📁 Migrated files: {migration_result['migrated_files']}")
                console.print(f"📊 Migration summary: {migration_result['summary']}")
            else:
                console.print(f"❌ Migration failed: {migration_result['error']}", style="red")
                exit(1)
        else:
            console.print(f"❌ RepositoryMigrationAgent is not available. Migration cannot proceed.", style="red")
            exit(1)
            
    except Exception as e:
        console.print(f"❌ Full migration failed: {e}", style="red")
        exit(1)


if __name__ == "__main__":
    main()