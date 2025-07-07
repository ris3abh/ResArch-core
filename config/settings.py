# config/settings.py
import os

# ─── OpenAI / CAMEL MODEL SETTINGS ─────────────────────────────────────────
# Ensure you have exported OPENAI_API_KEY in your shell environment.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

# Model platform and type for CAMEL
MODEL_PLATFORM = os.getenv("MODEL_PLATFORM", "openai")
MODEL_TYPE = os.getenv("MODEL_TYPE", "gpt-4o-mini")
MODEL_CONFIG = {
    "temperature": float(os.getenv("MODEL_TEMPERATURE", 0.7)),
    "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", 2048)),
}

# ─── MEMORY SETTINGS ────────────────────────────────────────────────────────
MEMORY_TOKEN_LIMIT = int(os.getenv("MEMORY_TOKEN_LIMIT", 1024))
MEMORY_KEEP_RATE = float(os.getenv("MEMORY_KEEP_RATE", 0.9))

# ─── VECTOR DB (Qdrant) SETTINGS ─────────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "spinscribe")
QDRANT_VECTOR_DIM = int(os.getenv("QDRANT_VECTOR_DIM", 1536))

# ─── WORKFLOW DEFAULTS ──────────────────────────────────────────────────────
DEFAULT_TASK_ID = os.getenv("DEFAULT_TASK_ID", "task-001")
