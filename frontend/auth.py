"""
Authentication module for LUCA frontend.

Handles user authentication and conversation management with Neo4j.
"""

import os
import hashlib
from typing import Optional, Dict, List
from datetime import datetime
from kg.connection import KGConnection

class AuthManager:
    """Manages user authentication and conversation data."""
    
    def __init__(self):
        """Initialize connection to Neo4j."""
        self.kg_connection = KGConnection()
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email (must end with @uca.edu.ar)
            password: User password
            
        Returns:
            User data if authentication successful, None otherwise
        """
        try:
            # Hash password for comparison
            password_hash = self._hash_password(password)
            
            query = """
            MATCH (u:Usuario {email: $email})
            WHERE u.password = $password
            SET u.last_login = datetime()
            RETURN u.email as email, u.nombre as nombre, u.created_at as created_at
            """
            
            result = self.kg_connection.execute_query(
                query, 
                {"email": email, "password": password}  # For demo, using plain text
            )
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def get_user_conversations(self, email: str) -> List[Dict]:
        """
        Get all conversations for a user.
        
        Args:
            email: User email
            
        Returns:
            List of conversation dictionaries
        """
        try:
            query = """
            MATCH (u:Usuario {email: $email})-[:OWNS]->(c:Conversacion)
            RETURN c.id as id, c.title as title, c.subject as subject, 
                   c.created_at as created_at, c.updated_at as updated_at,
                   c.message_count as message_count
            ORDER BY c.updated_at DESC
            """
            
            conversations = self.kg_connection.execute_query(query, {"email": email})
            return conversations or []
            
        except Exception as e:
            print(f"Error loading conversations: {e}")
            return []
    
    def create_conversation(self, email: str, title: str, subject: str) -> Optional[str]:
        """
        Create a new conversation for the user.
        
        Args:
            email: User email
            title: Conversation title
            subject: Educational subject
            
        Returns:
            Conversation ID if created successfully, None otherwise
        """
        try:
            query = """
            MATCH (u:Usuario {email: $email})
            CREATE (c:Conversacion {
                id: randomUUID(),
                title: $title,
                subject: $subject,
                created_at: datetime(),
                updated_at: datetime(),
                message_count: 0
            })
            CREATE (u)-[:OWNS]->(c)
            RETURN c.id as id
            """
            
            result = self.kg_connection.execute_query(
                query, 
                {"email": email, "title": title, "subject": subject}
            )
            
            if result:
                return result[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    def update_conversation(self, conversation_id: str, title: Optional[str] = None):
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation ID
            title: Optional new title
        """
        try:
            updates = ["c.updated_at = datetime()"]
            params = {"conversation_id": conversation_id}
            
            if title:
                updates.append("c.title = $title")
                params["title"] = title
            
            query = f"""
            MATCH (c:Conversacion {{id: $conversation_id}})
            SET {', '.join(updates)}
            RETURN c
            """
            
            self.kg_connection.execute_query(query, params)
            
        except Exception as e:
            print(f"Error updating conversation: {e}")
    
    def increment_message_count(self, conversation_id: str):
        """
        Increment message count for a conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        try:
            query = """
            MATCH (c:Conversacion {id: $conversation_id})
            SET c.message_count = COALESCE(c.message_count, 0) + 1,
                c.updated_at = datetime()
            RETURN c.message_count as count
            """
            
            self.kg_connection.execute_query(query, {"conversation_id": conversation_id})
            
        except Exception as e:
            print(f"Error incrementing message count: {e}")
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password for secure storage.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

# Global auth manager instance
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager

# Convenience functions for Streamlit
def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate user - convenience wrapper."""
    return get_auth_manager().authenticate_user(email, password)

def get_user_conversations(email: str) -> List[Dict]:
    """Get user conversations - convenience wrapper."""
    return get_auth_manager().get_user_conversations(email)

def create_conversation(email: str, title: str, subject: str) -> Optional[str]:
    """Create conversation - convenience wrapper."""
    return get_auth_manager().create_conversation(email, title, subject)

def update_conversation(conversation_id: str, title: Optional[str] = None):
    """Update conversation - convenience wrapper."""
    return get_auth_manager().update_conversation(conversation_id, title)

def increment_message_count(conversation_id: str):
    """Increment message count - convenience wrapper."""
    return get_auth_manager().increment_message_count(conversation_id)