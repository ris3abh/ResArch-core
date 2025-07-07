# File: config/settings.py (UPDATED WITH MISSING PORT)
import os

# ─── OpenAI / CAMEL MODEL SETTINGS ─────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

# Model platform and type for CAMEL
MODEL_PLATFORM = os.getenv("MODEL_PLATFORM", "openai")
MODEL_TYPE = os.getenv("MODEL_TYPE", "gpt-4o")  # Fixed: use gpt-4o not gpt-4o-mini
MODEL_CONFIG = {
    "temperature": float(os.getenv("MODEL_TEMPERATURE", 0.7)),
    "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", 4096)),  # Fixed: increased from 2048
}

# ─── MEMORY SETTINGS ────────────────────────────────────────────────────────
MEMORY_TOKEN_LIMIT = int(os.getenv("MEMORY_TOKEN_LIMIT", 2048))  # Fixed: increased from 1024
MEMORY_KEEP_RATE = float(os.getenv("MEMORY_KEEP_RATE", 0.9))

# ─── VECTOR DB (Qdrant) SETTINGS ─────────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))  # Fixed: Added missing port
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "spinscribe")
QDRANT_VECTOR_DIM = int(os.getenv("QDRANT_VECTOR_DIM", 1536))

# ─── WORKFLOW DEFAULTS ──────────────────────────────────────────────────────
DEFAULT_TASK_ID = os.getenv("DEFAULT_TASK_ID", "spinscribe-task-001")

# ─── SPINSCRIBE SPECIFIC SETTINGS ───────────────────────────────────────────
SUPPORTED_CONTENT_TYPES = ["landing_page", "article", "local_article"]
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5000))
ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"

# ─── LOGGING SETTINGS ───────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"