"""
Environment configuration loader for Spinscribe.
Handles loading from different .env files based on context.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")
    load_dotenv = None

class EnvironmentLoader:
    """Manages loading environment variables from multiple .env files."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        
    def load_core_env(self) -> None:
        """Load core Spinscribe environment variables."""
        if load_dotenv:
            env_path = self.project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ Loaded core environment from {env_path}")
            else:
                print(f"⚠️  Core .env file not found at {env_path}")
    
    def load_backend_env(self) -> None:
        """Load backend-specific environment variables.""" 
        if load_dotenv:
            env_path = self.project_root / "backend" / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ Loaded backend environment from {env_path}")
            else:
                print(f"⚠️  Backend .env file not found at {env_path}")
    
    def load_all(self) -> None:
        """Load all environment files in the correct order."""
        # Load core first (base configuration)
        self.load_core_env()
        
        # Load backend second (overrides where needed)
        self.load_backend_env()
        
        print("✅ All environment variables loaded")

# Global loader instance
env_loader = EnvironmentLoader()

def load_environment():
    """Convenience function to load all environment variables."""
    env_loader.load_all()
