#!/usr/bin/env python3
"""
Configuration utilities for handling API keys and settings.
"""

import json
import os
from pathlib import Path

def load_config():
    """Load configuration from config.json file."""
    config_file = Path("config.json")
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load config.json: {e}")
    
    return {}

def get_api_key():
    """Get Etherscan API key from config file or environment variable."""
    
    # First try config file
    config = load_config()
    api_key = config.get('etherscan_api_key')
    
    if api_key and api_key != "YOUR_ETHERSCAN_API_KEY_HERE":
        return api_key
    
    # Fallback to environment variable
    api_key = os.getenv('ETHERSCAN_API_KEY')
    if api_key:
        return api_key
    
    return None

def get_config_value(key, default=None):
    """Get a configuration value with optional default."""
    config = load_config()
    return config.get(key, default)

def setup_config():
    """Help user set up configuration file."""
    config_file = Path("config.json")
    example_file = Path("config.json.example")
    
    if config_file.exists():
        print("✅ config.json already exists")
        return
    
    if not example_file.exists():
        print("❌ config.json.example not found")
        return
    
    print("🔧 Setting up configuration...")
    print("📋 Please get your Etherscan API key from: https://etherscan.io/apis")
    
    # Copy example file
    with open(example_file, 'r') as f:
        config = json.load(f)
    
    # Ask for API key
    api_key = input("🔑 Enter your Etherscan API key: ").strip()
    
    if api_key:
        config['etherscan_api_key'] = api_key
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration saved to {config_file}")
        print("🔒 This file is gitignored to keep your API key private")
    else:
        print("❌ No API key provided. Please edit config.json manually.")

if __name__ == "__main__":
    setup_config() 