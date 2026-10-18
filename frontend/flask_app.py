"""LUCA: frontend Flask (login, chat con el tutor, panel de prácticas, conversaciones)."""

import os
import secrets
import sys
import asyncio
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from functools import wraps

from flask import Flask, render_template, request, jsonify, session
from werkzeug.middleware.proxy_fix import ProxyFix

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.executor import TutorExecutor
from course.practices import get_practice_repository
from auth import authenticate_user, generate_conversation_title
from storage import db
from utils import get_subjects as load_subjects


PRODUCTION = os.environ.get('FLASK_ENV') == 'production'
MAX_MESSAGE_CHARS = 4000  # caps what a single request can cost in LLM tokens
# Placeholders that have shipped in templates or code: never valid as a real key.
WEAK_SECRET_KEYS = {
    '', 'CHANGEME', 'dev-secret-key-change-in-production', 'dev-secret-key-for-luca',
    'production-secret-key-change-me', 'your-secure-secret-key-for-production',
}

app = Flask(__name__)
_secret_key = os.environ.get('FLASK_SECRET_KEY', '')
if _secret_key in WEAK_SECRET_KEYS:
    if PRODUCTION:
        raise RuntimeError("FLASK_SECRET_KEY falta o es un valor de ejemplo. Generá una con: python -c "
                           "\"import secrets; print(secrets.token_hex(32))\"")
    _secret_key = secrets.token_hex(32)  # development: sessions don't survive a restart
app.secret_key = _secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('LUCA_COOKIE_SECURE', '1' if PRODUCTION else '0') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=64 * 1024,
)
if os.environ.get('LUCA_BEHIND_PROXY') == '1':
    # Behind exactly one reverse proxy (Caddy): trust its X-Forwarded-* to get the client IP and scheme.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


class LoginThrottle:
    """Failed logins per client IP and per email in a sliding window. In memory: run a single worker."""

    def __init__(self, max_per_ip: int = 20, max_per_email: int = 5, window_seconds: int = 900):
        self.limits = {'ip': max_per_ip, 'email': max_per_email}
        self.window = window_seconds
        self._failures: Dict[tuple, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, key: tuple) -> deque:
        q = self._failures[key]
        while q and q[0] < time.time() - self.window:
            q.popleft()
        return q

    def blocked(self, ip: str, email: str) -> bool:
        with self._lock:
            return (len(self._recent(('ip', ip))) >= self.limits['ip']
                    or len(self._recent(('email', email))) >= self.limits['email'])

    def failure(self, ip: str, email: str) -> None:
        with self._lock:
            now = time.time()
            self._failures[('ip', ip)].append(now)
            self._failures[('email', email)].append(now)

    def success(self, email: str) -> None:
        with self._lock:
            self._failures.pop(('email', email), None)


login_throttle = LoginThrottle()

# Fail at startup rather than on the first page load if `python -m ingest` hasn't run.
get_practice_repository()

# Global tutor (shared across requests: conversation memory lives in its checkpointer)
tutor = TutorExecutor()

class ActivityMarker:
    """Touches LUCA_ACTIVITY_FILE on authenticated use; the idle-shutdown timer reads its mtime (deploy/aws).

    Only logged-in users count, so bots and health checks don't keep the server awake. At most once a minute.
    """

    def __init__(self, path: Optional[str], min_interval_seconds: int = 60):
        self.path = Path(path) if path else None
        self.min_interval = min_interval_seconds
        self._last = 0.0

    def touch(self) -> None:
        if self.path is None or time.time() - self._last < self.min_interval:
            return
        self._last = time.time()
        try:
            self.path.touch()
        except OSError as e:
            print(f"⚠️ Could not update the activity marker {self.path}: {e}")


activity = ActivityMarker(os.environ.get('LUCA_ACTIVITY_FILE'))


