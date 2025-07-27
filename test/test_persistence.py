"""
Tests for Neo4j persistence implementations.

This module tests the Neo4j-based checkpointer and memory store implementations
for LangGraph agent persistence functionality.
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from kg.persistence import Neo4jCheckpointSaver, Neo4jMemoryStore, create_neo4j_persistence
from kg.connection import KGConnection
from langchain_core.runnables import RunnableConfig


class TestNeo4jCheckpointSaver:
    """Test Neo4j checkpointer implementation."""
    
    @pytest.fixture
    def checkpointer(self):
        """Create a Neo4j checkpointer for testing."""
        return Neo4jCheckpointSaver()
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample runnable config."""
        return {
            "configurable": {
                "thread_id": f"test_thread_{uuid4()}",
                "checkpoint_id": f"checkpoint_{uuid4()}"
            }
        }
    
    @pytest.fixture
    def sample_checkpoint(self):
        """Create a sample checkpoint."""
        return {
            "id": f"checkpoint_{uuid4()}",
            "ts": datetime.now().isoformat(),
            "channel_values": {
                "state": {"test_data": "sample_value"},
                "metadata": {"version": "1.0"}
            },
            "channel_versions": {
                "__start__": 1,
                "state": 1
            },
            "versions_seen": {
                "__input__": {},
                "__start__": {"__start__": 1}
            }
        }
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return {
            "source": "test",
            "step": 1,
            "writes": {},
            "thread_id": "test_thread"
        }
    
    @pytest.mark.integration
    def test_checkpointer_initialization(self, checkpointer):
        """Test checkpointer initializes correctly."""
        assert checkpointer is not None
        assert checkpointer.kg is not None
        assert checkpointer.kg.driver is not None
    
    @pytest.mark.integration
    def test_put_and_get_checkpoint(self, checkpointer, sample_config, sample_checkpoint, sample_metadata):
        """Test storing and retrieving a checkpoint."""
        # Store checkpoint
        returned_config = checkpointer.put(sample_config, sample_checkpoint, sample_metadata)
        assert returned_config == sample_config
        
        # Retrieve checkpoint
        checkpoint_tuple = checkpointer.get_tuple(sample_config)
        assert checkpoint_tuple is not None
        assert checkpoint_tuple.config == sample_config
        assert checkpoint_tuple.checkpoint["id"] == sample_checkpoint["id"]
        assert checkpoint_tuple.metadata == sample_metadata
    
    @pytest.mark.integration
    def test_get_nonexistent_checkpoint(self, checkpointer):
        """Test retrieving a checkpoint that doesn't exist."""
        nonexistent_config = {
            "configurable": {
                "thread_id": f"nonexistent_{uuid4()}",
                "checkpoint_id": f"nonexistent_{uuid4()}"
            }
        }
        
        result = checkpointer.get_tuple(nonexistent_config)
        assert result is None
    
    @pytest.mark.integration
    def test_list_checkpoints(self, checkpointer, sample_config, sample_checkpoint, sample_metadata):
        """Test listing checkpoints for a thread."""
        # Store a checkpoint first
        checkpointer.put(sample_config, sample_checkpoint, sample_metadata)
        
        # List checkpoints
        checkpoints = list(checkpointer.list(sample_config, limit=10))
        assert len(checkpoints) >= 1
        
        # Find our checkpoint
        found = False
        for checkpoint_tuple in checkpoints:
            if checkpoint_tuple.checkpoint["id"] == sample_checkpoint["id"]:
                found = True
                break
        assert found, "Stored checkpoint not found in list"


