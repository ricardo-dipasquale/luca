# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Luca is a GenAI Learning Project that serves as an intelligent, interactive tutor designed to revolutionize how students engage with their courses. It combines a Neo4j knowledge graph with AI agents to provide personalized guidance and answers to complex questions about course materials.

The system consists of:
- **Knowledge Graph (Neo4j)**: Stores structured course data including subjects, topics, practices, exercises, and their relationships
- **KG Abstraction Layer (kg/)**: Connection management and query interface for Neo4j interactions
- **Centralized Tools (tools/)**: Shared LangChain tools for all agents including KG and utility operations
- **AI Agents**: Multiple agents built with the A2A framework (e.g., gapanalyzer/)
- **Database Scripts**: Knowledge graph creation and management utilities

## Development Commands

### Environment Setup
```bash
# Create and activate conda environment
conda create -n luca python=3.12
conda activate luca

# Install dependencies
pip install -r requirements.txt
# OR using uv (preferred)
uv sync
```

### Neo4j Database Setup
```bash
cd db

# Create required directories
mkdir -p data plugins logs import

# Set permissions (development only)
sudo chmod -R a+rw ./data ./plugins ./logs ./import

# Copy Neo4j plugins to plugins/ directory:
# - neo4j-graph-data-science-2.13.2.jar
# - apoc-5.26.1-core.jar

# Run Neo4j with environment file
docker run -d --env-file .env -p 7474:7474 -p 7687:7687 \
  -v ./data:/data -v ./logs:/logs -v ./import:/var/lib/neo4j/import \
  -v ./plugins:/plugins --name neo4j neo4j:5.26.1

# OR run without environment file
docker run -d -p 7474:7474 -p 7687:7687 \
  -v ./data:/data -v ./logs:/logs -v ./import:/var/lib/neo4j/import \
  -v ./plugins:/plugins \
  -e NEO4J_AUTH="neo4jusr/neo4jpassword" \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_apoc_import_file_use__neo4j__config=true \
  -e NEO4JLABS_PLUGINS='["apoc","graph-data-science"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  --name neo4j neo4j:5.26.1
```

### Knowledge Graph Creation
```bash
# Create knowledge graph from Excel data
python db/create_kg.py
```

### Agent Development
```bash
# Run the agent server
uv run gapanalyzer --host localhost --port 10000
# OR
python -m gapanalyzer --host localhost --port 10000

# Test the agent
python gapanalyzer/test_client.py
```

### Docker Deployment
```bash
# Build and run the containerized agent
docker build -t luca-agent .
docker run -p 10000:10000 luca-agent
```

## Code Architecture

### kg/ - Knowledge Graph Abstraction Layer
- **`connection.py`**: `KGConnection` class for Neo4j connection management using environment variables
- **`queries.py`**: `KGQueryInterface` class providing high-level functional interface to KG operations
- **`__init__.py`**: Module exports and documentation
- **`example.py`**: Usage examples and demonstrations

### tools/ - Centralized LangChain Tools
- **`kg_tools.py`**: Knowledge graph interaction tools (search, get subjects, practices, theoretical content, etc.)
- **`utility_tools.py`**: General utility tools (text processing, calculations, formatting)
- **`registry.py`**: Tool registry and factory pattern for tool discovery and management
- **`llm_config.py`**: Centralized LLM configuration and model management
- **`observability.py`**: Langfuse integration for LLM call observability and tracing
- **`__init__.py`**: Package exports and convenience functions

### Agent Architecture Pattern
All agents follow the A2A (Agent-to-Agent) framework pattern:
1. **Agent Class**: Implements core business logic with streaming responses and uses centralized tools
2. **Agent Executor**: Handles A2A protocol integration and task management  
3. **Request Handler**: Manages HTTP requests and agent card serving
4. **Server Application**: Starlette-based HTTP server with A2A endpoints

### gapanalyzer/ - Example AI Agent Module
- **`agent.py`**: Core `CurrencyAgent` class implementing currency conversion functionality
- **`agent_executor.py`**: `CurrencyAgentExecutor` that handles A2A protocol request/response lifecycle
- **`__main__.py`**: CLI entry point and server setup using A2A Starlette application
- **`test_client.py`**: Test client demonstrating A2A client usage patterns

### Knowledge Graph Schema
- **Materia** → **Carrera**, **Profesor**, **ObjetivoMateria**, **UnidadTematica**
- **UnidadTematica** → **Tema**
- **Practica** → **Tema**, **Tip**, **SeccionPractica**
- **SeccionPractica** → **Ejercicio**, **Tip**
- **Ejercicio** → **Respuesta**, **Tip**

All text nodes include vector embeddings using OpenAI's text-embedding-ada-002 model.

## Environment Variables

Required environment variables (create `.envrc` with direnv or `.env`):
```bash
# Neo4j Connection
NEO4J_URI="bolt://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="your_password"

# OpenAI Configuration
OPENAI_API_KEY="your_openai_key"

# Default LLM Configuration for Agents
DEFAULT_LLM_MODEL="gpt-4o-mini"      # OpenAI's efficient model (recommended)
DEFAULT_LLM_PROVIDER="openai"        # Provider: currently only OpenAI supported
DEFAULT_LLM_TEMPERATURE="0.1"        # Low temperature for consistent responses

# Optional: Advanced LLM settings
DEFAULT_LLM_MAX_TOKENS="4096"        # Maximum response tokens
DEFAULT_LLM_TIMEOUT="60"             # Request timeout in seconds

# LLM Graph Builder API (for theoretical content tool)
GRAPHBUILDER_URI="http://127.0.0.1:8000/chat_bot"
INTERNAL_NEO4J_URI="bolt://localhost:7687"

# Langfuse Observability (Optional)
LANGFUSE_HOST="http://localhost:3000"
LANGFUSE_PUBLIC_KEY="pk-lf-your-public-key"
LANGFUSE_SECRET_KEY="sk-lf-your-secret-key"
```

