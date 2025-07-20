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


class TestSpecificDataValidation:
    """Test specific data validation using practice 2, section '1', exercise 'd'."""
    
    @pytest.mark.integration
    def test_practice_2_exists(self, kg_interface: KGQueryInterface):
        """Test that practice 2 exists in the database."""
        practice_details = kg_interface.get_practice_details(2)
        assert practice_details is not None
        assert practice_details["number"] == 2
        assert practice_details["name"] == "Algebra Relacional"
        assert "álgebra relacional" in practice_details["objectives"].lower()
    
    @pytest.mark.integration
    def test_practice_2_section_1_exists(self, kg_interface: KGQueryInterface):
        """Test that practice 2 has section '1' with exercises."""
        exercises = kg_interface.get_practice_exercises(2)
        assert len(exercises) > 0
        
        # Find section '1'
        section_1_exercises = [ex for ex in exercises if ex["section_number"] == "1"]
        assert len(section_1_exercises) > 0
        
        # Validate section structure
        for exercise in section_1_exercises:
            assert exercise["section_statement"] is not None
            assert len(exercise["section_statement"]) > 0
            assert "esquema relacional" in exercise["section_statement"].lower()
    
    @pytest.mark.integration
    def test_exercise_d_exists_in_practice_2_section_1(self, kg_interface: KGQueryInterface):
        """Test that exercise 'd' exists in practice 2, section '1'."""
        exercise_details = kg_interface.get_exercise_details(2, "1", "d")
        
        assert exercise_details is not None
        assert exercise_details["practice_number"] == 2
        assert exercise_details["practice_name"] == "Algebra Relacional"
        assert exercise_details["section_number"] == "1"
        assert exercise_details["exercise_number"] == "d"
        assert exercise_details["exercise_statement"] == "Nombre de los clientes que no han comprado nada"
        
        # Validate answers exist and contain algebraic notation
        assert len(exercise_details["answers"]) > 0
        found_algebraic_notation = any(
            "π" in answer or "σ" in answer or "⋈" in answer or "−" in answer
            for answer in exercise_details["answers"]
        )
        assert found_algebraic_notation, "Exercise should contain relational algebra notation"
    
    @pytest.mark.integration
    def test_practice_2_all_exercises_in_section_1(self, kg_interface: KGQueryInterface):
        """Test all exercises in practice 2, section '1' including exercise 'd'."""
        exercises = kg_interface.get_practice_exercises(2)
        section_1_exercises = [ex for ex in exercises if ex["section_number"] == "1"]
        
        # Should have multiple exercises including 'd'
        assert len(section_1_exercises) >= 4
        
        exercise_numbers = [ex["exercise_number"] for ex in section_1_exercises]
        assert "d" in exercise_numbers
        assert "a" in exercise_numbers  # Should have other exercises too
        
        # Validate each exercise has required fields
        for exercise in section_1_exercises:
            assert exercise["exercise_statement"] is not None
            assert len(exercise["exercise_statement"]) > 0
            assert isinstance(exercise["answers"], list)
    
    @pytest.mark.integration
    def test_search_finds_exercise_d_content(self, kg_interface: KGQueryInterface):
        """Test that search can find exercise 'd' content."""
        # Search for key terms from exercise 'd'
        results = kg_interface.search_by_text("clientes que no han comprado", limit=10)
        
        # Should find at least one result
        assert len(results) > 0
        
        # At least one result should be an Ejercicio
        exercise_results = [r for r in results if r.node_type == "Ejercicio"]
        assert len(exercise_results) > 0
        
        # Verify we found our specific exercise
        found_exercise_d = False
        for result in exercise_results:
            if "clientes que no han comprado nada" in str(result.properties.get("enunciado", "")).lower():
                found_exercise_d = True
                break
        
        assert found_exercise_d, "Should find exercise 'd' when searching for its content"
    
    @pytest.mark.integration 
    def test_get_related_topics_for_practice_2_topics(self, kg_interface: KGQueryInterface):
        """Test getting related topics for topics used in practice 2."""
        practice_details = kg_interface.get_practice_details(2)
        assert practice_details is not None
        assert len(practice_details["topics"]) > 0
        
        # Test with "Modelo Relacional" topic
        if "Modelo Relacional" in practice_details["topics"]:
            related = kg_interface.get_related_topics("Modelo Relacional")
            # Should find other topics related through practice 2
            practice_2_related = [r for r in related if r["practice_number"] == 2]
            assert len(practice_2_related) > 0
    
    @pytest.mark.integration
    def test_get_topic_practice_path_to_exercise_d(self, kg_interface: KGQueryInterface):
        """Test getting learning path from topics to exercise 'd'."""
        practice_details = kg_interface.get_practice_details(2)
        assert practice_details is not None
        
        # Test with each topic in practice 2
        for topic in practice_details["topics"]:
            path = kg_interface.get_topic_practice_path(topic)
            
            # Find paths that lead to practice 2
            practice_2_paths = [p for p in path if p["practice_number"] == 2]
            
            if practice_2_paths:
                # Should have section '1' and various exercises
                section_1_paths = [p for p in practice_2_paths if p["section_number"] == "1"]
                assert len(section_1_paths) > 0
                
                # Should include exercise 'd'
                exercise_d_paths = [p for p in section_1_paths if p["exercise_number"] == "d"]
                if exercise_d_paths:
                    assert exercise_d_paths[0]["exercise_statement"] == "Nombre de los clientes que no han comprado nada"
    
    @pytest.mark.integration
    def test_get_practice_tips_with_filtering(self, kg_interface: KGQueryInterface):
        """Test the new filtering functionality of get_practice_tips."""
        # Test with practice only
        tips_practice_only = kg_interface.get_practice_tips(2)
        
        # Test with practice + section
        tips_with_section = kg_interface.get_practice_tips(2, "1")
        
        # Test with practice + section + exercise
        tips_with_exercise = kg_interface.get_practice_tips(2, "1", "d")
        
        # Validate filtering logic
        assert len(tips_practice_only) <= len(tips_with_section)
        assert len(tips_with_section) <= len(tips_with_exercise)
        
        # Validate tip levels
        if tips_practice_only:
            practice_levels = {tip["level"] for tip in tips_practice_only}
            assert practice_levels == {"practice"}
        
        if tips_with_section:
            section_levels = {tip["level"] for tip in tips_with_section}
            assert "practice" in section_levels
            # Should include section tips if they exist
            
        if tips_with_exercise:
            exercise_levels = {tip["level"] for tip in tips_with_exercise}
            assert "practice" in exercise_levels
            # Should include exercise tips if they exist
            
            # Check that we get specific tips for exercise 'd'
            exercise_tips = [tip for tip in tips_with_exercise if tip["level"] == "exercise"]
            if exercise_tips:
                # Verify the tips are for the correct exercise
                for tip in exercise_tips:
                    assert tip["section_number"] == "1"
                    assert tip["exercise_number"] == "d"


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