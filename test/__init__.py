"""
Test package for Luca KG modules.

This package contains unit tests for the knowledge graph abstraction layer.
Tests are designed to be read-only and will not modify the Neo4j database.

Test structure:
- test_connection.py: Tests for KGConnection class
- test_queries.py: Tests for KGQueryInterface class
- conftest.py: Pytest fixtures and configuration

Prerequisites for running tests:
- Neo4j database running with test data
- Environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- pytest and pytest dependencies installed

Run tests with:
    pytest test/
    pytest test/test_connection.py -v
    pytest test/test_queries.py -v
"""