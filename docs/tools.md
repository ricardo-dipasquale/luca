# Tools Reference

## 🛠️ Overview

The Luca project provides a comprehensive suite of centralized tools built on LangChain that enable consistent and powerful agent development. These tools are organized into categories and can be easily integrated into any agent through the tool registry system.

## 📋 Tool Categories

### 🔗 Knowledge Graph Tools
- **Purpose**: Interact with the Neo4j knowledge graph
- **Use Cases**: Semantic search, content retrieval, relationship exploration
- **Location**: `tools/kg_tools.py`

### 🔧 Utility Tools  
- **Purpose**: General-purpose utilities for text processing, validation, and calculations
- **Use Cases**: Data processing, input validation, mathematical operations
- **Location**: `tools/utility_tools.py`

### 🎯 Tool Registry
- **Purpose**: Centralized tool discovery and management
- **Use Cases**: Agent-specific tool selection, tool categorization
- **Location**: `tools/registry.py`

## 🔗 Knowledge Graph Tools

### search_knowledge_graph

Search the knowledge graph using semantic or keyword-based queries.

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
        query: Search query in natural language
        limit: Maximum number of results (default: 10)
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

**Features:**
- Vector similarity search using OpenAI embeddings
- Keyword-based text search
- Configurable result limits
- Rich metadata in results

**Response Format:**
```json
{
    "results": [
        {
            "node_id": "123",
            "labels": ["Tema"],
            "properties": {
                "nombre": "Normalización de Bases de Datos",
                "descripcion": "Proceso de estructuración...",
                "embedding": [0.1, 0.2, ...]
            },
            "score": 0.95,
            "relationships": [
                {
                    "type": "PERTENECE_A",
                    "target": "Bases de Datos Relacionales"
                }
            ]
        }
    ],
    "total_found": 15,
    "search_type": "semantic"
}
```

### get_subjects

Retrieve all subjects/courses from the knowledge graph.

```python
@tool
def get_subjects(career_filter: str = None) -> str:
    """
    Get all subjects/courses from the knowledge graph.
    
    Args:
        career_filter: Optional filter by career name
        
    Returns:
        JSON string with subjects information
        
    Example:
        subjects = get_subjects("Ingeniería en Sistemas")
    """
```

**Response Format:**
```json
{
    "subjects": [
        {
            "nombre": "Bases de Datos Relacionales",
            "codigo": "BD101",
            "carrera": "Ingeniería en Sistemas",
            "profesor": "Dr. Juan Pérez",
            "objetivos": [
                "Comprender el modelo relacional",
                "Dominar SQL y álgebra relacional"
            ],
            "unidades_tematicas": [
                "Introducción a Bases de Datos",
                "Modelo Relacional",
                "Normalización"
            ]
        }
    ]
}
```

### get_practice_exercises

