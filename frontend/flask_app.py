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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.agent_executor import OrchestratorAgentExecutor
from auth import authenticate_user, get_user_conversations, create_conversation
from utils import get_subjects_from_kg, format_timestamp

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
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
    conversations = get_user_conversations(session.get('user_email', ''))
    
    return render_template('chat.html', 
                         subjects=subjects,
                         conversations=conversations,
                         user_email=session.get('user_email'))

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
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Generate session ID
    if conversation_id:
        session_id = conversation_id
    else:
        if 'temp_session_id' not in session:
            session['temp_session_id'] = f"temp_session_{uuid4().hex[:8]}"
        session_id = session['temp_session_id']
    
    print(f"🎯 Flask processing message: {message}")
    print(f"🎯 Session: {session_id}")
    print(f"🎯 Subject: {subject}")
    
    try:
        # Process message synchronously
        result = process_message_sync(message, session_id, subject)
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

def process_message_sync(message: str, session_id: str, subject: Optional[str] = None) -> Dict[str, Any]:
    """Process message synchronously using asyncio.run in new event loop."""
    async def _process():
        context = {
            'session_id': session_id,
            'user_id': 'flask_user'
        }
        
        if subject:
            context['educational_subject'] = subject
        
        print(f"🔍 Processing with context: {context}")
        
        progress_steps = []
        final_response = ""
        
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
        
        return {
            'content': final_response,
            'progress_steps': progress_steps,
            'success': True
        }
    
    # Always create fresh event loop for each request
    return asyncio.run(_process())

@app.route('/conversations')
def get_conversations():
    """Get user conversations."""
    if 'authenticated' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conversations = get_user_conversations(session.get('user_email', ''))
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

if __name__ == '__main__':
    print("🚀 Starting LUCA Flask Frontend...")
    print("📡 Orchestrator initialized")
    print("🌐 Access the application at: http://localhost:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )