#!/usr/bin/env python3
"""
Create a public URL without authentication
"""
import subprocess
import sys

def create_public_url():
    """Create a public URL without authentication"""
    try:
        # Use the expose_port command with auth=none parameter
        cmd = ["expose_port", "local_port=8081", "auth=none"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            output = result.stdout
            print(f"Command output: {output}")
            
            # Extract the URL from the output
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
