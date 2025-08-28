#!/usr/bin/env python3
"""
RAG System Setup and Configuration Utility
Helps with initial setup, configuration, and environment preparation
"""

import os
import sys
import json
from typing import Dict, Any, List
import argparse

def check_environment() -> Dict[str, Any]:
    """Check if the environment is properly set up for RAG system"""
    status = {
        "python_version": sys.version,
        "required_files": {},
        "environment_vars": {},
        "dependencies": {},
        "overall_status": "unknown"
    }
    
    # Check required files
    required_files = [
        "test_data.json",
        "sample.md", 
        ".env.example",
        "requirements.txt",
        "rag.py"
    ]
    
    for file_path in required_files:
        status["required_files"][file_path] = os.path.exists(file_path)
    
    # Check environment variables
    env_vars = ["GOOGLE_API_KEY"]
    for var in env_vars:
        status["environment_vars"][var] = os.getenv(var) is not None
    
    # Check if .env file exists
    status["environment_vars"][".env_file"] = os.path.exists(".env")
    
    # Try to import required dependencies
    dependencies = [
        "langchain_core",
        "langchain_google_genai", 
        "langchain_weaviate",
        "weaviate",
        "dotenv"
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            status["dependencies"][dep] = True
        except ImportError:
            status["dependencies"][dep] = False
    
    # Determine overall status
    files_ok = all(status["required_files"].values())
    deps_ok = all(status["dependencies"].values())
    env_ok = status["environment_vars"]["GOOGLE_API_KEY"]
    
    if files_ok and deps_ok and env_ok:
        status["overall_status"] = "ready"
    elif files_ok and deps_ok:
        status["overall_status"] = "needs_env_config"
    elif files_ok:
        status["overall_status"] = "needs_dependencies"
    else:
        status["overall_status"] = "needs_setup"
    
    return status

def create_env_file():
    """Create .env file from .env.example"""
    if not os.path.exists(".env.example"):
        print("❌ .env.example file not found")
        return False
    
    if os.path.exists(".env"):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    try:
        with open(".env.example", 'r') as f:
            content = f.read()
        
        with open(".env", 'w') as f:
            f.write(content)
        
        print("✅ Created .env file from .env.example")
        print("📝 Please edit .env file and add your GOOGLE_API_KEY")
        return True
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt file not found")
        return False
    
    print("📦 Installing dependencies...")
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Error installing dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running pip install: {e}")
        return False

def validate_test_data():
    """Validate test data file"""
    if not os.path.exists("test_data.json"):
        print("❌ test_data.json file not found")
        return False
    
    try:
        with open("test_data.json", 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        if not isinstance(test_cases, list):
            print("❌ test_data.json should contain a list of test cases")
            return False
        
        print(f"✅ test_data.json is valid with {len(test_cases)} test cases")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in test_data.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading test_data.json: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = ["exports", "logs", "temp"]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"❌ Error creating directory {directory}: {e}")

def print_status_report(status: Dict[str, Any]):
    """Print detailed status report"""
    print("🔍 RAG System Environment Status")
    print("=" * 50)
    
    print(f"\n🐍 Python Version: {status['python_version']}")
    
    print(f"\n📁 Required Files:")
    for file_path, exists in status["required_files"].items():
        icon = "✅" if exists else "❌"
        print(f"  {icon} {file_path}")
    
    print(f"\n🔧 Environment Variables:")
    for var, exists in status["environment_vars"].items():
        icon = "✅" if exists else "❌"
        print(f"  {icon} {var}")
    
    print(f"\n📦 Dependencies:")
    for dep, installed in status["dependencies"].items():
        icon = "✅" if installed else "❌"
        print(f"  {icon} {dep}")
    
    print(f"\n🎯 Overall Status: {status['overall_status'].upper()}")
    
    # Provide recommendations
    if status['overall_status'] == "ready":
        print("🎉 System is ready to use!")
    elif status['overall_status'] == "needs_env_config":
        print("💡 Run: python setup_rag.py create-env")
        print("   Then edit .env file with your API keys")
    elif status['overall_status'] == "needs_dependencies":
        print("💡 Run: python setup_rag.py install-deps")
    else:
        print("💡 Run: python setup_rag.py full-setup")

def full_setup():
    """Perform complete system setup"""
    print("🚀 Starting full RAG system setup...")
    
    # Create directories
    setup_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False
    
    # Create .env file
    if not create_env_file():
        print("❌ Setup failed at .env file creation")
        return False
    
    # Validate test data
    if not validate_test_data():
        print("❌ Setup failed at test data validation")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("📝 Next steps:")
    print("1. Edit .env file and add your GOOGLE_API_KEY")
    print("2. Run: python rag.py")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="RAG System Setup Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check system status")
    
    # Create env command
    env_parser = subparsers.add_parser("create-env", help="Create .env file")
    
    # Install deps command
    deps_parser = subparsers.add_parser("install-deps", help="Install dependencies")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate test data")
    
    # Full setup command
    setup_parser = subparsers.add_parser("full-setup", help="Perform complete setup")
    
    args = parser.parse_args()
    
    if not args.command:
        # Default to status check
        args.command = "status"
    
    if args.command == "status":
        status = check_environment()
        print_status_report(status)
    
    elif args.command == "create-env":
        create_env_file()
    
    elif args.command == "install-deps":
        install_dependencies()
    
    elif args.command == "validate":
        validate_test_data()
    
    elif args.command == "full-setup":
        full_setup()

if __name__ == "__main__":
    main()