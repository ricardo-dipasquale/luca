# API Reference

## 📋 Overview

This document provides comprehensive API reference for all Luca system components, including agent interfaces, data schemas, tool APIs, and service endpoints.

## 🤖 Agent APIs

### GapAnalyzer Agent

The GapAnalyzer agent provides educational gap analysis capabilities through both streaming and non-streaming interfaces.

#### Agent Interface

```python
class GapAnalyzerAgent:
    """Educational Gap Analyzer Agent"""
    
    async def stream(
        self, 
        query: str | StudentContext, 
        context_id: str
    ) -> AsyncIterable[Dict[str, Any]]:
        """
        Stream gap analysis process with real-time progress updates.
        
        Args:
            query: Student question (plain text) or structured StudentContext
            context_id: Conversation context ID for continuity
            
        Yields:
            Progress updates and final analysis result
            
        Example:
            async for chunk in agent.stream(context, "session_123"):
                if chunk['is_task_complete']:
                    final_result = chunk
                else:
                    print(f"Progress: {chunk['content']}")
        """
```

#### A2A Protocol Integration

```python
class GapAnalyzerAgentExecutor(AgentExecutor):
    """A2A Framework integration for GapAnalyzer"""
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute gap analysis within A2A framework.
        
        Handles:
        - Input validation and parsing
        - Streaming response coordination
        - Task state management
        - Error handling and recovery
        """
```

#### Input Formats

**Plain Text Input:**
```python
query = "No entiendo por qué mi consulta SQL con LEFT JOIN no funciona"
```

**Structured Input (JSON):**
```json
{
    "student_question": "No entiendo por qué mi consulta SQL con LEFT JOIN no funciona",
    "conversation_history": [
        "Estoy trabajando en el ejercicio 1.d",
        "Mi consulta devuelve filas duplicadas"
    ],
    "subject_name": "Bases de Datos Relacionales",
    "practice_context": "Práctica: 2 - Algebra Relacional...",
    "exercise_context": "Ejercicio: 1.d - Nombre de los clientes...",
    "solution_context": "Solución esperada: [π_{Nombre}...]",
    "tips_context": "Tips nivel práctica..."
}
```

**Direct StudentContext Object:**
```python
from gapanalyzer.schemas import StudentContext

context = StudentContext(
    student_question="¿Cómo funciona un LEFT JOIN?",
    subject_name="Bases de Datos Relacionales",
    practice_context="...",
    exercise_context="...",
    solution_context="...",
    tips_context="..."
)
```

#### Response Format

**Streaming Responses:**
```python
# Progress update
{
    'is_task_complete': False,
    'require_user_input': False,
    'content': 'Analizando pregunta y extrayendo contexto...'
}

# Final response
{
    'is_task_complete': True,
    'require_user_input': False,
    'content': '**ANÁLISIS DE GAPS EDUCATIVOS**\n...',
    'structured_response': GapAnalysisResponse(...)
}
```

## 📊 Data Schemas

### Core Data Models

All data models use Pydantic for validation and serialization.

#### StudentContext

```python
class StudentContext(BaseModel):
    """Complete context about student's question and educational setting"""
    
    student_question: str = Field(
        description="The student's original question or concern"
    )
    conversation_history: List[str] = Field(
        default=[],
        description="Previous messages in conversation for context"
    )
    subject_name: str = Field(
        description="Name of the subject/course"
    )
    practice_context: str = Field(
        description="Complete practice context including objectives"
    )
    exercise_context: str = Field(
        description="Specific exercise statement and requirements"
    )
    solution_context: Optional[str] = Field(
        default=None,
        description="Expected solution or answer to the exercise"
    )
    tips_context: Optional[str] = Field(
        default=None,
        description="Tips and hints provided by the teacher"
    )
```

#### IdentifiedGap

```python
class IdentifiedGap(BaseModel):
    """A single identified learning gap"""
    
    gap_id: str = Field(description="Unique identifier for this gap")
    title: str = Field(description="Brief title describing the gap")
    description: str = Field(description="Detailed description of the gap")
    category: GapCategory = Field(description="Category of the gap")
    severity: GapSeverity = Field(description="Severity level of the gap")
    evidence: str = Field(description="Evidence from student's question")
    affected_concepts: List[str] = Field(description="Specific concepts affected")
    prerequisite_knowledge: List[str] = Field(
        default=[],
        description="Prerequisites the student might be missing"
    )
```

