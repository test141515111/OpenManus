#!/usr/bin/env python3
"""
Deploy the OpenManus Web UI with public access
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def ensure_templates():
    """Ensure all templates are in the correct directories."""
    try:
        print("Ensuring templates are in the correct directories...")
        
        # Create templates directory if it doesn't exist
        templates_dir = Path("webapp/templates")
        if not templates_dir.exists():
            templates_dir.mkdir(parents=True)
            
        # Create search templates directory if it doesn't exist
        search_templates_dir = templates_dir / "search"
        if not search_templates_dir.exists():
            search_templates_dir.mkdir(parents=True)
        
        return True
    except Exception as e:
        print(f"Error ensuring templates: {e}")
        return False

def ensure_static_files():
    """Ensure all static files are in the correct directories."""
    try:
        print("Ensuring static files are in the correct directories...")
        
        # Create static directory if it doesn't exist
        static_dir = Path("webapp/static")
        if not static_dir.exists():
            static_dir.mkdir(parents=True)
        
        return True
    except Exception as e:
        print(f"Error ensuring static files: {e}")
        return False

def start_server():
    """Start the OpenManus web server."""
    try:
        print("Starting the OpenManus web server...")
        
        # Check if the server is already running
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        if "webapp/run.py" in result.stdout:
            print("Server is already running.")
            return True
        
        # Ensure templates and static files
        ensure_templates()
        ensure_static_files()
        
        # Start the server in the background
        server_process = subprocess.Popen(
            ["python", "-m", "webapp.run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/home/ubuntu/repos/OpenManus"
        )
        
        # Wait for the server to start
        time.sleep(5)
        print("Server started.")
        
        return True
    except Exception as e:
        print(f"Error starting server: {e}")
        return False

def create_public_url():
    """Create a public URL without authentication."""
    try:
        print("Creating public URL without authentication...")
        
        # Start the server if it's not running
        if not start_server():
            return None
        
        # Use the expose_port command from Devin
        cmd = "expose_port local_port=8081 auth=none"
        print(f"Running command: {cmd}")
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Extract the URL from the result
        if result.returncode == 0:
            output = result.stdout
            print(f"Command output: {output}")
            if "URL:" in output:
                url = output.split("URL:")[1].strip()
                print(f"Public URL created: {url}")
                return url
            else:
                print("Failed to extract URL from output")
                return None
        else:
            print(f"Error creating public URL: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error creating public URL: {e}")
        return None

if __name__ == "__main__":
    url = create_public_url()
    if url:
        print(f"OpenManus Web UI is now publicly accessible at: {url}")
        print("You can access the search page at: {}/search".format(url))
    else:
        print("Failed to create public URL")
        sys.exit(1)
