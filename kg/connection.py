import os
import logging
from typing import Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError


logger = logging.getLogger(__name__)


class KGConnectionError(Exception):
    """Exception raised for KG connection related errors."""
    pass


class KGConnection:
    """
    Knowledge Graph connection manager for Neo4j.
    
    Handles Neo4j driver creation and session management using environment variables.
    Uses NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD from .envrc or environment.
    """
    
    def __init__(self, 
                 uri: Optional[str] = None,
                 user: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        Initialize KG connection with Neo4j credentials.
        
        Args:
            uri: Neo4j URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USERNAME env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv('NEO4J_URI')
        self.user = user or os.getenv('NEO4J_USERNAME')
        self.password = password or os.getenv('NEO4J_PASSWORD')
        
        if not all([self.uri, self.user, self.password]):
            missing = [var for var, val in [
                ('NEO4J_URI', self.uri),
                ('NEO4J_USERNAME', self.user), 
                ('NEO4J_PASSWORD', self.password)
            ] if not val]
            raise KGConnectionError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        self._driver: Optional[Driver] = None
    
    @property
    def driver(self) -> Driver:
        """Get or create Neo4j driver instance."""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self.uri, 
                    auth=(self.user, self.password)
                )
                # Test connection
                self._driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {self.uri}")
            except ServiceUnavailable as e:
                raise KGConnectionError(f"Failed to connect to Neo4j: {e}") from e
            except AuthError as e:
                raise KGConnectionError(f"Authentication failed: {e}") from e
            except Exception as e:
                raise KGConnectionError(f"Unexpected error connecting to Neo4j: {e}") from e
        
        return self._driver
    
    @contextmanager
    def session(self, **kwargs):
        """
        Context manager for Neo4j sessions.
        
        Args:
            **kwargs: Additional arguments passed to driver.session()
            
        Yields:
            Session: Neo4j session instance
            
        Example:
            with kg_conn.session() as session:
                result = session.run("MATCH (n) RETURN count(n)")
        """
        session = None
        try:
            session = self.driver.session(**kwargs)
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
        finally:
            if session:
                session.close()
    
    def execute_query(self, query: str, parameters: Optional[dict] = None):
        """
        Execute a single query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            
        Returns:
            List of dictionaries converted from query records
        """
        try:
            with self.session() as session:
                result = session.run(query, parameters or {})
                # Convert Neo4j Record objects to dictionaries
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise KGConnectionError(f"Query execution failed: {e}") from e
    
    def execute_write_query(self, query: str, parameters: Optional[dict] = None):
        """
        Execute a write query in a write transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            
        Returns:
            List of records from the query result
        """
        def _run_query(tx, query: str, parameters: dict):
            result = tx.run(query, parameters)
            return list(result)
        
        try:
            with self.session() as session:
                return session.execute_write(_run_query, query, parameters or {})
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise KGConnectionError(f"Write query execution failed: {e}") from e
    
    def test_connection(self) -> bool:
        """
        Test the Neo4j connection.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            with self.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return record["test"] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """
        Get basic database information.
        
        Returns:
            dict: Database information including version, node count, etc.
        """
        try:
            with self.session() as session:
                # Get version
                version_result = session.run("CALL dbms.components() YIELD name, versions")
                version_info = [dict(record) for record in version_result]
                
                # Get node count
                count_result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = count_result.single()["node_count"]
                
                # Get relationship count
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                rel_count = rel_result.single()["rel_count"]
                
                return {
                    "components": version_info,
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "uri": self.uri
                }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()