class TestNeo4jMemoryStore:
    """Test Neo4j memory store implementation."""
    
    @pytest.fixture
    def memory_store(self):
        """Create a Neo4j memory store for testing."""
        return Neo4jMemoryStore()
    
    @pytest.fixture
    def test_namespace(self):
        """Create a test namespace."""
        return (f"test_user_{uuid4()}", "test_memory")
    
    @pytest.fixture
    def sample_memory(self):
        """Create sample memory data."""
        return {
            "type": "test_memory",
            "content": "This is a test memory",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "importance": "high"
            },
            "tags": ["test", "sample"]
        }
    
    @pytest.mark.integration
    def test_memory_store_initialization(self, memory_store):
        """Test memory store initializes correctly."""
        assert memory_store is not None
        assert memory_store.kg is not None
        assert memory_store.kg.driver is not None
    
    @pytest.mark.integration
    def test_put_and_get_memory(self, memory_store, test_namespace, sample_memory):
        """Test storing and retrieving a memory."""
        key = f"test_memory_{uuid4()}"
        
        # Store memory
        memory_store.put(test_namespace, key, sample_memory)
        
        # Retrieve memory
        retrieved_memory = memory_store.get(test_namespace, key)
        assert retrieved_memory is not None
        assert retrieved_memory["type"] == sample_memory["type"]
        assert retrieved_memory["content"] == sample_memory["content"]
        assert retrieved_memory["metadata"]["importance"] == sample_memory["metadata"]["importance"]
    
    @pytest.mark.integration
    def test_get_nonexistent_memory(self, memory_store, test_namespace):
        """Test retrieving a memory that doesn't exist."""
        nonexistent_key = f"nonexistent_{uuid4()}"
        
        result = memory_store.get(test_namespace, nonexistent_key)
        assert result is None
    
    @pytest.mark.integration
    def test_delete_memory(self, memory_store, test_namespace, sample_memory):
        """Test deleting a memory."""
        key = f"test_memory_{uuid4()}"
        
        # Store memory
        memory_store.put(test_namespace, key, sample_memory)
        
        # Verify it exists
        retrieved = memory_store.get(test_namespace, key)
        assert retrieved is not None
        
        # Delete memory
        memory_store.delete(test_namespace, key)
        
        # Verify it's gone
        deleted_check = memory_store.get(test_namespace, key)
        assert deleted_check is None
    
    @pytest.mark.integration
    def test_list_memories(self, memory_store, test_namespace, sample_memory):
        """Test listing memories in a namespace."""
        # Store multiple memories
        keys = []
        for i in range(3):
            key = f"test_memory_{i}_{uuid4()}"
            keys.append(key)
            memory_store.put(test_namespace, key, {**sample_memory, "index": i})
        
        # List memories
        memory_keys = memory_store.list(test_namespace)
        assert len(memory_keys) >= 3
        
        # Check that our keys are in the list
        for key in keys:
            assert key in memory_keys
    
    @pytest.mark.integration
    def test_search_memories(self, memory_store, test_namespace):
        """Test searching memories."""
        # Store memories with different content
        memories = [
            {"type": "learning", "content": "SQL joins are important for database queries"},
            {"type": "learning", "content": "Normalization helps reduce data redundancy"},
            {"type": "practice", "content": "Practice exercise about relational algebra"}
        ]
        
        keys = []
        for i, memory in enumerate(memories):
            key = f"search_test_{i}_{uuid4()}"
            keys.append(key)
            memory_store.put(test_namespace, key, memory)
        
        # Search for SQL-related memories
        sql_results = memory_store.search(test_namespace, "SQL", limit=5)
        assert len(sql_results) >= 1
        
        # Check that we found the SQL memory
        found_sql = False
        for result_key, result_memory in sql_results:
            if "SQL" in result_memory["content"]:
                found_sql = True
                break
        assert found_sql, "SQL-related memory not found in search results"
        
        # Search with type filter
        learning_results = memory_store.search(
            test_namespace, 
            "data", 
            limit=5, 
            filter={"type": "learning"}
        )
        assert len(learning_results) >= 1


