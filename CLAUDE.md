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
- **Guardrails System (guardrails/)**: Hybrid security layer for educational content safety and quality assurance
- **Agent Testing Framework (agent-test/)**: Comprehensive testing system for agent evaluation and metrics
- **Flask Frontend (frontend/)**: Modern web interface for interacting with educational agents
- **Database Scripts**: Knowledge graph creation and management utilities
- **Utility Scripts (scripts/)**: Database cleanup and maintenance utilities

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

### Database Cleanup
```bash
# Interactive cleanup with confirmation prompt
python scripts/cleanup_database.py

# Auto-confirm cleanup (skip prompt) 
python scripts/cleanup_database.py --confirm

# Show database summary without cleanup
python scripts/cleanup_database.py --summary-only

# Verbose logging
python scripts/cleanup_database.py --verbose
```

**⚠️ WARNING**: Database cleanup permanently deletes ALL conversation data, checkpoints, and agent memory. Use only for development/testing.

### Agent Testing Framework

```bash
# Install testing dependencies
pip install langfuse click pydantic

# Quick start with pre-built suites
python -m agent-test.cli suite list
python -m agent-test.cli run orchestrator_basic_qa
python -m agent-test.cli results list

# Create custom test suite
python -m agent-test.cli suite create my_suite --agent=orchestrator
python -m agent-test.cli suite add-question my_suite \
  --question="¿Qué es normalización?" \
  --expected="Explicación del proceso de normalización..." \
  --subject="Bases de Datos" \
  --difficulty=medium

# Upload to Langfuse (optional)
python -m agent-test.cli dataset upload my_suite

# Run comprehensive testing
python -m agent-test.cli run my_suite --iterations=3
python -m agent-test.cli run-all --agent-filter=orchestrator

# Analyze results
python -m agent-test.cli results show <run_id>
python -m agent-test.cli results list --suite=my_suite
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

#### Full Stack Deployment (Recommended)
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and configuration

# Start all services (Neo4j, Langfuse, LUCA Flask app)
docker-compose up -d

# View logs
docker-compose logs -f luca

# Stop all services
docker-compose down
```

#### Flask Application Only
```bash
# Build LUCA Flask application image
docker build -t luca-app .

# Run with environment variables
docker run -p 5000:5000 \
  -e NEO4J_URI="bolt://localhost:7687" \
  -e NEO4J_USERNAME="neo4j" \
  -e NEO4J_PASSWORD="your_password" \
  -e OPENAI_API_KEY="your_openai_key" \
  -e DEFAULT_LLM_MODEL="gpt-4o-mini" \
  -e DEFAULT_LLM_PROVIDER="openai" \
  -e DEFAULT_LLM_TEMPERATURE="0.1" \
  luca-app
```

#### Individual Agent Deployment
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

### guardrails/ - Hybrid Educational Safety System
- **`core.py`**: Main `EducationalGuardrailLayer` orchestrating all validation components
- **`schemas.py`**: Pydantic data models for guardrail results, violations, and configurations
- **`content_safety.py`**: OpenAI Moderation API and Spanish profanity filtering
- **`educational_context.py`**: Academic relevance validation with LLM assessment
- **`rate_limiting.py`**: Multi-tier usage limits with escalating penalties
- **`agent_response_validation.py`**: Post-processing validation of agent responses for educational quality
- **`orchestrator_integration.py`**: Transparent streaming wrapper for Orchestrator integration
- **`config.py`**: Environment-based configuration management with predefined profiles
- **`__init__.py`**: Package exports and main entry points

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

# Guardrails System (Optional - defaults provided)
GUARDRAILS_ENABLE_OPENAI_MODERATION=true
GUARDRAILS_ENABLE_PROFANITY_FILTER=true
GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION=true
GUARDRAILS_ENABLE_RATE_LIMITING=true
GUARDRAILS_ENABLE_RESPONSE_VALIDATION=true
GUARDRAILS_ENABLE_LANGFUSE_LOGGING=true
GUARDRAILS_STRICT_ACADEMIC_MODE=false
GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE=true
GUARDRAILS_MAX_REQUESTS_PER_MINUTE=30
GUARDRAILS_MAX_REQUESTS_PER_HOUR=200
GUARDRAILS_MAX_REQUESTS_PER_DAY=1000

