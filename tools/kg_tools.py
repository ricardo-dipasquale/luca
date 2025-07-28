"""
Knowledge Graph tools for LangChain agents.

This module provides LangChain tools that interact with the Luca knowledge graph
using the KG abstraction layer. These tools can be used by any agent that needs
to query course materials, practices, and exercises.
"""

import logging
import hashlib
import time
from threading import Lock
from typing import List, Optional, Dict, Any, Tuple
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from kg import KGConnection, KGQueryInterface, KGConnectionError


logger = logging.getLogger(__name__)

# Global KG interface instance (lazy loaded)
_kg_interface: Optional[KGQueryInterface] = None

# Global cache for KG tools
class KGToolsCache:
    """Thread-safe cache for KG tools with TTL support."""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default TTL
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._lock = Lock()
        self.default_ttl = default_ttl
        
    def _generate_key(self, function_name: str, *args, **kwargs) -> str:
        """Generate a cache key from function name and arguments."""
        # Create a string representation of all arguments
        key_data = f"{function_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        # Use SHA256 hash for consistent, clean keys
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]
    
    def get(self, function_name: str, *args, **kwargs) -> Optional[Any]:
        """Get cached value if it exists and hasn't expired."""
        key = self._generate_key(function_name, *args, **kwargs)
        
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                current_time = time.time()
                
                # Check if cache entry has expired
                if current_time - timestamp < self.default_ttl:
                    logger.debug(f"Cache HIT for {function_name} (key: {key})")
                    return value
                else:
                    # Remove expired entry
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED for {function_name} (key: {key})")
            
            logger.debug(f"Cache MISS for {function_name} (key: {key})")
            return None
    
    def put(self, function_name: str, value: Any, *args, **kwargs) -> None:
        """Store value in cache with current timestamp."""
        key = self._generate_key(function_name, *args, **kwargs)
        current_time = time.time()
        
        with self._lock:
            self._cache[key] = (value, current_time)
            logger.debug(f"Cache STORE for {function_name} (key: {key})")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            cache_size = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {cache_size} entries removed")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, (value, timestamp) in self._cache.items():
                if current_time - timestamp >= self.default_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cache cleanup: {len(expired_keys)} expired entries removed")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for _, timestamp in self._cache.values()
                if current_time - timestamp >= self.default_ttl
            )
            active_entries = total_entries - expired_entries
            
            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "ttl_seconds": self.default_ttl
            }

# Global cache instance
_kg_cache = KGToolsCache(default_ttl=1800)  # 30 minutes TTL


def _is_meaningful_response(message: str, topic_description: str) -> bool:
    """
    Check if the API response contains meaningful theoretical content.
    
    Args:
        message: Response message from the API
        topic_description: Original topic description
        
    Returns:
        True if the response seems meaningful, False otherwise
    """
    if not message or len(message.strip()) < 20:
        return False
    
    # Check for generic "no information" responses
    no_info_indicators = [
        "no puedo proporcionar",
        "no tengo información",
        "no se encuentra información",
        "no hay datos",
        "información no disponible",
        "no está disponible",
        "no conozco",
        "no sé",
        "disculpa, pero no",
        "lo siento, no"
    ]
    
    message_lower = message.lower()
    
    # If message contains generic "no info" responses
    if any(indicator in message_lower for indicator in no_info_indicators):
        return False
    
    # Check if response is too generic (less than 50 characters)
    if len(message.strip()) < 50:
        return False
    
    return True


