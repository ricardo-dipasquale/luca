"""
Utility functions for LUCA frontend.
"""

import sys
import os
from datetime import datetime
from typing import List, Optional

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kg.queries import KGQueryInterface
from kg.connection import KGConnection

def get_subjects_from_kg() -> List[str]:
    """
    Get list of subjects from the knowledge graph.
    
    Returns:
        List of subject names
    """
    try:
        # Initialize KG connection and interface
        kg_connection = KGConnection()
        kg_interface = KGQueryInterface(kg_connection)
        
        # Get subjects using the existing method
        subjects = kg_interface.get_subjects()
        
        # Extract subject names
        subject_names = [subject['name'] for subject in subjects if 'name' in subject]
        
        kg_connection.close()
        return subject_names
        
    except Exception as e:
        print(f"Error loading subjects from KG: {e}")
        return ["Bases de Datos Relacionales"]  # Fallback

def format_timestamp(timestamp) -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: Datetime object or string
        
    Returns:
        Formatted timestamp string
    """
    try:
        if isinstance(timestamp, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif hasattr(timestamp, 'to_native'):
            # Neo4j datetime
            dt = timestamp.to_native()
        else:
            dt = timestamp
        
        # Format as relative time
        now = datetime.now()
        if hasattr(dt, 'replace'):
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        if diff.days > 0:
            return f"hace {diff.days} días"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"hace {hours} horas"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"hace {minutes} minutos"
        else:
            return "hace unos momentos"
            
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return "Fecha desconocida"

def validate_email(email: str) -> bool:
    """
    Validate that email is from UCA domain.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    return email.endswith("@uca.edu.ar") and "@" in email

def generate_conversation_title(message: str, max_length: int = 50) -> str:
    """
    Generate a conversation title from the first message.
    
    Args:
        message: First message in conversation
        max_length: Maximum title length
        
    Returns:
        Generated title
    """
    # Clean and truncate message
    title = message.strip()
    
    # Remove common question words to make title more concise
    for word in ["¿", "?", "cómo", "qué", "cuál", "dónde", "cuándo", "por qué"]:
        title = title.replace(word, "").strip()
    
    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    # Ensure it's not empty
    if not title:
        title = "Nueva conversación"
    
    return title.capitalize()

def sanitize_message(message: str) -> str:
    """
    Sanitize user message for safety.
    
    Args:
        message: Raw user message
        
    Returns:
        Sanitized message
    """
    # Basic sanitization - remove potentially harmful characters
    # In production, you might want more sophisticated sanitization
    message = message.strip()
    
    # Remove or escape potentially problematic characters
    dangerous_chars = ["<script", "</script", "javascript:", "eval(", "alert("]
    for char in dangerous_chars:
        message = message.replace(char, "")
    
    return message

def format_error_message(error: Exception) -> str:
    """
    Format error message for user display.
    
    Args:
        error: Exception object
        
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    if "connection" in error_str:
        return "Error de conexión. Por favor, verifica tu conexión a internet e intenta nuevamente."
    elif "timeout" in error_str:
        return "La operación tardó demasiado tiempo. Por favor, intenta nuevamente."
    elif "authentication" in error_str or "auth" in error_str:
        return "Error de autenticación. Por favor, verifica tus credenciales."
    elif "database" in error_str or "neo4j" in error_str:
        return "Error en la base de datos. Por favor, contacta al administrador del sistema."
    else:
        return "Ocurrió un error inesperado. Por favor, intenta nuevamente."