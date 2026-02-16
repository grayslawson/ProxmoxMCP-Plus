"""
Configuration loading utilities for the Proxmox MCP server.

This module handles loading and validation of server configuration:
- JSON configuration file loading
- Environment variable handling
- Configuration validation using Pydantic models
- Error handling for invalid configurations

The module ensures that all required configuration is present
and valid before the server starts operation.
"""
import json
import os
import sys
from typing import Optional
from .models import Config

def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from JSON file or environment.

    Performs the following steps:
    1. If config_path is provided and exists, loads JSON configuration
    2. Otherwise, attempts to build configuration from environment variables
    3. Validates required fields are present
    
    Args:
        config_path: Path to the JSON configuration file
    """
    config_data = {}

    # 1. Try loading from file if path exists
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
             raise ValueError(f"Failed to load config file: {e}")
    
    # 2. Layer in environment variables (overriding or providing defaults)
    def get_env_safe(key: str, default: Optional[str] = None) -> Optional[str]:
        val = os.getenv(key)
        # Check if the hub passed an unresolved placeholder like "${user_config...}"
        if not val or val.startswith("${"):
            return default
        return val

    # Proxmox Section
    if 'proxmox' not in config_data:
        config_data['proxmox'] = {}
    
    env_host = get_env_safe("PROXMOX_HOST")
    if env_host: config_data['proxmox']['host'] = env_host
    
    env_port = get_env_safe("PROXMOX_PORT")
    if env_port:
        try:
            config_data['proxmox']['port'] = int(env_port)
        except (ValueError, TypeError):
             print(f"Warning: Invalid PROXMOX_PORT '{env_port}', using default 8006", file=sys.stderr)
             config_data['proxmox']['port'] = 8006
    
    env_ssl = get_env_safe("PROXMOX_VERIFY_SSL")
    if env_ssl: config_data['proxmox']['verify_ssl'] = env_ssl.lower() == 'true'

    # Auth Section
    if 'auth' not in config_data:
        config_data['auth'] = {}
    
    env_user = get_env_safe("PROXMOX_USER")
    if env_user: config_data['auth']['user'] = env_user
    
    env_token_name = get_env_safe("PROXMOX_TOKEN_NAME")
    if env_token_name: config_data['auth']['token_name'] = env_token_name
    
    env_token_value = get_env_safe("PROXMOX_TOKEN_VALUE")
    if env_token_value: config_data['auth']['token_value'] = env_token_value

    # Logging & MCP Section defaults
    if 'logging' not in config_data:
        config_data['logging'] = {}
    if 'mcp' not in config_data:
        config_data['mcp'] = {}

    # Final validation check
    if not config_data.get('proxmox', {}).get('host'):
        raise ValueError("Proxmox host must be provided (via config file or PROXMOX_HOST env var)")
    if not config_data.get('auth', {}).get('user'):
        raise ValueError("Authentication credentials must be provided")

    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
