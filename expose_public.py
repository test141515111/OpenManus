#!/usr/bin/env python3
import subprocess
import sys
import time

def expose_port_public():
    """Expose port 8080 without authentication for public access"""
    try:
        # Check if the server is running
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        if "webapp/run.py" not in result.stdout:
            print("Starting the OpenManus web server...")
            # Start the server in the background
            server_process = subprocess.Popen(
                ["python", "webapp/run.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd="/home/ubuntu/repos/OpenManus"
            )
            
            # Wait for the server to start
            time.sleep(5)
            print("Server started.")
        
        # Expose the port without authentication
        print("Exposing port 8080 for public access...")
        result = subprocess.run(
            ["expose_port", "local_port=8080", "auth=none"],
            capture_output=True,
            text=True
        )
        
        # Extract the URL from the result
        if result.returncode == 0:
            output = result.stdout
            print(f"Output: {output}")
            return output
        else:
            print(f"Error exposing port: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    url = expose_port_public()
    if url:
        print(f"Public URL: {url}")
    else:
        print("Failed to create public URL")
        sys.exit(1)
