#!/usr/bin/env python3
"""
LUCA Frontend Launcher - Unified launcher for both Flask and Streamlit frontends.

This script allows you to choose between the modern Flask frontend (recommended)
or the legacy Streamlit frontend.
"""

import os
import sys
import subprocess
from pathlib import Path

def show_banner():
    """Display LUCA banner and frontend options."""
    print("=" * 60)
    print("🎓 LUCA - Asistente Educativo Frontend Launcher")
    print("=" * 60)
    print()
    print("Elige el frontend que deseas ejecutar:")
    print()
    print("1. 🚀 Flask Frontend (RECOMENDADO)")
    print("   - Soluciona problemas de conversaciones multi-turno")
    print("   - Mejor rendimiento y estabilidad")
    print("   - Interfaz moderna con Bootstrap 5")
    print("   - Compatible con Neo4j persistence")
    print("   - URL: http://localhost:5000")
    print()
    print("2. 📊 Streamlit Frontend (LEGACY)")
    print("   - Frontend original con problemas conocidos")
    print("   - Se cuelga en conversaciones multi-turno")
    print("   - Solo para testing y compatibilidad")
    print("   - URL: http://localhost:8501")
    print()
    print("3. ❌ Salir")
    print()

def run_flask_frontend():
    """Run the Flask frontend."""
    print("🚀 Iniciando LUCA Flask Frontend...")
    print("📡 URL: http://localhost:5000")
    print("📝 Credenciales de prueba: visitante@uca.edu.ar / visitante!")
    print("-" * 50)
    
    # Get the frontend directory
    frontend_dir = Path(__file__).parent
    project_root = frontend_dir.parent
    sys.path.insert(0, str(project_root))
    
    # Change to frontend directory
    os.chdir(frontend_dir)
    
    try:
        # Import and run Flask app
        from flask_app import app
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True
        )
    except ImportError as e:
        print(f"❌ Error importando Flask app: {e}")
        print("💡 Instala las dependencias con: pip install flask flask-cors")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 LUCA Flask Frontend detenido por el usuario")
    except Exception as e:
        print(f"❌ Error ejecutando Flask Frontend: {e}")
        sys.exit(1)

def run_streamlit_frontend():
    """Run the Streamlit frontend."""
    print("📊 Iniciando LUCA Streamlit Frontend (Legacy)...")
    print("⚠️  ADVERTENCIA: Este frontend tiene problemas conocidos con conversaciones multi-turno")
    print("📡 URL: http://localhost:8501")
    print("-" * 50)
    
    # Get the frontend directory
    frontend_dir = Path(__file__).parent
    project_root = frontend_dir.parent
    sys.path.insert(0, str(project_root))
    
    # Change to frontend directory
    os.chdir(frontend_dir)
    
    # Streamlit configuration
    config_args = [
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--theme.base=light",
        "--theme.primaryColor=#007bff",
        "--theme.backgroundColor=#ffffff",
        "--theme.secondaryBackgroundColor=#f0f2f6"
    ]
    
    # Build command
    cmd = ["streamlit", "run", "app.py"] + config_args
    
    try:
        # Run Streamlit
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 LUCA Streamlit Frontend detenido por el usuario")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando Streamlit Frontend: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Streamlit no encontrado. Instálalo con: pip install streamlit")
        print("💡 O usa el Flask Frontend que no requiere Streamlit")
        sys.exit(1)

def main():
    """Main launcher function."""
    while True:
        show_banner()
        
        try:
            choice = input("Selecciona una opción (1-3): ").strip()
            
            if choice == "1":
                run_flask_frontend()
                break
            elif choice == "2":
                confirm = input("⚠️  ¿Estás seguro de usar el frontend con problemas? (y/N): ").strip().lower()
                if confirm in ['y', 'yes', 'sí', 'si']:
                    run_streamlit_frontend()
                    break
                else:
                    continue
            elif choice == "3":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida. Por favor, selecciona 1, 2 o 3.")
                input("Presiona Enter para continuar...")
                os.system('clear' if os.name == 'posix' else 'cls')
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except EOFError:
            print("\n👋 ¡Hasta luego!")
            break

if __name__ == "__main__":
    main()