"""
Simple test for Neo4j persistence to verify basic functionality.
"""

from kg.persistence import Neo4jCheckpointSaver, Neo4jMemoryStore, create_neo4j_persistence
from uuid import uuid4
import json

def test_checkpointer():
    """Test basic checkpointer functionality."""
    print("Testing Neo4j Checkpointer...")
    
    checkpointer = Neo4jCheckpointSaver()
    
    # Create test data
    thread_id = f"test_thread_{uuid4()}"
    checkpoint_id = f"checkpoint_{uuid4()}"
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }
    
    checkpoint = {
        "id": checkpoint_id,
        "ts": "2025-01-27T10:00:00",
        "channel_values": {
            "state": {"message": "Hello world"},
            "metadata": {"version": "1.0"}
        },
        "channel_versions": {"state": 1},
        "versions_seen": {"__input__": {}}
    }
    
    metadata = {
        "step": 1,
        "writes": {"state": ["message_processed"]},
        "thread_id": thread_id
    }
    
    # Test put
    returned_config = checkpointer.put(config, checkpoint, metadata)
    print(f"✓ Stored checkpoint: {checkpoint_id}")
    
    # Test get
    result = checkpointer.get_tuple(config)
    assert result is not None
    assert result.checkpoint["id"] == checkpoint_id
    print(f"✓ Retrieved checkpoint: {result.checkpoint['id']}")
    
    # Test list
    checkpoints = list(checkpointer.list(config, limit=5))
    found = any(cp.checkpoint["id"] == checkpoint_id for cp in checkpoints)
    assert found
    print(f"✓ Found checkpoint in list of {len(checkpoints)} items")
    
    print("Checkpointer tests passed!\n")


def test_memory_store():
    """Test basic memory store functionality."""
    print("Testing Neo4j Memory Store...")
    
    memory_store = Neo4jMemoryStore()
    
    # Create test data
    namespace = (f"test_user_{uuid4()}", "test_memory")
    key = f"memory_{uuid4()}"
    
    memory_data = {
        "type": "test_memory",
        "content": "This is a test memory",
        "metadata": {
            "importance": "high",
            "created_at": "2025-01-27T10:00:00"
        },
        "tags": ["test", "persistence"]
    }
    
    # Test put
    memory_store.put(namespace, key, memory_data)
    print(f"✓ Stored memory: {key}")
    
    # Test get
    retrieved = memory_store.get(namespace, key)
    assert retrieved is not None
    assert retrieved["type"] == "test_memory"
    assert retrieved["content"] == "This is a test memory"
    print(f"✓ Retrieved memory: {retrieved['type']}")
    
    # Test list
    keys = memory_store.list(namespace)
    assert key in keys
    print(f"✓ Found memory in list of {len(keys)} items")
    
    # Test search
    search_results = memory_store.search(namespace, "test memory", limit=5)
    found = any(result_key == key for result_key, _ in search_results)
    assert found
    print(f"✓ Found memory in search results: {len(search_results)} items")
    
    # Test delete
    memory_store.delete(namespace, key)
    deleted_check = memory_store.get(namespace, key)
    assert deleted_check is None
    print(f"✓ Successfully deleted memory")
    
    print("Memory store tests passed!\n")


def test_integration():
    """Test integration scenario."""
    print("Testing Integration Scenario...")
    
    checkpointer, memory_store = create_neo4j_persistence()
    
    # Simulate a conversation workflow
    user_id = f"integration_user_{uuid4()}"
    thread_id = f"conversation_{uuid4()}"
    
    # Store conversation checkpoint
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": f"step_1_{uuid4()}"
        }
    }
    
    checkpoint = {
        "id": config["configurable"]["checkpoint_id"],
        "ts": "2025-01-27T10:00:00",
        "channel_values": {
            "conversation": {
                "messages": ["User: ¿Qué es un JOIN?", "Assistant: Un JOIN es..."],
                "intent": "theoretical_question",
                "subject": "Bases de Datos"
            }
        },
        "channel_versions": {"conversation": 1},
        "versions_seen": {"__input__": {}}
    }
    
    metadata = {
        "step": 1,
        "writes": {"conversation": ["response_generated"]},
        "thread_id": thread_id
    }
    
    checkpointer.put(config, checkpoint, metadata)
    print(f"✓ Stored conversation checkpoint")
    
    # Store learning memory
    namespace = (user_id, "educational_memory")
    memory_data = {
        "type": "learning_interaction",
        "topic": "SQL JOINs",
        "question": "¿Qué es un JOIN?",
        "confidence": 0.85,
        "subject": "Bases de Datos",
        "timestamp": "2025-01-27T10:00:00",
        "session_info": {
            "thread_id": thread_id,
            "intent": "theoretical_question"
        }
    }
    
    memory_store.put(namespace, f"interaction_{thread_id}", memory_data)
    print(f"✓ Stored learning memory")
    
    # Verify both are retrievable
    retrieved_checkpoint = checkpointer.get_tuple(config)
    assert retrieved_checkpoint is not None
    assert "JOIN" in str(retrieved_checkpoint.checkpoint["channel_values"])
    print(f"✓ Retrieved conversation checkpoint")
    
    retrieved_memory = memory_store.get(namespace, f"interaction_{thread_id}")
    assert retrieved_memory is not None
    assert retrieved_memory["topic"] == "SQL JOINs"
    assert retrieved_memory["confidence"] == 0.85
    print(f"✓ Retrieved learning memory")
    
    print("Integration tests passed!\n")


if __name__ == "__main__":
    try:
        test_checkpointer()
        test_memory_store()  
        test_integration()
        print("🎉 All persistence tests passed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()