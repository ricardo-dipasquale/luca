# Luca System Architecture

## 🏗️ Overview

Luca implements a layered, modular architecture designed for scalability, maintainability, and extensibility. The system follows Domain-Driven Design principles with clear separation of concerns across multiple layers.

## 📊 High-Level Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        FLASK[Flask Web Interface]
        UI[Student Chat Interface]
        API[A2A API Gateway]
    end
    
    subgraph "Agent Layer"
        ORCH[Orchestrator Agent]
        GA[GapAnalyzer Agent]
    end
    
    subgraph "Testing Layer"  
        ATF[Agent Testing Framework]
        SUITES[Test Suites]
        METRICS[Automated Metrics]
    end
    
    subgraph "Business Logic Layer"
        WF[Workflow Engine<br/>LangGraph]
        EXEC[Agent Executors<br/>A2A Framework]
        VAL[Validation Layer<br/>Pydantic]
    end
    
    subgraph "Tools & Services Layer"
        KGT[Knowledge Graph Tools]
        UT[Utility Tools]
        REG[Tool Registry]
        LLM[LLM Services]
    end
    
    subgraph "Data Layer"
        KG[(Neo4j<br/>Knowledge Graph)]
        EMB[Vector Embeddings<br/>OpenAI]
        CACHE[Redis Cache]
    end
    
    subgraph "Observability Layer"
        LF[Langfuse<br/>LLM Observability]
        METRICS[Metrics & Traces]
        LOGS[Structured Logging]
    end
    
    subgraph "Infrastructure Layer"
        DOCKER[Docker Containers]
        COMPOSE[Docker Compose]
        ENV[Environment Config]
    end
    
    UI --> API
    API --> GA
    API --> TA
    API --> PA
    API --> RA
    
    GA --> WF
    TA --> WF
    PA --> WF
    RA --> WF
    
    WF --> EXEC
    EXEC --> VAL
    
    GA --> KGT
    GA --> UT
    KGT --> KG
    KGT --> EMB
    UT --> LLM
    
    REG --> KGT
    REG --> UT
    
    GA --> LF
    TA --> LF
    PA --> LF
    RA --> LF
    
    LF --> METRICS
    METRICS --> LOGS
    
    KG --> DOCKER
    LF --> DOCKER
    DOCKER --> COMPOSE
    COMPOSE --> ENV
    
    class UI,API,WEB presentation
    class GA,TA,PA,RA agent
    class WF,EXEC,VAL business
    class KGT,UT,REG,LLM tools
    class KG,EMB,CACHE data
    class LF,METRICS,LOGS observability
    class DOCKER,COMPOSE,ENV infrastructure