def require_auth(f):
    """Decorator to require authentication for protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            if request.is_json:
                return jsonify({'error': 'Not authenticated'}), 401
            else:
                return render_template('login.html')
        activity.touch()
        return f(*args, **kwargs)
    return decorated_function

# Templates use inline <script> and onclick handlers, hence 'unsafe-inline'; third-party code is limited
# to the pinned CDN files, each with an SRI hash in base.html.
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
    "font-src 'self' https://cdnjs.cloudflare.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])


@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = CONTENT_SECURITY_POLICY
    if app.config['SESSION_COOKIE_SECURE']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.route('/healthz')
def healthz():
    """Liveness probe for Docker and the reverse proxy (no auth, no data)."""
    return jsonify({'status': 'ok'})

@app.route('/')
@require_auth
def index():
    """Main chat interface."""
    # Get subjects for dropdown
    subjects = load_subjects()
    user_email = session.get('user_email', '')
    conversations = db.list_conversations(user_email)
    
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
    try:
        data = request.json
        if not data:
            print("⚠️ Login attempt with no data")
            return jsonify({'success': False, 'error': 'Datos de login requeridos'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        # Basic validation
        if not email or not password:
            print(f"⚠️ Login attempt with missing credentials from IP: {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Email y contraseña son requeridos'}), 400
        
        # Domain validation
        if not email.endswith('@uca.edu.ar'):
            print(f"⚠️ Login attempt with invalid domain: {email} from IP: {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Email debe ser del dominio @uca.edu.ar'}), 400
        
        ip = request.remote_addr or 'unknown'
        if login_throttle.blocked(ip, email):
            print(f"⛔ Login throttled for {email} from IP: {ip}")
            return jsonify({'success': False, 'error': 'Demasiados intentos fallidos. Probá de nuevo en unos minutos.'}), 429

        user = authenticate_user(email, password)
        if user:
            session.clear()  # drop anything from a previous session before authenticating
            session.permanent = True
            session['authenticated'] = True
            session['user_email'] = email
            session['login_time'] = datetime.now().isoformat()
            login_throttle.success(email)
            activity.touch()
            print(f"✅ Successful login for user: {email} from IP: {ip}")
            return jsonify({'success': True})
        login_throttle.failure(ip, email)
        print(f"❌ Failed login attempt for user: {email} from IP: {ip}")
        return jsonify({'success': False, 'error': 'Email o contraseña incorrectos'}), 401
            
    except Exception as e:
        print(f"🚨 Login error: {e} from IP: {request.remote_addr}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

@app.route('/logout')
@require_auth
def logout():
    """Handle user logout."""
    user_email = session.get('user_email', 'unknown')
    print(f"🚪 User {user_email} logging out")
    session.clear()
    return jsonify({'success': True})

@app.route('/auth/status')
def auth_status():
    """Check authentication status."""
    if 'authenticated' in session and 'user_email' in session:
        return jsonify({
            'authenticated': True,
            'user_email': session.get('user_email')
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/chat', methods=['POST'])
@require_auth
def chat():
    """Handle a chat message. The conversation id is also the tutor's memory thread."""
    data = request.json
    message = data.get('message', '').strip()
    subject = data.get('subject')
    conversation_id = data.get('conversation_id') or None
    exercise_id = data.get('exercise_id') or None
    user_email = session.get('user_email')

    if not message:
        return jsonify({'error': 'Message is required'}), 400
    if len(message) > MAX_MESSAGE_CHARS:
        return jsonify({'success': False, 'error': f'El mensaje es demasiado largo (máximo {MAX_MESSAGE_CHARS} caracteres).'}), 400
    # The id selects the tutor's memory: never let a user write to (or read) someone else's thread.
    if conversation_id and db.conversation_owner(conversation_id) != user_email:
        return jsonify({'success': False, 'error': 'Access denied to this conversation'}), 403

    try:
        return jsonify(process_message_sync(message, user_email, subject, conversation_id, exercise_id))
    except Exception as e:
        print(f"❌ Flask chat error: {e}")
        import traceback
        traceback.print_exc()
        # Details stay in the server log: they can include internal paths or provider messages.
        return jsonify({
            'success': False,
            'error': 'Error interno',
            'content': 'Error al procesar el mensaje. Por favor, intentá nuevamente.'
        }), 500