# Flask Application (for Docker deployment)
FLASK_SECRET_KEY="your-secure-secret-key-for-production"
```

### Docker Environment Variables

When using Docker Compose, all required environment variables are automatically configured using the `.env` file. The LUCA service in `docker-compose.yml` includes:

- **Neo4j Connection**: Configured to use the internal Docker network (`bolt://neo4j:7687`)
- **OpenAI API**: Uses your `OPENAI_API_KEY` from `.env`
- **LLM Configuration**: Configurable model, provider, and temperature settings
- **Langfuse Integration**: Optional observability with automatic service discovery
- **Flask Security**: Production-ready secret key configuration

The docker-compose setup ensures all services can communicate internally while exposing only necessary ports to the host system.

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
- **click**: CLI interface for testing framework
- **pydantic**: Data validation and schemas
- **pandas**: Data processing for Excel files
- **flask**: Web framework for frontend interface

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

## Agent Testing Framework

LUCA includes a comprehensive testing framework for evaluating and monitoring agent performance with Langfuse integration.

### Architecture

```
agent-test/
├── cli.py                    # Main CLI interface
├── __main__.py              # Entry point
├── schemas.py               # Pydantic data models
├── config/
│   └── config.yaml         # Framework configuration
├── core/
│   ├── suite_manager.py    # Test suite management
│   ├── test_runner.py      # Agent execution engine
│   ├── metrics_collector.py # Automated metrics collection
│   ├── results_manager.py  # Results storage and analysis
│   └── langfuse_integration.py # Langfuse datasets and traces
├── suites/                 # JSON test suite files
├── results/                # Execution results storage
└── README.md              # Complete documentation
```

### Quick Start

```bash
# Install testing dependencies
pip install langfuse click pydantic

# Create your first test suite
python -m agent-test.cli suite create my_suite --agent=orchestrator \
  --description="Basic Q&A evaluation"

# Add test questions
python -m agent-test.cli suite add-question my_suite \
  --question="¿Qué es un LEFT JOIN?" \
  --expected="Explicación de LEFT JOIN con ejemplos" \
  --subject="Bases de Datos" \
  --difficulty=medium

# Upload to Langfuse (optional)
python -m agent-test.cli dataset upload my_suite

# Run the test suite
python -m agent-test.cli run my_suite

# View results
python -m agent-test.cli results list
python -m agent-test.cli results show <run_id>
```

### Test Suite Structure

Test suites are JSON files containing questions, expected answers, and evaluation metrics:

```json
{
  "name": "orchestrator_basic_qa",
  "agent_type": "orchestrator",
  "questions": [
    {
      "id": "q_01",
      "question": "¿Qué es un LEFT JOIN?",
      "expected_answer": "Explicación detallada...",
      "subject": "Bases de Datos",
      "difficulty": "medium",
      "metrics": {
        "should_use_kg": true,
        "expected_intent": "conceptual_explanation"
      }
    }
  ]
}
```

### Automated Metrics Collection

The framework automatically collects comprehensive metrics:

#### Orchestrator Agent Metrics
- **Intent Classification**: Detected intents and confidence scores
- **Routing Decisions**: When and why questions are routed to GapAnalyzer
- **Knowledge Graph Usage**: Queries executed and results found
- **Response Analysis**: Length, examples, mathematical notation usage
- **Educational Quality**: Explanation type, conceptual depth

#### GapAnalyzer Agent Metrics  
- **Gap Analysis**: Number and types of learning gaps identified
- **Content Retrieval**: Relevant educational content found
- **Pedagogical Elements**: Use of scaffolding, hints, step-by-step explanations
- **Response Depth**: Analysis of explanation comprehensiveness

#### General Quality Metrics
- **Performance**: Execution time, success rates
- **Response Quality**: Completeness, clarity, relevance, educational value
- **Language Quality**: Grammar, structure, variety

### Langfuse Integration

The framework provides seamless Langfuse integration:

```bash
# Configure Langfuse (optional)
export LANGFUSE_HOST="http://localhost:3000"
export LANGFUSE_PUBLIC_KEY="pk-lf-your-key" 
export LANGFUSE_SECRET_KEY="sk-lf-your-key"

# Upload test suites as datasets
python -m agent-test.cli dataset upload my_suite --name="Production Test Suite"

# All test runs automatically create traces in Langfuse
python -m agent-test.cli run my_suite  # Creates traces automatically

# List datasets in Langfuse
python -m agent-test.cli dataset list
```

### Advanced Usage

#### Multiple Agent Testing
```bash
# Test with both agents
python -m agent-test.cli suite create comprehensive_test --agent=both

# Run specific agent override
python -m agent-test.cli run my_suite --agent=gapanalyzer
```

#### Batch Operations
```bash
# Run all suites
python -m agent-test.cli run-all

# Filter by agent type
python -m agent-test.cli run-all --agent-filter=orchestrator
```

#### Results Analysis
```bash
# View run details
python -m agent-test.cli results show <run_id>

# Filter results
python -m agent-test.cli results list --suite=my_suite --limit=10

# Export to CSV
python -c "
from agent_test.core.results_manager import ResultsManager
manager = ResultsManager()
runs = manager.list_runs(limit=5)
manager.export_results([r['run_id'] for r in runs], format='csv')
"
```

#### Performance Monitoring
```bash
# Generate suite summary
python -c "
from agent_test.core.results_manager import ResultsManager
manager = ResultsManager()
summary = manager.generate_suite_summary('my_suite')
print(summary)
"

# Analyze trends
python -c "
from agent_test.core.results_manager import ResultsManager
manager = ResultsManager()
trends = manager.get_performance_trends('my_suite', days=7)
print(trends)
"
```

### Example Test Suites

The framework includes pre-built example suites:

#### Orchestrator Basic Q&A
```bash
python -m agent-test.cli suite show orchestrator_basic_qa
python -m agent-test.cli run orchestrator_basic_qa
```

#### GapAnalyzer Practice Analysis
```bash  
python -m agent-test.cli suite show gapanalyzer_practice_analysis
python -m agent-test.cli run gapanalyzer_practice_analysis
```

### Configuration

Framework behavior can be customized via `agent-test/config/config.yaml`:

```yaml
# Timeouts and performance
agents:
  orchestrator:
    timeout_seconds: 120
  gapanalyzer:
    timeout_seconds: 180

# Langfuse integration
langfuse:
  enabled: true
  auto_upload_datasets: true
  auto_create_traces: true

# Metrics collection
metrics:
  collect_agent_metadata: true
  collect_performance_metrics: true
  collect_response_quality: true
```

### Development and Extension

#### Adding Custom Metrics
1. Update schemas in `agent-test/schemas.py`
2. Implement collection logic in `metrics_collector.py`
3. Add detection patterns for new metric types

#### Supporting New Agent Types
1. Add to `AgentType` enum in schemas
2. Implement execution logic in `test_runner.py`
3. Create agent-specific metrics collection

For complete documentation, see `agent-test/README.md`.

## Guardrails System

LUCA includes a comprehensive **hybrid guardrails system** designed to ensure safe, appropriate, and educationally valuable interactions between students and AI agents.

### 🛡️ **Architecture Overview**

The guardrails system implements a **hybrid architecture** combining centralized validation with distributed agent-specific protections:

```
Student Input → Centralized Guardrail Layer → Agent Processing → Response Validation → Student
                ├─ Content Safety
                ├─ Educational Context  
                ├─ Rate Limiting
                └─ Profanity Filtering
```

### **Key Features**

- **Content Safety**: OpenAI Moderation API integration + Spanish profanity filtering contextual to Argentina/UCA
- **Educational Context Validation**: Ensures academic relevance and curriculum alignment
- **Rate Limiting**: Intelligent usage controls with escalating penalties
- **Response Quality Validation**: Post-processing checks for educational value
- **Complete Langfuse Integration**: Comprehensive observability and monitoring
- **Transparent Integration**: Seamless operation with existing agent infrastructure

### **Quick Start**

```bash
# Test the complete guardrails system
python test_guardrails_demo.py

# Enable guardrails in Orchestrator (enabled by default)
from orchestrator.agent_executor import OrchestratorAgentExecutor
executor = OrchestratorAgentExecutor(enable_guardrails=True)
```

