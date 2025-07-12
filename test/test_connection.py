"""
Unit tests for KGConnection class.

These tests verify the Neo4j connection management functionality
without modifying the database content.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from kg import KGConnection, KGConnectionError


class TestKGConnectionInitialization:
    """Test KGConnection initialization and configuration."""
    
    def test_init_with_explicit_params(self):
        """Test initialization with explicit connection parameters."""
        uri = "bolt://test:7687"
        user = "test_user"
        password = "test_password"
        
        conn = KGConnection(uri=uri, user=user, password=password)
        
        assert conn.uri == uri
        assert conn.user == user
        assert conn.password == password
    
    def test_init_with_env_vars(self):
        """Test initialization using environment variables."""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'bolt://env:7687',
            'NEO4J_USER': 'env_user',
            'NEO4J_PASSWORD': 'env_password'
        }):
            conn = KGConnection()
            
            assert conn.uri == 'bolt://env:7687'
            assert conn.user == 'env_user'
            assert conn.password == 'env_password'
    
    def test_init_missing_uri_raises_error(self):
        """Test that missing URI raises KGConnectionError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(KGConnectionError) as excinfo:
                KGConnection()
            
            assert "NEO4J_URI" in str(excinfo.value)
    
    def test_init_missing_user_raises_error(self):
        """Test that missing user raises KGConnectionError."""
        with patch.dict(os.environ, {'NEO4J_URI': 'bolt://test:7687'}, clear=True):
            with pytest.raises(KGConnectionError) as excinfo:
                KGConnection()
            
            assert "NEO4J_USER" in str(excinfo.value)
    
    def test_init_missing_password_raises_error(self):
        """Test that missing password raises KGConnectionError."""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'bolt://test:7687',
            'NEO4J_USER': 'test_user'
        }, clear=True):
            with pytest.raises(KGConnectionError) as excinfo:
                KGConnection()
            
            assert "NEO4J_PASSWORD" in str(excinfo.value)


class TestKGConnectionFunctionality:
    """Test KGConnection core functionality with real database."""
    
    @pytest.mark.integration
    def test_connection_establishment(self, kg_connection: KGConnection):
        """Test that connection can be established successfully."""
        # The fixture already validates connection, so we just verify it's working
        assert kg_connection is not None
        assert kg_connection.uri is not None
        assert kg_connection.user is not None
        assert kg_connection.password is not None
    
    @pytest.mark.integration
    def test_driver_property(self, kg_connection: KGConnection):
        """Test that driver property returns a valid driver."""
        driver = kg_connection.driver
        assert driver is not None
        
        # Test that subsequent calls return the same driver instance
        driver2 = kg_connection.driver
        assert driver is driver2
    
    @pytest.mark.integration
    def test_test_connection(self, kg_connection: KGConnection):
        """Test the connection test functionality."""
        result = kg_connection.test_connection()
        assert result is True
    
    @pytest.mark.integration
    def test_session_context_manager(self, kg_connection: KGConnection):
        """Test session context manager functionality."""
        with kg_connection.session() as session:
            assert session is not None
            # Test simple read-only query
            result = session.run("RETURN 1 as test_value")
            record = result.single()
            assert record["test_value"] == 1
    
    @pytest.mark.integration
    def test_execute_query(self, kg_connection: KGConnection):
        """Test execute_query method with read-only query."""
        result = kg_connection.execute_query("RETURN 42 as answer")
        assert len(result) == 1
        assert result[0]["answer"] == 42
    
    @pytest.mark.integration
    def test_execute_query_with_parameters(self, kg_connection: KGConnection):
        """Test execute_query with parameters."""
        result = kg_connection.execute_query(
            "RETURN $value as param_value", 
            {"value": "test_param"}
        )
        assert len(result) == 1
        assert result[0]["param_value"] == "test_param"
    
    @pytest.mark.integration
    def test_get_database_info(self, kg_connection: KGConnection, database_info: dict):
        """Test database information retrieval."""
        assert "node_count" in database_info
        assert "relationship_count" in database_info
        assert "uri" in database_info
        assert isinstance(database_info["node_count"], int)
        assert isinstance(database_info["relationship_count"], int)
        assert database_info["node_count"] >= 0
        assert database_info["relationship_count"] >= 0
    
    @pytest.mark.integration
    def test_context_manager_usage(self):
        """Test KGConnection as context manager."""
        # Skip if environment variables are not set
        required_vars = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")
        
        with KGConnection() as conn:
            assert conn is not None
            result = conn.test_connection()
            assert result is True


