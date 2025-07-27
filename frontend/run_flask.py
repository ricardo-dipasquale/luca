#!/usr/bin/env python3
"""
LUCA Flask Frontend Runner

Script para ejecutar la aplicación Flask de LUCA.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables if not already set
if 'FLASK_SECRET_KEY' not in os.environ:
    os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-for-luca'

if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'development'

from flask_app import app

if __name__ == '__main__':
    print("🚀 Starting LUCA Flask Frontend...")
    print("📡 Orchestrator initialized")
    print("🌐 Access the application at: http://localhost:5000")
    print("📝 Test credentials: visitante@uca.edu.ar / visitante!")
    print("-" * 60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )