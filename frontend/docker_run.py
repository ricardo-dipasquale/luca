#!/usr/bin/env python3
"""
LUCA Docker Runner - Flask Frontend

Docker-optimized script for running LUCA Flask application.
Supports both HTTP and HTTPS modes based on environment variables.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def find_ssl_certificates():
    """
    Find SSL certificate files in the ssl directory.

    Returns:
        tuple: (cert_file, key_file) paths or (None, None) if not found
    """
    # Try multiple possible SSL locations
    possible_ssl_dirs = [
        Path('/app/ssl'),           # Docker mounted path
        Path('../ssl'),             # Relative to frontend dir
        Path('./ssl'),              # Current directory
        project_root / 'ssl'        # Project root
    ]

    for ssl_dir in possible_ssl_dirs:
        cert_file = ssl_dir / 'luca.crt'
        key_file = ssl_dir / 'luca.key'

        if cert_file.exists() and key_file.exists():
            print(f"🔍 SSL certificates found in: {ssl_dir}")
            return str(cert_file), str(key_file)

    print(f"🔍 SSL certificates not found in any of these locations:")
    for ssl_dir in possible_ssl_dirs:
        print(f"   - {ssl_dir} (exists: {ssl_dir.exists()})")

    return None, None

def main():
    """Run the LUCA Flask frontend in Docker environment."""
    try:
        # Debug: Print current working directory and Python path
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries

        # Try importing Flask app with better error handling
        try:
            from flask_app import app
            print("✅ Flask app imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import flask_app: {e}")
            print("📁 Current directory contents:")
            print(os.listdir('.'))
            raise

        # Get configuration from environment variables
        enable_https = os.environ.get('LUCA_ENABLE_HTTPS', 'true').lower() == 'true'
        # Always use port 5000 inside container (Docker maps 443:5000)
        port = 5000
        host = '0.0.0.0'

        # SSL Configuration
        ssl_context = None
        protocol = "http"

        if enable_https:
            cert_file, key_file = find_ssl_certificates()

            if cert_file and key_file:
                ssl_context = (cert_file, key_file)
                protocol = "https"
                print("🔒 SSL certificates found and loaded")
                print(f"   Certificate: {cert_file}")
                print(f"   Private key: {key_file}")
            else:
                print("⚠️  SSL certificates not found, falling back to HTTP")
                print("💡 SSL certificates should be mounted at /app/ssl/")

        print("🚀 Starting LUCA Flask Frontend (Docker)")
        print("📡 Orchestrator initialized")

        if enable_https and ssl_context:
            print(f"🔐 Running on {protocol}://localhost:443 (external)")
            print(f"🔗 Container internal: {protocol}://{host}:{port}")
            print("⚠️  Browser will show security warning for self-signed certificates")
        else:
            print(f"🌐 Running on {protocol}://localhost:{port}")

        print("📝 Test credentials: visitante@uca.edu.ar / visitante!")
        print("-" * 60)

        # Run Flask application (production mode, no debug)
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True,
            ssl_context=ssl_context
        )

    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 LUCA Frontend stopped")
    except Exception as e:
        print(f"❌ Error running Flask Frontend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()