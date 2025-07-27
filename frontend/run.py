#!/usr/bin/env python3
"""
LUCA Frontend Runner - Updated to use the new unified launcher.

This script now redirects to the unified launcher that allows choosing
between Flask (recommended) and Streamlit (legacy) frontends.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the LUCA frontend launcher."""
    
    print("🎓 LUCA Frontend - Redirecting to unified launcher...")
    print("⚠️  NOTA: Este script ahora usa el launcher unificado.")
    print("💡 Recomendamos usar el Flask Frontend para mejor estabilidad.")
    print("=" * 60)
    
    # Get the frontend directory
    frontend_dir = Path(__file__).parent
    launcher_path = frontend_dir / "launcher.py"
    
    if launcher_path.exists():
        try:
            # Run the unified launcher
            subprocess.run([sys.executable, str(launcher_path)], check=True)
        except KeyboardInterrupt:
            print("\n👋 LUCA Frontend stopped by user")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running launcher: {e}")
            sys.exit(1)
    else:
        print("❌ Launcher not found. Falling back to direct Streamlit execution...")
        print("💡 Consider using the Flask frontend instead: python run_flask.py")
        
        # Fallback to original Streamlit execution
        legacy_main()

def legacy_main():
    """Original Streamlit execution (legacy fallback)."""
    
    # Get the frontend directory
    frontend_dir = Path(__file__).parent
    
    # Add the project root to Python path
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
    
    print("📊 Starting LUCA Streamlit Frontend (Legacy)...")
    print(f"Frontend directory: {frontend_dir}")
    print(f"Command: {' '.join(cmd)}")
    print("⚠️  WARNING: Streamlit frontend has known issues with multi-turn conversations")
    print("="*50)
    
    try:
        # Run Streamlit
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 LUCA Frontend stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running LUCA Frontend: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Streamlit not found. Please install it with: pip install streamlit")
        print("💡 Or use the Flask Frontend: python run_flask.py")
        sys.exit(1)

if __name__ == "__main__":
    main()