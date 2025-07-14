# File: config/settings.py (CORRECTED WITH PROPER TOKEN LIMITS)
"""
SpinScribe Configuration Settings
CORRECTED: Distinguish between context tokens and completion tokens.
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

# **CRITICAL FIX: Use proper completion token limits for each model**
# These are the COMPLETION/OUTPUT token limits (what the model can generate)
MODEL_COMPLETION_LIMITS = {
    "gpt-4o": 16384,        # GPT-4o completion limit
    "gpt-4o-mini": 16384,   # GPT-4o-mini completion limit
    "gpt-4": 8192,          # GPT-4 completion limit
    "gpt-3.5-turbo": 4096   # GPT-3.5-turbo completion limit
}

# **NEW: Context window limits (INPUT tokens) - these are much larger**
MODEL_CONTEXT_LIMITS = {
    "gpt-4o": 128000,       # GPT-4o context window
    "gpt-4o-mini": 128000,  # GPT-4o-mini context window
    "gpt-4": 8192,          # GPT-4 context window
    "gpt-3.5-turbo": 16385  # GPT-3.5-turbo context window
}

def get_completion_limit(model_name: str) -> int:
    """Get the completion token limit for a model."""
    clean_model = model_name.lower().replace('-0613', '').replace('-0314', '')
    if 'gpt-4o-mini' in clean_model:
        return MODEL_COMPLETION_LIMITS["gpt-4o-mini"]
    elif 'gpt-4o' in clean_model:
        return MODEL_COMPLETION_LIMITS["gpt-4o"]
    elif 'gpt-4' in clean_model:
        return MODEL_COMPLETION_LIMITS["gpt-4"]
    elif 'gpt-3.5' in clean_model:
        return MODEL_COMPLETION_LIMITS["gpt-3.5-turbo"]
    else:
        return MODEL_COMPLETION_LIMITS["gpt-4o-mini"]  # Safe default

def get_context_limit(model_name: str) -> int:
    """Get the context window limit for a model."""
    clean_model = model_name.lower().replace('-0613', '').replace('-0314', '')
    if 'gpt-4o-mini' in clean_model:
        return MODEL_CONTEXT_LIMITS["gpt-4o-mini"]
    elif 'gpt-4o' in clean_model:
        return MODEL_CONTEXT_LIMITS["gpt-4o"]
    elif 'gpt-4' in clean_model:
        return MODEL_CONTEXT_LIMITS["gpt-4"]
    elif 'gpt-3.5' in clean_model:
        return MODEL_CONTEXT_LIMITS["gpt-3.5-turbo"]
    else:
        return MODEL_CONTEXT_LIMITS["gpt-4o-mini"]  # Safe default

# **CORRECTED: Model config with proper completion limits**
MODEL_CONFIG = {
    "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.7")),
    "max_tokens": get_completion_limit(MODEL_TYPE),  # Use proper completion limit
    "top_p": float(os.getenv("MODEL_TOP_P", "1.0"))
}

# **NEW: Memory token limits (for context/input) - use high values for context retention**
MEMORY_TOKEN_LIMITS = {
    "chat_history": get_context_limit(MODEL_TYPE) - 4000,  # Reserve space for completion
    "longterm": get_context_limit(MODEL_TYPE) - 4000,      # Reserve space for completion
    "vector_db": get_context_limit(MODEL_TYPE) - 4000,     # Reserve space for completion
    "emergency": 50000                                      # Conservative fallback
}

# **NEW: Context management settings**
CONTEXT_SETTINGS = {
    "enable_truncation": False,     # Disable context truncation
    "preserve_full_context": True, # Always preserve full context
    "context_limit": get_context_limit(MODEL_TYPE),  # Use full context window
    "completion_limit": get_completion_limit(MODEL_TYPE),  # Proper completion limit
    "reserve_tokens": 4000,         # Reserve tokens for completion
    "chunk_size": 10000            # Reasonable chunk size for processing
}

# ─── API Configuration ───
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ─── HUMAN INTERACTION CONFIGURATION ───
ENABLE_HUMAN_TOOLKIT = os.getenv("ENABLE_HUMAN_TOOLKIT", "true").lower() == "true"
HUMAN_INPUT_TIMEOUT = int(os.getenv("HUMAN_INPUT_TIMEOUT", "300"))  # 5 minutes
HUMAN_INTERACTION_MODE = "console"

# ─── Task Configuration ───
DEFAULT_TASK_ID = "spinscribe-content-task"
DEFAULT_CONTENT_TYPE = "article"
DEFAULT_WORKFLOW_TIMEOUT = 1800  # 30 minutes for complex workflows

# ─── Knowledge Management ───
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "knowledge"
CLIENT_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "client_documents"
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

# ─── Logging Configuration ───
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = PROJECT_ROOT / "logs"
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"

# ─── Memory Configuration ───
MEMORY_TYPE = os.getenv("MEMORY_TYPE", "longterm")
ENABLE_MEMORY_PERSISTENCE = os.getenv("ENABLE_MEMORY_PERSISTENCE", "true").lower() == "true"

# ─── Qdrant Configuration ───
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "spinscribe_knowledge")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = "spinscribe"
QDRANT_VECTOR_DIM = 1536

# ─── Content Templates ───
TEMPLATE_DIR = PROJECT_ROOT / "spinscribe" / "templates"
DEFAULT_TEMPLATES = {
    "article": "article.md",
    "landing_page": "landing_page.md",
    "blog_post": "article.md",
}

# ─── Output Configuration ───
OUTPUT_DIR = PROJECT_ROOT / "output"
ENABLE_OUTPUT_PERSISTENCE = os.getenv("ENABLE_OUTPUT_PERSISTENCE", "true").lower() == "true"

# ─── Development & Debug Settings ───
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"

# **NEW: Performance Settings**
PERFORMANCE_SETTINGS = {
    "enable_parallel_processing": True,
    "max_concurrent_agents": 10,
    "batch_size": 100,
    "enable_caching": True,
    "cache_ttl": 3600  # 1 hour
}

# ─── Helper Functions ───

def has_api_keys() -> bool:
    """Check if required API keys are available."""
    return bool(OPENAI_API_KEY or ANTHROPIC_API_KEY)

def get_memory_token_limit(memory_type: str = "longterm") -> int:
    """Get token limit for specific memory type."""
    return MEMORY_TOKEN_LIMITS.get(memory_type, MEMORY_TOKEN_LIMITS["longterm"])

def get_safe_completion_tokens(model_name: str = None) -> int:
    """Get safe completion token limit for a model."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    # Use 80% of the limit for safety
    base_limit = get_completion_limit(model_name)
    return int(base_limit * 0.8)

