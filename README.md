# JerryRig 🔧

> A powerful web scraper and code migrator that converts open source repositories between programming languages using AI agents

JerryRig combines the power of web scraping with AI-driven code migration to help developers quickly convert repositories from one programming language to another. It uses gitingest for repository analysis and Solace agents for intelligent code translation.

## 🚀 Features

- **Repository Scraping**: Automatically analyze open source repositories using gitingest
- **Multi-Language Support**: Convert between Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more
- **AI-Powered Migration**: Uses Solace agents for intelligent code translation
- **Structure Preservation**: Maintains project architecture and patterns during migration
- **Batch Processing**: Process multiple repositories concurrently
- **Migration Reports**: Detailed reports with confidence scores and suggestions

## 🏗️ Architecture

```
JerryRig/
├── src/jerryrig/
│   ├── core/           # Core functionality
│   │   ├── scraper.py  # Repository scraping with gitingest
│   │   ├── analyzer.py # Code structure analysis
│   │   └── migrator.py # Code migration engine
│   ├── agents/         # AI agent interfaces
│   │   └── solace_agent.py # Solace AI agent integration
│   ├── utils/          # Utilities and helpers
│   │   └── logger.py   # Logging configuration
│   ├── cli.py          # Command line interface
│   └── __init__.py     # Package initialization
├── tests/              # Test suite
├── examples/           # Usage examples
└── docs/               # Documentation
```

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jerryrig-team/jerryrig.git
   cd jerryrig
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 🎯 Quick Start

### Command Line Usage

```bash
# Scrape a repository
jerryrig scrape https://github.com/user/repo --output-dir ./scraped

# Migrate code to another language
jerryrig migrate ./source_code python --output-dir ./migrated

# Full pipeline: scrape and migrate
jerryrig full-migration https://github.com/user/repo javascript --output-dir ./output
```

### Python API Usage

```python
from jerryrig import RepositoryScraper, CodeAnalyzer, CodeMigrator

# Initialize components
scraper = RepositoryScraper()
analyzer = CodeAnalyzer()
migrator = CodeMigrator()

# Scrape repository
repo_data = scraper.scrape_repository("https://github.com/user/repo")

# Analyze code structure
analysis = analyzer.analyze_repository("./repo_path")

# Migrate to target language
result = migrator.migrate_code("./source", "python", "./output")
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Solace AI API Configuration
SOLACE_API_KEY=your_solace_api_key_here
SOLACE_BASE_URL=https://api.solace.dev

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=jerryrig.log

# Scraping Configuration
GITINGEST_BASE_URL=https://gitingest.com
REQUEST_TIMEOUT=30
```

### Supported Languages

**Source Languages:**
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts)
- Java (.java)
- C++ (.cpp)
- C (.c)
- Go (.go)
- Rust (.rs)
- Ruby (.rb)
- PHP (.php)

**Target Languages:**
- All source languages plus:
- C# (.cs)
- Swift (.swift)
- Kotlin (.kt)
- Scala (.scala)

## 📖 Examples

### Example 1: Convert Python Flask App to JavaScript Express

```bash
# Scrape Flask repository
jerryrig scrape https://github.com/flask-examples/simple-app --output-dir ./flask_app

# Migrate to JavaScript
jerryrig migrate ./flask_app javascript --output-dir ./express_app
```

### Example 2: Batch Migration

```python
import asyncio
from jerryrig import RepositoryScraper

async def batch_migration():
    scraper = RepositoryScraper()
    repos = [
        "https://github.com/user/repo1",
        "https://github.com/user/repo2",
        "https://github.com/user/repo3"
    ]
    
    results = await scraper.scrape_multiple_repositories(repos)
    print(f"Scraped {len(results)} repositories")

asyncio.run(batch_migration())
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jerryrig

# Run specific test file
pytest tests/test_scraper.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Development Installation

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [https://jerryrig.readthedocs.io](https://jerryrig.readthedocs.io)
- **Issue Tracker**: [https://github.com/jerryrig-team/jerryrig/issues](https://github.com/jerryrig-team/jerryrig/issues)
- **Discussions**: [https://github.com/jerryrig-team/jerryrig/discussions](https://github.com/jerryrig-team/jerryrig/discussions)

## 🙏 Acknowledgments

- [GitIngest](https://gitingest.com) for repository analysis capabilities
- [Solace AI](https://solace.dev) for code migration intelligence
- The open source community for inspiration and support

---

**Built with ❤️ by the JerryRig Team**