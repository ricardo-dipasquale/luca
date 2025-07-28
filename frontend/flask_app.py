"""
LUCA Flask Frontend - Reemplazo del frontend de Streamlit

Frontend web moderno usando Flask que evita los problemas de AsyncIO y 
persistencia que tiene Streamlit con LangGraph.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

from flask import Flask, render_template, request, jsonify, session, stream_template
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.agent_executor import OrchestratorAgentExecutor
from auth import authenticate_user, get_user_conversations, create_conversation, generate_conversation_title, update_conversation, increment_message_count, add_message_to_conversation, get_conversation_messages
from utils import get_subjects_from_kg, format_timestamp


class Neo4jJSONProvider(DefaultJSONProvider):
    """Custom JSON provider that handles Neo4j DateTime objects."""
    
    def default(self, obj):
        """Convert Neo4j DateTime objects to strings."""
        if hasattr(obj, 'to_native'):
            # Neo4j DateTime object
            return obj.to_native().strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.json = Neo4jJSONProvider(app)  # Use custom JSON provider
CORS(app)

# Global orchestrator instance (shared across requests for session persistence)
orchestrator = OrchestratorAgentExecutor()

@app.route('/')
def index():
    """Main chat interface."""
    if 'authenticated' not in session:
        return render_template('login.html')
    
    # Get subjects for dropdown
    subjects = get_subjects_from_kg()
    user_email = session.get('user_email', '')
    conversations = get_user_conversations(user_email)
    
    print(f"🔍 Loading chat for user: {user_email}")
    print(f"📋 Found {len(conversations)} conversations")
    if conversations:
        print(f"📄 First conversation: {conversations[0].get('title', 'No title')}")
    
    return render_template('chat.html', 
                         subjects=subjects,
                         conversations=conversations,
                         user_email=user_email)

@app.route('/login', methods=['POST'])
def login():
    """Handle user authentication."""
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email.endswith('@uca.edu.ar'):
        return jsonify({'success': False, 'error': 'Email debe ser del dominio @uca.edu.ar'})
    
    user = authenticate_user(email, password)
    if user:
        session['authenticated'] = True
        session['user_email'] = email
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Email o contraseña incorrectos'})

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages with streaming response."""
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    message = data.get('message', '').strip()
    subject = data.get('subject')
    conversation_id = data.get('conversation_id')
    use_conversation_memory = data.get('use_conversation_memory', False)
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Generate session ID with memory continuity strategy
    if conversation_id and use_conversation_memory:
        # Use conversation_id as session_id for EXISTING conversations (selected from list)
        session_id = conversation_id
        print(f"🔄 Using conversation {conversation_id} for memory continuity")
    else:
        # For new conversations, maintain same temp session throughout the conversation
        # This ensures memory continuity within the same conversation thread
        if 'temp_session_id' not in session:
            session['temp_session_id'] = f"temp_session_{uuid4().hex[:8]}"
        session_id = session['temp_session_id']
        print(f"🆕 Using temporary session {session_id} (memory will persist within this conversation)")
    
    print(f"🎯 Flask processing message: {message}")
    print(f"🎯 Session: {session_id}")
    print(f"🎯 Subject: {subject}")
    
    try:
        # Process message synchronously
        result = process_message_sync(message, session_id, subject, conversation_id, session.get('user_email'))
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Flask chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'content': 'Error al procesar el mensaje. Por favor, intenta nuevamente.'
        }), 500

def process_message_sync(message: str, session_id: str, subject: Optional[str] = None, conversation_id: Optional[str] = None, user_email: Optional[str] = None) -> Dict[str, Any]:
    """Process message synchronously using asyncio.run in new event loop."""
    async def _process():
        # Initialize conversation_id in local scope
        local_conversation_id = conversation_id
        
        context = {
            'session_id': session_id,
            'user_id': 'flask_user'
        }
        
        if subject:
            context['educational_subject'] = subject
        
        print(f"🔍 Processing with context: {context}")
        
        progress_steps = []
        final_response = ""
        is_first_message = local_conversation_id is None
        
        async for chunk in orchestrator.stream(
            request={'message': message},
            context=context
        ):
            print(f"📦 Received chunk: {chunk.get('content', 'No content')[:100]}...")
            
            if chunk.get('is_task_complete'):
                final_response = chunk.get('content', 'No se pudo obtener respuesta')
                print(f"✅ Final response received")
                break
            else:
                progress_text = chunk.get('content', 'Procesando...')
                progress_steps.append(progress_text)
        
        # Handle conversation management
        if user_email and subject:
            message_order = 1  # Default for new conversations
            
            if is_first_message:
                # Generate descriptive title for new conversation
                generated_title = generate_conversation_title(message, subject)
                new_conversation_id = create_conversation(user_email, generated_title, subject)
                print(f"📝 Created new conversation '{generated_title}' with ID: {new_conversation_id}")
                
                # Update local conversation ID
                local_conversation_id = new_conversation_id
                
                # IMPORTANT: Migrate memory from temp session to conversation session
                # The orchestrator needs consistent session_id to maintain memory
                print(f"💾 Migrating memory from session {session_id} to conversation {new_conversation_id}")
                
                # TODO: Implement memory migration
                # For now, we'll use a consistent session strategy to avoid memory loss
            else:
                # Get current message count to determine order
                existing_messages = get_conversation_messages(local_conversation_id, limit=1000)
                message_order = len(existing_messages) + 1
            
            # Save user message and assistant response to conversation
            if local_conversation_id:
                # Save user message
                add_message_to_conversation(local_conversation_id, message, "user", message_order)
                # Save assistant response
                add_message_to_conversation(local_conversation_id, final_response, "assistant", message_order + 1)
                
                # Increment message count (for both user message and assistant response)
                increment_message_count(local_conversation_id)
                increment_message_count(local_conversation_id)
                print(f"📈 Saved messages and incremented count for conversation: {local_conversation_id}")
        
        return {
            'content': final_response,
            'progress_steps': progress_steps,
            'success': True,
            'conversation_id': local_conversation_id,
            'session_id_used': session_id  # Return which session was used
        }
    
    # Always create fresh event loop for each request
    return asyncio.run(_process())

@app.route('/conversations')
def get_conversations():
    """Get user conversations."""
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_email = session.get('user_email', '')
    conversations = get_user_conversations(user_email)
    
    return jsonify(conversations)

@app.route('/conversations', methods=['POST'])
def create_new_conversation():
    """Create a new conversation."""
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    title = data.get('title', 'Nueva Conversación')
    subject = data.get('subject')
    
    conv_id = create_conversation(
        session.get('user_email', ''),
        title,
        subject
    )
    
    if conv_id:
        return jsonify({'success': True, 'conversation_id': conv_id})
    else:
        return jsonify({'success': False, 'error': 'No se pudo crear la conversación'})

@app.route('/subjects')
def get_subjects():
    """Get available subjects."""
    subjects = get_subjects_from_kg()
    return jsonify(subjects)

@app.route('/conversations/<conversation_id>/messages')
def get_conversation_history(conversation_id):
    """Get message history for a conversation."""
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        messages = get_conversation_messages(conversation_id, limit=20)
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        print(f"Error loading conversation history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting LUCA Flask Frontend...")
    print("📡 Orchestrator initialized")
    print("🌐 Access the application at: http://localhost:8080")
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        threaded=True
    )