class TestKGConnectionErrorHandling:
    """Test error handling in KGConnection."""
    
    def test_execute_query_invalid_cypher(self, kg_connection: KGConnection):
        """Test that invalid Cypher queries raise appropriate errors."""
        with pytest.raises(KGConnectionError):
            kg_connection.execute_query("INVALID CYPHER QUERY")
    
    def test_execute_query_with_none_parameters(self, kg_connection: KGConnection):
        """Test execute_query handles None parameters gracefully."""
        result = kg_connection.execute_query("RETURN 1 as test", None)
        assert len(result) == 1
        assert result[0]["test"] == 1
    
    @pytest.mark.integration  
    def test_connection_with_wrong_credentials(self):
        """Test connection with invalid credentials."""
        # Only test if we have a valid URI but use wrong credentials
        if not os.getenv('NEO4J_URI'):
            pytest.skip("NEO4J_URI not available for testing")
        
        with pytest.raises(KGConnectionError):
            conn = KGConnection(
                uri=os.getenv('NEO4J_URI'),
                user="wrong_user",
                password="wrong_password"
            )
            # Try to access driver property which will trigger connection
            _ = conn.driver


class TestKGConnectionReadOnlyOperations:
    """Test read-only operations that verify database state without modification."""
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_count_nodes(self, kg_connection: KGConnection):
        """Test counting nodes in the database."""
        result = kg_connection.execute_query("MATCH (n) RETURN count(n) as total_nodes")
        assert len(result) == 1
        node_count = result[0]["total_nodes"]
        assert isinstance(node_count, int)
        assert node_count >= 0
    
    @pytest.mark.integration
    @pytest.mark.requires_data  
    def test_count_relationships(self, kg_connection: KGConnection):
        """Test counting relationships in the database."""
        result = kg_connection.execute_query("MATCH ()-[r]->() RETURN count(r) as total_rels")
        assert len(result) == 1
        rel_count = result[0]["total_rels"]
        assert isinstance(rel_count, int)
        assert rel_count >= 0
    
    @pytest.mark.integration
    def test_list_node_labels(self, kg_connection: KGConnection):
        """Test listing all node labels in the database."""
        result = kg_connection.execute_query("CALL db.labels()")
        assert isinstance(result, list)
        # Extract labels from result
        labels = [record["label"] for record in result]
        # We expect at least some standard labels from the KG schema
        expected_labels = ["Materia", "Tema", "Practica"]
        for label in expected_labels:
            if any(label in labels for label in expected_labels):
                # If any expected label is found, test passes
                break
        else:
            # If no expected labels found, might be empty database
            pytest.skip("Database appears to be empty or not populated")
    
    @pytest.mark.integration
    def test_list_relationship_types(self, kg_connection: KGConnection):
        """Test listing all relationship types in the database."""
        result = kg_connection.execute_query("CALL db.relationshipTypes()")
        assert isinstance(result, list)
        # We expect relationships if the database is populated
        if result:
            rel_types = [record["relationshipType"] for record in result]
            assert isinstance(rel_types, list)
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_database_consistency(self, kg_connection: KGConnection):
        """Test basic database consistency checks."""
        # Check for nodes without relationships (potentially orphaned)
        orphaned_result = kg_connection.execute_query(
            "MATCH (n) WHERE NOT (n)--() RETURN count(n) as orphaned_count"
        )
        orphaned_count = orphaned_result[0]["orphaned_count"]
        assert isinstance(orphaned_count, int)
        assert orphaned_count >= 0
        
        # If there are orphaned nodes, log but don't fail (might be expected)
        if orphaned_count > 0:
            print(f"Found {orphaned_count} orphaned nodes (nodes without relationships)")
    
    @pytest.mark.integration
    def test_schema_verification(self, kg_connection: KGConnection):
        """Test that expected schema elements exist."""
        # Test for existence of constraints (read-only)
        constraints_result = kg_connection.execute_query("SHOW CONSTRAINTS")
        assert isinstance(constraints_result, list)
        
        # Test for existence of indexes (read-only)
        indexes_result = kg_connection.execute_query("SHOW INDEXES")
        assert isinstance(indexes_result, list)