Retrieve practice exercises for a specific subject and topic.

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
        difficulty_level: Optional filter by difficulty ("basic", "intermediate", "advanced")
        
    Returns:
        JSON string with exercises including statements, solutions, and tips
        
    Example:
        exercises = get_practice_exercises(
            "Bases de Datos Relacionales",
            topic_filter="JOIN",
            difficulty_level="intermediate"
        )
    """
```

### get_practice_tips

Get tips and hints for practice exercises.

```python
@tool
def get_practice_tips(
    practice_name: str = None,
    exercise_context: str = None
) -> str:
    """
    Get tips and hints for practice exercises.
    
    Args:
        practice_name: Name of the practice
        exercise_context: Context of the specific exercise
        
    Returns:
        JSON string with categorized tips
    """
```

### get_related_topics

Find topics related to a given subject or concept.

```python
@tool
def get_related_topics(
    topic_name: str,
    relationship_types: List[str] = None,
    max_depth: int = 2
) -> str:
    """
    Find topics related to a given topic through knowledge graph relationships.
    
    Args:
        topic_name: Name of the topic to find relations for
        relationship_types: Types of relationships to follow
        max_depth: Maximum depth of relationships to explore
        
    Returns:
        JSON string with related topics and relationship paths
    """
```

### get_theoretical_content

Generate theoretical content using the LLM Graph Builder API.

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

### get_learning_path

Generate a learning path between topics.

```python
@tool
def get_learning_path(
    start_topic: str,
    end_topic: str,
    subject_context: str = None
) -> str:
    """
    Generate a learning path between two topics.
    
    Args:
        start_topic: Starting topic/concept
        end_topic: Target topic/concept
        subject_context: Optional subject context for better path finding
        
    Returns:
        JSON string with ordered learning steps and prerequisites
    """
```

## 🔧 Utility Tools

### process_text

Advanced text processing with multiple operations.

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
        
    Available Operations:
        - "clean": Remove extra whitespace and normalize
        - "count_words": Count words in text
        - "count_characters": Count characters (with/without spaces)
        - "extract_keywords": Extract key terms using NLP
        - "summarize": Create brief summary
        - "translate": Translate to specified language (requires 'target_lang' param)
        - "sentiment": Analyze sentiment
        - "readability": Calculate readability score
        
    Returns:
        Dictionary with operation results
        
    Example:
        result = process_text(
            "Este es un texto de ejemplo para procesar.",
            ["clean", "count_words", "extract_keywords"]
        )
    """
```

**Response Format:**
```json
{
    "original_text": "Este es un texto de ejemplo...",
    "results": {
        "clean": "Este es un texto de ejemplo para procesar.",
        "count_words": 8,
        "extract_keywords": ["texto", "ejemplo", "procesar"]
    },
    "processing_time_ms": 45
}
```

### validate_input

Comprehensive input validation for various data types.

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
        
    Validation Types:
        - "email": Email address validation
        - "url": URL validation  
        - "number": Numeric validation (supports min/max)
        - "date": Date format validation (supports format specification)
        - "text_length": Text length validation (requires min_length/max_length)
        - "regex": Custom regex validation (requires pattern)
        - "phone": Phone number validation
        - "postal_code": Postal code validation (supports country)
        
    Returns:
        Validation result with is_valid flag and details
        
    Example:
        result = validate_input(
            "test@example.com",
            "email"
        )
        
        result = validate_input(
            "123",
            "number",
            min_value=1,
            max_value=100
        )
    """
```

### calculate

Safe mathematical calculations with support for common functions.

```python
@tool
def calculate(expression: str) -> Dict[str, Any]:
    """
    Perform safe mathematical calculations.
    
    Args:
        expression: Mathematical expression as string
        
    Supported Operations:
        - Basic arithmetic: +, -, *, /, %, **
        - Math functions: sin, cos, tan, log, log10, sqrt, abs, ceil, floor
        - Constants: pi, e
        - Comparison: ==, !=, <, >, <=, >=
        
    Returns:
        Calculation result or error information
        
    Example:
        result = calculate("sqrt(25) + log10(100)")
        result = calculate("sin(pi/2) * cos(0)")
    """
```

**Security Features:**
- Restricted function set (no exec, eval, import)
- Input sanitization
- Expression complexity limits
- Timeout protection

### datetime_operations

Date and time manipulation utilities.

```python
@tool
def datetime_operations(
    operation: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Perform date and time operations.
    
    Args:
        operation: Type of operation to perform
        **kwargs: Operation-specific parameters
        
    Operations:
        - "current_time": Get current timestamp
        - "parse_date": Parse date string (requires 'date_string', optional 'format')
        - "format_date": Format datetime (requires 'datetime', 'format')
        - "add_time": Add time to date (requires 'datetime', 'years', 'months', 'days', 'hours', 'minutes')
        - "time_diff": Calculate difference between dates (requires 'start_date', 'end_date')
        - "timezone_convert": Convert timezone (requires 'datetime', 'from_tz', 'to_tz')
        
    Returns:
        Operation result with formatted dates and calculations
        
    Example:
        result = datetime_operations(
            "add_time",
            datetime="2024-01-15 10:00:00",
            days=7,
            hours=2
        )
    """
```

