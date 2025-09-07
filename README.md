# JerryRig �️

> A distributed code migration platform powered by Solace Agent Mesh for converting repositories between programming languages using AI agents

JerryRig is an event-driven, distributed system that uses Solace Agent Mesh to orchestrate AI-powered code migration across multiple programming languages. It features a modern web interface and real-time processing capabilities.

## 🚀 Features

- **Distributed Agent Mesh**: Event-driven architecture using Solace Agent Mesh
- **Real-time Web Interface**: Modern, responsive UI with live migration status
- **Multi-Language Support**: Convert between Python, JavaScript, TypeScript, Java, Go, Rust, C++, C#
- **Cloud-Ready**: Deploy locally or on cloud platforms with Solace Cloud
- **Scalable Processing**: Horizontal scaling with agent-based architecture
- **Live Status Updates**: Real-time progress tracking and notifications

## 🏗️ Architecture

```
JerryRig Agent Mesh/
├── src/jerryrig/
│   ├── core/                    # Core mesh components
│   │   ├── mesh_launcher.py     # Mesh lifecycle management
│   │   ├── mesh_client.py       # REST API client
│   │   ├── mesh_initializer.py  # Project scaffolding
│   │   ├── migrator.py          # Code migration engine
│   │   └── analyzer.py          # Code analysis
│   ├── agents/                  # Event mesh agents
│   │   └── event_mesh_agent.py  # Agent coordinator
│   ├── cli.py                   # Command line interface
│   └── utils/                   # Utilities
├── sam_project/                 # Solace Agent Mesh project
│   ├── config.yaml             # Mesh configuration
│   ├── agents/                 # Agent modules
│   │   ├── repository_input.py      # Input handling
│   │   ├── repository_orchestrator.py # Workflow coordination
│   │   ├── repository_chunker.py     # Code chunking
│   │   ├── code_analyzer.py          # Analysis agent
│   │   ├── code_migrator.py          # Migration agent
│   │   └── result_aggregator.py     # Result assembly
│   └── logs/                   # Agent logs
└── output/                     # Migration results
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Solace API key (get from [Solace Cloud](https://console.solace.cloud))

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/raeeceip/jerryrig.git
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

3. **Install JerryRig:**
   ```bash
   pip install -e .
   ```

4. **Configure environment variables:**
   ```bash
   # Copy the example .env file
   cp .env .env.local
   
   # Edit .env.local with your API keys:
   # SOLACE_API_KEY=your_solace_api_key_here
   # OPENAI_API_KEY=your_openai_api_key_here
   ```

### Environment Configuration

Create or update your `.env` file:

```env
# Solace Cloud Configuration
SOLACE_API_KEY=your_solace_api_key_from_console_solace_cloud
SOLACE_BASE_URL=https://api.solace.dev

# LLM Provider (OpenAI recommended)
OPENAI_API_KEY=your_openai_api_key

# SAM Configuration
LLM_SERVICE_ENDPOINT=openai
LLM_SERVICE_API_KEY=${OPENAI_API_KEY}
LLM_SERVICE_PLANNING_MODEL_NAME=gpt-4
LLM_SERVICE_GENERAL_MODEL_NAME=gpt-3.5-turbo

# Logging
LOG_LEVEL=INFO
LOG_FILE=jerryrig.log
```

## 🎯 Quick Start

### 1. Initialize Agent Mesh Project (Optional)

```bash
# Create a new mesh project (if you want to customize)
jerryrig init-mesh --project-name my-migration-mesh
```

### 2. Start the Agent Mesh

```bash
# Start the distributed agent mesh with web UI
jerryrig start-mesh -c ./sam_project/config.yaml

# The web interface will be available at: http://localhost:8000
```

### 3. Submit Migration Requests

**Via Web Interface:**
- Open http://localhost:8000 in your browser
- Fill in repository URL and target language
- Click "Start Migration" and watch real-time progress

**Via CLI:**
```bash
# Submit migration request to the running mesh
jerryrig mesh-migration https://github.com/octocat/Hello-World python

