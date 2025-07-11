# ─── COMPLETE FIXED FILE: config/settings.py ───

"""
Configuration settings for SpinScribe.
COMPLETE FIXED VERSION with all required settings and fallbacks.
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

# ─── Task Configuration ───
DEFAULT_TASK_ID = "spinscribe-content-task"
DEFAULT_CONTENT_TYPE = "article"
DEFAULT_WORKFLOW_TIMEOUT = 900  # 15 minutes

# ─── Checkpoint Configuration ───
ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "false").lower() == "true"
ENABLE_MOCK_REVIEWER = os.getenv("ENABLE_MOCK_REVIEWER", "true").lower() == "true"
CHECKPOINT_TIMEOUT = int(os.getenv("CHECKPOINT_TIMEOUT", "300"))  # 5 minutes

# ─── Knowledge Management ───
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge"
CLIENT_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "client_documents"
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

# ─── Logging Configuration ───
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_PATH = PROJECT_ROOT / "logs" / "spinscribe.log"
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"

# ─── Memory Configuration ───
MEMORY_TYPE = os.getenv("MEMORY_TYPE", "chat_history")
MEMORY_MAX_TOKENS = int(os.getenv("MEMORY_MAX_TOKENS", "4000"))

# ─── Content Configuration ───
DEFAULT_CONTENT_LENGTH = {
    "article": {"min": 800, "max": 1200},
    "landing_page": {"min": 300, "max": 600},
    "local_article": {"min": 600, "max": 1000},
    "blog_post": {"min": 500, "max": 900}
}

CONTENT_QUALITY_THRESHOLD = float(os.getenv("CONTENT_QUALITY_THRESHOLD", "0.8"))

# ─── Workflow Configuration ───
MAX_WORKFLOW_RETRIES = int(os.getenv("MAX_WORKFLOW_RETRIES", "3"))
WORKFLOW_RETRY_DELAY = int(os.getenv("WORKFLOW_RETRY_DELAY", "30"))  # seconds

# ─── Agent Configuration ───
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "120"))  # 2 minutes per agent
MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "4"))

# ─── Development Configuration ───
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
ENABLE_VERBOSE_LOGGING = os.getenv("ENABLE_VERBOSE_LOGGING", "false").lower() == "true"

# ─── Performance Configuration ───
ASYNC_TIMEOUT = int(os.getenv("ASYNC_TIMEOUT", "600"))  # 10 minutes
PROCESS_TIMEOUT = int(os.getenv("PROCESS_TIMEOUT", "900"))  # 15 minutes

# ─── File Processing Configuration ───
SUPPORTED_DOCUMENT_TYPES = [".txt", ".md", ".doc", ".docx", ".pdf"]
MAX_DOCUMENT_SIZE = int(os.getenv("MAX_DOCUMENT_SIZE", "10485760"))  # 10MB
MAX_DOCUMENTS_PER_PROJECT = int(os.getenv("MAX_DOCUMENTS_PER_PROJECT", "50"))

# ─── Quality Assurance Configuration ───
ENABLE_QUALITY_CHECKS = os.getenv("ENABLE_QUALITY_CHECKS", "true").lower() == "true"
QUALITY_CHECK_TIMEOUT = int(os.getenv("QUALITY_CHECK_TIMEOUT", "60"))
MIN_CONTENT_QUALITY_SCORE = float(os.getenv("MIN_CONTENT_QUALITY_SCORE", "75.0"))

# ─── Error Handling Configuration ───
MAX_ERROR_RETRIES = int(os.getenv("MAX_ERROR_RETRIES", "3"))
ERROR_RETRY_DELAY = int(os.getenv("ERROR_RETRY_DELAY", "5"))  # seconds
ENABLE_FALLBACK_MODE = os.getenv("ENABLE_FALLBACK_MODE", "true").lower() == "true"

# ─── Security Configuration ───
ENABLE_INPUT_VALIDATION = os.getenv("ENABLE_INPUT_VALIDATION", "true").lower() == "true"
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "50000"))  # characters
ALLOWED_FILE_EXTENSIONS = [".txt", ".md", ".doc", ".docx"]

# ─── Cache Configuration ───
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "false").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "100"))  # number of items

# ─── Integration Configuration ───
ENABLE_WEBHOOK_NOTIFICATIONS = os.getenv("ENABLE_WEBHOOK_NOTIFICATIONS", "false").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "30"))  # seconds

# ─── Template Configuration ───
TEMPLATE_PATH = PROJECT_ROOT / "spinscribe" / "templates"
DEFAULT_TEMPLATE = "article.md"
ENABLE_CUSTOM_TEMPLATES = os.getenv("ENABLE_CUSTOM_TEMPLATES", "true").lower() == "true"

# ─── Validation Functions ───

def validate_settings():
    """Validate configuration settings and provide warnings."""
    warnings = []
    
    # Check API keys
    if not OPENAI_API_KEY and MODEL_PLATFORM == "openai":
        warnings.append("OPENAI_API_KEY not set but using OpenAI platform")
    
    if not ANTHROPIC_API_KEY and MODEL_PLATFORM == "anthropic":
        warnings.append("ANTHROPIC_API_KEY not set but using Anthropic platform")
    
    # Check paths
    if not KNOWLEDGE_BASE_PATH.exists():
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        warnings.append(f"Created knowledge base directory: {KNOWLEDGE_BASE_PATH}")
    
    if not CLIENT_DOCUMENTS_PATH.exists():
        CLIENT_DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
        warnings.append(f"Created client documents directory: {CLIENT_DOCUMENTS_PATH}")
    
    if ENABLE_FILE_LOGGING and not LOG_FILE_PATH.parent.exists():
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        warnings.append(f"Created logs directory: {LOG_FILE_PATH.parent}")
    
    # Check timeout values
    if DEFAULT_WORKFLOW_TIMEOUT < 60:
        warnings.append("DEFAULT_WORKFLOW_TIMEOUT is very low, may cause timeouts")
    
    if AGENT_TIMEOUT < 30:
        warnings.append("AGENT_TIMEOUT is very low, agents may not complete tasks")
    
    return warnings

def get_model_config():
    """Get complete model configuration."""
    return {
        "platform": MODEL_PLATFORM,
        "type": MODEL_TYPE,
        "config": MODEL_CONFIG.copy()
    }

def get_checkpoint_config():
    """Get checkpoint configuration."""
    return {
        "enabled": ENABLE_HUMAN_CHECKPOINTS,
        "mock_reviewer": ENABLE_MOCK_REVIEWER,
        "timeout": CHECKPOINT_TIMEOUT
    }

def get_workflow_config():
    """Get workflow configuration."""
    return {
        "timeout": DEFAULT_WORKFLOW_TIMEOUT,
        "max_retries": MAX_WORKFLOW_RETRIES,
        "retry_delay": WORKFLOW_RETRY_DELAY,
        "agent_timeout": AGENT_TIMEOUT,
        "max_concurrent_agents": MAX_CONCURRENT_AGENTS
    }

def get_quality_config():
    """Get quality assurance configuration."""
    return {
        "enabled": ENABLE_QUALITY_CHECKS,
        "timeout": QUALITY_CHECK_TIMEOUT,
        "min_score": MIN_CONTENT_QUALITY_SCORE,
        "threshold": CONTENT_QUALITY_THRESHOLD
    }

def get_knowledge_config():
    """Get knowledge management configuration."""
    return {
        "enable_rag": ENABLE_RAG,
        "knowledge_base_path": str(KNOWLEDGE_BASE_PATH),
        "client_documents_path": str(CLIENT_DOCUMENTS_PATH),
        "supported_types": SUPPORTED_DOCUMENT_TYPES,
        "max_document_size": MAX_DOCUMENT_SIZE,
        "max_documents": MAX_DOCUMENTS_PER_PROJECT
    }

def get_content_config():
    """Get content generation configuration."""
    return {
        "default_lengths": DEFAULT_CONTENT_LENGTH.copy(),
        "quality_threshold": CONTENT_QUALITY_THRESHOLD,
        "enable_quality_checks": ENABLE_QUALITY_CHECKS,
        "template_path": str(TEMPLATE_PATH),
        "default_template": DEFAULT_TEMPLATE
    }

def get_logging_config():
    """Get logging configuration."""
    return {
        "level": LOG_LEVEL,
        "file_path": str(LOG_FILE_PATH),
        "enable_file_logging": ENABLE_FILE_LOGGING,
        "verbose": ENABLE_VERBOSE_LOGGING,
        "debug_mode": DEBUG_MODE
    }

def get_security_config():
    """Get security configuration."""
    return {
        "input_validation": ENABLE_INPUT_VALIDATION,
        "max_input_length": MAX_INPUT_LENGTH,
        "allowed_extensions": ALLOWED_FILE_EXTENSIONS.copy(),
        "max_document_size": MAX_DOCUMENT_SIZE
    }

# ─── Environment Detection ───

def is_development():
    """Check if running in development mode."""
    return DEBUG_MODE or os.getenv("ENVIRONMENT", "production").lower() == "development"

def is_production():
    """Check if running in production mode."""
    return not is_development()

def has_api_keys():
    """Check if required API keys are available."""
    if MODEL_PLATFORM == "openai":
        return bool(OPENAI_API_KEY)
    elif MODEL_PLATFORM == "anthropic":
        return bool(ANTHROPIC_API_KEY)
    else:
        return False

# ─── Configuration Summary ───

def get_config_summary():
    """Get a summary of current configuration."""
    return {
        "project": {
            "name": PROJECT_NAME,
            "version": PROJECT_VERSION,
            "root": str(PROJECT_ROOT)
        },
        "model": get_model_config(),
        "workflow": get_workflow_config(),
        "knowledge": get_knowledge_config(),
        "quality": get_quality_config(),
        "logging": get_logging_config(),
        "security": get_security_config(),
        "environment": {
            "development": is_development(),
            "production": is_production(),
            "api_keys_available": has_api_keys()
        },
        "features": {
            "human_checkpoints": ENABLE_HUMAN_CHECKPOINTS,
            "mock_reviewer": ENABLE_MOCK_REVIEWER,
            "rag": ENABLE_RAG,
            "quality_checks": ENABLE_QUALITY_CHECKS,
            "file_logging": ENABLE_FILE_LOGGING,
            "caching": ENABLE_CACHING,
            "webhooks": ENABLE_WEBHOOK_NOTIFICATIONS
        }
    }

# ─── Initialization ───

def initialize_settings():
    """Initialize settings and create required directories."""
    warnings = validate_settings()
    
    if warnings and (DEBUG_MODE or ENABLE_VERBOSE_LOGGING):
        print("⚠️ Configuration Warnings:")
        for warning in warnings:
            print(f"   • {warning}")
    
    return len(warnings) == 0

# Auto-initialize when module is imported
_SETTINGS_INITIALIZED = initialize_settings()

if __name__ == "__main__":
    # Display configuration summary when run directly
    import json
    
    print("🔧 SpinScribe Configuration Summary")
    print("=" * 50)
    
    config = get_config_summary()
    print(json.dumps(config, indent=2, default=str))
    
    print(f"\n✅ Settings initialized: {_SETTINGS_INITIALIZED}")
    
    if not has_api_keys():
        print("\n⚠️ Warning: No API keys configured!")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
    
    print("\n💡 To modify settings, set environment variables or edit this file.")