### format_data

Data formatting utilities for various output formats.

```python
@tool
def format_data(
    data: Any,
    output_format: str,
    **kwargs
) -> str:
    """
    Format data into specified output format.
    
    Args:
        data: Data to format (dict, list, or primitive)
        output_format: Target format
        **kwargs: Format-specific options
        
    Supported Formats:
        - "json": JSON formatting (supports 'indent', 'sort_keys')
        - "csv": CSV formatting (supports 'delimiter', 'headers')
        - "table": ASCII table formatting (supports 'max_width')
        - "markdown": Markdown table formatting
        - "yaml": YAML formatting
        - "xml": XML formatting (requires 'root_element')
        - "list": Formatted list (supports 'bullet_style')
        
    Returns:
        Formatted string representation
        
    Example:
        formatted = format_data(
            [{"name": "Juan", "age": 25}, {"name": "María", "age": 30}],
            "table"
        )
    """
```

## 🎯 Tool Registry System

### Registry Architecture

The tool registry provides centralized management and discovery of tools across the system.

```python
class ToolRegistry:
    """Central registry for tool discovery and management"""
    
    def __init__(self):
        self._tools = {}
        self._categories = {}
        self._agent_mappings = {}
        self._load_default_tools()
    
    def register_tool(
        self,
        tool: Tool,
        categories: List[str],
        agents: List[str] = None
    ) -> None:
        """Register a new tool with categories and agent assignments"""
        
    def get_tools_for_agent(self, agent_type: str) -> List[Tool]:
        """Get tools configured for specific agent type"""
        
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category"""
        
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        
    def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name or description"""
```

### Agent-Tool Mappings

```python
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
        "get_theoretical_content",
        "format_data"
    ],
    "practice_helper": [
        "get_practice_exercises",
        "get_practice_tips",
        "get_related_topics",
        "calculate",
        "validate_input"
    ],
    "recommendation": [
        "search_knowledge_graph",
        "get_learning_path",
        "get_related_topics",
        "format_data"
    ]
}
```

### Usage Examples

#### Getting Tools for an Agent

```python
from tools.registry import ToolRegistry

# Initialize registry
registry = ToolRegistry()

# Get tools for GapAnalyzer
gapanalyzer_tools = registry.get_tools_for_agent("gapanalyzer")

# Use in LangGraph agent
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, tools=gapanalyzer_tools)
```

#### Adding Custom Tools

```python
from langchain.tools import tool
from tools.registry import ToolRegistry

@tool
def custom_domain_tool(query: str) -> str:
    """Custom tool for domain-specific logic"""
    # Implementation here
    return result

# Register the tool
registry = ToolRegistry()
registry.register_tool(
    tool=custom_domain_tool,
    categories=["custom", "domain"],
    agents=["gapanalyzer", "tutor"]
)
```

## 🔧 LLM Configuration

### Default LLM Creation

```python
from tools import create_default_llm, create_observed_llm

# Create LLM with environment configuration
llm = create_default_llm()

# Create LLM with observability (recommended)
observed_llm = create_observed_llm()

# Override specific parameters
custom_llm = create_default_llm(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=2048
)
```

### Supported Models

```python
SUPPORTED_MODELS = {
    "openai": {
        "gpt-4o": {
            "max_tokens": 128000,
            "supports_functions": True,
            "cost_per_1k_tokens": {"input": 0.005, "output": 0.015}
        },
        "gpt-4o-mini": {
            "max_tokens": 128000,
            "supports_functions": True,
            "cost_per_1k_tokens": {"input": 0.00015, "output": 0.0006}
        },
        "gpt-4-turbo": {
            "max_tokens": 128000,
            "supports_functions": True,
            "cost_per_1k_tokens": {"input": 0.01, "output": 0.03}
        }
    }
}
```

### Environment Configuration

