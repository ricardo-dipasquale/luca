"""
Pytest configuration and fixtures for KG module testing.

This module provides shared fixtures and configuration for testing
the knowledge graph abstraction layer.
"""

import pytest
import os
import logging
from typing import Generator

from kg import KGConnection, KGQueryInterface, KGConnectionError


# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def kg_connection() -> Generator[KGConnection, None, None]:
    """
    Session-scoped fixture providing a KGConnection instance.
    
    This fixture creates a single connection that is reused across all tests
    in the session to improve performance.
    
    Yields:
        KGConnection: Active connection to Neo4j
        
    Raises:
        pytest.skip: If connection cannot be established or env vars missing
    """
    # Check if required environment variables are present
    required_vars = ['NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        with KGConnection() as conn:
            # Test the connection before yielding
            if not conn.test_connection():
                pytest.skip("Neo4j connection test failed")
            
            logger.info("KG connection established for testing")
            yield conn
            
    except KGConnectionError as e:
        pytest.skip(f"Could not establish KG connection: {e}")
    except Exception as e:
        pytest.skip(f"Unexpected error connecting to KG: {e}")


@pytest.fixture(scope="session")
def kg_interface(kg_connection: KGConnection) -> KGQueryInterface:
    """
    Session-scoped fixture providing a KGQueryInterface instance.
    
    Args:
        kg_connection: KGConnection fixture dependency
        
    Returns:
        KGQueryInterface: Query interface for the knowledge graph
    """
    return KGQueryInterface(kg_connection)


@pytest.fixture(scope="session") 
def database_info(kg_connection: KGConnection) -> dict:
    """
    Session-scoped fixture providing database information.
    
    Args:
        kg_connection: KGConnection fixture dependency
        
    Returns:
        dict: Database information including node counts, version, etc.
    """
    return kg_connection.get_database_info()


@pytest.fixture(scope="session")
def node_counts(kg_interface: KGQueryInterface) -> dict:
    """
    Session-scoped fixture providing node counts by type.
    
    Args:
        kg_interface: KGQueryInterface fixture dependency
        
    Returns:
        dict: Mapping of node types to their counts
    """
    return kg_interface.get_node_count_by_type()


@pytest.fixture
def sample_subject_name(kg_interface: KGQueryInterface) -> str:
    """
    Fixture providing the name of a sample subject for testing.
    
    Args:
        kg_interface: KGQueryInterface fixture dependency
        
    Returns:
        str: Name of the first available subject
        
    Raises:
        pytest.skip: If no subjects are found in the database
    """
    subjects = kg_interface.get_subjects()
    if not subjects:
        pytest.skip("No subjects found in database")
    
    return subjects[0]['name']


@pytest.fixture
def sample_practice_number(kg_interface: KGQueryInterface) -> int:
    """
    Fixture providing a sample practice number for testing.
    
    Args:
        kg_interface: KGQueryInterface fixture dependency
        
    Returns:
        int: Number of the first available practice
        
    Raises:
        pytest.skip: If no practices are found in the database
    """
    practices = kg_interface.get_practices()
    if not practices:
        pytest.skip("No practices found in database")
    
    return practices[0]['number']


class TestDataValidation:
    """
    Helper class for validating test data assumptions.
    """
    
    @staticmethod
    def has_minimal_data(node_counts: dict) -> bool:
        """
        Check if database has minimal required data for testing.
        
        Args:
            node_counts: Dictionary of node counts by type
            
        Returns:
            bool: True if minimal data requirements are met
        """
        required_nodes = {
            'Materia': 1,
            'UnidadTematica': 1, 
            'Tema': 1,
            'Practica': 1
        }
        
        for node_type, min_count in required_nodes.items():
            if node_counts.get(node_type, 0) < min_count:
                return False
        
        return True
    
    @staticmethod
    def validate_test_environment(node_counts: dict) -> None:
        """
        Validate that the test environment has sufficient data.
        
        Args:
            node_counts: Dictionary of node counts by type
            
        Raises:
            pytest.skip: If test environment validation fails
        """
        if not TestDataValidation.has_minimal_data(node_counts):
            pytest.skip(
                "Insufficient test data in database. "
                f"Node counts: {node_counts}. "
                "Please ensure the knowledge graph is populated with test data."
            )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "requires_data: mark test as requiring specific data in the database"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )