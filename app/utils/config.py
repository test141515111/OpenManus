"""Configuration utilities for OpenManus"""
import os
import toml
from pathlib import Path

def load_config():
    """Load configuration from config.toml file with environment variable support"""
    # Process environment variables in config
    def process_env_vars(config_dict):
        """Replace environment variable placeholders in config values"""
        for section in config_dict:
            for key, value in config_dict[section].items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    env_value = os.environ.get(env_var, '')
                    if env_value:
                        config_dict[section][key] = env_value
                    else:
                        print(f"Warning: Environment variable {env_var} not found")
        return config_dict
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
            config_dict = toml.load(config_path)
            # Process environment variables
            config_dict = process_env_vars(config_dict)
            return config_dict
    
    raise FileNotFoundError(f"Config file not found at any of these locations: {possible_paths}")