def process_message_sync(message: str, user_email: str, subject: Optional[str], conversation_id: Optional[str],
                         exercise_id: Optional[str]) -> Dict[str, Any]:
    """Run one tutor turn (asyncio.run per request) and persist both messages."""
    is_new = conversation_id is None
    if is_new:
        conversation_id = db.create_conversation(user_email, message[:60], subject)

    async def _process():
        progress_steps = []
        final_response = ""
        structured_response = {}
        # Consume the whole stream: the guardrails' output validation runs after the final answer.
        async for chunk in tutor.stream(message, conversation_id, exercise_id=exercise_id, user_id=user_email, subject=subject):
            if chunk.get('is_task_complete'):
                final_response = chunk.get('content', 'No se pudo obtener respuesta')
                structured_response = chunk.get('structured_response', {})
            elif chunk.get('guardrail_step') == 'response_validation':
                violations = chunk['response_validation'].get('violations', [])
                print(f"⚠️ Response validation for {conversation_id}: {[v.get('message') for v in violations]}")
            elif chunk.get('content'):
                progress_steps.append(chunk['content'])
        return final_response, structured_response, progress_steps

    final_response, structured_response, progress_steps = asyncio.run(_process())
    db.add_message(conversation_id, "user", message, exercise_id)
    db.add_message(conversation_id, "assistant", final_response, exercise_id)
    if is_new:
        db.rename_conversation(conversation_id, generate_conversation_title(message, subject or ""))

    return {
        'content': final_response,
        'progress_steps': progress_steps,
        'success': True,
        'conversation_id': conversation_id,
        'exercise_id': exercise_id,
        'modo': structured_response.get('modo'),
        'fuentes': structured_response.get('fuentes', []),
    }

@app.route('/conversations')
@require_auth
def get_conversations():
    """Get user conversations."""
    return jsonify(db.list_conversations(session.get('user_email', '')))

@app.route('/conversations', methods=['POST'])
@require_auth
def create_new_conversation():
    """Create a new conversation."""
    data = request.json or {}
    conv_id = db.create_conversation(session.get('user_email', ''), data.get('title', 'Nueva Conversación'), data.get('subject'))
    return jsonify({'success': True, 'conversation_id': conv_id})

@app.route('/subjects')
@require_auth
def get_subjects():
    """Get available subjects."""
    subjects = load_subjects()
    return jsonify(subjects)

@app.route('/practicas')
@require_auth
def get_practicas():
    """Practices tree for the side panel (statements only, no solutions)."""
    return jsonify(get_practice_repository().tree())

@app.route('/conversations/<conversation_id>/messages')
@require_auth
def get_conversation_history(conversation_id):
    """Message history (with the exercise each message was about) of one of the user's conversations."""
    if db.conversation_owner(conversation_id) != session.get('user_email'):
        return jsonify({'success': False, 'error': 'Access denied to this conversation'}), 403
    return jsonify({'success': True, 'messages': db.list_messages(conversation_id, limit=50)})

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
@require_auth
def delete_conversation_endpoint(conversation_id):
    """Delete one of the user's conversations and its messages."""
    if db.delete_conversation(conversation_id, session.get('user_email', '')):
        return jsonify({'success': True, 'message': 'Conversación eliminada exitosamente'})
    return jsonify({'success': False, 'error': 'No se pudo eliminar la conversación'}), 400

if __name__ == '__main__':
    print("🚀 Starting LUCA Flask Frontend...")
    print("📡 Tutor initialized")
    print("🌐 Access the application at: http://localhost:8080")
    
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        threaded=True
    )