```

## 🎯 Core Design Principles

### 1. **Modularity & Separation of Concerns**
- Each layer has a single, well-defined responsibility
- Clear interfaces between layers prevent tight coupling
- Components can be developed, tested, and deployed independently

### 2. **Scalability & Performance**
- Horizontal scaling through containerization
- Caching strategies at multiple levels
- Async processing with streaming capabilities
- Vector search for fast semantic retrieval

### 3. **Observability & Monitoring**
- Comprehensive tracing of all LLM interactions
- Structured logging throughout the system
- Performance metrics and alerting
- Cost tracking and optimization

### 4. **Extensibility & Plugin Architecture**
- Tool registry pattern for easy tool addition
- Agent-agnostic workflow components
- Plugin-based LLM provider support
- Configurable deployment options

## 🔍 Detailed Layer Architecture

### 1. Presentation Layer

**Responsibilities**: User interaction, API exposure, request routing

#### Components:
- **Flask Web Interface**: Modern web application with conversation management
- **Student Chat Interface**: Real-time chat interface with streaming responses
- **A2A API Gateway**: Agent-to-Agent protocol implementation for agent communication

#### Key Features:
- Session-based authentication with UCA domain validation
- Real-time streaming chat responses
- Conversation persistence and management
- Mathematical symbols panel for educational queries
- Educational subject context injection

### 2. Agent Layer

**Responsibilities**: Educational AI logic, conversation orchestration, gap analysis

#### Current Agents:

**Orchestrator Agent**:
- Main conversation manager and coordinator
- Intent classification for routing decisions
- Multi-turn conversation memory management
- Educational subject context handling
- Seamless integration with GapAnalyzer for specific queries

**GapAnalyzer Agent**:
- Specialized educational gap analysis
- Practice exercise context understanding
- Learning gap identification and evaluation
- Pedagogical response generation

#### Agent Architecture Pattern:
All agents follow the A2A framework pattern:
1. **Agent Class**: Core business logic with streaming support
2. **Agent Executor**: A2A protocol integration
3. **Schemas**: Pydantic data models for validation
4. **Local Runner**: Development and debugging interface

### 3. Testing Layer

**Responsibilities**: Agent evaluation, performance monitoring, quality assurance

#### Components:
- **Agent Testing Framework**: Comprehensive CLI-based testing system
- **Test Suites**: JSON-based test case management
- **Automated Metrics**: Performance and quality metrics collection
- **Langfuse Integration**: Dataset management and trace analysis

#### Key Features:
- Automated agent evaluation with configurable test suites
- Multi-agent testing capabilities (Orchestrator, GapAnalyzer, both)
- Real-time metrics collection from agent schemas
- Langfuse dataset upload and trace management
- Performance trend analysis and reporting

#### Agent Architecture Pattern:
All agents follow a consistent pattern:

```python
class Agent:
    """Base agent pattern"""
    def __init__(self):
        self.llm = create_observed_llm()
        self.tools = self._load_tools()
        self.workflow = self._create_workflow()
    
    async def stream(self, input_data, context_id):
        """Streaming response interface"""
        pass
    
    def _create_workflow(self):
        """LangGraph workflow creation"""
        pass
```

#### Specialized Agents:

**GapAnalyzer Agent** (`gapanalyzer/`):
- Educational gap identification and analysis
- Multi-iteration feedback loops for quality improvement
- Pedagogical evaluation and prioritization
- Structured output with confidence scoring

**Tutor Agent** (planned):
- Interactive tutoring and explanation
- Adaptive questioning and hints
- Learning path recommendation
- Progress tracking and assessment

**Practice Assistant** (planned):
- Exercise-specific help and guidance
- Step-by-step problem solving
- Solution validation and feedback
- Alternative approach suggestions

### 3. Business Logic Layer

**Responsibilities**: Workflow orchestration, validation, business rules

#### Workflow Engine (LangGraph):
```python
workflow = StateGraph(WorkflowState)

# Add nodes
workflow.add_node("validate_context", validate_context_node)
workflow.add_node("analyze_gaps", analyze_gaps_node)
workflow.add_node("evaluate_gaps", evaluate_gaps_node)
workflow.add_node("prioritize_gaps", prioritize_gaps_node)

# Add conditional edges
workflow.add_conditional_edges(
    "prioritize_gaps",
    should_do_feedback,
    {
        "feedback": "feedback_analysis",
        "complete": "generate_response"
    }
)
```

#### Agent Executors (A2A Framework):
- Protocol compliance and message handling
- Task state management
- Streaming response coordination
- Error handling and recovery

#### Validation Layer (Pydantic):
```python
class StudentContext(BaseModel):
    student_question: str
    conversation_history: List[str] = []
    subject_name: str
    practice_context: str
    exercise_context: str
    solution_context: Optional[str] = None
    tips_context: Optional[str] = None
```

### 4. Tools & Services Layer

**Responsibilities**: Reusable business logic, external service integration

#### Tool Categories:

**Knowledge Graph Tools** (`tools/kg_tools.py`):
```python
@tool
def search_knowledge_graph(query: str, limit: int = 10):
    """Search the knowledge graph semantically"""
    pass

