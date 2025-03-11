"""Configuration utilities for OpenManus"""
import os
import toml
from pathlib import Path

def load_config():
    """Load configuration from config.toml file"""
    # Try to find config file in different locations
    possible_paths = [
        Path("config/config.toml"),  # Current directory
        Path(os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config/config.toml"))),  # Project root
        Path("/home/ubuntu/repos/OpenManus/config/config.toml")  # Absolute path
    ]
    
    for config_path in possible_paths:
        if config_path.exists():
            print(f"Found config at: {config_path}")
            return toml.load(config_path)
    
    raise FileNotFoundError(f"Config file not found at any of these locations: {possible_paths}")