def _get_fallback_theoretical_content(topic_description: str) -> str:
    """
    Get theoretical content using direct LLM call as fallback.
    
    Args:
        topic_description: Description of the topic to get theory for
        
    Returns:
        Formatted string with theoretical content from LLM
    """
    # Check cache first
    cached_result = _kg_cache.get("_get_fallback_theoretical_content", topic_description)
    if cached_result is not None:
        return cached_result
    
    import os
    import threading
    from openai import OpenAI
    from .observability import observe_openai_call
    
    try:
        # Get configuration from environment
        api_key = os.getenv('OPENAI_API_KEY')
        model = os.getenv('DEFAULT_LLM_MODEL', 'gpt-4o-mini')
        temperature = float(os.getenv('DEFAULT_LLM_TEMPERATURE', '0.1'))
        
        if not api_key:
            return f"Error: No se pudo obtener contenido teórico para {topic_description} (falta configuración)"
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create concise prompt
        prompt = f"""Explicá de manera muy concisa (máximo 1 párrafo) los conceptos teóricos fundamentales sobre "{topic_description}".

Incluí:
- Definición básica
- Principios clave
- Relación con otros conceptos

Mantené la respuesta en español argentino y sé específico pero breve."""

        # Prepare messages
        messages = [
            {"role": "system", "content": "Sos un tutor experto en Ingeniería. Respondé de manera concisa y clara."},
            {"role": "user", "content": prompt}
        ]
        
        # Generate thread-safe session ID
        thread_id = threading.current_thread().ident or 0
        session_id = f"theoretical_content_{thread_id}"
        
        # Make observed API call
        response = observe_openai_call(
            client=client,
            messages=messages,
            model=model,
            operation_name="theoretical_content_fallback",
            session_id=session_id,
            metadata={
                "topic": topic_description,
                "source": "fallback_llm",
                "tool": "get_theoretical_content"
            },
            temperature=temperature,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        if content:
            result = [f"Contenido teórico para '{topic_description}' (fuente: LLM):"]
            result.append("")
            result.append(content)
            
            formatted_result = "\n".join(result)
            logger.info(f"Successfully retrieved fallback theoretical content for: {topic_description}")
            
            # Cache the successful result
            _kg_cache.put("_get_fallback_theoretical_content", formatted_result, topic_description)
            return formatted_result
        else:
            error_msg = f"No se pudo generar contenido teórico para: {topic_description}"
            # Don't cache error responses
            return error_msg
            
    except Exception as e:
        logger.error(f"Error in fallback theoretical content: {e}")
        error_msg = f"Error al generar contenido teórico alternativo para {topic_description}: {str(e)}"
        # Don't cache error responses
        return error_msg


def get_kg_interface() -> KGQueryInterface:
    """
    Get or create a shared KGQueryInterface instance.
    
    Returns:
        KGQueryInterface: Shared interface instance
        
    Raises:
        KGConnectionError: If connection cannot be established
    """
    global _kg_interface
    if _kg_interface is None:
        try:
            connection = KGConnection()
            _kg_interface = KGQueryInterface(connection)
            logger.info("KG interface initialized for tools")
        except Exception as e:
            logger.error(f"Failed to initialize KG interface: {e}")
            raise KGConnectionError(f"Cannot initialize KG tools: {e}") from e
    
    return _kg_interface


class SubjectQuery(BaseModel):
    """Input schema for subject-related queries."""
    subject_name: Optional[str] = Field(
        None, 
        description="Name of the specific subject. If not provided, returns all subjects."
    )


class PracticeQuery(BaseModel):
    """Input schema for practice-related queries."""
    practice_number: int = Field(
        description="Number of the practice session (e.g., 1, 2, 3)"
    )


class SearchQuery(BaseModel):
    """Input schema for search queries."""
    query_text: str = Field(
        description="Text to search for in the knowledge graph"
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return"
    )


class TopicQuery(BaseModel):
    """Input schema for topic-related queries."""
    topic_description: str = Field(
        description="Description of the topic to query"
    )


class PracticeTipsQuery(BaseModel):
    """Input schema for practice tips queries."""
    practice_number: int = Field(
        description="Number of the practice session (e.g., 1, 2, 3)"
    )
    section_number: Optional[str] = Field(
        default=None,
        description="Section number (string, e.g., '1', '2') - optional"
    )
    exercise_number: Optional[str] = Field(
        default=None,
        description="Exercise number (string, e.g., 'a', 'b', 'd') - optional"
    )


@tool("get_subjects", args_schema=SubjectQuery)
def get_subjects_tool(subject_name: Optional[str] = None) -> str:
    """
    Get information about course subjects.
    
    If subject_name is provided, returns detailed information about that subject
    including its topics and objectives. If not provided, returns all available subjects.
    
    Args:
        subject_name: Optional name of specific subject
        
    Returns:
        Formatted string with subject information
    """
    try:
        kg = get_kg_interface()
        
        if subject_name:
            # Get specific subject details
            topics = kg.get_subject_topics(subject_name)
            objectives = kg.get_subject_objectives(subject_name)
            
            if not topics and not objectives:
                return f"No information found for subject: {subject_name}"
            
            result = [f"Subject: {subject_name}"]
            
            if objectives:
                result.append("\nObjectives:")
                for i, obj in enumerate(objectives, 1):
                    result.append(f"  {i}. {obj}")
            
            if topics:
                result.append("\nTopics by Unit:")
                current_unit = None
                for topic in topics:
                    if topic['unit_number'] != current_unit:
                        current_unit = topic['unit_number']
                        result.append(f"\n  Unit {current_unit}: {topic['unit_title']}")
                    result.append(f"    - {topic['topic_description']}")
            
            return "\n".join(result)
        else:
            # Get all subjects
            subjects = kg.get_subjects()
            if not subjects:
                return "No subjects found in the knowledge graph."
            
            result = ["Available Subjects:"]
            for subject in subjects:
                result.append(f"  - {subject['name']}")
            
            return "\n".join(result)
            
    except Exception as e:
        logger.error(f"Error in get_subjects_tool: {e}")
        return f"Error retrieving subject information: {str(e)}"


@tool("get_practice_exercises", args_schema=PracticeQuery)
def get_practice_exercises_tool(practice_number: int) -> str:
    """
    Get exercises for a specific practice session.
    
    Returns all exercises organized by sections for the given practice number,
    including exercise statements and answers where available.
    
    Args:
        practice_number: Number of the practice session
        
    Returns:
        Formatted string with practice exercises
    """
    try:
        kg = get_kg_interface()
        exercises = kg.get_practice_exercises(practice_number)
        
        if not exercises:
            return f"No exercises found for practice {practice_number}."
        
        result = [f"Practice {practice_number} - Exercises:"]
        current_section = None
        
        for exercise in exercises:
            section_num = exercise['section_number']
            if section_num != current_section:
                current_section = section_num
                result.append(f"\nSection {section_num}: {exercise['section_statement']}")
            
            result.append(f"\n  Exercise {exercise['exercise_number']}:")
            result.append(f"    {exercise['exercise_statement']}")
            
            if exercise['answers']:
                result.append("    Answers:")
                for answer in exercise['answers']:
                    result.append(f"      - {answer}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error in get_practice_exercises_tool: {e}")
        return f"Error retrieving practice exercises: {str(e)}"


@tool("get_practice_tips", args_schema=PracticeTipsQuery)
def get_practice_tips_tool(practice_number: int, section_number: Optional[str] = None, exercise_number: Optional[str] = None) -> str:
    """
    Get tips and hints for a specific practice, section, and/or exercise.
    
    Returns tips connected to:
    - The specified practice (always included)
    - The specified section (if section_number provided)
    - The specified exercise (if both section_number and exercise_number provided)
    
    Args:
        practice_number: Number of the practice session
        section_number: Section number (string, e.g., "1", "2") - optional
        exercise_number: Exercise number (string, e.g., "a", "b", "d") - optional
        
    Returns:
        Formatted string with filtered practice tips
    """
    try:
        kg = get_kg_interface()
        tips = kg.get_practice_tips(practice_number, section_number, exercise_number)
        
        if not tips:
            context_desc = f"practice {practice_number}"
            if section_number:
                context_desc += f", section {section_number}"
            if exercise_number:
                context_desc += f", exercise {exercise_number}"
            return f"No tips found for {context_desc}."
        
        # Build context description
        context_desc = f"Practice {practice_number}"
        if section_number:
            context_desc += f", Section {section_number}"
        if exercise_number:
            context_desc += f", Exercise {exercise_number}"
        
        result = [f"{context_desc} - Tips:"]
        
        # Group tips by level
        practice_tips = [tip for tip in tips if tip['level'] == 'practice']
        section_tips = [tip for tip in tips if tip['level'] == 'section']
        exercise_tips = [tip for tip in tips if tip['level'] == 'exercise']
        
        if practice_tips:
            result.append("\nGeneral Practice Tips:")
            for tip in practice_tips:
                result.append(f"  - {tip['tip_text']}")
        
        if section_tips:
            result.append("\nSection-Specific Tips:")
            for tip in section_tips:
                result.append(f"  Section {tip['section_number']}: {tip['tip_text']}")
        
        if exercise_tips:
            result.append("\nExercise-Specific Tips:")
            for tip in exercise_tips:
                result.append(f"  Section {tip['section_number']}, Exercise {tip['exercise_number']}: {tip['tip_text']}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error in get_practice_tips_tool: {e}")
        return f"Error retrieving practice tips for practice {practice_number}, section {section_number}, exercise {exercise_number}: {str(e)}"


@tool("search_knowledge_graph", args_schema=SearchQuery)
def search_knowledge_graph_tool(query_text: str, limit: int = 10) -> str:
    """
    Search the knowledge graph for content matching the query text.
    
    Searches across all searchable content including topics, exercises, 
    objectives, and answers for relevant information.
    
    Args:
        query_text: Text to search for
        limit: Maximum number of results to return
        
    Returns:
        Formatted string with search results
    """
    # Check cache first
    cached_result = _kg_cache.get("search_knowledge_graph_tool", query_text, limit=limit)
    if cached_result is not None:
        return cached_result
    
    try:
        kg = get_kg_interface()
        results = kg.search_by_text(query_text, limit=limit)
        
        if not results:
            no_results_msg = f"No results found for: {query_text}"
            # Don't cache "no results" responses as they might change when data is added
            return no_results_msg
        
        result_lines = [f"Search results for '{query_text}':"]
        
        for i, result in enumerate(results, 1):
            result_lines.append(f"\n{i}. {result.node_type} (ID: {result.node_id})")
            
            # Extract relevant properties for display
            if 'descripcion' in result.properties:
                result_lines.append(f"   Description: {result.properties['descripcion']}")
            elif 'enunciado' in result.properties:
                result_lines.append(f"   Statement: {result.properties['enunciado']}")
            elif 'texto' in result.properties:
                result_lines.append(f"   Text: {result.properties['texto']}")
            elif 'titulo' in result.properties:
                result_lines.append(f"   Title: {result.properties['titulo']}")
            
            if result.score:
                result_lines.append(f"   Relevance: {result.score:.2f}")
        
        formatted_result = "\n".join(result_lines)
        
        # Cache the successful result
        _kg_cache.put("search_knowledge_graph_tool", formatted_result, query_text, limit=limit)
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error in search_knowledge_graph_tool: {e}")
        error_msg = f"Error searching knowledge graph: {str(e)}"
        # Don't cache error responses
        return error_msg


@tool("get_related_topics", args_schema=TopicQuery)
def get_related_topics_tool(topic_description: str) -> str:
    """
    Find topics related to a given topic through shared practices.
    
    Helps students discover related concepts and learning paths by finding
    topics that appear together in practice sessions.
    
    Args:
        topic_description: Description of the topic to find relations for
        
    Returns:
        Formatted string with related topics
    """
    try:
        kg = get_kg_interface()
        related = kg.get_related_topics(topic_description)
        
        if not related:
            return f"No related topics found for: {topic_description}"
        
        result = [f"Topics related to '{topic_description}':"]
        
        # Group by practice
        by_practice = {}
        for item in related:
            practice_num = item['practice_number']
            if practice_num not in by_practice:
                by_practice[practice_num] = []
            by_practice[practice_num].append(item['related_topic'])
        
        for practice_num in sorted(by_practice.keys()):
            result.append(f"\n  Through Practice {practice_num}:")
            for topic in by_practice[practice_num]:
                result.append(f"    - {topic}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error in get_related_topics_tool: {e}")
        return f"Error finding related topics: {str(e)}"


@tool("get_theoretical_content", args_schema=TopicQuery)
def get_theoretical_content_tool(topic_description: str) -> str:
    """
    Get theoretical content and background for a given topic using LLM Graph Builder API.
    
    Retrieves comprehensive theoretical information including definitions,
    concepts, and explanations for better understanding of topics.
    
    Args:
        topic_description: Description of the topic to get theory for
        
    Returns:
        Formatted string with theoretical content
    """
    # Check cache first
    cached_result = _kg_cache.get("get_theoretical_content_tool", topic_description)
    if cached_result is not None:
        return cached_result
    
    import os
    import requests
    import threading
    from urllib.parse import quote
    
    try:
        # Get configuration from environment
        graphbuilder_uri = os.getenv('GRAPHBUILDER_URI', 'http://127.0.0.1:8000/chat_bot')
        neo4j_uri = os.getenv('INTERNAL_NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        
        # Generate thread-safe session ID
        thread_id = threading.current_thread().ident or 0
        session_id = f"theory_tool_{thread_id}_{hash(topic_description) % 10000:04d}"
        
        # Prepare the question with theoretical focus
        #question = f"Explicá los conceptos teóricos fundamentales sobre {topic_description}. Incluí definiciones, principios y fundamentos teóricos."
        question = f"{topic_description}"
        
        # Prepare form data
        form_data = {
            'mode': 'graph',
            'document_names': '',
            'session_id': session_id,
            'question': question,
            'model': 'openai_gpt_4o_mini',
            'uri': neo4j_uri,
            'userName': neo4j_user,
            'database': 'neo4j',
            'password': neo4j_password,
            'email': ''  # Empty as requested
        }
        
        # Make POST request
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        logger.info(f"Requesting theoretical content for: {topic_description}")
        response = requests.post(
            graphbuilder_uri,
            data=form_data,
            headers=headers,
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get('status') == 'Success':
                data = response_data.get('data', {})
                message = data.get('message', '')
                
                if message and _is_meaningful_response(message, topic_description):
                    result = [f"Contenido teórico para '{topic_description}':"]
                    result.append("")
                    result.append(message)
                    
                    formatted_result = "\n".join(result)
                    logger.info(f"Successfully retrieved theoretical content for: {topic_description}")
                    
                    # Cache the successful result
                    _kg_cache.put("get_theoretical_content_tool", formatted_result, topic_description)
                    return formatted_result
                else:
                    # Fallback to direct LLM if API response is insufficient
                    logger.info(f"API response insufficient for {topic_description}, using fallback LLM")
                    fallback_result = _get_fallback_theoretical_content(topic_description)
                    # Cache the fallback result too (it's already cached by the fallback function, but cache here as well for this tool)
                    _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
                    return fallback_result
            else:
                logger.error(f"API returned error status: {response_data.get('status')}")
                # Try fallback on API error
                fallback_result = _get_fallback_theoretical_content(topic_description)
                _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
                return fallback_result
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            # Try fallback on HTTP error
            fallback_result = _get_fallback_theoretical_content(topic_description)
            _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
            return fallback_result
        
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to LLM Graph Builder API, trying fallback")
        fallback_result = _get_fallback_theoretical_content(topic_description)
        _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
        return fallback_result
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to LLM Graph Builder API, trying fallback")
        fallback_result = _get_fallback_theoretical_content(topic_description)
        _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
        return fallback_result
    except Exception as e:
        logger.error(f"Error in get_theoretical_content_tool: {e}, trying fallback")
        fallback_result = _get_fallback_theoretical_content(topic_description)
        _kg_cache.put("get_theoretical_content_tool", fallback_result, topic_description)
        return fallback_result


@tool("get_learning_path", args_schema=TopicQuery)
def get_learning_path_tool(topic_description: str) -> str:
    """
    Get the learning path from a topic to practical exercises.
    
    Shows how theoretical topics connect to hands-on practice through
    the topic -> practice -> section -> exercise progression.
    
    Args:
        topic_description: Description of the topic
        
    Returns:
        Formatted string with learning path
    """
    try:
        kg = get_kg_interface()
        path = kg.get_topic_practice_path(topic_description)
        
        if not path:
            return f"No learning path found for topic: {topic_description}"
        
        result = [f"Learning path for '{topic_description}':"]
        
        # Group by practice
        by_practice = {}
        for item in path:
            practice_num = item['practice_number']
            if practice_num not in by_practice:
                by_practice[practice_num] = []
            by_practice[practice_num].append(item)
        
        for practice_num in sorted(by_practice.keys()):
            result.append(f"\n  Practice {practice_num}:")
            
            # Group by section within practice
            by_section = {}
            for item in by_practice[practice_num]:
                section_num = item['section_number']
                if section_num not in by_section:
                    by_section[section_num] = []
                by_section[section_num].append(item)
            
            for section_num in sorted(by_section.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):
                section_items = by_section[section_num]
                if section_items:
                    result.append(f"    Section {section_num}: {section_items[0]['section_statement']}")
                    for item in section_items:
                        result.append(f"      Exercise {item['exercise_number']}: {item['exercise_statement'][:100]}...")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error in get_learning_path_tool: {e}")
        return f"Error retrieving learning path: {str(e)}"


def get_kg_tools() -> List:
    """
    Get all available knowledge graph tools.
    
    Returns:
        List of LangChain tool functions for KG operations
    """
    return [
        get_subjects_tool,
        get_practice_exercises_tool,
        get_practice_tips_tool,
        search_knowledge_graph_tool,
        get_related_topics_tool,
        get_theoretical_content_tool,
        get_learning_path_tool
    ]


# Cache management utilities

def clear_kg_cache() -> None:
    """Clear all cached entries in the KG tools cache."""
    _kg_cache.clear()
    logger.info("KG tools cache cleared")


def cleanup_expired_cache() -> int:
    """Remove expired entries from the cache and return count removed."""
    return _kg_cache.cleanup_expired()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dictionary with cache statistics including total entries, 
        active entries, expired entries, and TTL settings
    """
    return _kg_cache.get_stats()


@tool("kg_cache_stats")
def kg_cache_stats_tool() -> str:
    """
    Get current cache statistics for KG tools.
    
    Returns:
        Formatted string with cache performance information
    """
    stats = get_cache_stats()
    
    result = ["KG Tools Cache Statistics:"]
    result.append(f"  Total entries: {stats['total_entries']}")
    result.append(f"  Active entries: {stats['active_entries']}")
    result.append(f"  Expired entries: {stats['expired_entries']}")
    result.append(f"  TTL: {stats['ttl_seconds']} seconds ({stats['ttl_seconds']//60} minutes)")
    
    # Calculate cache efficiency if we have data
    if stats['total_entries'] > 0:
        efficiency = (stats['active_entries'] / stats['total_entries']) * 100
        result.append(f"  Cache efficiency: {efficiency:.1f}%")
    
    return "\n".join(result)