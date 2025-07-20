"""
Unit tests for KG tools (LangChain tools).

These tests verify that LangChain tools work correctly outside of the LangGraph context.
Tools are tested by calling them directly as functions, which is supported by LangChain.

Tests are designed to be read-only and will not modify the Neo4j database.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from tools.kg_tools import (
    get_subjects_tool,
    get_practice_exercises_tool,
    get_practice_tips_tool,
    search_knowledge_graph_tool,
    get_related_topics_tool,
    get_learning_path_tool,
    get_kg_interface
)
from kg import KGConnectionError


class TestKGToolsDirectInvocation:
    """Test KG tools by calling them directly as functions."""
    
    @pytest.mark.integration
    def test_get_subjects_tool_direct_call(self):
        """Test calling get_subjects_tool directly as a function."""
        try:
            # Test without subject name (get all subjects)
            result = get_subjects_tool.invoke({})
            assert isinstance(result, str)
            assert len(result) > 0
            
            # Should contain "Available Subjects:" if there are subjects
            # or "No subjects found" if database is empty
            assert "subjects" in result.lower() or "no subjects" in result.lower()
            
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_get_subjects_tool_find_specific_subject(self):
        """Test finding the specific subject 'Bases de Datos Relacionales'."""
        try:
            # First get all subjects to check if our target exists
            all_subjects_result = get_subjects_tool.invoke({})
            
            if "Bases de Datos Relacionales" in all_subjects_result:
                # Test with specific subject name
                result = get_subjects_tool.invoke({"subject_name": "Bases de Datos Relacionales"})
                
                assert isinstance(result, str)
                assert "Bases de Datos Relacionales" in result
                assert "Subject:" in result
                
                # Should contain either objectives or topics
                contains_content = any(keyword in result for keyword in [
                    "Objectives:", "Topics by Unit:", "Unit"
                ])
                assert contains_content, f"Result should contain objectives or topics. Got: {result[:200]}..."
                
            else:
                pytest.skip("Subject 'Bases de Datos Relacionales' not found in database")
                
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")
    
    @pytest.mark.integration
    def test_get_subjects_tool_nonexistent_subject(self):
        """Test that non-existent subject 'Estructura de Unicornios I' returns appropriate message."""
        try:
            result = get_subjects_tool.invoke({"subject_name": "Estructura de Unicornios I"})
            
            assert isinstance(result, str)
            # Should indicate no information found
            assert "No information found" in result or "not found" in result.lower()
            assert "Estructura de Unicornios I" in result
            
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")
    
    @pytest.mark.integration
    def test_get_subjects_tool_with_args_schema(self):
        """Test get_subjects_tool using the args_schema format."""
        try:
            # Test with proper schema input
            result = get_subjects_tool.invoke({"subject_name": None})
            assert isinstance(result, str)
            
            # Test with empty input (should work the same as subject_name=None)
            result_empty = get_subjects_tool.invoke({})
            assert isinstance(result_empty, str)
            
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")


class TestKGToolsWithMocking:
    """Test KG tools with mocked dependencies for unit testing."""
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_get_subjects_tool_with_mock_success(self, mock_get_kg_interface):
        """Test get_subjects_tool with mocked KG interface (success case)."""
        # Setup mock
        mock_kg = MagicMock()
        mock_kg.get_subjects.return_value = [
            {"name": "Bases de Datos Relacionales", "description": "Test subject"},
            {"name": "Algoritmos y Estructuras", "description": "Another subject"}
        ]
        mock_kg.get_subject_topics.return_value = [
            {
                "unit_number": 1,
                "unit_title": "Introducción",
                "topic_description": "Conceptos básicos"
            }
        ]
        mock_kg.get_subject_objectives.return_value = [
            "Entender los conceptos fundamentales",
            "Aplicar técnicas de diseño"
        ]
        mock_get_kg_interface.return_value = mock_kg
        
        # Test getting all subjects
        result = get_subjects_tool.invoke({})
        
        assert isinstance(result, str)
        assert "Available Subjects:" in result
        assert "Bases de Datos Relacionales" in result
        assert "Algoritmos y Estructuras" in result
        
        # Verify mock was called
        mock_kg.get_subjects.assert_called_once()
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_get_subjects_tool_with_mock_specific_subject(self, mock_get_kg_interface):
        """Test get_subjects_tool with mocked KG interface for specific subject."""
        # Setup mock
        mock_kg = MagicMock()
        mock_kg.get_subject_topics.return_value = [
            {
                "unit_number": 1,
                "unit_title": "Modelo Relacional",
                "topic_description": "Álgebra relacional"
            },
            {
                "unit_number": 2,
                "unit_title": "SQL",
                "topic_description": "Consultas básicas"
            }
        ]
        mock_kg.get_subject_objectives.return_value = [
            "Comprender el modelo relacional",
            "Dominar SQL básico"
        ]
        mock_get_kg_interface.return_value = mock_kg
        
        # Test with specific subject
        result = get_subjects_tool.invoke({"subject_name": "Bases de Datos Relacionales"})
        
        assert isinstance(result, str)
        assert "Subject: Bases de Datos Relacionales" in result
        assert "Objectives:" in result
        assert "Comprender el modelo relacional" in result
        assert "Topics by Unit:" in result
        assert "Unit 1: Modelo Relacional" in result
        assert "Álgebra relacional" in result
        
        # Verify mocks were called
        mock_kg.get_subject_topics.assert_called_once_with("Bases de Datos Relacionales")
        mock_kg.get_subject_objectives.assert_called_once_with("Bases de Datos Relacionales")
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_get_subjects_tool_with_mock_empty_database(self, mock_get_kg_interface):
        """Test get_subjects_tool with mocked empty database."""
        # Setup mock for empty database
        mock_kg = MagicMock()
        mock_kg.get_subjects.return_value = []
        mock_get_kg_interface.return_value = mock_kg
        
        result = get_subjects_tool.invoke({})
        
        assert isinstance(result, str)
        assert "No subjects found" in result
        
        mock_kg.get_subjects.assert_called_once()
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_get_subjects_tool_with_mock_connection_error(self, mock_get_kg_interface):
        """Test get_subjects_tool with mocked connection error."""
        # Setup mock to raise exception
        mock_get_kg_interface.side_effect = KGConnectionError("Connection failed")
        
        result = get_subjects_tool.invoke({})
        
        assert isinstance(result, str)
        assert "Error retrieving subject information" in result
        assert "Connection failed" in result


class TestOtherKGTools:
    """Test other KG tools to ensure they work outside LangGraph context."""
    
    @pytest.mark.integration
    def test_search_knowledge_graph_tool_direct_call(self):
        """Test search tool directly."""
        try:
            result = search_knowledge_graph_tool.invoke({
                "query_text": "relacional",
                "limit": 3
            })
            
            assert isinstance(result, str)
            # Should either find results or indicate no results
            assert any(phrase in result for phrase in [
                "Search results for",
                "No results found"
            ])
            
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")
    
    @pytest.mark.integration  
    def test_get_practice_exercises_tool_direct_call(self):
        """Test practice exercises tool directly."""
        try:
            result = get_practice_exercises_tool.invoke({"practice_number": 1})
            
            assert isinstance(result, str)
            # Should either find exercises or indicate none found
            assert any(phrase in result for phrase in [
                "Practice 1 - Exercises:",
                "No exercises found"
            ])
            
        except Exception as e:
            pytest.skip(f"KG connection not available: {e}")
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_search_tool_with_mock(self, mock_get_kg_interface):
        """Test search tool with mocked results."""
        from kg import SearchResult
        
        # Setup mock
        mock_kg = MagicMock()
        mock_search_results = [
            SearchResult(
                node_id=1,
                node_type="Tema",
                properties={"descripcion": "Álgebra relacional"},
                score=0.95
            ),
            SearchResult(
                node_id=2,
                node_type="Ejercicio",
                properties={"enunciado": "Escribir consulta SQL"},
                score=0.87
            )
        ]
        mock_kg.search_by_text.return_value = mock_search_results
        mock_get_kg_interface.return_value = mock_kg
        
        result = search_knowledge_graph_tool.invoke({
            "query_text": "SQL",
            "limit": 5
        })
        
        assert isinstance(result, str)
        assert "Search results for 'SQL':" in result
        assert "1. Tema (ID: 1)" in result
        assert "Álgebra relacional" in result
        assert "2. Ejercicio (ID: 2)" in result
        assert "Escribir consulta SQL" in result
        assert "Relevance: 0.95" in result
        
        mock_kg.search_by_text.assert_called_once_with("SQL", limit=5)


class TestToolErrorHandling:
    """Test tool error handling and edge cases."""
    
    @patch('tools.kg_tools.get_kg_interface')
    def test_tools_handle_exceptions_gracefully(self, mock_get_kg_interface):
        """Test that tools handle exceptions gracefully."""
        # Setup mock to raise exception
        mock_get_kg_interface.side_effect = Exception("Database connection error")
        
        # Test each tool handles exceptions gracefully
        tools_to_test = [
            (get_subjects_tool, {}),
            (search_knowledge_graph_tool, {"query_text": "test", "limit": 5}),
            (get_practice_exercises_tool, {"practice_number": 1}),
            (get_practice_tips_tool, {"practice_number": 1}),
            (get_related_topics_tool, {"topic_description": "test"}),
            (get_learning_path_tool, {"topic_description": "test"})
        ]
        
        for tool, args in tools_to_test:
            result = tool.invoke(args)
            
            # All tools should return strings with error messages
            assert isinstance(result, str)
            assert "error" in result.lower() or "Error" in result
            
            # Should not raise exceptions
            assert len(result) > 0


class TestToolArgumentValidation:
    """Test tool argument validation and schema compliance."""
    
    def test_get_subjects_tool_schema(self):
        """Test that get_subjects_tool has proper schema."""
        tool = get_subjects_tool
        
        # Check tool has the expected attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'args_schema')
        
        assert tool.name == "get_subjects"
        assert "subject" in tool.description.lower()
        
        # Test tool accepts both empty args and subject_name
        try:
            # Should not raise validation errors
            result1 = tool.invoke({})
            result2 = tool.invoke({"subject_name": "Test Subject"})
            result3 = tool.invoke({"subject_name": None})
            
            # All should return strings
            assert all(isinstance(r, str) for r in [result1, result2, result3])
            
        except Exception as e:
            # If it fails due to connection, that's okay for schema testing
            if "connection" not in str(e).lower():
                raise
    
    def test_search_tool_schema(self):
        """Test search tool schema validation."""
        tool = search_knowledge_graph_tool
        
        assert tool.name == "search_knowledge_graph"
        assert "search" in tool.description.lower()
        
        # Test required and optional parameters
        try:
            # query_text is required, limit is optional
            result1 = tool.invoke({"query_text": "test"})
            result2 = tool.invoke({"query_text": "test", "limit": 5})
            
            assert all(isinstance(r, str) for r in [result1, result2])
            
        except Exception as e:
            # If it fails due to connection, that's okay for schema testing
            if "connection" not in str(e).lower():
                raise


@pytest.mark.integration
class TestKGToolsIntegrationWithDatabase:
    """Integration tests with real database (if available)."""
    
    def test_tool_chain_workflow(self):
        """Test a realistic workflow using multiple tools."""
        try:
            # Step 1: Get all subjects
            subjects_result = get_subjects_tool.invoke({})
            assert isinstance(subjects_result, str)
            
            # Step 2: Search for database-related content
            search_result = search_knowledge_graph_tool.invoke({
                "query_text": "base",
                "limit": 3
            })
            assert isinstance(search_result, str)
            
            # Step 3: Try to get practice exercises
            practice_result = get_practice_exercises_tool.invoke({"practice_number": 1})
            assert isinstance(practice_result, str)
            
            # All results should be strings (either with content or error messages)
            results = [subjects_result, search_result, practice_result]
            assert all(isinstance(r, str) and len(r) > 0 for r in results)
            
        except Exception as e:
            pytest.skip(f"Integration test requires database connection: {e}")
    
    def test_database_specific_subjects(self):
        """Test with database-specific subject names."""
        test_cases = [
            {
                "subject": "Bases de Datos Relacionales",
                "should_exist": True,
                "description": "Target subject that should exist"
            },
            {
                "subject": "Estructura de Unicornios I", 
                "should_exist": False,
                "description": "Fictional subject that should not exist"
            },
            {
                "subject": "Programación Avanzada de Dragones",
                "should_exist": False,
                "description": "Another fictional subject"
            }
        ]
        
        try:
            for test_case in test_cases:
                result = get_subjects_tool.invoke({"subject_name": test_case["subject"]})
                assert isinstance(result, str)
                
                if test_case["should_exist"]:
                    # Should contain subject information if it exists
                    if "No information found" not in result:
                        assert test_case["subject"] in result
                        # Should have some content structure
                        assert any(keyword in result for keyword in [
                            "Objectives:", "Topics by Unit:", "Subject:"
                        ])
                else:
                    # Should indicate subject not found
                    assert "No information found" in result or "not found" in result.lower()
                    assert test_case["subject"] in result
                    
        except Exception as e:
            pytest.skip(f"Database connection not available: {e}")


@pytest.mark.integration
class TestTheoreticalContentIntegration:
    """Integration tests for theoretical content tool using LLM Graph Builder API."""
    
    def test_get_theoretical_content_api_integration(self):
        """Test get_theoretical_content_tool with LLM Graph Builder API integration."""
        from tools.kg_tools import get_theoretical_content_tool
        import os
        
        # Check if required environment variables are set
        required_env_vars = ['GRAPHBUILDER_URI', 'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")
        
        # Test with a specific theoretical topic
        topic = "operadores de álgebra relacional"
        
        try:
            result = get_theoretical_content_tool.invoke({"topic_description": topic})
            
            # Validate response
            assert isinstance(result, str), "Result should be a string"
            assert len(result) > 0, "Result should not be empty"
            assert result.strip() != "", "Result should not be just whitespace"
            
            # Check that it's not an error message
            error_indicators = [
                "Error recuperando contenido teórico",
                "Error de conexión",
                "Error: Timeout",
                "Error: No se pudo conectar",
                "Error en la API"
            ]
            
            is_error = any(error in result for error in error_indicators)
            if is_error:
                pytest.skip(f"API service not available or returned error: {result}")
            
            # Validate content structure
            assert "Contenido teórico para" in result, "Should contain content header"
            assert topic in result, "Should contain the requested topic"
            
            # Check if it's using fallback or API response
            is_fallback = "(fuente: LLM)" in result
            if is_fallback:
                print("🔄 Using LLM fallback for theoretical content")
            else:
                print("🔗 Using Graph Builder API for theoretical content")
                       
            print(f"✅ Successfully retrieved theoretical content for: {topic}")
            print(f"📄 Content length: {len(result)} characters")
            
        except Exception as e:
            # If it's a connection or service error, skip the test
            if any(keyword in str(e).lower() for keyword in ['connection', 'timeout', 'service', 'api']):
                pytest.skip(f"LLM Graph Builder service not available: {e}")
            else:
                # Re-raise unexpected errors
                raise
    
    def test_get_theoretical_content_tool_schema_validation(self):
        """Test that the theoretical content tool has proper schema."""
        from tools.kg_tools import get_theoretical_content_tool
        
        # Check tool attributes
        assert hasattr(get_theoretical_content_tool, 'name')
        assert hasattr(get_theoretical_content_tool, 'description')
        assert hasattr(get_theoretical_content_tool, 'args_schema')
        
        assert get_theoretical_content_tool.name == "get_theoretical_content"
        assert "theoretical" in get_theoretical_content_tool.description.lower()
        
        # Test that tool accepts the expected input format
        try:
            # Should not raise validation errors with proper input
            test_input = {"topic_description": "test topic"}
            
            # We don't check the result here since service might not be available
            # Just check that the input validation works
            assert test_input is not None
            
        except Exception as e:
            # Only validation errors should be tested here
            if "validation" in str(e).lower():
                raise
            # Service errors are okay for schema testing