#### GapEvaluation

```python
class GapEvaluation(BaseModel):
    """Evaluation of a gap's relevance and importance"""
    
    gap_id: str = Field(description="Reference to the gap being evaluated")
    pedagogical_relevance: float = Field(
        ge=0.0, le=1.0,
        description="Relevance to current learning objectives (0-1)"
    )
    impact_on_learning: float = Field(
        ge=0.0, le=1.0,
        description="Impact on overall learning progress (0-1)"
    )
    addressability: float = Field(
        ge=0.0, le=1.0,
        description="How easily this gap can be addressed (0-1)"
    )
    priority_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall priority score calculated from factors"
    )
    evaluation_reasoning: str = Field(description="Explanation of evaluation")
```

#### PrioritizedGap

```python
class PrioritizedGap(BaseModel):
    """A gap with its evaluation and priority ranking"""
    
    gap: IdentifiedGap = Field(description="The identified gap")
    evaluation: GapEvaluation = Field(description="Evaluation of the gap")
    rank: int = Field(description="Priority ranking (1 = highest priority)")
    recommended_actions: List[str] = Field(
        default=[],
        description="Specific actions to address this gap"
    )
```

#### GapAnalysisResult

```python
class GapAnalysisResult(BaseModel):
    """Complete result of the gap analysis workflow"""
    
    student_context: StudentContext = Field(description="Original student context")
    educational_context: EducationalContext = Field(description="Retrieved context")
    identified_gaps: List[IdentifiedGap] = Field(description="All identified gaps")
    prioritized_gaps: List[PrioritizedGap] = Field(
        description="Gaps ordered by priority (highest first)"
    )
    summary: str = Field(description="Executive summary of the analysis")
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in the analysis quality (0-1)"
    )
    recommendations: List[str] = Field(description="General recommendations")
```

### Enumerations

#### GapCategory

```python
class GapCategory(str, Enum):
    """Categories of learning gaps"""
    CONCEPTUAL = "conceptual"        # Misunderstanding of concepts
    PROCEDURAL = "procedural"        # Issues with procedures/methods
    THEORETICAL = "theoretical"      # Gap in theoretical understanding
    PRACTICAL = "practical"          # Difficulty applying knowledge
    PREREQUISITE = "prerequisite"    # Missing prerequisite knowledge
    COMMUNICATION = "communication"  # Issues expressing understanding
```

#### GapSeverity

```python
class GapSeverity(str, Enum):
    """Severity levels for identified learning gaps"""
    CRITICAL = "critical"   # Fundamental misunderstanding, blocks progress
    HIGH = "high"          # Significant gap affecting comprehension
    MEDIUM = "medium"      # Moderate gap, may cause confusion
    LOW = "low"            # Minor gap, easily addressable
```

## 🛠️ Tools API

### Knowledge Graph Tools

#### search_knowledge_graph

```python
@tool
def search_knowledge_graph(
    query: str,
    limit: int = 10,
    search_type: str = "semantic"
) -> str:
    """
    Search the knowledge graph for relevant educational content.
    
    Args:
        query: Search query (natural language)
        limit: Maximum number of results to return
        search_type: "semantic" for vector search, "keyword" for text search
        
    Returns:
        JSON string with search results including nodes and relationships
        
    Example:
        results = search_knowledge_graph(
            "bases de datos normalización",
            limit=5,
            search_type="semantic"
        )
    """
```

#### get_subjects

```python
@tool
def get_subjects(career_filter: str = None) -> str:
    """
    Get all subjects/courses from the knowledge graph.
    
    Args:
        career_filter: Optional filter by career name
        
    Returns:
        JSON string with subjects information including:
        - Subject name and code
        - Associated career(s)
        - Professor information
        - Learning objectives
        
    Example:
        subjects = get_subjects("Ingeniería en Sistemas")
    """
```

#### get_practice_exercises

```python
@tool
def get_practice_exercises(
    subject_name: str,
    topic_filter: str = None,
    difficulty_level: str = None
) -> str:
    """
    Get practice exercises for a specific subject.
    
    Args:
        subject_name: Name of the subject
        topic_filter: Optional filter by topic
        difficulty_level: Optional filter by difficulty
        
    Returns:
        JSON string with exercises including:
        - Exercise statements and requirements
        - Expected solutions
        - Related tips and hints
        - Difficulty level and topic associations
    """
```

#### get_theoretical_content

