# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Luca is a GenAI Learning Project that serves as an intelligent, interactive tutor designed to revolutionize how students engage with their courses. It combines a Neo4j knowledge graph with AI agents to provide personalized guidance and answers to complex questions about course materials.

The system consists of:
- **Knowledge Graph (Neo4j)**: Stores structured course data including subjects, topics, practices, exercises, and their relationships
- **AI Agent (gapanalyzer/)**: A currency conversion agent built with the A2A (Agent-to-Agent) framework using LangChain and LangGraph
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

### gapanalyzer/ - AI Agent Module
- **`agent.py`**: Core `CurrencyAgent` class implementing currency conversion functionality using LangChain/LangGraph
- **`agent_executor.py`**: `CurrencyAgentExecutor` that handles A2A protocol request/response lifecycle
- **`__main__.py`**: CLI entry point and server setup using A2A Starlette application
- **`test_client.py`**: Test client demonstrating A2A client usage patterns

### Agent Architecture Pattern
The agent follows the A2A (Agent-to-Agent) framework pattern:
1. **Agent Class**: Implements core business logic with streaming responses
2. **Agent Executor**: Handles A2A protocol integration and task management  
3. **Request Handler**: Manages HTTP requests and agent card serving
4. **Server Application**: Starlette-based HTTP server with A2A endpoints

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
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_password"

# OpenAI for embeddings
OPENAI_API_KEY="your_openai_key"

# Agent Configuration
GOOGLE_API_KEY="your_google_api_key"  # For Google models
# OR
TOOL_LLM_URL="http://localhost:11434"  # For local LLM
TOOL_LLM_NAME="llama3"
model_source="google"  # or "local"
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
- **openai**: Embeddings generation
- **uvicorn**: ASGI server for agent endpoints
- **click**: CLI interface
- **pandas**: Data processing for Excel files

## Testing

Run the test client to verify agent functionality:
```bash
python gapanalyzer/test_client.py
```

This tests both public agent card resolution and message exchange patterns including multi-turn conversations and streaming responses.