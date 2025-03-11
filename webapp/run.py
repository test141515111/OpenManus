#!/usr/bin/env python
import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webapp.async_app import socket_app

if __name__ == "__main__":
    import uvicorn
    
    # Try to find an available port
    port = 8080
    import socket
    
    # Check if port is available
    def is_port_available(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0
    
    # Find available port
    while not is_port_available(port) and port < 8100:
        print(f"Port {port} is in use, trying next port...")
        port += 1
    
    print(f"Starting server on port {port}")
    uvicorn.run(socket_app, host='0.0.0.0', port=port)
