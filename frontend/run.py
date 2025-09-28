#!/usr/bin/env python3
"""
LUCA Frontend Runner - Flask Frontend

Script para ejecutar la aplicación Flask de LUCA.
Este es ahora el único frontend soportado.
Supports both HTTP and HTTPS modes with SSL certificates.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables if not already set
if 'FLASK_SECRET_KEY' not in os.environ:
    os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-for-luca'

if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'development'

def find_ssl_certificates():
    """
    Find SSL certificate files in the ssl directory.

    Returns:
        tuple: (cert_file, key_file) paths or (None, None) if not found
    """
    ssl_dir = project_root / 'ssl'
    cert_file = ssl_dir / 'luca.crt'
    key_file = ssl_dir / 'luca.key'

    if cert_file.exists() and key_file.exists():
        return str(cert_file), str(key_file)
    return None, None

def main():
    """Run the LUCA Flask frontend."""
    parser = argparse.ArgumentParser(description='Run LUCA Flask Frontend')
    parser.add_argument('--https', action='store_true',
                       help='Run with HTTPS using SSL certificates')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to run the application on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--cert', type=str,
                       help='Path to SSL certificate file')
    parser.add_argument('--key', type=str,
                       help='Path to SSL private key file')
    parser.add_argument('--no-debug', action='store_true',
                       help='Disable debug mode')

    args = parser.parse_args()

    try:
        from flask_app import app

        # SSL Configuration
        ssl_context = None
        protocol = "http"

        if args.https:
            # Use provided certificate files or find them automatically
            cert_file = args.cert
            key_file = args.key

            if not cert_file or not key_file:
                cert_file, key_file = find_ssl_certificates()

            if cert_file and key_file:
                ssl_context = (cert_file, key_file)
                protocol = "https"
                print("🔒 SSL certificates found and loaded")
                print(f"   Certificate: {cert_file}")
                print(f"   Private key: {key_file}")
            else:
                print("❌ SSL certificates not found!")
                print("💡 Generate certificates with: python scripts/generate_ssl_certs.py")
                print("🔄 Falling back to HTTP mode")
                args.https = False

        # Check if running in Docker environment
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('FLASK_ENV') == 'production'
        debug_mode = not args.no_debug and not is_docker

        print("🚀 Starting LUCA Flask Frontend...")
        print("📡 Orchestrator initialized")

        if args.https and ssl_context:
            print(f"🔐 Access the application at: {protocol}://{args.host}:{args.port}")
            print("⚠️  Browser will show security warning for self-signed certificates")
        else:
            print(f"🌐 Access the application at: {protocol}://{args.host}:{args.port}")

        print("📝 Test credentials: visitante@uca.edu.ar / visitante!")
        print("-" * 60)

        # Run Flask application
        app.run(
            host=args.host,
            port=args.port,
            debug=debug_mode,
            threaded=True,
            ssl_context=ssl_context
        )
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        print("💡 Install dependencies with: pip install flask flask-cors")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 LUCA Frontend stopped by user")
    except Exception as e:
        print(f"❌ Error running Flask Frontend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()