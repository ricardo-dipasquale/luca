# Development Guide

## 🚀 Getting Started

This guide provides comprehensive instructions for setting up a development environment and contributing to the Luca project.

## 📋 Prerequisites

### Required Software

- **Python 3.12+**: Primary development language
- **Docker & Docker Compose**: For Neo4j and supporting services
- **Git**: Version control
- **Node.js 18+**: For optional tools (mermaid-cli)

### Recommended Tools

- **VS Code**: Primary IDE with extensions:
  - Python
  - Docker
  - GitLens
  - Python Docstring Generator
- **uv**: Fast Python package manager (recommended over pip)
- **direnv**: Environment variable management
- **Neo4j Desktop**: GUI for database development

## 🛠️ Environment Setup

### 1. Clone and Setup Repository

```bash
# Clone the repository
git clone <repository-url>
cd luca

# Create and activate conda environment
conda create -n luca python=3.12
conda activate luca

# Install uv (recommended package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
# OR using pip
pip install -r requirements.txt

# Install development dependencies
uv sync --group dev
# OR using pip
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

Create a `.envrc` file (for direnv) or `.env` file:

```bash
# Neo4j Configuration
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_secure_password"

# OpenAI Configuration
export OPENAI_API_KEY="sk-your-openai-api-key"

# LLM Configuration
export DEFAULT_LLM_MODEL="gpt-4o-mini"
export DEFAULT_LLM_PROVIDER="openai"
export DEFAULT_LLM_TEMPERATURE="0.1"
export DEFAULT_LLM_MAX_TOKENS="4096"

# Langfuse Observability (Optional)
export LANGFUSE_HOST="http://localhost:3000"
export LANGFUSE_PUBLIC_KEY="pk-lf-your-public-key"
export LANGFUSE_SECRET_KEY="sk-lf-your-secret-key"

# LLM Graph Builder API
export GRAPHBUILDER_URI="http://127.0.0.1:8000/chat_bot"
export INTERNAL_NEO4J_URI="bolt://localhost:7687"

# Development settings
export PYTHONPATH="$PWD"
export LOG_LEVEL="DEBUG"
```

If using direnv:
```bash
# Allow the .envrc file
direnv allow
```

### 3. Database Setup

```bash
cd db

# Create required directories
mkdir -p data plugins logs import

# Download Neo4j plugins to plugins/ directory:
# - neo4j-graph-data-science-2.13.2.jar
# - apoc-5.26.1-core.jar
# Available from: https://neo4j.com/deployment-center/

# Set permissions (development only)
sudo chmod -R a+rw ./data ./plugins ./logs ./import

# Start Neo4j container
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -v $PWD/data:/data \
  -v $PWD/logs:/logs \
  -v $PWD/import:/var/lib/neo4j/import \
  -v $PWD/plugins:/plugins \
  -e NEO4J_AUTH="neo4j/your_secure_password" \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_apoc_import_file_use__neo4j__config=true \
  -e NEO4JLABS_PLUGINS='["apoc","graph-data-science"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  neo4j:5.26.1

# Wait for Neo4j to start (check logs)
docker logs -f neo4j

# Create knowledge graph
python create_kg.py
```

### 4. Verify Installation

```bash
# Test KG connection
python -c "from kg import KGConnection; conn = KGConnection(); print('KG Connected:', conn.test_connection())"

# Test LLM configuration
python -c "from tools import create_default_llm; llm = create_default_llm(); print('LLM Model:', llm.model_name)"

# Run basic agent test
python -m gapanalyzer.local_runner --help
```

## 🏗️ Development Workflow

### Project Structure Understanding

```
luca/
├── docs/                      # Documentation
├── kg/                        # Knowledge Graph abstraction
│   ├── connection.py          # Connection management
│   ├── queries.py             # Query interface
│   └── example.py             # Usage examples
├── tools/                     # Centralized tools
│   ├── kg_tools.py            # KG tools
│   ├── utility_tools.py       # Utility tools
│   ├── llm_config.py          # LLM configuration
│   ├── observability.py       # Langfuse integration
│   └── registry.py            # Tool registry
├── gapanalyzer/              # Gap analysis agent
│   ├── agent.py               # Core agent
│   ├── workflow.py            # LangGraph workflow
│   ├── schemas.py             # Data models
│   ├── agent_executor.py      # A2A integration
│   └── local_runner.py        # Development runner
├── test/                      # Test suite
│   ├── conftest.py            # Pytest configuration
│   ├── test_kg/               # KG tests
│   ├── test_tools/            # Tools tests
│   └── test_agents/           # Agent tests
└── db/                        # Database setup
    ├── create_kg.py           # KG creation script
    ├── datasources/           # Excel data
    └── docker-compose.yml     # Services
