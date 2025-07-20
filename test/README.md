# KG Module Tests

This directory contains unit and integration tests for the Luca Knowledge Graph (KG) modules.

## Overview

The test suite validates the functionality of:
- **KGConnection**: Neo4j connection management
- **KGQueryInterface**: High-level query abstractions

All tests are designed to be **read-only** and will not modify the Neo4j database content.

## Prerequisites

### 1. Environment Setup
Ensure you have the required environment variables set (via `.envrc` or direct export):
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
```

### 2. Database Requirements
- Neo4j database running and accessible
- Knowledge graph populated with test data (see `db/create_kg.py`)
- Database should contain the expected schema (Materia, Tema, Practica, etc.)

### 3. Dependencies
Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
# OR using uv
uv sync
```

## Running Tests

### Run All Tests
```bash
pytest test/
```

### Run Specific Test Files
```bash
pytest test/test_connection.py -v
pytest test/test_queries.py -v
```

### Run Tests by Marker
```bash
# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run only tests that require specific data
pytest -m requires_data
```

### Run with Coverage
```bash
pytest --cov=kg --cov-report=html
```

## Test Structure

### `test_connection.py`
Tests for the `KGConnection` class:
- ✅ Connection initialization with environment variables
- ✅ Driver creation and session management
- ✅ Error handling for invalid credentials
- ✅ Read-only database operations
- ✅ Context manager functionality

### `test_queries.py`
Tests for the `KGQueryInterface` class:
- ✅ Course structure queries (subjects, topics, objectives)
- ✅ Practice and exercise retrieval
- ✅ Search functionality
- ✅ Relationship and path queries
- ✅ Utility methods and validation
- ✅ Error handling

### `conftest.py`
Shared fixtures and configuration:
- Session-scoped connection fixtures
- Data validation helpers
- Test markers and configuration

## Test Categories

### Unit Tests
- Test individual methods in isolation
- Mock external dependencies where appropriate
- Fast execution, no database required for basic functionality

### Integration Tests
- Test against real Neo4j database
- Marked with `@pytest.mark.integration`
- Require database connection and may be slower

### Data-Dependent Tests
- Test functionality that requires specific data in the database
- Marked with `@pytest.mark.requires_data`
- Automatically skipped if insufficient test data

## Test Safety

🛡️ **All tests are read-only and safe**:
- No data modification operations
- No deletion or creation of nodes/relationships
- Only `MATCH`, `RETURN`, `COUNT`, and similar read operations
- Database state remains unchanged after test execution

## Troubleshooting

### Tests Skipped Due to Missing Environment Variables
Ensure NEO4J_* environment variables are properly set:
```bash
# Check environment variables
echo $NEO4J_URI
echo $NEO4J_USERNAME
echo $NEO4J_PASSWORD
```

### Tests Skipped Due to Database Connection
1. Verify Neo4j is running: `docker ps` or check Neo4j service
2. Test connection manually: `python kg/example.py`
3. Check network connectivity and firewall settings

### Tests Skipped Due to Insufficient Data
The database needs to be populated with knowledge graph data:
```bash
# Create knowledge graph from Excel sources
python db/create_kg.py
```

### Coverage Issues
If coverage is below threshold (80%), identify untested code:
```bash
pytest --cov=kg --cov-report=html
# Open htmlcov/index.html in browser
```

## Example Test Execution

```bash
# Complete test run with coverage
pytest test/ -v --cov=kg --cov-report=term-missing

# Quick smoke test (skip slow tests)
pytest test/ -m "not slow" -v

# Test specific functionality
pytest test/test_queries.py::TestCourseStructureQueries -v

# Debug failing test
pytest test/test_connection.py::TestKGConnectionFunctionality::test_connection_establishment -v -s
```

## Test Data Requirements

For comprehensive testing, the database should contain:
- At least 1 `Materia` (subject)
- At least 1 `UnidadTematica` (thematic unit)
- At least 1 `Tema` (topic)
- At least 1 `Practica` (practice)
- Proper relationships between these entities

Tests will automatically skip or adapt based on available data.