### **System Components**

#### **1. Centralized Guardrail Layer**
**File**: `guardrails/core.py`

```python
from guardrails import EducationalGuardrailLayer, GuardrailConfig, EducationalContext

# Initialize with configuration
config = GuardrailConfig(
    enable_openai_moderation=True,
    enable_profanity_filter=True,
    enable_educational_validation=True,
    enable_rate_limiting=True
)

guardrail = EducationalGuardrailLayer(config)

# Validate student input
context = EducationalContext(
    student_id="student_123",
    session_id="session_456",
    subject="Bases de Datos"
)

result = await guardrail.validate_input(user_message, context)
```

#### **2. Content Safety Guardrail**
**File**: `guardrails/content_safety.py`

- **OpenAI Moderation API**: Detects inappropriate content, harassment, violence
- **Spanish Profanity Filter**: Context-aware detection for Argentine educational environment
- **Academic Integrity**: Identifies attempts to bypass learning (e.g., "haceme la tarea")
- **Manipulation Detection**: Prevents prompt injection and instruction bypassing

#### **3. Educational Context Guardrail** 
**File**: `guardrails/educational_context.py`

- **Curriculum Alignment**: Validates relevance to engineering and computer science domains
- **Academic Keywords**: Detects programming, databases, algorithms, mathematics terminology
- **LLM Assessment**: Uses GPT-4 for ambiguous content evaluation
- **Flexible vs Strict Modes**: Configurable academic strictness levels

#### **4. Rate Limiting Guardrail**
**File**: `guardrails/rate_limiting.py`

- **Multi-tier Limits**: 30/minute, 200/hour, 1000/day (configurable)
- **Escalating Penalties**: Progressive restrictions for abuse
- **Student-specific Tracking**: Individual usage monitoring
- **Graceful Degradation**: Continues operation if rate limiting fails

#### **5. Response Validation**
**File**: `guardrails/agent_response_validation.py`

- **Educational Quality Assessment**: Validates pedagogical value of agent responses
- **Content Appropriateness**: Ensures responses maintain professional educational tone
- **Completeness Checks**: Verifies responses adequately address student questions

### **Configuration Management**

#### **Environment Variables**
```bash
# Content Safety
export GUARDRAILS_ENABLE_OPENAI_MODERATION=true
export GUARDRAILS_ENABLE_PROFANITY_FILTER=true
export GUARDRAILS_CONTENT_SAFETY_THRESHOLD=0.7

# Educational Context
export GUARDRAILS_ENABLE_EDUCATIONAL_VALIDATION=true
export GUARDRAILS_STRICT_ACADEMIC_MODE=false
export GUARDRAILS_ALLOW_GENERAL_KNOWLEDGE=true

# Rate Limiting
export GUARDRAILS_ENABLE_RATE_LIMITING=true
export GUARDRAILS_MAX_REQUESTS_PER_MINUTE=30
export GUARDRAILS_MAX_REQUESTS_PER_HOUR=200

# Observability
export GUARDRAILS_ENABLE_LANGFUSE_LOGGING=true
export GUARDRAILS_LOG_ALL_INTERACTIONS=true
```

#### **Predefined Configurations**
```python
from guardrails.config import (
    get_development_config,    # Permissive for development
    get_production_config,     # Strict for production
    get_testing_config,        # Minimal for tests
    create_config_for_environment  # Auto-detect environment
)

# Auto-configuration based on environment
config = create_config_for_environment()
```

### **Integration with Agents**

#### **Automatic Orchestrator Integration**
The guardrails system integrates automatically with the Orchestrator agent:

```python
# Guardrails enabled by default in OrchestratorAgentExecutor
executor = OrchestratorAgentExecutor(enable_guardrails=True)

# Check guardrail status
status = executor.get_guardrail_status("student_123")
print(f"Guardrails active: {status['guardrails_enabled']}")
```

#### **Streaming Integration**
All streaming responses are automatically validated:

```python
# Transparent guardrail validation during streaming
async for chunk in executor.stream(request, context):
    if chunk.get('guardrail_blocked'):
        print("Request blocked by guardrails")
    yield chunk
```

### **Observability and Monitoring**

