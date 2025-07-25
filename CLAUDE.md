# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Luca is a GenAI Learning Project that serves as an intelligent, interactive tutor designed to revolutionize how students engage with their courses. It combines a Neo4j knowledge graph with AI agents to provide personalized guidance and answers to complex questions about course materials.

The system consists of:
- **Knowledge Graph (Neo4j)**: Stores structured course data including subjects, topics, practices, exercises, and their relationships
- **KG Abstraction Layer (kg/)**: Connection management and query interface for Neo4j interactions
- **Centralized Tools (tools/)**: Shared LangChain tools for all agents including KG and utility operations
- **AI Agents Ecosystem**: Multi-agent system built with the A2A framework
  - **Orchestrator Agent (orchestrator/)**: Main conversation manager and agent coordinator
  - **GapAnalyzer Agent (gapanalyzer/)**: Specialized learning gap analysis
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

#### Orchestrator Agent (Main Entry Point)
```bash
# Run the orchestrator server
python -m orchestrator --host localhost --port 10001

# Test with a single message
python -m orchestrator --test-message "¿Qué es un LEFT JOIN?"

# Test with session ID
python -m orchestrator --test-message "Necesito ayuda con la práctica 2" --session-id "student_123"

# Local debugging and development
python -m orchestrator.local_runner interactive              # Interactive conversation mode
python -m orchestrator.local_runner single "Your message"   # Single message testing
python -m orchestrator.local_runner intent-test             # Intent classification testing

# Run comprehensive tests
python orchestrator/test_client.py

# Run interactive test mode
python orchestrator/test_client.py interactive
```

#### GapAnalyzer Agent (Specialized Agent)
```bash
# Run the GapAnalyzer server
python -m gapanalyzer --host localhost --port 10000

# Test with specific practice data
python -m gapanalyzer.local_runner 2 1.d "No entiendo por qué mi consulta no funciona"

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

### orchestrator/ - Main Conversation Management Agent
- **`agent.py`**: Core `OrchestratorAgent` class managing educational conversations and multi-agent coordination
- **`workflow.py`**: `OrchestratorWorkflow` LangGraph implementation with intent classification and agent routing
- **`schemas.py`**: Data models for conversation memory, intent classification, and multi-agent coordination
- **`agent_executor.py`**: `OrchestratorAgentExecutor` handling A2A protocol and session management
- **`__main__.py`**: CLI entry point and server setup with session management endpoints
- **`test_client.py`**: Comprehensive test client for conversation flows and multi-agent integration

### gapanalyzer/ - Specialized Learning Gap Analysis Agent
- **`agent.py`**: Core `GapAnalyzerAgent` class implementing educational gap detection and evaluation
- **`workflow.py`**: `GapAnalysisWorkflow` LangGraph implementation for gap identification and evaluation
- **`schemas.py`**: Data models for gap analysis, student context, and educational assessment
- **`agent_executor.py`**: `GapAnalyzerAgentExecutor` handling A2A protocol request/response lifecycle
- **`local_runner.py`**: Local testing tool with real knowledge graph data integration
- **`__main__.py`**: CLI entry point and server setup using A2A Starlette application
- **`test_client.py`**: Test client demonstrating gap analysis workflows

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

## Debugging and Development

### VSCode Debugging Configuration

The project includes comprehensive debugging configurations for VSCode in `.vscode/launch.json`:

#### Orchestrator Agent Debugging
- **Orchestrator Interactive Mode**: Interactive conversation debugging with full logging
- **Orchestrator Single Message**: Test specific messages with detailed analysis
- **Orchestrator Intent Test**: Test intent classification with multiple scenarios
- **Orchestrator Server**: Debug the A2A server with full request/response cycle

#### GapAnalyzer Agent Debugging
- **GapAnalyzer Local Runner**: Debug with real KG data using practice/exercise context
- **GapAnalyzer Server**: Debug the A2A server for gap analysis

#### Usage in VSCode
1. Open VSCode in the project root
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select desired configuration from dropdown
4. Set breakpoints in agent code
5. Press F5 to start debugging

### Local Runners for Development

#### Orchestrator Local Runner
```bash
# Interactive mode - full conversation debugging
python -m orchestrator.local_runner interactive

# Single message testing
python -m orchestrator.local_runner single "¿Qué es normalización?"

# Intent classification testing
python -m orchestrator.local_runner intent-test
```

**Features:**
- Multi-turn conversation with memory persistence
- Detailed response analysis and context inspection
- Intent classification debugging
- Multi-agent coordination tracing
- Session state management
- Special commands: `session`, `intent-test`, `quit`

#### GapAnalyzer Local Runner
```bash
# Practice-specific context from KG
python -m gapanalyzer.local_runner 2 1.d "Mi consulta no funciona"
```

**Features:**
- Real knowledge graph data integration
- Practice and exercise context building
- Gap analysis workflow debugging
- Comprehensive result analysis

### Workflow Visualization

Both agents include workflow visualization tools for understanding LangGraph structure:

#### Orchestrator Workflow Visualization
```bash
# Generate PNG workflow diagram
python orchestrator/visualize_workflow.py