```

### Development Patterns

#### 1. Agent Development Pattern

All agents follow the A2A framework pattern:

```python
# agent.py - Core business logic
class MyAgent:
    def __init__(self):
        self.llm = create_observed_llm()
        self.tools = self._load_tools()
    
    async def stream(self, query, context_id):
        # Streaming response implementation
        pass

# agent_executor.py - A2A integration
class MyAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = MyAgent()
    
    async def execute(self, context, event_queue):
        # A2A protocol handling
        pass

# schemas.py - Data models
class MyRequestData(BaseModel):
    query: str
    context: Optional[str] = None

# local_runner.py - Development testing
class LocalMyAgentRunner:
    def __init__(self):
        self.agent = MyAgent()
    
    async def run_test(self, query):
        # Local testing implementation
        pass
```

#### 2. Tool Development Pattern

```python
from langchain.tools import tool
from tools.registry import ToolRegistry

@tool
def my_custom_tool(input_param: str) -> str:
    """
    Description of what the tool does.
    
    Args:
        input_param: Description of the parameter
        
    Returns:
        Description of the return value
    """
    # Tool implementation
    return result

# Register the tool
registry = ToolRegistry()
registry.register_tool(
    tool=my_custom_tool,
    categories=["custom", "utility"],
    agents=["gapanalyzer", "tutor"]
)
```

#### 3. Workflow Development Pattern

```python
from langgraph.graph import StateGraph
from pydantic import BaseModel

class WorkflowState(BaseModel):
    input_data: str
    intermediate_result: Optional[str] = None
    final_result: Optional[str] = None
    error_message: Optional[str] = None

def create_workflow():
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("process_input", process_input_node)
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("generate_output", generate_output_node)
    
    # Add edges
    workflow.set_entry_point("process_input")
    workflow.add_edge("process_input", "analyze_data")
    workflow.add_edge("analyze_data", "generate_output")
    workflow.add_edge("generate_output", END)
    
    return workflow.compile()
```

## 🧪 Testing

### Test Structure

```
test/
├── conftest.py                # Shared fixtures
├── test_kg/
│   ├── test_connection.py     # Connection tests
│   ├── test_queries.py        # Query interface tests
│   └── integration/           # Integration tests
├── test_tools/
│   ├── test_kg_tools.py       # KG tools tests
│   ├── test_utility_tools.py  # Utility tools tests
│   └── test_registry.py       # Registry tests
└── test_agents/
    ├── test_gapanalyzer.py    # GapAnalyzer tests
    └── integration/           # End-to-end tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kg --cov=tools --cov=gapanalyzer --cov-report=html

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests
pytest -m tools             # Tools tests only

# Run specific test file
pytest test/test_kg/test_connection.py -v

# Run with debugging
pytest -s --pdb test/test_agents/test_gapanalyzer.py
```

### Test Configuration

```python
# conftest.py
import pytest
from kg import KGConnection
from tools import create_default_llm

@pytest.fixture(scope="session")
def kg_connection():
    """Shared KG connection for tests"""
    conn = KGConnection()
    yield conn
    conn.close()

@pytest.fixture
def test_llm():
    """Test LLM configuration"""
    return create_default_llm(temperature=0.0)

@pytest.fixture
def sample_student_context():
    """Sample data for testing"""
    from gapanalyzer.schemas import StudentContext
    return StudentContext(
        student_question="Test question",
        subject_name="Test Subject",
        practice_context="Test practice",
        exercise_context="Test exercise"
    )
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from unittest.mock import Mock, patch
from gapanalyzer.agent import GapAnalyzerAgent

class TestGapAnalyzerAgent:
    def test_init(self):
        """Test agent initialization"""
        agent = GapAnalyzerAgent()
        assert agent.llm is not None
        assert agent.workflow is not None
    
    @pytest.mark.asyncio
    async def test_stream_basic(self, sample_student_context):
        """Test basic streaming functionality"""
        agent = GapAnalyzerAgent()
        
        results = []
        async for chunk in agent.stream(sample_student_context, "test_context"):
            results.append(chunk)
        
        assert len(results) > 0
        assert results[-1]['is_task_complete'] is True
    
    @patch('gapanalyzer.agent.create_observed_llm')
    def test_init_with_mock_llm(self, mock_llm):
        """Test with mocked LLM"""
        mock_llm.return_value = Mock()
        agent = GapAnalyzerAgent()
        assert agent.llm is not None
```

#### Integration Test Example

```python
import pytest
from kg import KGConnection