## Data Sources

Knowledge graph is populated from Excel files in `db/datasources/`:
- **Programa.xlsx**: Course program structure (subjects, topics, objectives)
- **Prácticas Bases de Datos.xlsx**: Practice exercises and solutions
- Additional PDF materials for reference

## Key Dependencies

- **a2a-sdk**: Agent-to-Agent communication framework
- **langchain/langgraph**: LLM orchestration and agent workflows
- **neo4j**: Graph database driver
- **openai**: Embeddings generation and LLM API
- **langfuse**: LLM observability and tracing
- **uvicorn**: ASGI server for agent endpoints
- **click**: CLI interface
- **pandas**: Data processing for Excel files

## Tool Usage in Agents

### Using Centralized Tools and LLM Configuration
```python
from tools import (
    create_default_llm,           # LLM from environment config
    get_kg_tools, 
    get_utility_tools
)
from tools.observability import create_observed_llm  # LLM with Langfuse tracing
from tools.registry import ToolRegistry
from langgraph.prebuilt import create_react_agent

# Create LLM using environment variables
llm = create_default_llm()  # Uses DEFAULT_LLM_* env vars

# Create LLM with automatic Langfuse observability (recommended)
observed_llm = create_observed_llm()  # Includes automatic tracing

# Get tools by category
kg_tools = get_kg_tools()
utility_tools = get_utility_tools()

# Get tools for specific agent types
registry = ToolRegistry()
tutor_tools = registry.get_tools_for_agent("tutor")
practice_tools = registry.get_tools_for_agent("practice_helper")

# Create agent with observed LLM and tools (recommended for production)
agent = create_react_agent(observed_llm, tools=kg_tools + utility_tools)
```

### LLM Configuration Options
```python
from tools.llm_config import (
    create_default_llm,
    create_openai_llm,
    get_model_info,
    validate_model_compatibility
)

# Use default configuration (uses DEFAULT_LLM_* environment variables)
llm = create_default_llm()

# Override specific parameters
llm = create_default_llm(temperature=0.2, max_tokens=2048)

# Use specific OpenAI model
llm = create_openai_llm(model="gpt-4o", temperature=0.0)

# Check model compatibility
is_compatible = validate_model_compatibility("openai", "gpt-4o-mini")

# Get current configuration info
info = get_model_info()
print(f"Using: {info['provider']} - {info['model']}")
```

### Available OpenAI Models
- **gpt-4o-mini**: Efficient, fast model (recommended default for most use cases)
- **gpt-4o**: Most capable model for complex reasoning tasks
- **gpt-4-turbo**: High performance model with fast response times
- **gpt-3.5-turbo**: Legacy efficient model for simple tasks

### Available Tool Categories
- **Knowledge Graph Tools**: Search KG, get subjects/topics/practices, theoretical content, find related content
- **Utility Tools**: Text processing, calculations, data formatting, validation
- **Tool Registry**: Centralized discovery, categorization, and agent-specific tool selection

### Observability and Monitoring

The project includes comprehensive LLM observability using Langfuse:

#### Automatic LLM Tracing
```python
from tools.observability import create_observed_llm

# Create LLM with automatic tracing
llm = create_observed_llm()

# All LLM calls are automatically traced to Langfuse
response = llm.invoke("Your prompt here")
```

#### Direct OpenAI Call Observability
```python
from tools.observability import observe_openai_call
from openai import OpenAI

client = OpenAI()
messages = [{"role": "user", "content": "Hello"}]

# Observed OpenAI call
response = observe_openai_call(
    client=client,
    messages=messages,
    model="gpt-4o-mini",
    operation_name="test_call",
    metadata={"purpose": "testing"}
)
```

#### LangChain Integration
All agents using `create_observed_llm()` automatically get:
- Request/response tracing
- Token usage tracking
- Error monitoring
- Session grouping
- Performance metrics

#### Langfuse Setup
1. Configure environment variables in `.envrc`:
   ```bash
   LANGFUSE_HOST="http://localhost:3000"
   LANGFUSE_PUBLIC_KEY="pk-lf-your-key"
   LANGFUSE_SECRET_KEY="sk-lf-your-key"
   ```

2. Start Langfuse (via docker-compose or hosted service)

3. Use `create_observed_llm()` instead of `create_default_llm()` in agents

The system gracefully falls back to unobserved LLMs when Langfuse is not configured.

## Testing

### KG Module Tests
```bash
# Run all KG tests
pytest test/ -v

# Run with coverage
pytest test/ --cov=kg --cov-report=html

# Run specific test categories
pytest -m integration  # Integration tests with database
pytest -m "not slow"   # Skip slow tests
```

### Agent Testing
```bash
# Test example agent
python gapanalyzer/test_client.py
```

This tests both public agent card resolution and message exchange patterns including multi-turn conversations and streaming responses.