```python
@tool
def get_theoretical_content(
    topic_description: str,
    detail_level: str = "medium"
) -> str:
    """
    Get theoretical content for a topic using LLM Graph Builder API.
    
    Args:
        topic_description: Description of the topic
        detail_level: "basic", "medium", or "advanced"
        
    Returns:
        Detailed theoretical explanation of the topic
        
    Example:
        content = get_theoretical_content(
            "LEFT JOIN en bases de datos relacionales",
            detail_level="medium"
        )
    """
```

### Utility Tools

#### process_text

```python
@tool
def process_text(
    text: str,
    operations: List[str]
) -> Dict[str, Any]:
    """
    Process text with specified operations.
    
    Args:
        text: Input text to process
        operations: List of operations to perform
        
    Available operations:
        - "clean": Remove extra whitespace and normalize
        - "count_words": Count words in text
        - "count_characters": Count characters
        - "extract_keywords": Extract key terms
        - "summarize": Create brief summary
        
    Returns:
        Dictionary with operation results
    """
```

#### validate_input

```python
@tool
def validate_input(
    input_value: str,
    validation_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Validate input according to specified type.
    
    Args:
        input_value: Value to validate
        validation_type: Type of validation to perform
        **kwargs: Additional validation parameters
        
    Validation types:
        - "email": Email address validation
        - "url": URL validation
        - "number": Numeric validation
        - "date": Date format validation
        - "text_length": Text length validation
        
    Returns:
        Validation result with is_valid flag and details
    """
```

#### calculate

```python
@tool
def calculate(expression: str) -> Dict[str, Any]:
    """
    Perform safe mathematical calculations.
    
    Args:
        expression: Mathematical expression as string
        
    Supported operations:
        - Basic arithmetic (+, -, *, /, %, **)
        - Math functions (sin, cos, tan, log, sqrt, etc.)
        - Constants (pi, e)
        
    Returns:
        Calculation result or error information
        
    Example:
        result = calculate("sqrt(25) + log(100)")
    """
```

## 🔗 Knowledge Graph API

### Connection Interface

```python
class KGConnection:
    """Neo4j connection management with automatic reconnection"""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize connection using environment variables or parameters"""
        
    def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query with parameters"""
        
    def execute_write_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None
    ) -> None:
        """Execute write query (CREATE, UPDATE, DELETE)"""
        
    def close(self) -> None:
        """Close database connection"""
```

### Query Interface

```python
class KGQueryInterface:
    """High-level functional interface for common KG operations"""
    
    def search_by_text(
        self,
        search_text: str,
        node_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Text-based search across specified node types"""
        
    def search_by_vector(
        self,
        query_vector: List[float],
        node_types: List[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Vector similarity search using embeddings"""
        
    def get_node_relationships(
        self,
        node_id: str,
        relationship_types: List[str] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Get relationships for a specific node"""
        
    def get_learning_path(
        self,
        start_topic: str,
        end_topic: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Find learning path between topics"""
```

## ⚙️ Configuration API

### LLM Configuration

```python
def create_default_llm(**overrides) -> BaseLLM:
    """
    Create LLM using environment configuration with optional overrides.
    
    Environment Variables:
        DEFAULT_LLM_MODEL: Model name (default: "gpt-4o-mini")
        DEFAULT_LLM_PROVIDER: Provider (default: "openai")
        DEFAULT_LLM_TEMPERATURE: Temperature (default: "0.1")
        DEFAULT_LLM_MAX_TOKENS: Max tokens (default: "4096")
        
    Args:
        **overrides: Override any default configuration
        
    Returns:
        Configured LLM instance
    """

def create_observed_llm(**overrides) -> BaseLLM:
    """
    Create LLM with Langfuse observability integration.
    
    Automatically adds Langfuse callbacks for:
    - Request/response tracing
    - Token usage tracking
    - Error monitoring
    - Performance metrics
    """

def get_model_info() -> Dict[str, str]:
    """
    Get current LLM configuration information.
    
    Returns:
        Dictionary with provider, model, and configuration details
    """
```

### Tool Registry API

```python
class ToolRegistry:
    """Central registry for tool discovery and management"""
    
    def get_tools_for_agent(self, agent_type: str) -> List[Tool]:
        """
        Get tools configured for specific agent type.
        
        Agent types:
            - "gapanalyzer": Gap analysis tools
            - "tutor": Tutoring and explanation tools
            - "practice_helper": Exercise assistance tools
            - "recommendation": Recommendation generation tools
        """
        
    def register_tool(
        self,
        tool: Tool,
        categories: List[str],
        agents: List[str]
    ) -> None:
        """Register a new tool with categories and agent assignments"""
        
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """
        Get tools by category.
        
        Categories:
            - "knowledge_graph": KG interaction tools
            - "utility": General utility tools
            - "analysis": Analysis and processing tools
            - "validation": Input validation tools
        """
```

