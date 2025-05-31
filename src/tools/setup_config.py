#!/usr/bin/env python3
"""
Configuration setup tool for the contract debugging toolkit.
"""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import setup_config


def main():
    """Main entry point for the setup configuration tool."""
    print("🔧 Contract Debugging Toolkit - Configuration Setup")
    print("=" * 55)
    print()
    
    try:
        setup_config()
        return 0
    except KeyboardInterrupt:
        print("\n⏹️  Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 