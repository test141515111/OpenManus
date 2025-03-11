#!/usr/bin/env python3
import os
import sys
import subprocess
import time

def deploy_frontend():
    """Deploy the frontend application to devinapps.com"""
    try:
        print("Deploying frontend application...")
        # Use the expose_port command from Devin
        result = subprocess.run(
            ["expose_port", "local_port=8087"],
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Extract the URL from the output
        for line in result.stdout.splitlines():
            if "https://" in line and "devinapps.com" in line:
                url = line.strip()
                print(f"Frontend deployed successfully at: {url}")
                return url
        
        print("Could not find deployment URL in output")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error deploying frontend: {e}")
        print(f"Error output: {e.stderr}")
        return None

def prepare_build():
    """Prepare the build directory with environment variables properly set"""
    try:
        print("Preparing build directory...")
        
        # Create build directory
        os.makedirs("/home/ubuntu/repos/OpenManus/webapp/build", exist_ok=True)
        
        # Copy templates
        subprocess.run(
            ["cp", "-r", "/home/ubuntu/repos/OpenManus/webapp/templates", "/home/ubuntu/repos/OpenManus/webapp/build/"],
            check=True
        )
        
        # Create static directory
        os.makedirs("/home/ubuntu/repos/OpenManus/webapp/build/static", exist_ok=True)
        
        # Copy static files
        subprocess.run(
            ["cp", "-r", "/home/ubuntu/repos/OpenManus/webapp/static", "/home/ubuntu/repos/OpenManus/webapp/build/"],
            check=True
        )
        
        # Create config directory
        os.makedirs("/home/ubuntu/repos/OpenManus/webapp/build/config", exist_ok=True)
        
        # Create config.toml with environment variables
        api_key = os.environ.get('oepnai_api', '')
        if not api_key:
            print("Warning: OpenAI API key not found in environment")
            return False
        
        config_content = f"""[llm]
provider = "openai"
model = "gpt-4"
api_key = "{api_key}"
base_url = "https://api.openai.com/v1"
temperature = 0.7
max_tokens = 4096

[agent]
name = "manus"
memory_enabled = true

[tools]
python_execute = true
file_saver = true
browser_use = true
google_search = true
web_search_report = true
"""
        
        with open("/home/ubuntu/repos/OpenManus/webapp/build/config/config.toml", "w") as f:
            f.write(config_content)
        
        print("Build directory prepared successfully")
        return True
    except Exception as e:
        print(f"Error preparing build: {e}")
        return False

if __name__ == "__main__":
    if prepare_build():
        url = deploy_frontend()
        if url:
            print(f"Application deployed successfully at: {url}")
            print("Note: The server enters sleep mode after 15 minutes of inactivity.")
            print("It will automatically wake up within a few seconds when receiving new requests.")
            sys.exit(0)
    
    print("Deployment failed")
    sys.exit(1)