@tool  
def get_practice_exercises(subject: str, topic: str):
    """Get practice exercises for a topic"""
    pass

@tool
def get_theoretical_content(topic: str):
    """Get theoretical content via LLM Graph Builder"""
    pass
```

**Utility Tools** (`tools/utility_tools.py`):
```python
@tool
def process_text(text: str, operations: List[str]):
    """Process text with specified operations"""
    pass

@tool
def validate_input(input_value: str, validation_type: str):
    """Validate input according to type"""
    pass
```

#### Tool Registry Pattern:
```python
class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._agent_tool_mapping = {}
    
    def get_tools_for_agent(self, agent_type: str):
        """Get tools specific to agent type"""
        pass
    
    def register_tool(self, tool, categories, agents):
        """Register a new tool"""
        pass
```

#### LLM Configuration:
```python
def create_observed_llm(
    model: str = None,
    temperature: float = None,
    max_tokens: int = None
) -> BaseLLM:
    """Create LLM with observability integration"""
    # Load from environment variables
    # Add Langfuse callbacks
    # Return configured LLM
    pass
```

### 5. Data Layer

**Responsibilities**: Data persistence, retrieval, and caching

#### Neo4j Knowledge Graph:
- **Nodes**: Subjects, Topics, Exercises, Tips, Professors
- **Relationships**: hierarchical and associative connections
- **Properties**: Metadata, content, and vector embeddings
- **Indexes**: Optimized for common query patterns

#### Vector Embeddings (OpenAI):
- Text-embedding-ada-002 model for semantic search
- Cached embeddings for performance
- Similarity search capabilities
- Multi-language support preparation

#### Caching Strategy:
- **L1 Cache**: In-memory caching within agents
- **L2 Cache**: Redis for shared caching across agents
- **L3 Cache**: Database query result caching

### 6. Observability Layer

**Responsibilities**: Monitoring, logging, and performance tracking

#### Langfuse Integration:
```python
def create_observed_llm():
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # Add Langfuse callback
    langfuse_handler = LangfuseCallbackHandler()
    llm.callbacks = [langfuse_handler]
    
    return llm
```

#### Metrics & Monitoring:
- **LLM Metrics**: Token usage, response times, costs
- **Agent Metrics**: Success rates, error rates, user satisfaction
- **System Metrics**: Resource usage, database performance
- **Business Metrics**: User engagement, learning outcomes

#### Structured Logging:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "gap_analysis_completed",
    agent="gapanalyzer",
    gaps_found=3,
    confidence_score=0.85,
    processing_time_ms=1250
)
```

### 7. Infrastructure Layer

**Responsibilities**: Deployment, scaling, and environment management

#### Docker Containerization:
```dockerfile
FROM registry.access.redhat.com/ubi8/python-312:1-77

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . /app
WORKDIR /app

# Run as non-root user
USER 1001

EXPOSE 10000
CMD ["python", "-m", "gapanalyzer"]
```

#### Docker Compose Services:
```yaml
services:
  neo4j:
    image: neo4j:5.26.1
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4JLABS_PLUGINS=["apoc","graph-data-science"]
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - ./data:/data
      - ./plugins:/plugins

  langfuse:
    image: langfuse/langfuse:2
    environment:
      - DATABASE_URL=postgresql://langfuse:password@postgres:5432/langfuse
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - redis
```

## 🔄 Data Flow & Communication Patterns

### 1. Request Processing Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as A2A Gateway
    participant GA as GapAnalyzer
    participant WF as Workflow
    participant KG as Knowledge Graph
    participant LLM as LLM Service
    participant LF as Langfuse
    
    C->>A: Student Question + Context
    A->>GA: Parse & Validate Request
    GA->>WF: Initialize Workflow State
    
    WF->>KG: Retrieve Educational Context
    KG-->>WF: Context Data
    
    WF->>LLM: Analyze Gaps (via observed LLM)
    LLM->>LF: Log Interaction
    LLM-->>WF: Identified Gaps
    
    WF->>LLM: Evaluate Gaps
    LLM->>LF: Log Interaction  
    LLM-->>WF: Gap Evaluations
    
    WF->>GA: Prioritized Gaps
    GA->>A: Streaming Response
    A->>C: Formatted Response
