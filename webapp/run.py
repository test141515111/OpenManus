#!/usr/bin/env python3
"""
Run the OpenManus Web UI application
"""
import os
import sys
import asyncio
import hypercorn.asyncio
from hypercorn.config import Config

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the application
from webapp.app import socket_app

# Configure Hypercorn
config = Config()
config.bind = ["0.0.0.0:8080"]
config.use_reloader = True

# Run the application
if __name__ == "__main__":
    asyncio.run(hypercorn.asyncio.serve(socket_app, config))
