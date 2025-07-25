# File: config/settings.py (UPDATED WITH MISSING PORT)
import os

# ─── CHECKPOINT SYSTEM SETTINGS ─────────────────────────────────
ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"
DEFAULT_CHECKPOINT_TIMEOUT_HOURS = int(os.getenv("DEFAULT_CHECKPOINT_TIMEOUT_HOURS", 24))
ENABLE_MOCK_REVIEWER = os.getenv("ENABLE_MOCK_REVIEWER", "false").lower() == "true"
MOCK_REVIEWER_AUTO_APPROVE_RATE = float(os.getenv("MOCK_REVIEWER_AUTO_APPROVE_RATE", 0.7))
MOCK_REVIEWER_DELAY_RANGE = (1, 5)  # seconds

# Notification settings
ENABLE_EMAIL_NOTIFICATIONS = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
ENABLE_SLACK_NOTIFICATIONS = os.getenv("ENABLE_SLACK_NOTIFICATIONS", "false").lower() == "true"
NOTIFICATION_EMAIL_FROM = os.getenv("NOTIFICATION_EMAIL_FROM", "rishabhsharma@spinutech.com")

# User role mappings for checkpoint assignments
DEFAULT_CHECKPOINT_ASSIGNMENTS = {
    "style_guide_approval": "content_strategist",
    "outline_review": "content_strategist", 
    "draft_review": "editor",
    "final_approval": "project_manager"
}

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

# ─── KNOWLEDGE MANAGEMENT SETTINGS ──────────────────────────────
KNOWLEDGE_BASE_ENABLED = os.getenv("KNOWLEDGE_BASE_ENABLED", "true").lower() == "true"
MAX_DOCUMENT_SIZE_MB = int(os.getenv("MAX_DOCUMENT_SIZE_MB", 50))
SUPPORTED_DOCUMENT_TYPES = [".pdf", ".docx", ".doc", ".txt", ".md", ".html"]
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", 500))  # words per chunk
KNOWLEDGE_RETRIEVAL_LIMIT = int(os.getenv("KNOWLEDGE_RETRIEVAL_LIMIT", 5))

# Document storage paths
DOCUMENTS_STORAGE_PATH = os.getenv("DOCUMENTS_STORAGE_PATH", "./data/documents")
KNOWLEDGE_INDEX_PATH = os.getenv("KNOWLEDGE_INDEX_PATH", "./data/knowledge_index")

# ─── SPINSCRIBE SPECIFIC SETTINGS ───────────────────────────────────────────
SUPPORTED_CONTENT_TYPES = ["landing_page", "article", "local_article"]
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5000))
ENABLE_HUMAN_CHECKPOINTS = os.getenv("ENABLE_HUMAN_CHECKPOINTS", "true").lower() == "true"

# ─── LOGGING SETTINGS ───────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"