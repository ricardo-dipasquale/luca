"""
Neo4j-based persistence implementations for LangGraph memory and checkpoints.

This module provides Neo4j implementations for both checkpointers (short-term memory)
and memory stores (long-term memory) to enable persistent agent memory across sessions.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Sequence, Iterator
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.store.base import BaseStore
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from pydantic import BaseModel

from .connection import KGConnection

logger = logging.getLogger(__name__)


def serialize_for_neo4j(obj: Any) -> str:
    """
    Custom serializer that properly handles Pydantic models and other complex objects.
    """
    def default_serializer(o):
        if isinstance(o, BaseModel):
            # Serialize Pydantic models as JSON with type information
            return {
                '__pydantic_model__': o.__class__.__module__ + '.' + o.__class__.__qualname__,
                '__data__': o.model_dump()
            }
        elif hasattr(o, '__dict__'):
            # For other objects with __dict__, serialize their dict representation
            return {
                '__object_type__': str(type(o).__name__),
                '__data__': o.__dict__
            }
        elif isinstance(o, (datetime,)):
            return o.isoformat()
        else:
            # Let JSON handle other types or raise TypeError
            return str(o)
    
    return json.dumps(obj, default=default_serializer, ensure_ascii=False)


def migrate_legacy_data(data: Dict[str, Any], class_name: str) -> Dict[str, Any]:
    """
    Migrate legacy data structures to current schema.
    """
    if class_name == "ConversationTurn":
        # Migrate old 'evaluation' and 'clarification' intents to 'practical_specific'
        if 'intent' in data:
            if data['intent'] == 'evaluation':
                logger.info("Migrating legacy 'evaluation' intent to 'practical_specific'")
                data['intent'] = 'practical_specific'
            elif data['intent'] == 'clarification':
                logger.info("Migrating legacy 'clarification' intent to 'practical_specific'")
                data['intent'] = 'practical_specific'
    elif class_name == "ConversationContext":
        # Migrate conversation history turns
        if 'memory' in data and 'conversation_history' in data['memory']:
            for turn in data['memory']['conversation_history']:
                if turn.get('intent') == 'evaluation':
                    logger.info("Migrating legacy 'evaluation' intent to 'practical_specific' in conversation history")
                    turn['intent'] = 'practical_specific'
                elif turn.get('intent') == 'clarification':
                    logger.info("Migrating legacy 'clarification' intent to 'practical_specific' in conversation history")
                    turn['intent'] = 'practical_specific'
    elif class_name == "IntentClassificationResult":
        # Migrate old 'evaluation' and 'clarification' predicted intents to 'practical_specific'
        if 'predicted_intent' in data:
            if data['predicted_intent'] == 'evaluation':
                logger.info("Migrating legacy 'evaluation' predicted_intent to 'practical_specific'")
                data['predicted_intent'] = 'practical_specific'
                # Update reasoning to reflect the change
                if 'reasoning' in data:
                    data['reasoning'] = data['reasoning'].replace(
                        "evaluación", "consulta práctica específica"
                    ).replace(
                        "evaluar su conocimiento", "revisar ejercicio específico"
                    )
            elif data['predicted_intent'] == 'clarification':
                logger.info("Migrating legacy 'clarification' predicted_intent to 'practical_specific'")
                data['predicted_intent'] = 'practical_specific'
                # Update reasoning to reflect the change
                if 'reasoning' in data:
                    data['reasoning'] = data['reasoning'].replace(
                        "clarificación", "consulta práctica específica"
                    ).replace(
                        "aclaración", "pregunta específica"
                    )
    
    return data


def deserialize_from_neo4j(json_str: str) -> Any:
    """
    Custom deserializer that reconstructs Pydantic models and other complex objects.
    """
    def object_hook(obj_dict):
        if '__pydantic_model__' in obj_dict:
            # Reconstruct Pydantic model
            module_path, class_name = obj_dict['__pydantic_model__'].rsplit('.', 1)
            try:
                # Dynamically import the module and get the class
                import importlib
                module = importlib.import_module(module_path)
                model_class = getattr(module, class_name)
                
                # Apply data migration before reconstruction
                migrated_data = migrate_legacy_data(obj_dict['__data__'], class_name)
                
                reconstructed = model_class(**migrated_data)
                logger.debug(f"Successfully reconstructed Pydantic model: {class_name}")
                return reconstructed
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to reconstruct Pydantic model {obj_dict['__pydantic_model__']}: {e}")
                # Return the raw data if we can't reconstruct the model
                return obj_dict['__data__']
            except Exception as e:
                logger.warning(f"Failed to reconstruct Pydantic model {class_name} after migration: {e}")
                # Try to return migrated data even if reconstruction fails
                return migrate_legacy_data(obj_dict['__data__'], class_name)
        elif '__object_type__' in obj_dict:
            # For now, just return the data - could be extended to reconstruct objects
            return obj_dict['__data__']
        return obj_dict
    
    try:
        result = json.loads(json_str, object_hook=object_hook)
        logger.debug(f"Deserialized data from Neo4j: {type(result)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize JSON: {e}")
        logger.error(f"Problematic JSON string: {json_str[:200]}...")
        return json_str  # Return original string if deserialization fails


class Neo4jCheckpointSaver(BaseCheckpointSaver):
    """
    Neo4j-based checkpoint saver for LangGraph agents.
    
    Stores agent state checkpoints in Neo4j graph database, enabling
    persistent conversations and resumable agent workflows.
    """
    
    def __init__(self, kg_connection: Optional[KGConnection] = None):
        """Initialize with Neo4j connection."""
        super().__init__()
        self.kg = kg_connection or KGConnection()
        self._ensure_checkpoint_schema()
    
    def _ensure_checkpoint_schema(self):
        """Create necessary Neo4j constraints and indexes for checkpoints."""
        with self.kg.driver.session() as session:
            try:
                # Create constraints
                session.run("""
                    CREATE CONSTRAINT checkpoint_thread_id_step 
                    IF NOT EXISTS 
                    FOR (c:Checkpoint) 
                    REQUIRE (c.thread_id, c.checkpoint_id) IS UNIQUE
                """)
                
                # Create indexes
                session.run("""
                    CREATE INDEX checkpoint_thread_timestamp 
                    IF NOT EXISTS 
                    FOR (c:Checkpoint) 
                    ON (c.thread_id, c.timestamp)
                """)
                
                logger.info("Neo4j checkpoint schema initialized")
                
            except Neo4jError as e:
                logger.warning(f"Schema initialization warning: {e}")
    
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> RunnableConfig:
        """Store a checkpoint in Neo4j."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        
        # Serialize checkpoint data using custom serializer
        checkpoint_data = serialize_for_neo4j(checkpoint)
        metadata_data = serialize_for_neo4j(metadata) if metadata else "{}"
        versions_data = serialize_for_neo4j(new_versions) if new_versions else "{}"
        
        with self.kg.driver.session() as session:
            try:
                session.run("""
                    MERGE (c:Checkpoint {thread_id: $thread_id, checkpoint_id: $checkpoint_id})
                    SET c.checkpoint_data = $checkpoint_data,
                        c.metadata = $metadata,
                        c.versions = $versions,
                        c.timestamp = datetime(),
                        c.updated_at = datetime()
                    RETURN c
                """, {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_data": checkpoint_data,
                    "metadata": metadata_data,
                    "versions": versions_data
                })
                
                logger.debug(f"Stored checkpoint {checkpoint_id} for thread {thread_id}")
                
            except Neo4jError as e:
                logger.error(f"Failed to store checkpoint: {e}")
                raise
        
        return config
    
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> RunnableConfig:
        """Async version of put method."""
        return self.put(config, checkpoint, metadata, new_versions)
    
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Retrieve a specific checkpoint from Neo4j."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        
        with self.kg.driver.session() as session:
            try:
                if checkpoint_id:
                    # Get specific checkpoint
                    result = session.run("""
                        MATCH (c:Checkpoint {thread_id: $thread_id, checkpoint_id: $checkpoint_id})
                        RETURN c.checkpoint_data as checkpoint_data,
                               c.metadata as metadata,
                               c.versions as versions,
                               c.checkpoint_id as checkpoint_id
                    """, {"thread_id": thread_id, "checkpoint_id": checkpoint_id})
                else:
                    # Get latest checkpoint
                    result = session.run("""
                        MATCH (c:Checkpoint {thread_id: $thread_id})
                        RETURN c.checkpoint_data as checkpoint_data,
                               c.metadata as metadata,
                               c.versions as versions,
                               c.checkpoint_id as checkpoint_id
                        ORDER BY c.timestamp DESC
                        LIMIT 1
                    """, {"thread_id": thread_id})
                
                record = result.single()
                if not record:
                    return None
                
                # Deserialize data using custom deserializer
                checkpoint = deserialize_from_neo4j(record["checkpoint_data"])
                metadata = deserialize_from_neo4j(record["metadata"]) if record["metadata"] != "{}" else {}
                parent_config = config.copy() if checkpoint.get("parent_config") else None
                
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config
                )
                
            except (Neo4jError, json.JSONDecodeError) as e:
                logger.error(f"Failed to retrieve checkpoint: {e}")
                return None
    
    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Async version of get_tuple method."""
        return self.get_tuple(config)
    
    def list(
        self,
        config: RunnableConfig,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints for a thread."""
        thread_id = config["configurable"]["thread_id"]
        
        query = """
            MATCH (c:Checkpoint {thread_id: $thread_id})
            RETURN c.checkpoint_data as checkpoint_data,
                   c.metadata as metadata,
                   c.versions as versions,
                   c.checkpoint_id as checkpoint_id,
                   c.timestamp as timestamp
            ORDER BY c.timestamp DESC
        """
        
        params = {"thread_id": thread_id}
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.kg.driver.session() as session:
            try:
                result = session.run(query, params)
                
                for record in result:
                    checkpoint = deserialize_from_neo4j(record["checkpoint_data"])
                    metadata = deserialize_from_neo4j(record["metadata"]) if record["metadata"] != "{}" else {}
                    
                    checkpoint_config = config.copy()
                    checkpoint_config["configurable"]["checkpoint_id"] = record["checkpoint_id"]
                    
                    parent_config = config.copy() if checkpoint.get("parent_config") else None
                    
                    yield CheckpointTuple(
                        config=checkpoint_config,
                        checkpoint=checkpoint,
                        metadata=metadata,
                        parent_config=parent_config
                    )
                    
            except (Neo4jError, json.JSONDecodeError) as e:
                logger.error(f"Failed to list checkpoints: {e}")
    
    async def alist(
        self,
        config: RunnableConfig,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """Async version of list method."""
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item
    
    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store intermediate writes (async). Not fully implemented for basic checkpointing."""
        # For now, we just store the writes as metadata since this is an intermediate operation
        # This could be extended to store more detailed checkpoint information
        pass


class Neo4jMemoryStore(BaseStore):
    """
    Neo4j-based memory store for long-term agent memory.
    
    Stores agent memories as nodes in Neo4j with vector embeddings
    for semantic search and graph relationships for context.
    """
    
    def __init__(self, kg_connection: Optional[KGConnection] = None):
        """Initialize with Neo4j connection."""
        self.kg = kg_connection or KGConnection()
        self._ensure_memory_schema()
    
    def _ensure_memory_schema(self):
        """Create necessary Neo4j constraints and indexes for memory storage."""
        with self.kg.driver.session() as session:
            try:
                # Create constraints
                session.run("""
                    CREATE CONSTRAINT agent_memory_key 
                    IF NOT EXISTS 
                    FOR (m:AgentMemory) 
                    REQUIRE (m.namespace, m.key) IS UNIQUE
                """)
                
                # Create indexes
                session.run("""
                    CREATE INDEX agent_memory_namespace 
                    IF NOT EXISTS 
                    FOR (m:AgentMemory) 
                    ON m.namespace
                """)
                
                session.run("""
                    CREATE INDEX agent_memory_created 
                    IF NOT EXISTS 
                    FOR (m:AgentMemory) 
                    ON m.created_at
                """)
                
                logger.info("Neo4j memory store schema initialized")
                
            except Neo4jError as e:
                logger.warning(f"Memory schema initialization warning: {e}")
    
    def put(
        self,
        namespace: Tuple[str, ...],
        key: str,
        value: Dict[str, Any],
    ) -> None:
        """Store a memory in Neo4j."""
        namespace_str = "/".join(namespace)
        value_json = serialize_for_neo4j(value)
        
        with self.kg.driver.session() as session:
            try:
                session.run("""
                    MERGE (m:AgentMemory {namespace: $namespace, key: $key})
                    SET m.value = $value,
                        m.created_at = CASE 
                            WHEN m.created_at IS NULL THEN datetime() 
                            ELSE m.created_at 
                        END,
                        m.updated_at = datetime(),
                        m.type = $memory_type
                    RETURN m
                """, {
                    "namespace": namespace_str,
                    "key": key,
                    "value": value_json,
                    "memory_type": value.get("type", "general")
                })
                
                logger.debug(f"Stored memory {key} in namespace {namespace_str}")
                
            except Neo4jError as e:
                logger.error(f"Failed to store memory: {e}")
                raise
    
    async def aput(
        self,
        namespace: Tuple[str, ...],
        key: str,
        value: Dict[str, Any],
    ) -> None:
        """Async version of put method."""
        self.put(namespace, key, value)
    
    def get(
        self,
        namespace: Tuple[str, ...],
        key: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory from Neo4j."""
        namespace_str = "/".join(namespace)
        
        with self.kg.driver.session() as session:
            try:
                result = session.run("""
                    MATCH (m:AgentMemory {namespace: $namespace, key: $key})
                    RETURN m.value as value
                """, {"namespace": namespace_str, "key": key})
                
                record = result.single()
                if not record:
                    return None
                
                return deserialize_from_neo4j(record["value"])
                
            except (Neo4jError, json.JSONDecodeError) as e:
                logger.error(f"Failed to retrieve memory: {e}")
                return None
    
    async def aget(
        self,
        namespace: Tuple[str, ...],
        key: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of get method."""
        return self.get(namespace, key)
    
    def delete(
        self,
        namespace: Tuple[str, ...],
        key: str,
    ) -> None:
        """Delete a memory from Neo4j."""
        namespace_str = "/".join(namespace)
        
        with self.kg.driver.session() as session:
            try:
                result = session.run("""
                    MATCH (m:AgentMemory {namespace: $namespace, key: $key})
                    DELETE m
                    RETURN count(m) as deleted_count
                """, {"namespace": namespace_str, "key": key})
                
                record = result.single()
                deleted_count = record["deleted_count"] if record else 0
                
                logger.debug(f"Deleted {deleted_count} memory records for {key}")
                
            except Neo4jError as e:
                logger.error(f"Failed to delete memory: {e}")
                raise
    
    def list(
        self,
        namespace: Tuple[str, ...],
    ) -> List[str]:
        """List all memory keys in a namespace."""
        namespace_str = "/".join(namespace)
        
        with self.kg.driver.session() as session:
            try:
                result = session.run("""
                    MATCH (m:AgentMemory {namespace: $namespace})
                    RETURN m.key as key
                    ORDER BY m.updated_at DESC
                """, {"namespace": namespace_str})
                
                return [record["key"] for record in result]
                
            except Neo4jError as e:
                logger.error(f"Failed to list memories: {e}")
                return []
    
    def search(
        self,
        namespace: Tuple[str, ...],
        query: str,
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Search memories using text search in Neo4j."""
        namespace_str = "/".join(namespace)
        
        # Basic text search using CONTAINS
        search_query = """
            MATCH (m:AgentMemory {namespace: $namespace})
            WHERE toLower(m.value) CONTAINS toLower($query)
        """
        
        params = {
            "namespace": namespace_str,
            "query": query
        }
        
        # Add filters if provided
        if filter:
            for key, value in filter.items():
                if key == "type":
                    search_query += f" AND m.type = $filter_{key}"
                    params[f"filter_{key}"] = value
        
        search_query += """
            RETURN m.key as key, m.value as value
            ORDER BY m.updated_at DESC
            LIMIT $limit
        """
        params["limit"] = limit
        
        with self.kg.driver.session() as session:
            try:
                result = session.run(search_query, params)
                
                return [
                    (record["key"], deserialize_from_neo4j(record["value"]))
                    for record in result
                ]
                
            except (Neo4jError, json.JSONDecodeError) as e:
                logger.error(f"Failed to search memories: {e}")
                return []
    
    async def abatch(
        self,
        operations: Sequence[tuple],
    ) -> List[Any]:
        """Async batch operations - not implemented for Neo4j store."""
        raise NotImplementedError("Async batch operations not implemented for Neo4j store")
    
    def batch(
        self,
        operations: Sequence[tuple],
    ) -> List[Any]:
        """Batch operations - not implemented for Neo4j store."""
        raise NotImplementedError("Batch operations not implemented for Neo4j store")


def create_neo4j_persistence(kg_connection: Optional[KGConnection] = None) -> Tuple[Neo4jCheckpointSaver, Neo4jMemoryStore]:
    """
    Create Neo4j-based persistence components for LangGraph agents.
    
    Returns:
        Tuple of (checkpointer, memory_store) for agent configuration
    """
    kg = kg_connection or KGConnection()
    checkpointer = Neo4jCheckpointSaver(kg)
    memory_store = Neo4jMemoryStore(kg)
    
    logger.info("Created Neo4j persistence components")
    return checkpointer, memory_store