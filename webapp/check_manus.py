#!/usr/bin/env python
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.config import load_config
from app.agent.manus import Manus

async def main():
    try:
        print("Loading config...")
        config = load_config()
        print("Config loaded:", config)
        
        print("Initializing Manus...")
        manus = Manus(config=config)
        print("Manus initialized successfully")
        
        print("Testing Manus run...")
        result = await manus.run("Hello, what can you do?")
        print("Manus run result:", result)
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