def get_safe_context_tokens(model_name: str = None) -> int:
    """Get safe context token limit for a model."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    # Use 90% of context limit, reserve space for completion
    context_limit = get_context_limit(model_name)
    completion_limit = get_completion_limit(model_name)
    
    # Reserve space for completion + some buffer
    safe_context = context_limit - completion_limit - 2000
    return max(safe_context, 10000)  # Minimum 10K context

def get_config_summary() -> dict:
    """Get a summary of current configuration."""
    return {
        "project": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "model_type": MODEL_TYPE,
        "context_limit": get_context_limit(MODEL_TYPE),
        "completion_limit": get_completion_limit(MODEL_TYPE),
        "safe_context_tokens": get_safe_context_tokens(),
        "safe_completion_tokens": get_safe_completion_tokens(),
        "memory_token_limit": get_memory_token_limit(),
        "memory_type": MEMORY_TYPE,
        "enable_rag": ENABLE_RAG,
        "qdrant_host": QDRANT_HOST,
        "debug_mode": DEBUG_MODE,
        "context_truncation_disabled": not CONTEXT_SETTINGS["enable_truncation"]
    }

def validate_token_limits() -> bool:
    """Validate that token limits are properly configured."""
    try:
        context_limit = get_context_limit(MODEL_TYPE)
        completion_limit = get_completion_limit(MODEL_TYPE)
        memory_limit = get_memory_token_limit()
        
        print(f"✅ Model: {MODEL_TYPE}")
        print(f"✅ Context limit: {context_limit:,} tokens")
        print(f"✅ Completion limit: {completion_limit:,} tokens")
        print(f"✅ Memory limit: {memory_limit:,} tokens")
        print(f"✅ Safe context: {get_safe_context_tokens():,} tokens")
        print(f"✅ Safe completion: {get_safe_completion_tokens():,} tokens")
        
        # Validate that memory limit doesn't exceed context limit
        if memory_limit > context_limit:
            print(f"⚠️ Warning: Memory limit ({memory_limit}) exceeds context limit ({context_limit})")
            return False
        
        print("✅ All token limits are properly configured")
        return True
        
    except Exception as e:
        print(f"❌ Error validating token limits: {e}")
        return False

# **NEW: Environment variable overrides for token limits**
def apply_environment_overrides():
    """Apply environment variable overrides for token limits."""
    global MEMORY_TOKEN_LIMITS
    
    # Override memory token limits from environment
    env_memory_limit = os.getenv("SPINSCRIBE_MEMORY_TOKEN_LIMIT")
    if env_memory_limit:
        try:
            limit = int(env_memory_limit)
            max_safe_limit = get_safe_context_tokens()
            if limit <= max_safe_limit:
                for memory_type in MEMORY_TOKEN_LIMITS:
                    MEMORY_TOKEN_LIMITS[memory_type] = limit
                print(f"✅ Applied environment memory token limit: {limit}")
            else:
                print(f"⚠️ Environment memory limit ({limit}) too high, using safe limit ({max_safe_limit})")
        except ValueError:
            print(f"⚠️ Invalid environment memory token limit: {env_memory_limit}")

# Apply environment overrides on import
apply_environment_overrides()

# Validate configuration on import
if __name__ == "__main__":
    print("SpinScribe Configuration Summary:")
    print("=" * 40)
    for key, value in get_config_summary().items():
        print(f"{key}: {value}")
    print("=" * 40)
    validate_token_limits()