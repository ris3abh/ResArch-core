# File: config/settings.py
"""
SpinScribe Configuration Settings
Clean version using only CAMEL's native HumanToolkit - no custom checkpoints.
"""

import os
from pathlib import Path

# ─── Project Configuration ───
PROJECT_NAME = "SpinScribe"
PROJECT_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).parent.parent

# ─── Model Configuration ───
MODEL_PLATFORM = os.getenv("MODEL_PLATFORM", "openai")
MODEL_TYPE = os.getenv("MODEL_TYPE", "gpt-4o-mini")
MODEL_CONFIG = {
    "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "2000")),
    "top_p": float(os.getenv("MODEL_TOP_P", "1.0"))
}

# ─── API Configuration ───
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ─── HUMAN INTERACTION CONFIGURATION (CAMEL NATIVE ONLY) ───
# Using only CAMEL's built-in HumanToolkit - no external dependencies

ENABLE_HUMAN_TOOLKIT = os.getenv("ENABLE_HUMAN_TOOLKIT", "true").lower() == "true"
HUMAN_INPUT_TIMEOUT = int(os.getenv("HUMAN_INPUT_TIMEOUT", "300"))  # 5 minutes

# Console-based human interaction settings (CAMEL's HumanToolkit default)
HUMAN_INTERACTION_MODE = "console"

# ─── Task Configuration ───
DEFAULT_TASK_ID = "spinscribe-content-task"
DEFAULT_CONTENT_TYPE = "article"
DEFAULT_WORKFLOW_TIMEOUT = 900  # 15 minutes

# ─── Knowledge Management ───
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge"
CLIENT_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "client_documents"
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

# ─── Logging Configuration ───
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = PROJECT_ROOT / "logs"
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"

# ─── Memory Configuration ───
MEMORY_TYPE = os.getenv("MEMORY_TYPE", "contextual")
ENABLE_MEMORY_PERSISTENCE = os.getenv("ENABLE_MEMORY_PERSISTENCE", "true").lower() == "true"

# ─── Qdrant Configuration ───
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "spinscribe_knowledge")

# ─── Content Templates ───
TEMPLATE_DIR = PROJECT_ROOT / "spinscribe" / "templates"
DEFAULT_TEMPLATES = {
    "article": "article.md",
    "landing_page": "landing_page.md",
    "blog_post": "article.md",  # Use article template for blog posts
}

# ─── Output Configuration ───
OUTPUT_DIR = PROJECT_ROOT / "output"
ENABLE_OUTPUT_PERSISTENCE = os.getenv("ENABLE_OUTPUT_PERSISTENCE", "true").lower() == "true"

# ─── Development & Debug Settings ───
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"

# ─── Helper Functions ───

def has_api_keys() -> bool:
    """Check if required API keys are available."""
    return bool(OPENAI_API_KEY or ANTHROPIC_API_KEY)

def get_config_summary() -> dict:
    """Get a summary of current configuration."""
    return {
        "project": {
            "name": PROJECT_NAME,
            "version": PROJECT_VERSION,
            "root": str(PROJECT_ROOT)
        },
        "model": {
            "platform": MODEL_PLATFORM,
            "type": MODEL_TYPE,
            "config": MODEL_CONFIG
        },
        "human_interaction": {
            "enabled": ENABLE_HUMAN_TOOLKIT,
            "mode": HUMAN_INTERACTION_MODE,
            "timeout": HUMAN_INPUT_TIMEOUT
        },
        "features": {
            "rag_enabled": ENABLE_RAG,
            "memory_persistence": ENABLE_MEMORY_PERSISTENCE,
            "output_persistence": ENABLE_OUTPUT_PERSISTENCE,
            "debug_mode": DEBUG_MODE
        },
        "api_keys": {
            "openai_available": bool(OPENAI_API_KEY),
            "anthropic_available": bool(ANTHROPIC_API_KEY)
        }
    }

def validate_config() -> list:
    """Validate configuration and return any issues."""
    issues = []
    
    if not has_api_keys():
        issues.append("No API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    if not KNOWLEDGE_BASE_PATH.exists():
        issues.append(f"Knowledge base path does not exist: {KNOWLEDGE_BASE_PATH}")
    
    if not TEMPLATE_DIR.exists():
        issues.append(f"Template directory does not exist: {TEMPLATE_DIR}")
    
    return issues

# ─── Initialize Directories ───
def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        LOG_DIR,
        OUTPUT_DIR,
        KNOWLEDGE_BASE_PATH,
        CLIENT_DOCUMENTS_PATH
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Auto-create directories on import
ensure_directories()