"""
Shared configuration values between Spinscribe core and backend.
This ensures consistency across both systems.
"""

import os
from pathlib import Path

# Root project directory
PROJECT_ROOT = Path(__file__).parent.parent

# Shared OpenAI Configuration
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# Shared Workflow Configuration
DEFAULT_WORKFLOW_TIMEOUT = int(os.getenv("DEFAULT_WORKFLOW_TIMEOUT", "600"))
MAX_CONCURRENT_WORKFLOWS = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "5"))

# Shared Knowledge Configuration
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", str(PROJECT_ROOT / "knowledge"))
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))

# Shared Checkpoint Configuration
ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"
ENABLE_HUMAN_APPROVAL = os.getenv("ENABLE_HUMAN_APPROVAL", "true").lower() == "true"