@pytest.mark.integration
class TestKGIntegration:
    def test_kg_connection(self, kg_connection):
        """Test actual KG connection"""
        result = kg_connection.test_connection()
        assert result is True
    
    def test_basic_query(self, kg_connection):
        """Test basic query execution"""
        result = kg_connection.execute_query(
            "MATCH (n) RETURN count(n) as node_count"
        )
        assert isinstance(result, list)
        assert len(result) > 0
```

## 🔧 Development Tools

### Code Quality Tools

```bash
# Format code
black .
isort .

# Type checking
mypy kg/ tools/ gapanalyzer/

# Linting
flake8 .
pylint kg/ tools/ gapanalyzer/

# Security scanning
bandit -r .
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

Install and activate:
```bash
pip install pre-commit
pre-commit install
```

### Development Scripts

Create useful development scripts in `scripts/` directory:

```bash
# scripts/setup_dev.sh
#!/bin/bash
set -e

echo "Setting up development environment..."
conda activate luca
uv sync --group dev
python -c "from kg import KGConnection; print('KG OK:', KGConnection().test_connection())"
echo "Development environment ready!"

# scripts/run_tests.sh
#!/bin/bash
pytest --cov=kg --cov=tools --cov=gapanalyzer --cov-report=html
echo "Coverage report generated in htmlcov/"

# scripts/start_services.sh
#!/bin/bash
cd db
docker-compose up -d
echo "Services started. Neo4j: http://localhost:7474"
```

## 🐛 Debugging

### Local Development Debugging

#### GapAnalyzer Local Runner

```bash
# Interactive mode
python -m gapanalyzer.local_runner --interactive

# Direct question
python -m gapanalyzer.local_runner "¿Cómo funciona un LEFT JOIN?"

# Verbose logging
LOG_LEVEL=DEBUG python -m gapanalyzer.local_runner --interactive
```

#### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "GapAnalyzer Local Runner",
            "type": "python",
            "request": "launch",
            "module": "gapanalyzer.local_runner",
            "args": ["--interactive"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Pytest Current File",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v", "-s"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

#### Neo4j Browser Queries

Access Neo4j Browser at `http://localhost:7474` and run diagnostic queries:

```cypher
// Check node counts
MATCH (n) RETURN labels(n) as label, count(n) as count

// Check embeddings
MATCH (n) WHERE n.embedding IS NOT NULL 
RETURN labels(n) as label, count(n) as with_embeddings

// Sample practice data
MATCH (p:Practica)-[:TIENE_SECCION]->(s:SeccionPractica)-[:TIENE_EJERCICIO]->(e:Ejercicio)
RETURN p.nombre, s.nombre, e.enunciado LIMIT 5
```

### Performance Debugging

#### LLM Call Monitoring

Use Langfuse dashboard to monitor:
- Token usage and costs
- Response times
- Error rates
- Prompt effectiveness

#### Database Performance

```cypher
// Show query performance
CALL db.queryJmx('org.neo4j:instance=kernel#0,name=Page cache')
YIELD attributes
RETURN attributes

// Check indexes
CALL db.indexes()

// Explain query performance
EXPLAIN MATCH (n:Tema) WHERE n.nombre CONTAINS 'JOIN' RETURN n
```

## 🔄 CI/CD and Deployment

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      neo4j:
        image: neo4j:5.26.1
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install uv
        uv sync
    
    - name: Run tests
      env:
        NEO4J_URI: bolt://localhost:7687
        NEO4J_USERNAME: neo4j
        NEO4J_PASSWORD: testpassword
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        pytest --cov=kg --cov=tools --cov=gapanalyzer
```

### Docker Development

```dockerfile
# Dockerfile.dev
FROM python:3.12-slim

# Install development tools
RUN pip install uv pytest black isort mypy

# Copy source
COPY . /app
WORKDIR /app

# Install dependencies
RUN uv sync --group dev

# Development command
CMD ["python", "-m", "gapanalyzer.local_runner", "--interactive"]
```

## 🤝 Contributing Guidelines

### Code Standards

1. **Type Hints**: All functions must have complete type hints
2. **Docstrings**: Use Google-style docstrings
3. **Pydantic Models**: Use for all data validation
4. **Error Handling**: Implement comprehensive error handling
5. **Testing**: Maintain minimum 80% test coverage

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all tests pass and coverage requirements met
4. Update documentation if needed
5. Submit pull request with clear description

### Code Review Checklist

- [ ] Code follows project patterns and standards
- [ ] All tests pass and coverage is maintained
- [ ] Documentation is updated for new features
- [ ] No hardcoded secrets or sensitive data
- [ ] Error handling is comprehensive
- [ ] Performance considerations addressed

### Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create release branch
4. Final testing and validation
5. Merge to main and tag release
6. Deploy to production environments

This development guide should provide everything needed to contribute effectively to the Luca project.