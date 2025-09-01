#!/usr/bin/env python
"""
Quick start script for Xplainable MCP Server.

This script helps set up and test the MCP server locally.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if required dependencies are installed."""
    print("Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        return False
    print(f"✅ Python {sys.version}")
    
    # Check for .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Creating from .env.example...")
        
        example_path = Path(".env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text())
            print("   ✅ Created .env file - please edit it with your API key")
        else:
            print("   ❌ .env.example not found")
        return False
    else:
        print("✅ .env file found")
    
    # Check for API key
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("XPLAINABLE_API_KEY"):
        print("❌ XPLAINABLE_API_KEY not set in .env file")
        return False
    print("✅ API key configured")
    
    return True


def install_dependencies():
    """Install required dependencies."""
    print("\nInstalling dependencies...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            check=True
        )
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def run_tests():
    """Run the test suite."""
    print("\nRunning tests...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            check=True
        )
        print("✅ All tests passed")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Some tests failed - this may be expected if xplainable-client is not installed")
        return True  # Don't fail quickstart on test failures


def start_server():
    """Start the MCP server."""
    print("\nStarting MCP server...")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "xplainable_mcp.server"],
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        return False
    
    return True


def main():
    """Main quickstart flow."""
    print("=" * 60)
    print("Xplainable MCP Server - Quick Start")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        print("\n⚠️  Please fix the above issues and try again")
        print("\nTo set up your API key:")
        print("1. Edit the .env file")
        print("2. Add your Xplainable API key")
        print("3. Run this script again")
        return 1
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Run tests
    run_tests()
    
    # Prompt to start server
    print("\n" + "=" * 60)
    print("Setup complete! Ready to start the server.")
    print("=" * 60)
    
    response = input("\nStart the MCP server now? (y/n): ")
    if response.lower() == 'y':
        start_server()
    else:
        print("\nTo start the server manually, run:")
        print("  python -m xplainable_mcp.server")
        print("\nOr with Docker:")
        print("  docker-compose up")
    
    print("\n✅ Quick start complete!")
    print("\nNext steps:")
    print("1. Configure your MCP client to connect to the server")
    print("2. Review the README.md for available tools")
    print("3. Check SECURITY.md for production deployment")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())