```

### 2. Tool Integration Pattern

```mermaid
graph LR
    subgraph "Agent Context"
        A[Agent]
        W[Workflow]
    end
    
    subgraph "Tool Layer"
        R[Tool Registry]
        KGT[KG Tools]
        UT[Utility Tools]
    end
    
    subgraph "External Services"
        KG[(Knowledge Graph)]
        LLM[LLM APIs]
        EXT[External APIs]
    end
    
    A --> R
    R --> KGT
    R --> UT
    W --> KGT
    W --> UT
    
    KGT --> KG
    UT --> LLM
    UT --> EXT
```

## 🔧 Configuration Management

### Environment-Based Configuration

```python
# tools/llm_config.py
@dataclass
class LLMConfig:
    model: str = field(default_factory=lambda: os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"))
    provider: str = field(default_factory=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "openai"))
    temperature: float = field(default_factory=lambda: float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.1")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("DEFAULT_LLM_MAX_TOKENS", "4096")))

def create_default_llm(**overrides) -> BaseLLM:
    config = LLMConfig()
    
    # Apply overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return create_openai_llm(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )
```

### Agent-Specific Configuration

```python
# tools/registry.py
AGENT_TOOL_MAPPING = {
    "gapanalyzer": [
        "search_knowledge_graph",
        "get_practice_exercises", 
        "get_theoretical_content",
        "process_text",
        "validate_input"
    ],
    "tutor": [
        "search_knowledge_graph",
        "get_subjects",
        "get_learning_path",
        "format_data"
    ],
    "practice_helper": [
        "get_practice_exercises",
        "get_practice_tips",
        "validate_input",
        "calculate"
    ]
}
```

## 🔒 Security Considerations

### 1. **Data Protection**
- Environment variables for sensitive configuration
- No hardcoded secrets in codebase
- Secure handling of student data and conversations

### 2. **API Security**
- Authentication and authorization for all endpoints
- Rate limiting to prevent abuse
- Input validation and sanitization

### 3. **Container Security**
- Non-root user execution
- Minimal container images
- Regular security updates

### 4. **Database Security**
- Encrypted connections to Neo4j
- Access control and user permissions
- Regular backup and recovery procedures

## 📈 Scalability & Performance

### 1. **Horizontal Scaling**
- Stateless agent design enables easy scaling
- Load balancing across multiple agent instances
- Database read replicas for improved performance

### 2. **Caching Strategy**
- Multi-level caching (memory, Redis, database)
- Vector embedding caching for semantic search
- LLM response caching for common queries

### 3. **Performance Optimization**
- Async processing throughout the stack
- Streaming responses for better user experience
- Efficient database query patterns
- Connection pooling and resource management

### 4. **Monitoring & Alerting**
- Real-time performance monitoring
- Automated alerting for system issues
- Capacity planning based on usage metrics
- Cost optimization through usage analysis

## 🔮 Future Architecture Considerations

### 1. **Multi-tenancy**
- Support for multiple educational institutions
- Tenant-specific configuration and customization
- Isolated data and processing

### 2. **Advanced AI Features**
- Multi-modal support (images, audio, video)
- Federated learning for privacy-preserving improvements
- Advanced personalization algorithms

### 3. **Integration Ecosystem**
- LTI (Learning Tools Interoperability) support
- LMS (Learning Management System) integrations
- Third-party educational tool connections

### 4. **Advanced Analytics**
- Learning analytics and insights
- Predictive modeling for student success
- Automated curriculum optimization

This architecture provides a solid foundation for current needs while maintaining flexibility for future enhancements and scaling requirements.