```bash
# LLM Configuration Variables
DEFAULT_LLM_MODEL=gpt-4o-mini          # Recommended for cost-efficiency
DEFAULT_LLM_PROVIDER=openai            # Currently only OpenAI supported
DEFAULT_LLM_TEMPERATURE=0.1            # Low temperature for consistency
DEFAULT_LLM_MAX_TOKENS=4096            # Maximum response tokens
DEFAULT_LLM_TIMEOUT=60                 # Request timeout in seconds
```

## 📊 Observability Integration

### Langfuse Integration

All tools automatically integrate with Langfuse when using `create_observed_llm()`.

```python
from tools.observability import create_observed_llm, observe_openai_call

# Create observed LLM (automatic tracing)
llm = create_observed_llm()

# Direct OpenAI call observation
from openai import OpenAI
client = OpenAI()

response = observe_openai_call(
    client=client,
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4o-mini",
    operation_name="custom_tool_call",
    metadata={"tool": "custom_tool", "agent": "gapanalyzer"}
)
```

### Metrics Tracking

```python
# Example tool with custom metrics
@tool
def instrumented_tool(query: str) -> str:
    """Tool with custom observability"""
    import time
    start_time = time.time()
    
    try:
        # Tool logic here
        result = process_query(query)
        
        # Log success metrics
        langfuse_handler.log_event(
            name="tool_execution",
            properties={
                "tool_name": "instrumented_tool",
                "execution_time": time.time() - start_time,
                "status": "success",
                "query_length": len(query)
            }
        )
        
        return result
        
    except Exception as e:
        # Log error metrics
        langfuse_handler.log_event(
            name="tool_error",
            properties={
                "tool_name": "instrumented_tool",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        )
        raise
```

## 🔒 Security and Best Practices

### Input Validation

All tools implement comprehensive input validation:

```python
def validate_tool_input(input_value: Any, expected_type: type, constraints: Dict = None) -> None:
    """Validate tool input parameters"""
    if not isinstance(input_value, expected_type):
        raise ValueError(f"Expected {expected_type.__name__}, got {type(input_value).__name__}")
    
    if constraints:
        if "max_length" in constraints and len(str(input_value)) > constraints["max_length"]:
            raise ValueError(f"Input exceeds maximum length of {constraints['max_length']}")
        
        if "min_value" in constraints and input_value < constraints["min_value"]:
            raise ValueError(f"Input below minimum value of {constraints['min_value']}")
```

### Error Handling

```python
class ToolError(Exception):
    """Base exception for tool errors"""
    pass

class ValidationError(ToolError):
    """Raised when input validation fails"""
    pass

class ExecutionError(ToolError):
    """Raised when tool execution fails"""
    pass

# Example error handling in tools
@tool
def safe_tool(input_param: str) -> str:
    """Tool with comprehensive error handling"""
    try:
        # Validate input
        if not input_param or len(input_param.strip()) == 0:
            raise ValidationError("Input parameter cannot be empty")
        
        # Execute tool logic
        result = process_input(input_param)
        
        return result
        
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        # Wrap unexpected errors
        raise ExecutionError(f"Tool execution failed: {str(e)}") from e
```

### Rate Limiting

```python
from functools import wraps
import time
from collections import defaultdict

# Simple rate limiting decorator
def rate_limit(calls_per_minute: int = 60):
    call_times = defaultdict(list)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            minute_ago = now - 60
            
            # Clean old calls
            func_name = func.__name__
            call_times[func_name] = [t for t in call_times[func_name] if t > minute_ago]
            
            # Check rate limit
            if len(call_times[func_name]) >= calls_per_minute:
                raise Exception(f"Rate limit exceeded for {func_name}")
            
            # Record this call
            call_times[func_name].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@tool
@rate_limit(calls_per_minute=30)
def rate_limited_tool(query: str) -> str:
    """Tool with rate limiting"""
    return process_query(query)
```

This tools reference provides comprehensive documentation for all available tools in the Luca system, including usage examples, configuration options, and best practices for tool development and integration.