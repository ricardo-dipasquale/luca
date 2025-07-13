"""
Knowledge Graph tools for LangChain agents.

This module provides LangChain tools that interact with the Luca knowledge graph
using the KG abstraction layer. These tools can be used by any agent that needs
to query course materials, practices, and exercises.
"""

import logging
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from kg import KGConnection, KGQueryInterface, KGConnectionError


logger = logging.getLogger(__name__)

# Global KG interface instance (lazy loaded)
_kg_interface: Optional[KGQueryInterface] = None


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
    import os
    from openai import OpenAI
    
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

        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Sos un tutor experto en Ingeniería. Respondé de manera concisa y clara."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=300  # Limit for conciseness
        )
        
        content = response.choices[0].message.content.strip()
        
        if content:
            result = [f"Contenido teórico para '{topic_description}' (fuente: LLM):"]
            result.append("")
            result.append(content)
            
            logger.info(f"Successfully retrieved fallback theoretical content for: {topic_description}")
            return "\n".join(result)
        else:
            return f"No se pudo generar contenido teórico para: {topic_description}"
            
    except Exception as e:
        logger.error(f"Error in fallback theoretical content: {e}")
        return f"Error al generar contenido teórico alternativo para {topic_description}: {str(e)}"


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


@tool("get_practice_tips", args_schema=PracticeQuery)
def get_practice_tips_tool(practice_number: int) -> str:
    """
    Get tips and hints for a specific practice session.
    
    Returns tips at practice, section, and exercise levels to help students
    with the given practice.
    
    Args:
        practice_number: Number of the practice session
        
    Returns:
        Formatted string with practice tips
    """
    try:
        kg = get_kg_interface()
        tips = kg.get_practice_tips(practice_number)
        
        if not tips:
            return f"No tips found for practice {practice_number}."
        
        result = [f"Practice {practice_number} - Tips:"]
        
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
        return f"Error retrieving practice tips: {str(e)}"


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
    try:
        kg = get_kg_interface()
        results = kg.search_by_text(query_text, limit=limit)
        
        if not results:
            return f"No results found for: {query_text}"
        
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
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error in search_knowledge_graph_tool: {e}")
        return f"Error searching knowledge graph: {str(e)}"


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
    import os
    import requests
    import threading
    from urllib.parse import quote
    
    try:
        # Get configuration from environment
        graphbuilder_uri = os.getenv('GRAPHBUILDER_URI', 'http://127.0.0.1:8000/chat_bot')
        neo4j_uri = os.getenv('INTERNAL_NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
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
                    
                    logger.info(f"Successfully retrieved theoretical content for: {topic_description}")
                    return "\n".join(result)
                else:
                    # Fallback to direct LLM if API response is insufficient
                    logger.info(f"API response insufficient for {topic_description}, using fallback LLM")
                    return _get_fallback_theoretical_content(topic_description)
            else:
                logger.error(f"API returned error status: {response_data.get('status')}")
                # Try fallback on API error
                return _get_fallback_theoretical_content(topic_description)
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            # Try fallback on HTTP error
            return _get_fallback_theoretical_content(topic_description)
        
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to LLM Graph Builder API, trying fallback")
        return _get_fallback_theoretical_content(topic_description)
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to LLM Graph Builder API, trying fallback")
        return _get_fallback_theoretical_content(topic_description)
    except Exception as e:
        logger.error(f"Error in get_theoretical_content_tool: {e}, trying fallback")
        return _get_fallback_theoretical_content(topic_description)


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
            
            for section_num in sorted(by_section.keys()):
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