## 🔍 Observability API

### Langfuse Integration

```python
def observe_openai_call(
    client: OpenAI,
    messages: List[Dict[str, str]],
    model: str,
    operation_name: str = None,
    metadata: Dict[str, Any] = None,
    **kwargs
) -> Any:
    """
    Make observed OpenAI API call with automatic tracing.
    
    Args:
        client: OpenAI client instance
        messages: Chat messages
        model: Model name
        operation_name: Custom operation name for tracing
        metadata: Additional metadata for the trace
        **kwargs: Additional OpenAI API parameters
        
    Returns:
        OpenAI API response
    """

class LangfuseCallbackHandler:
    """LangChain callback handler for Langfuse integration"""
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts processing"""
        
    def on_llm_end(self, response, **kwargs):
        """Called when LLM finishes processing"""
        
    def on_llm_error(self, error, **kwargs):
        """Called when LLM encounters an error"""
```

## 🚦 Error Handling

### Standard Error Responses

```python
class LucaError(Exception):
    """Base exception for Luca system errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}

class ValidationError(LucaError):
    """Raised when input validation fails"""
    pass

class KnowledgeGraphError(LucaError):
    """Raised when KG operations fail"""
    pass

class AgentExecutionError(LucaError):
    """Raised when agent execution fails"""
    pass

class LLMError(LucaError):
    """Raised when LLM operations fail"""
    pass
```

### Error Response Format

```json
{
    "error": {
        "type": "ValidationError",
        "message": "Invalid student context provided",
        "code": "INVALID_INPUT",
        "details": {
            "field": "student_question",
            "reason": "Field is required but was empty"
        },
        "timestamp": "2024-01-20T10:30:00Z",
        "request_id": "req_123456789"
    }
}
```

## 📝 Usage Examples

### Complete Gap Analysis Flow

```python
import asyncio
from gapanalyzer import GapAnalyzerAgent
from gapanalyzer.schemas import StudentContext

async def analyze_student_gap():
    # Initialize agent
    agent = GapAnalyzerAgent()
    
    # Create context
    context = StudentContext(
        student_question="No entiendo la diferencia entre INNER JOIN y LEFT JOIN",
        subject_name="Bases de Datos Relacionales",
        practice_context="Práctica 2: Operaciones de JOIN en SQL",
        exercise_context="Ejercicio 3: Consultas con múltiples tablas",
        solution_context="SELECT * FROM clientes c LEFT JOIN ventas v ON c.id = v.cliente_id",
        tips_context="Recordar que LEFT JOIN incluye todos los registros de la tabla izquierda"
    )
    
    # Stream analysis
    async for chunk in agent.stream(context, "session_001"):
        if chunk['is_task_complete']:
            # Process final result
            result = chunk['structured_response']
            print(f"Found {result.gaps_found} gaps")
            print(f"Confidence: {result.detailed_analysis.confidence_score:.1%}")
            break
        else:
            print(f"Progress: {chunk['content']}")

# Run the analysis
asyncio.run(analyze_student_gap())
```

### Using Knowledge Graph Tools

```python
from tools import get_kg_tools

# Get KG tools
kg_tools = get_kg_tools()

# Find specific tool
search_tool = next(tool for tool in kg_tools if tool.name == "search_knowledge_graph")

# Use the tool
results = search_tool.invoke({
    "query": "normalización bases de datos",
    "limit": 5,
    "search_type": "semantic"
})

print(results)
```

### Custom Tool Development

```python
from langchain.tools import tool
from tools.registry import ToolRegistry

@tool
def custom_analysis_tool(input_text: str) -> str:
    """Custom analysis tool for specific domain logic"""
    # Implement custom logic
    return f"Analysis result for: {input_text}"

# Register the tool
registry = ToolRegistry()
registry.register_tool(
    tool=custom_analysis_tool,
    categories=["analysis", "custom"],
    agents=["gapanalyzer", "tutor"]
)
```

This API reference provides comprehensive coverage of all system interfaces and should be used in conjunction with the example code and integration guides.