# Generate JPG with custom output
python orchestrator/visualize_workflow.py --format jpg --output ./docs/

# Show only workflow information (no image)
python orchestrator/visualize_workflow.py --info-only

# Run as module
python -m orchestrator.visualize_workflow --format png
```

#### GapAnalyzer Workflow Visualization
```bash
# Generate PNG workflow diagram
python gapanalyzer/visualize_workflow.py

# Generate JPG with custom output
python gapanalyzer/visualize_workflow.py --format jpg --output ./docs/

# Show only workflow information (no image)
python gapanalyzer/visualize_workflow.py --info-only

# Run as module
python -m gapanalyzer.visualize_workflow --format png
```

**Workflow Visualization Features:**
- **Automatic Diagram Generation**: Creates visual representations of LangGraph workflows
- **Multiple Formats**: PNG, JPG, or Mermaid (.mmd) text files
- **Detailed Node Information**: Shows all workflow nodes, edges, and conditional logic
- **Intent Classification Details**: Updated system with practical_general vs practical_specific distinction
- **Comprehensive Documentation**: Includes workflow features, data flow, and architecture details
- **Mermaid CLI Integration**: Optional conversion using @mermaid-js/mermaid-cli

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

## Frontend Application (Streamlit)

### Overview
LUCA includes a complete web frontend built with Streamlit that provides an educational chat interface similar to Claude/OpenAI. The frontend connects directly to the Orchestrator agent and provides a professional user experience with UCA branding.

### Features
- 🎓 **Educational Chat Interface**: Clean, intuitive chat with real-time streaming
- 🔐 **UCA Authentication**: Secure login with @uca.edu.ar email validation  
- 📚 **Dynamic Subject Selection**: Loads subjects from Knowledge Graph
- 💬 **Conversation Management**: Persistent conversation history in Neo4j
- 🎨 **Professional Design**: FICA and LUCA branding with responsive layout
- ⚡ **Real-time Streaming**: Live response updates from Orchestrator

### Quick Start
```bash
# Install frontend dependencies
pip install streamlit aiohttp

# Test all components
cd frontend
python test_frontend.py

# Start application
python run.py

# Access at http://localhost:8501
# Login: visitante@uca.edu.ar / visitante!
```

### Architecture
```
frontend/
├── app.py              # Main Streamlit application
├── auth.py             # User authentication & conversation management
├── chat.py             # Orchestrator client & streaming
├── utils.py            # Utilities (subjects, formatting)
├── run.py              # Application runner
├── test_frontend.py    # Complete test suite
└── assets/             # Logos and static files
```

### Neo4j Schema Extensions
The frontend adds two new node types to the Knowledge Graph:

```cypher
# User authentication
(:Usuario {
  email: string,           # Must end with @uca.edu.ar
  password: string,        # Plain text for development
  nombre: string,          # Display name
  created_at: datetime,
  last_login: datetime
})

# Conversation management  
(:Conversacion {
  id: string,              # UUID
  title: string,           # Auto-generated from first message
  subject: string,         # Educational subject from KG
  created_at: datetime,
  updated_at: datetime,
  message_count: integer
})

# Relationship
(:Usuario)-[:OWNS]->(:Conversacion)
```

### Integration with Agents
- **Direct Connection**: Uses `OrchestratorAgentExecutor` for real-time communication
- **Subject Injection**: Passes selected subject to orchestrator context via `educational_subject` parameter
- **Streaming Display**: Shows progress indicators and intermediate processing steps
- **Session Management**: Maintains conversation continuity across interactions

### Testing
```bash
# Comprehensive test suite
python frontend/test_frontend.py

# Tests covered:
# ✅ Dependencies (streamlit, aiohttp, neo4j)
# ✅ Neo4j connection and user data
# ✅ Authentication and conversation management  
# ✅ Subject loading from Knowledge Graph
# ✅ Orchestrator client initialization
```

### Development Workflow
```bash
# 1. Start Neo4j and ensure KG is populated
docker run -d -p 7687:7687 -p 7474:7474 --name neo4j neo4j:5.26.1

# 2. Test backend agents work
python -m orchestrator.local_runner single "Test message"

# 3. Test frontend components
cd frontend && python test_frontend.py

# 4. Start frontend application  
python run.py

# 5. Access http://localhost:8501 and test full flow
```

For detailed frontend documentation, see `frontend/GETTING_STARTED.md` and `frontend/README.md`.