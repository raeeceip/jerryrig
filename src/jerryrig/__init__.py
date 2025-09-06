"""JerryRig - Code Migration Tool

A web scraper and code migrator that converts open source repositories 
between programming languages using AI agents and gitingest.
"""

__version__ = "0.1.0"
__author__ = "JerryRig Team"
__email__ = "team@jerryrig.dev"

from .core.scraper import RepositoryScraper
from .core.analyzer import CodeAnalyzer
from .core.migrator import CodeMigrator
from .agents.solace_agent import SolaceAgent

__all__ = [
    "RepositoryScraper",
    "CodeAnalyzer", 
    "CodeMigrator",
    "SolaceAgent",
]