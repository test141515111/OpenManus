#!/usr/bin/env python3
"""
Run the OpenManus Web UI
"""
import os
import sys
import asyncio

# Add the parent directory to the path so we can import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
    os.environ["PYTHONPATH"] = parent_dir

# Set OpenAI API key if available
if "oepnai" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["oepnai"]
    print(f"Set OpenAI API key from environment")

# Import the socket app
try:
    from webapp.app import socket_app
    print("Successfully imported socket_app")
except Exception as e:
    print(f"Error importing socket_app: {e}")
    sys.exit(1)

# Run the app
if __name__ == '__main__':
    try:
        import hypercorn.asyncio
        from hypercorn.config import Config as HyperConfig
        
        config = HyperConfig()
        config.bind = ["0.0.0.0:8081"]
        config.use_reloader = True
        
        print(f"Starting server on {config.bind[0]}")
        asyncio.run(hypercorn.asyncio.serve(socket_app, config))
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
