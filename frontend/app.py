"""
LUCA - Frontend Chat Application

Interactive educational chat interface for LUCA system.
"""

import streamlit as st
import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Local imports
from auth import authenticate_user, get_user_conversations, create_conversation
from chat import get_orchestrator_client
from utils import get_subjects_from_kg, format_timestamp

# Configure Streamlit page
st.set_page_config(
    page_title="LUCA - Asistente Educativo",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom header styling */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .logo-fica {
        width: 80px;
        height: auto;
    }
    
    .logo-luca {
        width: 120px;
        height: auto;
    }
    
    /* Chat styling */
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background-color: #fafafa;
        margin-bottom: 1rem;
    }
    
    .message-user {
        background-color: #007bff;
        color: white;
        padding: 0.75rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-left: 20%;
        text-align: right;
    }
    
    .message-assistant {
        background-color: #f1f3f4;
        color: #333;
        padding: 0.75rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        margin-right: 20%;
    }
    
    .thinking-indicator {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #ffc107;
        font-style: italic;
    }
    
    /* Sidebar styling */
    .sidebar-conversation {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 8px;
        cursor: pointer;
        border: 1px solid #e0e0e0;
    }
    
    .sidebar-conversation:hover {
        background-color: #f0f0f0;
    }
    
    .sidebar-conversation.active {
        background-color: #007bff;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'current_conversation_id' not in st.session_state:
        st.session_state.current_conversation_id = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    if 'selected_subject' not in st.session_state:
        st.session_state.selected_subject = None
    if 'thinking' not in st.session_state:
        st.session_state.thinking = False

def show_login():
    """Display login form."""
    st.markdown("## 🎓 LUCA - Asistente Educativo")
    st.markdown("### Iniciar Sesión")
    
    with st.form("login_form"):
        email = st.text_input(
            "Email",
            placeholder="usuario@uca.edu.ar",
            help="Debe ser un email de dominio @uca.edu.ar"
        )
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")
        
        if submit:
            if not email.endswith("@uca.edu.ar"):
                st.error("El email debe ser del dominio @uca.edu.ar")
                return
                
            user = authenticate_user(email, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.success("¡Bienvenido/a a LUCA!")
                st.rerun()
            else:
                st.error("Email o contraseña incorrectos")

def show_header():
    """Display application header with logos."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.write("")  # Spacer
        
    with col2:
        try:
            st.image("frontend/assets/logo luca.png", width=200)
        except:
            st.markdown("### 🎓 LUCA")
            
    with col3:
        try:
            st.image("frontend/assets/Logo FICA uso excepcional color.png", width=80)
        except:
            st.markdown("#### FICA")

def show_sidebar():
    """Display sidebar with conversation history."""
    with st.sidebar:
        st.markdown("### 💬 Conversaciones")
        
        # New conversation button
        if st.button("➕ Nueva Conversación", use_container_width=True):
            create_new_conversation()
        
        st.markdown("---")
        
        # Load conversations if not loaded
        if not st.session_state.conversations:
            st.session_state.conversations = get_user_conversations(st.session_state.user_email)
        
        # Display conversations
        for conv in st.session_state.conversations:
            is_active = conv['id'] == st.session_state.current_conversation_id
            
            if st.button(
                f"📝 {conv['title'][:30]}{'...' if len(conv['title']) > 30 else ''}",
                key=f"conv_{conv['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_conversation_id = conv['id']
                load_conversation_messages(conv['id'])
                st.rerun()
            
            # Show conversation details
            if is_active:
                st.markdown(f"**Materia:** {conv.get('subject', 'No especificada')}")
                st.markdown(f"**Creada:** {format_timestamp(conv.get('created_at'))}")
                st.markdown(f"**Mensajes:** {conv.get('message_count', 0)}")

def create_new_conversation():
    """Create a new conversation."""
    if st.session_state.selected_subject:
        conv_id = create_conversation(
            st.session_state.user_email,
            f"Conversación sobre {st.session_state.selected_subject}",
            st.session_state.selected_subject
        )
        if conv_id:
            st.session_state.current_conversation_id = conv_id
            st.session_state.messages = []
            # Refresh conversations list
            st.session_state.conversations = get_user_conversations(st.session_state.user_email)
            st.success("Nueva conversación creada")
    else:
        st.warning("Selecciona una materia antes de crear una conversación")

def load_conversation_messages(conversation_id: str):
    """Load messages for a specific conversation."""
    # For now, we'll start with empty messages
    # In a full implementation, you'd load from the database
    st.session_state.messages = []

def show_subject_selector():
    """Display subject selection dropdown."""
    subjects = get_subjects_from_kg()
    
    if subjects:
        selected = st.selectbox(
            "📚 Selecciona una materia:",
            options=[""] + subjects,
            index=0 if not st.session_state.selected_subject else subjects.index(st.session_state.selected_subject) + 1,
            help="Elige la materia sobre la que quieres conversar"
        )
        
        if selected:
            st.session_state.selected_subject = selected
    else:
        st.error("No se pudieron cargar las materias. Verifica la conexión con la base de datos.")

def display_chat_messages():
    """Display chat messages."""
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="message-user">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="message-assistant">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Show thinking indicator if processing
        if st.session_state.thinking:
            st.markdown('<div class="thinking-indicator">🤔 LUCA está pensando...</div>', unsafe_allow_html=True)

def process_user_message_sync(user_input: str):
    """Process user message using synchronous orchestrator client."""
    if not st.session_state.selected_subject:
        st.warning("Selecciona una materia antes de enviar un mensaje")
        return
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.thinking = True
    
    # Show progress container
    progress_container = st.empty()
    
    try:
        print(f"🎯 Frontend processing message: {user_input}")
        print(f"🎯 Session: {st.session_state.current_conversation_id or 'temp_session'}")
        print(f"🎯 Subject: {st.session_state.selected_subject}")
        
        # Create client and process message synchronously
        client = get_orchestrator_client()
        
        # Show initial progress
        progress_container.markdown('<div class="thinking-indicator">🤔 Iniciando procesamiento...</div>', unsafe_allow_html=True)
        
        # Process message synchronously
        result = client.process_message_sync(
            user_input,
            st.session_state.current_conversation_id or "temp_session",
            st.session_state.selected_subject
        )
        
        # Show progress steps
        for step in result.get('progress_steps', []):
            progress_container.markdown(f'<div class="thinking-indicator">🤔 {step}</div>', unsafe_allow_html=True)
        
        print(f"📊 Frontend completed with {len(result.get('progress_steps', []))} steps")
        
        # Add assistant response
        response_content = result.get('content', 'No se pudo obtener respuesta')
        st.session_state.messages.append({"role": "assistant", "content": response_content})
        
        if not result.get('success', True):
            st.warning("Hubo un problema al procesar tu mensaje, pero aquí tienes una respuesta.")
        
    except Exception as e:
        print(f"❌ Frontend error: {e}")
        import traceback
        traceback.print_exc()
        
        st.error(f"Error al procesar el mensaje: {str(e)}")
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta nuevamente."
        })
    
    finally:
        st.session_state.thinking = False
        progress_container.empty()

def show_chat_interface():
    """Display main chat interface."""
    # Header
    show_header()
    
    # Subject selector
    show_subject_selector()
    
    st.markdown("---")
    
    # Chat messages
    st.markdown("### 💬 Conversación")
    display_chat_messages()
    
    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Escribe tu pregunta:",
            placeholder="Ejemplo: ¿Cómo funciona un LEFT JOIN en álgebra relacional?",
            height=100,
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns([4, 1])
        with col2:
            submit = st.form_submit_button("Enviar", use_container_width=True)
        
        if submit and user_input.strip():
            # Process message synchronously (Streamlit-friendly)
            process_user_message_sync(user_input.strip())
            st.rerun()

def main():
    """Main application function."""
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login()
    else:
        # Show sidebar
        show_sidebar()
        
        # Main content
        show_chat_interface()

if __name__ == "__main__":
    main()