#### **Langfuse Integration**
All guardrail validations are automatically traced in Langfuse:

- **Violation Tracking**: Content safety, educational context, rate limiting violations
- **Performance Metrics**: Validation timing, success rates, error rates
- **Student Behavior Analysis**: Usage patterns, violation frequencies
- **Quality Assessment**: Educational value scores, response quality metrics

#### **Available Metrics**
- **Block Rate**: Percentage of requests blocked vs total
- **Violation Types**: Distribution of safety, educational, and rate limit violations
- **Student Usage Patterns**: Peak hours, request frequencies, subject preferences
- **Educational Quality Scores**: Relevance and pedagogical value assessments

### **Testing and Validation**

#### **Complete Demo**
```bash
# Run comprehensive guardrails demonstration
python test_guardrails_demo.py
```

**Demo includes**:
- Content safety validation with various input types
- Educational context assessment with academic and non-academic queries
- Rate limiting demonstration with escalating restrictions
- Orchestrator integration verification
- Langfuse observability confirmation

#### **Unit Testing**
```python
import pytest
from guardrails import EducationalGuardrailLayer, EducationalContext
from guardrails.config import get_testing_config

@pytest.fixture
def guardrail_system():
    return EducationalGuardrailLayer(get_testing_config())

@pytest.mark.asyncio
async def test_appropriate_academic_content(guardrail_system, edu_context):
    result = await guardrail_system.validate_input(
        "¿Cómo funciona un algoritmo de ordenamiento?", 
        edu_context
    )
    assert result.passed
    assert not result.violations
```

### **Error Handling and Fallbacks**

The system implements **graceful degradation**:

- **OpenAI API Failures**: Falls back to local profanity filters
- **Langfuse Unavailable**: Continues validation without logging
- **Rate Limiting Errors**: Temporarily disables limits
- **Educational Assessment Failures**: Uses keyword-based fallback

### **Security Considerations**

- **API Key Management**: Secure handling of OpenAI and Langfuse credentials
- **Data Privacy**: Student interactions logged only with appropriate consent
- **Bypass Prevention**: Multiple validation layers prevent circumvention
- **Audit Trail**: Complete logging of all guardrail decisions for accountability

### **Performance Impact**

The guardrails system is designed for minimal latency impact:

- **Parallel Validation**: Multiple guardrails run concurrently
- **Efficient Caching**: Rate limiting and profanity filters use in-memory caches
- **Async Processing**: Non-blocking validation prevents response delays
- **Configurable Strictness**: Balance between security and performance

For complete documentation, configuration options, and advanced usage patterns, see `guardrails/README.md`.

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

## Frontend Application

LUCA provides a **Flask-based web frontend** for interacting with the educational AI agents.

### 🚀 Flask Frontend

**Modern web interface** built with Flask that provides a stable, professional educational chat experience.

#### Características
- ✅ **Conversaciones multi-turno estables**: Sin colgados en seguimientos
- 🚀 **Mejor rendimiento**: Event loops aislados, sin conflictos AsyncIO  
- 🎨 **Interfaz moderna**: Bootstrap 5 con branding UCA profesional
- 🔄 **Compatible con Neo4j persistence**: Sin problemas de state sharing
- 📱 **Responsive design**: Funciona en dispositivos móviles
- ⚡ **Streaming real-time**: Indicadores de progreso sin recargas

#### Quick Start
```bash
# Install Flask dependencies
pip install flask flask-cors

# Start Flask application
cd frontend
python run.py
# OR
python run_flask.py

# Access at http://localhost:5000
# Login: visitante@uca.edu.ar / visitante!

# Test components
python test_frontend.py
```

### Architecture

```
frontend/
├── flask_app.py              # Main Flask application
├── run.py                    # Primary runner script
├── run_flask.py              # Alternative runner script
├── templates/
│   ├── base.html             # Bootstrap base template
│   ├── login.html            # Authentication page
│   └── chat.html             # Main chat interface
├── auth.py                   # User authentication & conversation management
├── utils.py                  # Utilities (subjects, formatting)
├── test_frontend.py          # Test suite
├── requirements.txt          # Flask dependencies
├── README.md                 # Frontend documentation
└── assets/                   # Logos and static files
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