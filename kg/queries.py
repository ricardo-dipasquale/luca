import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from .connection import KGConnection


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result from the knowledge graph."""
    node_id: int
    node_type: str
    properties: Dict[str, Any]
    score: Optional[float] = None
    
    def __str__(self):
        return f"{self.node_type}({self.node_id}): {self.properties}"


class KGQueryInterface:
    """
    Knowledge Graph query interface providing high-level abstractions for common operations.
    
    This class encapsulates Cypher queries and provides a functional interface for
    interacting with the Luca knowledge graph without exposing Cypher syntax to agents.
    """
    
    def __init__(self, connection: KGConnection):
        """
        Initialize with a KG connection.
        
        Args:
            connection: KGConnection instance
        """
        self.connection = connection
    
    # ==================== COURSE STRUCTURE QUERIES ====================
    
    def get_subjects(self) -> List[Dict[str, Any]]:
        """
        Get all subjects (Materia) in the knowledge graph.
        
        Returns:
            List of subject dictionaries with properties
        """
        query = """
        MATCH (m:Materia)
        RETURN m.nombre AS name, properties(m) AS properties
        ORDER BY m.nombre
        """
        try:
            results = self.connection.execute_query(query)
            return [{"name": record["name"], **record["properties"]} for record in results]
        except Exception as e:
            logger.error(f"Failed to get subjects: {e}")
            return []
    
    def get_subject_topics(self, subject_name: str) -> List[Dict[str, Any]]:
        """
        Get all topics for a specific subject.
        
        Args:
            subject_name: Name of the subject
            
        Returns:
            List of topic dictionaries organized by thematic units
        """
        query = """
        MATCH (m:Materia {nombre: $subject_name})-[:HAS_UNIDAD_TEMATICA]->(u:UnidadTematica)
        MATCH (u)-[:HAS_TEMA]->(t:Tema)
        RETURN u.numero AS unit_number, u.titulo AS unit_title, 
               t.descripcion AS topic_description
        ORDER BY u.numero, t.descripcion
        """
        try:
            results = self.connection.execute_query(query, {"subject_name": subject_name})
            return [dict(record) for record in results]
        except Exception as e:
            logger.error(f"Failed to get topics for subject {subject_name}: {e}")
            return []
    
    def get_subject_objectives(self, subject_name: str) -> List[str]:
        """
        Get learning objectives for a specific subject.
        
        Args:
            subject_name: Name of the subject
            
        Returns:
            List of objective descriptions
        """
        query = """
        MATCH (m:Materia {nombre: $subject_name})-[:HAS_OBJETIVO]->(o:ObjetivoMateria)
        RETURN o.descripcion AS objective
        ORDER BY objective
        """
        try:
            results = self.connection.execute_query(query, {"subject_name": subject_name})
            return [record["objective"] for record in results]
        except Exception as e:
            logger.error(f"Failed to get objectives for subject {subject_name}: {e}")
            return []
    
    # ==================== PRACTICE QUERIES ====================
    
    def get_practices(self) -> List[Dict[str, Any]]:
        """
        Get all practice sessions.
        
        Returns:
            List of practice dictionaries with metadata
        """
        query = """
        MATCH (p:Practica)
        RETURN p.numeropractica AS number, p.descripcion AS description,
               p.objetivos AS objectives, properties(p) AS all_properties
        ORDER BY p.numeropractica
        """
        try:
            results = self.connection.execute_query(query)
            return [dict(record) for record in results]
        except Exception as e:
            logger.error(f"Failed to get practices: {e}")
            return []
    
    def get_practice_exercises(self, practice_number: int) -> List[Dict[str, Any]]:
        """
        Get all exercises for a specific practice.
        
        Args:
            practice_number: Practice number
            
        Returns:
            List of exercises organized by sections
        """
        query = """
        MATCH (p:Practica {numeropractica: $practice_number})-[:HAS_SECCION]->(s:SeccionPractica)
        MATCH (s)-[:HAS_EJERCICIO]->(e:Ejercicio)
        OPTIONAL MATCH (e)-[:HAS_RESPUESTA]->(r:Respuesta)
        RETURN s.numero AS section_number, s.enunciado AS section_statement,
               e.numero AS exercise_number, e.enunciado AS exercise_statement,
               collect(r.texto) AS answers
        ORDER BY s.numero, e.numero
        """
        try:
            results = self.connection.execute_query(query, {"practice_number": practice_number})
            return [dict(record) for record in results]
        except Exception as e:
            logger.error(f"Failed to get exercises for practice {practice_number}: {e}")
            return []
    
    def get_practice_tips(self, practice_number: int) -> List[Dict[str, Any]]:
        """
        Get all tips for a practice (practice-level, section-level, and exercise-level).
        
        Args:
            practice_number: Practice number
            
        Returns:
            List of tips with their context
        """
        query = """
        MATCH (p:Practica {numeropractica: $practice_number})
        OPTIONAL MATCH (p)-[:HAS_TIP]->(tip_p:Tip)
        OPTIONAL MATCH (p)-[:HAS_SECCION]->(s:SeccionPractica)-[:HAS_TIP]->(tip_s:Tip)
        OPTIONAL MATCH (p)-[:HAS_SECCION]->(s2:SeccionPractica)-[:HAS_EJERCICIO]->(e:Ejercicio)-[:HAS_TIP]->(tip_e:Tip)
        RETURN 
          'practice' AS level, null AS section_number, null AS exercise_number, tip_p.texto AS tip_text
        UNION
        RETURN 
          'section' AS level, s.numero AS section_number, null AS exercise_number, tip_s.texto AS tip_text
        UNION  
        RETURN
          'exercise' AS level, s2.numero AS section_number, e.numero AS exercise_number, tip_e.texto AS tip_text
        """
        try:
            results = self.connection.execute_query(query, {"practice_number": practice_number})
            return [dict(record) for record in results if record["tip_text"]]
        except Exception as e:
            logger.error(f"Failed to get tips for practice {practice_number}: {e}")
            return []
    
    # ==================== SEARCH QUERIES ====================
    
    def search_by_text(self, search_text: str, limit: int = 10) -> List[SearchResult]:
        """
        Search for content by text similarity across all searchable nodes.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        # This would require vector similarity search if embeddings are available
        query = """
        CALL {
          MATCH (o:ObjetivoMateria) WHERE o.descripcion CONTAINS $search_text
          RETURN id(o) AS node_id, 'ObjetivoMateria' AS node_type, properties(o) AS props, 1.0 AS score
          UNION
          MATCH (t:Tema) WHERE t.descripcion CONTAINS $search_text  
          RETURN id(t) AS node_id, 'Tema' AS node_type, properties(t) AS props, 1.0 AS score
          UNION
          MATCH (e:Ejercicio) WHERE e.enunciado CONTAINS $search_text
          RETURN id(e) AS node_id, 'Ejercicio' AS node_type, properties(e) AS props, 1.0 AS score
          UNION
          MATCH (r:Respuesta) WHERE r.texto CONTAINS $search_text
          RETURN id(r) AS node_id, 'Respuesta' AS node_type, properties(r) AS props, 1.0 AS score
        }
        RETURN node_id, node_type, props, score
        ORDER BY score DESC
        LIMIT $limit
        """
        try:
            results = self.connection.execute_query(query, {
                "search_text": search_text,
                "limit": limit
            })
            return [
                SearchResult(
                    node_id=record["node_id"],
                    node_type=record["node_type"], 
                    properties=record["props"],
                    score=record["score"]
                )
                for record in results
            ]
        except Exception as e:
            logger.error(f"Failed to search by text '{search_text}': {e}")
            return []
    
    def vector_search(self, query_text: str, node_types: Optional[List[str]] = None, 
                     limit: int = 10) -> List[SearchResult]:
        """
        Perform vector similarity search using embeddings.
        
        Args:
            query_text: Text to search for
            node_types: Optional list of node types to search (e.g., ['Tema', 'Ejercicio'])
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects ranked by similarity
        """
        # Note: This requires OpenAI API to generate embedding for query_text
        # and assumes vector indexes exist for the target node types
        logger.warning("Vector search not implemented - requires OpenAI API integration")
        return []
    
    # ==================== RELATIONSHIP QUERIES ====================
    
    def get_related_topics(self, topic_description: str) -> List[Dict[str, Any]]:
        """
        Get topics related to a given topic through practices.
        
        Args:
            topic_description: Description of the topic
            
        Returns:
            List of related topics with relationship context
        """
        query = """
        MATCH (t1:Tema {descripcion: $topic_description})<-[:HAS_TEMA]-(p:Practica)-[:HAS_TEMA]->(t2:Tema)
        WHERE t1 <> t2
        RETURN DISTINCT t2.descripcion AS related_topic, p.numeropractica AS practice_number
        ORDER BY practice_number, related_topic
        """
        try:
            results = self.connection.execute_query(query, {"topic_description": topic_description})
            return [dict(record) for record in results]
        except Exception as e:
            logger.error(f"Failed to get related topics for '{topic_description}': {e}")
            return []
    
    def get_topic_practice_path(self, topic_description: str) -> List[Dict[str, Any]]:
        """
        Get the learning path from topic to practices and exercises.
        
        Args:
            topic_description: Description of the topic
            
        Returns:
            List showing topic -> practice -> section -> exercise path
        """
        query = """
        MATCH path = (t:Tema {descripcion: $topic_description})<-[:HAS_TEMA]-(p:Practica)
                     -[:HAS_SECCION]->(s:SeccionPractica)-[:HAS_EJERCICIO]->(e:Ejercicio)
        RETURN t.descripcion AS topic, p.numeropractica AS practice_number,
               s.numero AS section_number, s.enunciado AS section_statement,
               e.numero AS exercise_number, e.enunciado AS exercise_statement
        ORDER BY practice_number, section_number, exercise_number
        """
        try:
            results = self.connection.execute_query(query, {"topic_description": topic_description})
            return [dict(record) for record in results]
        except Exception as e:
            logger.error(f"Failed to get practice path for topic '{topic_description}': {e}")
            return []
    
    # ==================== UTILITY METHODS ====================
    
    def get_node_count_by_type(self) -> Dict[str, int]:
        """
        Get count of nodes by type/label.
        
        Returns:
            Dictionary mapping node types to counts
        """
        query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {}) YIELD value
        RETURN label, value.count AS count
        ORDER BY label
        """
        try:
            results = self.connection.execute_query(query)
            return {record["label"]: record["count"] for record in results}
        except Exception as e:
            logger.error(f"Failed to get node counts: {e}")
            # Fallback to individual queries if APOC is not available
            labels = ["Materia", "Carrera", "Profesor", "ObjetivoMateria", "UnidadTematica", 
                     "Tema", "Practica", "Tip", "SeccionPractica", "Ejercicio", "Respuesta"]
            counts = {}
            for label in labels:
                try:
                    result = self.connection.execute_query(f"MATCH (n:{label}) RETURN count(n) as count")
                    counts[label] = result[0]["count"] if result else 0
                except Exception:
                    counts[label] = 0
            return counts
    
    def validate_graph_structure(self) -> Dict[str, Any]:
        """
        Validate the knowledge graph structure and return health metrics.
        
        Returns:
            Dictionary with validation results
        """
        validations = {}
        
        try:
            # Check for orphaned nodes
            orphaned_query = """
            MATCH (n) WHERE NOT (n)--() 
            RETURN labels(n) AS labels, count(n) AS count
            """
            orphaned = self.connection.execute_query(orphaned_query)
            validations["orphaned_nodes"] = [dict(record) for record in orphaned]
            
            # Check for missing relationships
            missing_rel_query = """
            MATCH (m:Materia) WHERE NOT (m)-[:HAS_UNIDAD_TEMATICA]->()
            RETURN count(m) AS subjects_without_units
            """
            missing_rel = self.connection.execute_query(missing_rel_query)
            validations["subjects_without_units"] = missing_rel[0]["subjects_without_units"] if missing_rel else 0
            
            # Check for practices without exercises
            practices_no_exercises_query = """
            MATCH (p:Practica) WHERE NOT (p)-[:HAS_SECCION]->()-[:HAS_EJERCICIO]->()
            RETURN count(p) AS practices_without_exercises
            """
            practices_no_ex = self.connection.execute_query(practices_no_exercises_query)
            validations["practices_without_exercises"] = practices_no_ex[0]["practices_without_exercises"] if practices_no_ex else 0
            
            validations["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Failed to validate graph structure: {e}")
            validations["status"] = "error"
            validations["error"] = str(e)
        
        return validations