# Specify custom output directory
jerryrig mesh-migration https://github.com/user/repo javascript -o ./my-output
```

### 4. Monitor Progress

The web interface provides:
- ✅ **Real-time status updates** - Live progress tracking
- 📊 **Migration statistics** - Success rates, processing times
- 📜 **Migration history** - Complete audit trail
- 🔄 **Agent mesh status** - Active agents and health checks

## 🌐 Cloud Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f jerryrig-mesh

# Stop the mesh
docker-compose down
```

### Cloud Platforms

**AWS/Azure/GCP:**
```bash
# Deploy using the provided Dockerfile
docker build -t jerryrig-mesh .
docker run -p 8000:8000 --env-file .env jerryrig-mesh
```

**Kubernetes:**
```yaml
# See k8s-deployment.yaml for full configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jerryrig-mesh
spec:
  replicas: 3
  selector:
    matchLabels:
      app: jerryrig-mesh
  template:
    spec:
      containers:
      - name: jerryrig
        image: jerryrig-mesh:latest
        ports:
        - containerPort: 8000
        env:
        - name: SOLACE_API_KEY
          valueFrom:
            secretKeyRef:
              name: jerryrig-secrets
              key: solace-api-key
```

## 🔧 CLI Commands

### Mesh Management
```bash
# Initialize new mesh project
jerryrig init-mesh --project-name my-mesh

# Start the agent mesh
jerryrig start-mesh -c ./sam_project/config.yaml -p 8000

# Submit migration to running mesh
jerryrig mesh-migration <repo-url> <target-language> [options]
```

### Direct Migration (Legacy)
```bash
# Quick migration without mesh
jerryrig migrate ./source_code python --output-dir ./output

# Full pipeline
jerryrig full-migration https://github.com/user/repo javascript
```

### Repository Analysis
```bash
# Analyze repository structure
jerryrig scrape https://github.com/user/repo --output-dir ./analysis
```

## 📊 Supported Languages

| Source → Target | Python | JavaScript | TypeScript | Java | Go | Rust | C++ | C# |
|----------------|--------|------------|------------|------|----|----- |-----|-----|
| **Python**     | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **JavaScript** | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **TypeScript** | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **Java**       | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **Go**         | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **Rust**       | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **C++**        | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |
| **C#**         | ✅     | ✅         | ✅         | ✅   | ✅ | ✅   | ✅  | ✅  |

## 🧪 Development

### Running Tests
```bash
pytest tests/
```

### Local Development
```bash
# Install development dependencies
pip install -e ".[dev]"

# Start mesh in development mode
jerryrig start-mesh -c ./sam_project/config.yaml

# Run tests with the mesh running
pytest tests/test_mesh_integration.py
```

## 🔗 API Reference

### Web Interface Endpoints

```http
GET  /                 # Web interface
GET  /status          # Mesh status
POST /migrate         # Submit migration request
GET  /migrations/{id} # Get migration status
```

### Migration Request Format

```json
{
  "repository_url": "https://github.com/user/repo",
  "target_language": "python",
  "source_language": "javascript",  // optional
  "priority": "normal"              // normal, high, urgent
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Solace Cloud Console**: [https://console.solace.cloud](https://console.solace.cloud)
- **Agent Mesh Docs**: [https://docs.solace.dev/agent-mesh](https://docs.solace.dev/agent-mesh)
- **Issue Tracker**: [https://github.com/raeeceip/jerryrig/issues](https://github.com/raeeceip/jerryrig/issues)

## 🙏 Acknowledgments

- [Solace Agent Mesh](https://solace.com/products/event-broker/software/agent-mesh/) for distributed event-driven architecture
- [OpenAI](https://openai.com) for language model capabilities
- The open source community for continuous inspiration

---

**Built with ❤️ using Solace Agent Mesh**

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