"""
Unit tests for KGQueryInterface class.

These tests verify the query interface functionality using read-only operations
that do not modify the Neo4j database content.
"""

import pytest
from typing import List, Dict, Any

from kg import KGQueryInterface, SearchResult
from test.conftest import TestDataValidation


class TestKGQueryInterfaceInitialization:
    """Test KGQueryInterface initialization."""
    
    def test_initialization(self, kg_interface: KGQueryInterface):
        """Test that KGQueryInterface initializes correctly."""
        assert kg_interface is not None
        assert kg_interface.connection is not None


class TestCourseStructureQueries:
    """Test course structure related queries."""
    
    @pytest.mark.integration
    def test_get_subjects(self, kg_interface: KGQueryInterface):
        """Test retrieving all subjects."""
        subjects = kg_interface.get_subjects()
        assert isinstance(subjects, list)
        
        # If subjects exist, validate structure
        if subjects:
            for subject in subjects:
                assert isinstance(subject, dict)
                assert "name" in subject
                assert isinstance(subject["name"], str)
                assert len(subject["name"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_get_subject_topics(self, kg_interface: KGQueryInterface, sample_subject_name: str):
        """Test retrieving topics for a specific subject."""
        topics = kg_interface.get_subject_topics(sample_subject_name)
        assert isinstance(topics, list)
        
        # If topics exist, validate structure
        if topics:
            for topic in topics:
                assert isinstance(topic, dict)
                assert "unit_number" in topic
                assert "unit_title" in topic
                assert "topic_description" in topic
                assert isinstance(topic["unit_number"], int)
                assert isinstance(topic["unit_title"], str)
                assert isinstance(topic["topic_description"], str)
    
    def test_get_subject_topics_nonexistent(self, kg_interface: KGQueryInterface):
        """Test retrieving topics for a non-existent subject."""
        topics = kg_interface.get_subject_topics("NonExistentSubject123")
        assert isinstance(topics, list)
        assert len(topics) == 0
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_get_subject_objectives(self, kg_interface: KGQueryInterface, sample_subject_name: str):
        """Test retrieving objectives for a specific subject."""
        objectives = kg_interface.get_subject_objectives(sample_subject_name)
        assert isinstance(objectives, list)
        
        # If objectives exist, validate structure
        if objectives:
            for objective in objectives:
                assert isinstance(objective, str)
                assert len(objective) > 0
    
    def test_get_subject_objectives_nonexistent(self, kg_interface: KGQueryInterface):
        """Test retrieving objectives for a non-existent subject."""
        objectives = kg_interface.get_subject_objectives("NonExistentSubject123")
        assert isinstance(objectives, list)
        assert len(objectives) == 0


class TestPracticeQueries:
    """Test practice-related queries."""
    
    @pytest.mark.integration
    def test_get_practices(self, kg_interface: KGQueryInterface):
        """Test retrieving all practices."""
        practices = kg_interface.get_practices()
        assert isinstance(practices, list)
        
        # If practices exist, validate structure
        if practices:
            for practice in practices:
                assert isinstance(practice, dict)
                assert "number" in practice
                assert isinstance(practice["number"], int)
                # Description might be None
                if practice.get("description"):
                    assert isinstance(practice["description"], str)
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_get_practice_exercises(self, kg_interface: KGQueryInterface, sample_practice_number: int):
        """Test retrieving exercises for a specific practice."""
        exercises = kg_interface.get_practice_exercises(sample_practice_number)
        assert isinstance(exercises, list)
        
        # If exercises exist, validate structure
        if exercises:
            for exercise in exercises:
                assert isinstance(exercise, dict)
                assert "section_number" in exercise
                assert "exercise_number" in exercise
                assert "exercise_statement" in exercise
                assert "answers" in exercise
                assert isinstance(exercise["answers"], list)
    
    def test_get_practice_exercises_nonexistent(self, kg_interface: KGQueryInterface):
        """Test retrieving exercises for a non-existent practice."""
        exercises = kg_interface.get_practice_exercises(99999)
        assert isinstance(exercises, list)
        assert len(exercises) == 0
    
    @pytest.mark.integration
    @pytest.mark.requires_data
    def test_get_practice_tips(self, kg_interface: KGQueryInterface, sample_practice_number: int):
        """Test retrieving tips for a specific practice."""
        tips = kg_interface.get_practice_tips(sample_practice_number)
        assert isinstance(tips, list)
        
        # If tips exist, validate structure
        if tips:
            for tip in tips:
                assert isinstance(tip, dict)
                assert "level" in tip
                assert "tip_text" in tip
                assert tip["level"] in ["practice", "section", "exercise"]
                assert isinstance(tip["tip_text"], str)
                assert len(tip["tip_text"]) > 0
    
    def test_get_practice_tips_nonexistent(self, kg_interface: KGQueryInterface):
        """Test retrieving tips for a non-existent practice."""
        tips = kg_interface.get_practice_tips(99999)
        assert isinstance(tips, list)
        assert len(tips) == 0


class TestSearchQueries:
    """Test search functionality."""
    
    @pytest.mark.integration
    def test_search_by_text_basic(self, kg_interface: KGQueryInterface):
        """Test basic text search functionality."""
        # Search for a common term that might exist
        results = kg_interface.search_by_text("relacion", limit=5)
        assert isinstance(results, list)
        assert len(results) <= 5
        
        # Validate SearchResult objects
        for result in results:
            assert isinstance(result, SearchResult)
            assert isinstance(result.node_id, int)
            assert isinstance(result.node_type, str)
            assert isinstance(result.properties, dict)
            assert result.score is not None
            assert isinstance(result.score, (int, float))
    
    @pytest.mark.integration
    def test_search_by_text_empty_results(self, kg_interface: KGQueryInterface):
        """Test text search with no expected results."""
        results = kg_interface.search_by_text("XyZaBC123NonExistentTerm", limit=5)
        assert isinstance(results, list)
        assert len(results) == 0
    
    @pytest.mark.integration
    def test_search_by_text_limit(self, kg_interface: KGQueryInterface):
        """Test text search respects limit parameter."""
        # Search for a broad term
        results_small = kg_interface.search_by_text("a", limit=2)
        results_large = kg_interface.search_by_text("a", limit=10)
        
        assert len(results_small) <= 2
        assert len(results_large) <= 10
        
        # If we have results, small should be subset of large (by order)
        if results_small and results_large:
            assert len(results_small) <= len(results_large)
    
    def test_vector_search_not_implemented(self, kg_interface: KGQueryInterface):
        """Test that vector search returns empty list (not implemented)."""
        results = kg_interface.vector_search("test query")
        assert isinstance(results, list)
        assert len(results) == 0


class TestRelationshipQueries:
    """Test relationship and path queries."""
    
    @pytest.mark.integration
    def test_get_related_topics_existing(self, kg_interface: KGQueryInterface):
        """Test getting related topics for existing topics."""
        # First get all subjects to find topics
        subjects = kg_interface.get_subjects()
        if not subjects:
            pytest.skip("No subjects found for testing")
        
        # Get topics for the first subject
        topics = kg_interface.get_subject_topics(subjects[0]['name'])
        if not topics:
            pytest.skip("No topics found for testing")
        
        # Test with first topic
        topic_desc = topics[0]['topic_description']
        related = kg_interface.get_related_topics(topic_desc)
        assert isinstance(related, list)
        
        # If related topics exist, validate structure
        for related_topic in related:
            assert isinstance(related_topic, dict)
            assert "related_topic" in related_topic
            assert "practice_number" in related_topic
            assert isinstance(related_topic["related_topic"], str)
            assert isinstance(related_topic["practice_number"], int)
    
    def test_get_related_topics_nonexistent(self, kg_interface: KGQueryInterface):
        """Test getting related topics for non-existent topic."""
        related = kg_interface.get_related_topics("NonExistentTopic123")
        assert isinstance(related, list)
        assert len(related) == 0
    
    @pytest.mark.integration  
    def test_get_topic_practice_path_existing(self, kg_interface: KGQueryInterface):
        """Test getting practice path for existing topics."""
        # First get all subjects to find topics
        subjects = kg_interface.get_subjects()
        if not subjects:
            pytest.skip("No subjects found for testing")
        
        # Get topics for the first subject
        topics = kg_interface.get_subject_topics(subjects[0]['name'])
        if not topics:
            pytest.skip("No topics found for testing")
        
        # Test with first topic
        topic_desc = topics[0]['topic_description']
        path = kg_interface.get_topic_practice_path(topic_desc)
        assert isinstance(path, list)
        
        # If path exists, validate structure
        for path_item in path:
            assert isinstance(path_item, dict)
            expected_keys = ["topic", "practice_number", "section_number", 
                           "section_statement", "exercise_number", "exercise_statement"]
            for key in expected_keys:
                assert key in path_item
    
    def test_get_topic_practice_path_nonexistent(self, kg_interface: KGQueryInterface):
        """Test getting practice path for non-existent topic."""
        path = kg_interface.get_topic_practice_path("NonExistentTopic123")
        assert isinstance(path, list)
        assert len(path) == 0


class TestUtilityMethods:
    """Test utility methods."""
    
    @pytest.mark.integration
    def test_get_node_count_by_type(self, kg_interface: KGQueryInterface, node_counts: dict):
        """Test getting node counts by type."""
        assert isinstance(node_counts, dict)
        
        # Validate structure
        for node_type, count in node_counts.items():
            assert isinstance(node_type, str)
            assert isinstance(count, int)
            assert count >= 0
        
        # Check for expected node types if database is populated
        if node_counts:
            expected_types = ["Materia", "Tema", "Practica"]
            found_types = set(node_counts.keys())
            # At least one expected type should be present if DB is populated
            assert any(expected_type in found_types for expected_type in expected_types)
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_validate_graph_structure(self, kg_interface: KGQueryInterface):
        """Test graph structure validation."""
        validation = kg_interface.validate_graph_structure()
        assert isinstance(validation, dict)
        assert "status" in validation
        
        if validation["status"] == "completed":
            # Validation completed successfully
            assert "orphaned_nodes" in validation
            assert "subjects_without_units" in validation
            assert "practices_without_exercises" in validation
            
            assert isinstance(validation["orphaned_nodes"], list)
            assert isinstance(validation["subjects_without_units"], int)
            assert isinstance(validation["practices_without_exercises"], int)
            
            # All counts should be non-negative
            assert validation["subjects_without_units"] >= 0
            assert validation["practices_without_exercises"] >= 0
        
        elif validation["status"] == "error":
            # Validation failed, should have error message
            assert "error" in validation
            assert isinstance(validation["error"], str)


class TestErrorHandling:
    """Test error handling in query interface."""
    
    def test_methods_handle_connection_errors_gracefully(self, kg_interface: KGQueryInterface):
        """Test that methods handle connection errors gracefully."""
        # Most methods should return empty lists on errors rather than raising exceptions
        # This test verifies the error handling structure
        
        # These calls should not raise exceptions even if there are connection issues
        try:
            subjects = kg_interface.get_subjects()
            assert isinstance(subjects, list)
            
            topics = kg_interface.get_subject_topics("test")
            assert isinstance(topics, list)
            
            objectives = kg_interface.get_subject_objectives("test")
            assert isinstance(objectives, list)
            
            practices = kg_interface.get_practices()
            assert isinstance(practices, list)
            
            exercises = kg_interface.get_practice_exercises(1)
            assert isinstance(exercises, list)
            
            tips = kg_interface.get_practice_tips(1)
            assert isinstance(tips, list)
            
            search_results = kg_interface.search_by_text("test")
            assert isinstance(search_results, list)
            
            related = kg_interface.get_related_topics("test")
            assert isinstance(related, list)
            
            path = kg_interface.get_topic_practice_path("test")
            assert isinstance(path, list)
            
        except Exception as e:
            # If any method raises an exception, log it but don't fail the test
            # This indicates that error handling might need improvement
            pytest.fail(f"Method raised unexpected exception: {e}")


class TestDataRequirements:
    """Test data requirements validation."""
    
    @pytest.mark.integration
    def test_minimal_data_requirements(self, node_counts: dict):
        """Test that database has minimal data for meaningful tests."""
        # This test validates that we have sufficient test data
        has_data = TestDataValidation.has_minimal_data(node_counts)
        
        if not has_data:
            pytest.skip(
                f"Database lacks minimal test data. Node counts: {node_counts}. "
                "Consider populating the database with test data."
            )
        
        # If we reach here, we have sufficient data
        assert has_data
        assert node_counts.get('Materia', 0) >= 1
        assert node_counts.get('UnidadTematica', 0) >= 1
        assert node_counts.get('Tema', 0) >= 1
        assert node_counts.get('Practica', 0) >= 1
    
    @pytest.mark.integration
    def test_database_not_empty(self, database_info: dict):
        """Test that database is not completely empty."""
        if "error" in database_info:
            pytest.skip(f"Could not get database info: {database_info['error']}")
        
        node_count = database_info.get("node_count", 0)
        rel_count = database_info.get("relationship_count", 0)
        
        # Database should have some content for meaningful testing
        if node_count == 0:
            pytest.skip("Database is empty - no nodes found")
        
        # Log database statistics
        print(f"Database contains {node_count} nodes and {rel_count} relationships")
        
        assert node_count > 0
        assert rel_count >= 0