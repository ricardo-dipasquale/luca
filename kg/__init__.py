"""
Knowledge Graph (KG) module for Luca.

This module provides abstraction layers for interacting with the Neo4j knowledge graph
containing course materials, practices, and exercises.

Main components:
- KGConnection: Neo4j connection management using environment variables
- KGQueryInterface: High-level functional interface for common KG operations  
- SearchResult: Data class for search results

Example usage:
    from kg import KGConnection, KGQueryInterface
    
    # Initialize connection (uses NEO4J_* environment variables)
    with KGConnection() as conn:
        kg = KGQueryInterface(conn)
        
        # Get all subjects
        subjects = kg.get_subjects()
        
        # Search for content
        results = kg.search_by_text("relational algebra")
        
        # Get practice exercises
        exercises = kg.get_practice_exercises(practice_number=1)
"""

from .connection import KGConnection, KGConnectionError
from .queries import KGQueryInterface, SearchResult

__all__ = [
    'KGConnection',
    'KGConnectionError', 
    'KGQueryInterface',
    'SearchResult'
]