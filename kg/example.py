#!/usr/bin/env python3
"""
Example usage of the KG abstraction layer.

This script demonstrates how to use the KGConnection and KGQueryInterface
classes to interact with the Luca knowledge graph.

Prerequisites:
- Neo4j database running with knowledge graph data
- Environment variables set: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""

import logging
from kg import KGConnection, KGQueryInterface, KGConnectionError


def main():
    """Demonstrate KG abstraction layer usage."""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize connection (uses environment variables)
        with KGConnection() as conn:
            logger.info("Connected to Neo4j successfully")
            
            # Test connection
            if not conn.test_connection():
                logger.error("Connection test failed")
                return
            
            # Get database info
            db_info = conn.get_database_info()
            logger.info(f"Database info: {db_info}")
            
            # Initialize query interface
            kg = KGQueryInterface(conn)
            
            # Example 1: Get all subjects
            logger.info("\n=== SUBJECTS ===")
            subjects = kg.get_subjects()
            for subject in subjects:
                logger.info(f"Subject: {subject}")
            
            # Example 2: Get node counts
            logger.info("\n=== NODE COUNTS ===")
            counts = kg.get_node_count_by_type()
            for node_type, count in counts.items():
                logger.info(f"{node_type}: {count} nodes")
            
            # Example 3: Get topics for first subject (if available)
            if subjects:
                subject_name = subjects[0]['name']
                logger.info(f"\n=== TOPICS FOR {subject_name} ===")
                topics = kg.get_subject_topics(subject_name)
                for topic in topics[:5]:  # Show first 5
                    logger.info(f"Unit {topic['unit_number']}: {topic['topic_description']}")
            
            # Example 4: Get all practices
            logger.info("\n=== PRACTICES ===")
            practices = kg.get_practices()
            for practice in practices[:3]:  # Show first 3
                logger.info(f"Practice {practice['number']}: {practice.get('description', 'No description')}")
            
            # Example 5: Get exercises for first practice (if available)
            if practices:
                practice_num = practices[0]['number']
                logger.info(f"\n=== EXERCISES FOR PRACTICE {practice_num} ===")
                exercises = kg.get_practice_exercises(practice_num)
                for exercise in exercises[:3]:  # Show first 3
                    logger.info(f"Section {exercise['section_number']}, Exercise {exercise['exercise_number']}")
                    logger.info(f"  Statement: {exercise['exercise_statement'][:100]}...")
            
            # Example 6: Search by text
            logger.info("\n=== TEXT SEARCH ===")
            search_results = kg.search_by_text("relacional", limit=5)
            for result in search_results:
                logger.info(f"Found: {result}")
            
            # Example 7: Validate graph structure
            logger.info("\n=== GRAPH VALIDATION ===")
            validation = kg.validate_graph_structure()
            logger.info(f"Validation status: {validation.get('status')}")
            if validation.get('orphaned_nodes'):
                logger.info(f"Orphaned nodes: {validation['orphaned_nodes']}")
            
            logger.info("\nKG abstraction layer demo completed successfully!")
            
    except KGConnectionError as e:
        logger.error(f"KG Connection error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()