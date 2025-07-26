#!/usr/bin/env python3
"""
Run script for LUCA frontend application.

This script starts the Streamlit application with proper configuration.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the LUCA frontend application."""
    
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
    
    print("🎓 Starting LUCA Frontend...")
    print(f"Frontend directory: {frontend_dir}")
    print(f"Project root: {project_root}")
    print(f"Command: {' '.join(cmd)}")
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
        sys.exit(1)

if __name__ == "__main__":
    main()