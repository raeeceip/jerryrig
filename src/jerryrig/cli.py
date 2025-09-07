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
    default="./jerryrig_fast_output", 
    help="Output directory for the migration"
)
@click.option(
    "--max-workers", 
    "-w", 
    default=10, 
    help="Number of parallel workers"
)
def fast_migration(repo_url: str, target_language: str, output_dir: str, max_workers: int):
    """FAST migration: GitHub API -> Parallel Processing -> No GitIngest."""
    console.print(f"⚡ Starting FAST migration pipeline")
    console.print(f"📥 Source: {repo_url}")
    console.print(f"🎯 Target Language: {target_language}")
    console.print(f"📁 Output: {output_dir}")
    console.print(f"👥 Workers: {max_workers}")
    
    try:
        import time
        start_time = time.time()
        
        # Use the fast migrator
        from .core.fast_migrator import FastRepositoryMigrator
        migrator = FastRepositoryMigrator(max_workers=max_workers)
        
        console.print(f"\n⚡ Processing repository with {max_workers} parallel workers...")
        
        result = migrator.migrate_repository_fast(repo_url, target_language, output_dir)
        
        total_time = time.time() - start_time
        
        console.print(f"\n✅ FAST migration complete!")
        console.print(f"📊 Results:")
        console.print(f"   📁 Total Files: {result['total_files']}")
        console.print(f"   ✅ Migrated: {result['migrated_files']}")
        console.print(f"   ❌ Failed: {result['failed_files']}")
        console.print(f"   ⏱️  Processing Time: {result['processing_time']:.2f}s")
        console.print(f"   🚀 Total Time: {total_time:.2f}s")
        console.print(f"   📂 Output: {result['output_directory']}")
        
        if result['migrated_files'] > 0:
            success_rate = (result['migrated_files'] / result['total_files']) * 100
            console.print(f"   📈 Success Rate: {success_rate:.1f}%")
        
    except Exception as e:
        console.print(f"❌ FAST migration failed: {e}", style="red")
        exit(1)


@main.command()
@click.argument("repo_url")
@click.argument("target_language")
@click.option(
    "--output-dir", 
    "-o", 
    default="./jerryrig_simple_output", 
    help="Output directory for the migration"
)
def simple_migration(repo_url: str, target_language: str, output_dir: str):
    """Simple migration: GitIngest -> Download Zip -> Feed to Solace Agent."""
    console.print(f"🚀 Starting simple migration pipeline")
    console.print(f"📥 Source: {repo_url}")
    console.print(f"🎯 Target Language: {target_language}")
    console.print(f"📁 Output: {output_dir}")
    
    try:
        # Step 1: Use GitIngest to analyze repository
        console.print("\n📡 Step 1: Analyzing repository with GitIngest...")
        from .core.scraper import RepositoryScraper
        scraper = RepositoryScraper()
        
        # Create analysis directory
        analysis_dir = f"{output_dir}/analysis"
        gitingest_file = scraper.scrape_repository(repo_url, analysis_dir)
        console.print(f"✅ GitIngest analysis complete: {gitingest_file}")
        
        # Step 2: Parse GitIngest output and download repository
        console.print("\n📦 Step 2: Parsing GitIngest and downloading repository...")
        from .core.analyzer import RepositoryParser
        parser = RepositoryParser()
        
        repo_package = parser.create_repository_package(
            gitingest_file=gitingest_file,
            repo_url=repo_url,
            output_dir=output_dir
        )
        
        console.print(f"✅ Repository package created:")
        console.print(f"   📊 Primary Language: {repo_package.gitingest_analysis.language_breakdown['primary_language']}")
        console.print(f"   📁 Total Files: {repo_package.gitingest_analysis.total_files}")
        console.print(f"   🎯 Estimated Tokens: {repo_package.gitingest_analysis.estimated_tokens}")
        console.print(f"   📦 Zip File: {repo_package.zip_path}")
        console.print(f"   📂 Extracted: {repo_package.extracted_path}")
        
        # Step 3: Feed to Solace Agent for migration
        console.print(f"\n🤖 Step 3: Feeding to Solace Agent for {target_language} migration...")
        from .agents.solace_agent import SolaceAgent
        agent = SolaceAgent()
        
        # For now, migrate key files (this can be enhanced with SAM for parallel processing)
        migrated_files = []
        important_files = [f for f in repo_package.source_files if not f.startswith('.') and '/' not in f][:5]  # Top level files first
        
        for file_path in important_files:
            full_path = os.path.join(repo_package.extracted_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Detect file language
                    file_ext = os.path.splitext(file_path)[1]
                    source_lang = {'.py': 'python', '.js': 'javascript', '.java': 'java'}.get(file_ext, 'unknown')
                    
                    if source_lang != 'unknown':
                        console.print(f"   🔄 Migrating: {file_path}")
                        
                        result = agent.migrate_code(content, source_lang, target_language)
                        
                        if result['success']:
                            # Save migrated file
                            output_file = os.path.join(output_dir, 'migrated', file_path)
                            os.makedirs(os.path.dirname(output_file), exist_ok=True)
                            
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(result['migrated_code'])
                            
                            migrated_files.append(output_file)
                            
                except Exception as e:
                    console.print(f"   ❌ Error migrating {file_path}: {e}")
        
        console.print(f"\n✅ Simple migration complete!")
        console.print(f"📁 Migrated {len(migrated_files)} files to: {output_dir}/migrated")
        
        # Cleanup
        parser.cleanup()
        
    except Exception as e:
        console.print(f"❌ Simple migration failed: {e}", style="red")
        exit(1)


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