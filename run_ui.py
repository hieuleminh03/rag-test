#!/usr/bin/env python3
"""
Simple launcher for the RAG Test Case Management Web UI
Handles basic setup and starts the Flask application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_flask():
    """Check if Flask is installed"""
    try:
        import flask
        return True
    except ImportError:
        return False

def install_flask():
    """Install Flask if not available"""
    print("📦 Installing Flask...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "flask", "--break-system-packages"], 
                      check=True, capture_output=True)
        print("✅ Flask installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Flask: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["templates", "static", "exports", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Directories created")

def check_files():
    """Check if required files exist"""
    required_files = [
        "test_data.json",
        "sample.md", 
        "data_manager.py",
        "rag_utils.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def main():
    print("🚀 Starting RAG Test Case Management Web UI...")
    print("=" * 50)
    
    # Check and install Flask if needed
    if not check_flask():
        if not install_flask():
            print("❌ Cannot proceed without Flask")
            sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Check required files
    if not check_files():
        print("⚠️  Some files are missing, but continuing anyway...")
    
    # Start the application
    print("\n🌐 Starting web server...")
    print("📊 Dashboard: http://localhost:5000")
    print("📋 Test Cases: http://localhost:5000/test-cases")
    print("🤖 RAG Demo: http://localhost:5000/rag-demo")
    print("📈 Coverage Analysis: http://localhost:5000/coverage-analysis")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Import and run the Flask app
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError as e:
        print(f"❌ Error importing app: {e}")
        print("Make sure app.py exists in the current directory")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()