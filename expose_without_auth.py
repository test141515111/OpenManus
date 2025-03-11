#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    """Create a public URL without authentication"""
    try:
        # Use the expose_port command with auth=none parameter
        cmd = ["expose_port", "local_port=8080", "auth=none"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        print(f"Command output: {result.stdout}")
        print(f"Command error: {result.stderr}")
        
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            return False
            
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