class TestPersistenceFactory:
    """Test persistence factory function."""
    
    @pytest.mark.integration
    def test_create_neo4j_persistence(self):
        """Test creating Neo4j persistence components."""
        checkpointer, memory_store = create_neo4j_persistence()
        
        assert isinstance(checkpointer, Neo4jCheckpointSaver)
        assert isinstance(memory_store, Neo4jMemoryStore)
        assert checkpointer.kg is not None
        assert memory_store.kg is not None
    
    @pytest.mark.integration
    def test_create_neo4j_persistence_with_connection(self):
        """Test creating persistence with existing connection."""
        kg_connection = KGConnection()
        checkpointer, memory_store = create_neo4j_persistence(kg_connection)
        
        assert isinstance(checkpointer, Neo4jCheckpointSaver)
        assert isinstance(memory_store, Neo4jMemoryStore)
        assert checkpointer.kg == kg_connection
        assert memory_store.kg == kg_connection


class TestPersistenceIntegration:
    """Test integration scenarios with both persistence components."""
    
    @pytest.fixture
    def persistence_components(self):
        """Create both persistence components."""
        return create_neo4j_persistence()
    
    @pytest.mark.integration
    def test_agent_workflow_persistence_simulation(self, persistence_components):
        """Simulate agent workflow with both checkpoint and memory persistence."""
        checkpointer, memory_store = persistence_components
        
        # Simulate agent state checkpointing
        thread_id = f"workflow_test_{uuid4()}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": f"step_1_{uuid4()}"
            }
        }
        
        checkpoint = {
            "id": config["configurable"]["checkpoint_id"],
            "ts": datetime.now().isoformat(),
            "channel_values": {
                "conversation_state": {
                    "messages": ["Hello", "How can I help with SQL?"],
                    "current_intent": "theoretical_question"
                }
            },
            "channel_versions": {"conversation_state": 1},
            "versions_seen": {"__input__": {}}
        }
        
        metadata = {
            "step": 1,
            "writes": {"conversation_state": ["user_message_processed"]},
            "thread_id": thread_id
        }
        
        # Store checkpoint
        checkpointer.put(config, checkpoint, metadata)
        
        # Store long-term memory
        namespace = ("test_user", "educational_memory")
        memory_data = {
            "type": "learning_interaction",
            "topic": "SQL",
            "user_question": "How do JOIN operations work?",
            "confidence_level": 0.85,
            "session_data": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        memory_store.put(namespace, f"interaction_{thread_id}", memory_data)
        
        # Verify both were stored
        retrieved_checkpoint = checkpointer.get_tuple(config)
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.checkpoint["id"] == checkpoint["id"]
        
        retrieved_memory = memory_store.get(namespace, f"interaction_{thread_id}")
        assert retrieved_memory is not None
        assert retrieved_memory["topic"] == "SQL"
        assert retrieved_memory["confidence_level"] == 0.85
    
    @pytest.mark.integration  
    def test_memory_patterns_analysis(self, persistence_components):
        """Test storing and analyzing learning patterns."""
        checkpointer, memory_store = persistence_components
        
        namespace = ("pattern_test_user", "learning_patterns")
        
        # Store multiple learning interactions
        interactions = [
            {"type": "sql_question", "difficulty": "basic", "success": True},
            {"type": "sql_question", "difficulty": "intermediate", "success": False},
            {"type": "normalization_question", "difficulty": "basic", "success": True},
            {"type": "sql_question", "difficulty": "advanced", "success": False}
        ]
        
        for i, interaction in enumerate(interactions):
            key = f"pattern_{i}_{uuid4()}"
            memory_store.put(namespace, key, {
                **interaction,
                "timestamp": datetime.now().isoformat(),
                "session_id": f"session_{i}"
            })
        
        # Search for SQL-related patterns
        sql_patterns = memory_store.search(namespace, "sql_question", limit=10)
        assert len(sql_patterns) >= 3
        
        # Analyze success patterns
        sql_successes = [
            result for key, result in sql_patterns 
            if result.get("success", False)
        ]
        
        sql_failures = [
            result for key, result in sql_patterns 
            if not result.get("success", True)
        ]
        
        assert len(sql_successes) >= 1
        assert len(sql_failures) >= 2
        
        # This could be used by agents to identify learning gaps
        assert all(failure["difficulty"] in ["intermediate", "advanced"] for failure in sql_failures)