"""
Authentication module for LUCA frontend.

Handles user authentication and conversation management with Neo4j.
"""

import os
import hashlib
import sys
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
from kg.connection import KGConnection

# Add project root to path for tools import
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.llm_config import create_default_llm

class AuthManager:
    """Manages user authentication and conversation data."""
    
    def __init__(self):
        """Initialize connection to Neo4j."""
        self.kg_connection = KGConnection()
        self.llm = create_default_llm()
    
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
            
            # No need to convert DateTime objects - Flask JSON provider will handle it
            
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
    
    def generate_conversation_title(self, message: str, subject: str) -> str:
        """
        Generate a descriptive conversation title using LLM based on the first message.
        
        Args:
            message: First user message
            subject: Educational subject
            
        Returns:
            Generated descriptive title
        """
        try:
            # Apply abbreviations to subject
            subject_abbrev = self._abbreviate_subject(subject)
            
            prompt = f"""
            Genera un título descriptivo (máximo 60 caracteres) para una conversación educativa basada en:
            
            Materia: {subject_abbrev}
            Primer mensaje: {message}
            
            INSTRUCCIONES IMPORTANTES:
            1. Si el mensaje menciona un ejercicio específico (ej: "ejercicio 2", "práctica 3", "punto 1.a"), inclúyelo en el título
            2. Usa abreviaciones comunes: "Álgebra Relacional" → "A.R.", "Base de Datos" → "BD"
            3. Sé específico sobre el tema si es posible
            4. Máximo 60 caracteres
            5. Responde SOLO con el título, sin comillas ni explicaciones
            
            Ejemplos buenos:
            - "Ejercicio 2.3 - JOIN con múltiples tablas en A.R."
            - "Práctica 1 - Normalización de BD y formas normales"
            - "LEFT JOIN vs RIGHT JOIN - diferencias y uso"
            - "Consulta σ con múltiples condiciones y operadores"
            - "Punto 1.d - División relacional paso a paso"
            """
            
            response = self.llm.invoke(prompt)
            title = response.content.strip().strip('"').strip("'")
            
            # Truncate if too long
            if len(title) > 60:
                title = title[:57] + "..."
            
            return title
            
        except Exception as e:
            print(f"Error generating conversation title: {e}")
            return f"Consulta sobre {self._abbreviate_subject(subject)}"
    
    def _abbreviate_subject(self, subject: str) -> str:
        """
        Apply common abbreviations to subject names.
        
        Args:
            subject: Full subject name
            
        Returns:
            Abbreviated subject name
        """
        abbreviations = {
            "Álgebra Relacional": "A.R.",
            "Algebra Relacional": "A.R.",  # Without accent
            "Base de Datos": "BD",
            "Bases de Datos": "BD",
            "Sistemas de Gestión": "SG",
            "Programación": "Prog.",
            "Matemáticas": "Mat.",
            "Matematicas": "Mat.",  # Without accent
            "Estructuras de Datos": "ED",
            "Análisis de Sistemas": "AS",
            "Analisis de Sistemas": "AS"  # Without accent
        }
        
        for full_name, abbrev in abbreviations.items():
            if full_name.lower() in subject.lower():
                return subject.replace(full_name, abbrev)
        
        return subject
    
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
    
    def add_message_to_conversation(self, conversation_id: str, content: str, role: str, order: int):
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            content: Message content
            role: 'user' or 'assistant'
            order: Message order in conversation
        """
        try:
            query = """
            MATCH (c:Conversacion {id: $conversation_id})
            CREATE (m:Mensaje {
                id: randomUUID(),
                content: $content,
                role: $role,
                order: $order,
                created_at: datetime()
            })
            CREATE (c)-[:CONTAINS]->(m)
            RETURN m.id as message_id
            """
            
            result = self.kg_connection.execute_query(
                query, 
                {
                    "conversation_id": conversation_id,
                    "content": content,
                    "role": role,
                    "order": order
                }
            )
            
            if result:
                return result[0]["message_id"]
            return None
            
        except Exception as e:
            print(f"Error adding message to conversation: {e}")
            return None
    
    def get_conversation_messages(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries ordered by creation time
        """
        try:
            query = """
            MATCH (c:Conversacion {id: $conversation_id})-[:CONTAINS]->(m:Mensaje)
            RETURN m.content as content, m.role as role, m.order as order, 
                   m.created_at as created_at
            ORDER BY m.order DESC
            LIMIT $limit
            """
            
            messages = self.kg_connection.execute_query(
                query, 
                {"conversation_id": conversation_id, "limit": limit}
            )
            
            # No need to convert DateTime objects - Flask JSON provider will handle it
            
            # Reverse to show oldest first
            return list(reversed(messages)) if messages else []
            
        except Exception as e:
            print(f"Error loading conversation messages: {e}")
            return []
    
    def _neo4j_datetime_to_string(self, dt) -> str:
        """
        Convert Neo4j DateTime object to string for JSON serialization.
        
        Args:
            dt: Neo4j DateTime object
            
        Returns:
            Formatted datetime string
        """
        try:
            # Check if it's a Neo4j DateTime object
            if hasattr(dt, 'to_native'):
                # Convert to Python datetime first
                python_dt = dt.to_native()
                return python_dt.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(dt, 'strftime'):
                # Regular Python datetime
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Fallback to string conversion
                return str(dt)
        except Exception as e:
            print(f"Error converting datetime: {e}")
            return str(dt)
    
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

def generate_conversation_title(message: str, subject: str) -> str:
    """Generate conversation title - convenience wrapper."""
    return get_auth_manager().generate_conversation_title(message, subject)

def add_message_to_conversation(conversation_id: str, content: str, role: str, order: int):
    """Add message to conversation - convenience wrapper."""
    return get_auth_manager().add_message_to_conversation(conversation_id, content, role, order)

def get_conversation_messages(conversation_id: str, limit: int = 10) -> List[Dict]:
    """Get conversation messages - convenience wrapper."""
    return get_auth_manager().get_conversation_messages(conversation_id, limit)