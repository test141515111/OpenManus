#!/usr/bin/env python3
import os
import sys
import subprocess

def deploy_backend():
    """Deploy the backend to a public URL using expose_port"""
    try:
        # Start the backend server
        print("Starting backend server...")
        server_process = subprocess.Popen(
            ["python", "webapp/run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/home/ubuntu/repos/OpenManus"
        )
        
        # Wait a bit for the server to start
        import time
        time.sleep(3)
        
        # Check if the server is running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"Error starting server: {stderr}")
            return None
        
        # Expose the port
        print("Exposing port 8081...")
        result = subprocess.run(
            ["expose_port", "local_port=8081"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Extract the URL from the output
        for line in result.stdout.splitlines():
            if "https://" in line:
                url = line.strip()
                print(f"Backend exposed at: {url}")
                return url, server_process
        
        print("Could not find exposed URL in output")
        return None, server_process
    except subprocess.CalledProcessError as e:
        print(f"Error exposing port: {e}")
        print(f"Error output: {e.stderr}")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None

if __name__ == "__main__":
    try:
        url, process = deploy_backend()
        if url:
            print(f"Backend deployed successfully at: {url}")
            print("Now you can create a static build pointing to this URL")
            print(f"Run: python create_static_build.py {url}")
        else:
            print("Failed to deploy backend")
            sys.exit(1)
    except Exception as e:
        print(f"Error deploying backend: {e}")
        sys.exit(1)
