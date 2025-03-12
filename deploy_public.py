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
        
        # Copy templates from build if they exist, otherwise use the originals
        build_templates = Path("webapp/build/templates")
        if build_templates.exists():
            # Copy main index.html if it exists
            build_index = build_templates / "index.html"
            if build_index.exists() and not (templates_dir / "index.html").exists():
                import shutil
                shutil.copy(build_index, templates_dir / "index.html")
                print("Copied index.html from build to templates")
            
            # Copy search index.html if it exists
            build_search_index = build_templates / "search" / "index.html"
            if build_search_index.exists() and not (search_templates_dir / "index.html").exists():
                import shutil
                shutil.copy(build_search_index, search_templates_dir / "index.html")
                print("Copied search/index.html from build to templates")
        
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
        
        # Copy static files from build if they exist
        build_static = Path("webapp/build/static")
        if build_static.exists():
            import shutil
            
            # Copy script.js if it exists
            build_script = build_static / "script.js"
            if build_script.exists() and not (static_dir / "script.js").exists():
                shutil.copy(build_script, static_dir / "script.js")
                print("Copied script.js from build to static")
            
            # Copy style.css if it exists
            build_style = build_static / "style.css"
            if build_style.exists() and not (static_dir / "style.css").exists():
                shutil.copy(build_style, static_dir / "style.css")
                print("Copied style.css from build to static")
            
            # Copy search.js if it exists
            build_search = build_static / "search.js"
            if build_search.exists() and not (static_dir / "search.js").exists():
                shutil.copy(build_search, static_dir / "search.js")
                print("Copied search.js from build to static")
        
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
            ["python", "webapp/run.py"],
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
        
        # Expose the port without authentication
        result = subprocess.run(
            "expose_port local_port=8080 auth=none",
            shell=True,
            capture_output=True,
            text=True
        )
        
        # Extract the URL from the result
        if result.returncode == 0:
            output = result.stdout
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
