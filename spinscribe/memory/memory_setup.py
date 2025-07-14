# File: spinscribe/memory/memory_setup.py (CORRECTED VERSION)
"""
Memory setup with CORRECTED token limits.
This fixes the confusion between context tokens and completion tokens.
"""

import logging
import hashlib
import uuid
from typing import Optional, Dict, Any

# Correct CAMEL memory imports based on documentation
from camel.memories import (
    ChatHistoryMemory,
    ScoreBasedContextCreator,
    LongtermAgentMemory,
    ChatHistoryBlock,
    VectorDBBlock
)
from camel.types import ModelType
from camel.utils import OpenAITokenCounter

# Import config
import os

# **CORRECTED: Use proper context limits (not completion limits)**
try:
    from config.settings import (
        QDRANT_HOST, 
        QDRANT_PORT, 
        QDRANT_API_KEY, 
        QDRANT_COLLECTION,
        QDRANT_VECTOR_DIM,
        MODEL_TYPE,
        get_safe_context_tokens,
        get_context_limit,
        get_completion_limit
    )
except ImportError as e:
    # Fallback values
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_API_KEY = ""
    QDRANT_COLLECTION = "spinscribe"
    QDRANT_VECTOR_DIM = 1536
    MODEL_TYPE = "gpt-4o-mini"
    
    def get_safe_context_tokens(model_name: str = "gpt-4o-mini") -> int:
        # Fallback: GPT-4o-mini has 128K context, reserve space for completion
        return 120000  # 120K tokens for context
    
    def get_context_limit(model_name: str = "gpt-4o-mini") -> int:
        return 128000  # 128K context window
    
    def get_completion_limit(model_name: str = "gpt-4o-mini") -> int:
        return 16384   # 16K completion limit

logger = logging.getLogger(__name__)

def create_context_creator(model_name: str = "gpt-4o-mini", token_limit: int = None) -> ScoreBasedContextCreator:
    """
    Create a context creator with proper context token limits.
    This is for CONTEXT/INPUT tokens, not completion tokens.
    """
    
    # **CRITICAL FIX: Use safe context token limit, not completion limit**
    if token_limit is None:
        token_limit = get_safe_context_tokens(model_name)
        logger.info(f"🔧 Using safe context token limit {token_limit:,} for model {model_name}")
    
    # Validate token limit doesn't exceed model's context window
    max_context = get_context_limit(model_name)
    if token_limit > max_context:
        token_limit = max_context - 4000  # Reserve some space
        logger.warning(f"⚠️ Reduced token limit to {token_limit:,} (max context: {max_context:,})")
    
    logger.info(f"🔧 Creating ScoreBasedContextCreator with context token_limit={token_limit:,}")
    
    # Map model names to CAMEL ModelType
    clean_model = model_name.lower().replace('-0613', '').replace('-0314', '')
    if 'gpt-4o-mini' in clean_model:
        model_type = ModelType.GPT_4O_MINI
    elif 'gpt-4o' in clean_model:
        model_type = ModelType.GPT_4O
    elif 'gpt-4' in clean_model:
        model_type = ModelType.GPT_4
    else:
        model_type = ModelType.GPT_4O_MINI  # Default
    
    logger.info(f"🔧 Model type: {model_type}")
    
    return ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(model_type),
        token_limit=token_limit
    )

def setup_agent_memory(
    agent_id: str = None,
    model_name: str = "gpt-4o-mini",
    enable_vector_storage: bool = True,
    memory_type: str = "longterm",
    token_limit: int = None  # Context token limit
) -> Any:
    """
    Set up agent memory with proper context token limits.
    
    Args:
        agent_id: Unique identifier for the agent
        model_name: Model name for token counting
        enable_vector_storage: Whether to enable vector storage
        memory_type: Type of memory to create
        token_limit: Context token limit (not completion limit)
        
    Returns:
        Configured memory instance
    """
    if agent_id is None:
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    # **FIXED: Use safe context token limit**
    if token_limit is None:
        token_limit = get_safe_context_tokens(model_name)
    
    logger.info(f"Setting up {memory_type} memory for agent: {agent_id}")
    logger.info(f"Model: {model_name}, Context token limit: {token_limit:,}")
    
    try:
        # **FIXED: Create context creator with proper context token limit**
        context_creator = create_context_creator(model_name, token_limit)
        
        if memory_type == "chat_history" or not enable_vector_storage:
            # Use simple chat history memory
            logger.info(f"Creating ChatHistoryMemory with {token_limit:,} context tokens")
            
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info(f"✅ Memory system initialized with chat history ({token_limit:,} context tokens)")
            
        elif memory_type == "longterm" and enable_vector_storage:
            # Use longterm memory with both chat history and vector DB
            logger.info(f"Creating LongtermAgentMemory with vector storage ({token_limit:,} context tokens)")
            
            try:
                # Test Qdrant connection first
                from qdrant_client import QdrantClient
                client = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")
                collections = client.get_collections()
                logger.info("✅ Vector storage connection successful")
                
                # Create memory blocks
                chat_history_block = ChatHistoryBlock()
                vector_db_block = VectorDBBlock()
                
                memory = LongtermAgentMemory(
                    context_creator=context_creator,
                    chat_history_block=chat_history_block,
                    vector_db_block=vector_db_block
                )
                logger.info(f"✅ Memory system initialized with chat history and vector storage ({token_limit:,} context tokens)")
                
            except Exception as e:
                logger.warning(f"⚠️ Vector storage failed, falling back to chat history: {e}")
                memory = ChatHistoryMemory(
                    context_creator=context_creator
                )
                logger.info(f"✅ Memory system initialized with chat history fallback ({token_limit:,} context tokens)")
        
        else:
            # Fallback to simple memory
            logger.info(f"Creating fallback ChatHistoryMemory with {token_limit:,} context tokens")
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info(f"✅ Memory system initialized with fallback chat history ({token_limit:,} context tokens)")
        
        return memory
        
    except Exception as e:
        logger.error(f"❌ Failed to setup memory: {e}")
        # **FIXED: Emergency fallback with safe context token limit**
        safe_limit = get_safe_context_tokens(model_name)
        emergency_context_creator = ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
            token_limit=safe_limit
        )
        
        fallback_memory = ChatHistoryMemory(
            context_creator=emergency_context_creator
        )
        logger.warning(f"⚠️ Using emergency fallback memory with {safe_limit:,} context tokens")
        return fallback_memory

def get_memory(agent_id: str = None, model_name: str = None, token_limit: int = None):
    """Get enhanced memory with proper context token limits."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    if token_limit is None:
        token_limit = get_safe_context_tokens(model_name)
    
    return setup_agent_memory(
        agent_id=agent_id,
        model_name=model_name,
        enable_vector_storage=True,
        memory_type="longterm",
        token_limit=token_limit
    )

def get_chat_memory(model_name: str = None, token_limit: int = None):
    """Get basic chat history memory with proper context token limits."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    if token_limit is None:
        token_limit = get_safe_context_tokens(model_name)
    
    return setup_agent_memory(
        agent_id=None,
        model_name=model_name,
        enable_vector_storage=False,
        memory_type="chat_history",
        token_limit=token_limit
    )

def get_unlimited_memory(model_name: str = None):
    """
    Get memory with maximum safe context tokens for complex workflows.
    Uses the full available context window minus space for completion.
    """
    if model_name is None:
        model_name = MODEL_TYPE
    
    # Use maximum safe context (full context window minus completion space)
    max_context = get_context_limit(model_name)
    completion_reserve = get_completion_limit(model_name)
    max_safe_context = max_context - completion_reserve - 2000  # Extra buffer
    
    logger.info(f"🚀 Creating unlimited memory with {max_safe_context:,} context tokens")
    
    return setup_agent_memory(
        agent_id=None,
        model_name=model_name,
        enable_vector_storage=True,
        memory_type="longterm",
        token_limit=max_safe_context
    )

def patch_memory_token_limits(memory_obj, new_limit: int = None):
    """
    Patch existing memory objects to use higher context token limits.
    Use this to fix already-created memory objects.
    """
    if new_limit is None:
        new_limit = get_safe_context_tokens(MODEL_TYPE)
    
    try:
        if hasattr(memory_obj, 'context_creator'):
            old_limit = getattr(memory_obj.context_creator, 'token_limit', 'unknown')
            memory_obj.context_creator.token_limit = new_limit
            logger.info(f"✅ Patched memory context token limit: {old_limit} → {new_limit:,}")
        else:
            logger.warning("⚠️ Memory object doesn't have context_creator attribute")
    except Exception as e:
        logger.error(f"❌ Failed to patch memory token limit: {e}")

def get_model_info(model_name: str = None) -> dict:
    """Get comprehensive model information."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    return {
        "model_name": model_name,
        "context_window": get_context_limit(model_name),
        "completion_limit": get_completion_limit(model_name),
        "safe_context_tokens": get_safe_context_tokens(model_name),
        "recommended_memory_limit": get_safe_context_tokens(model_name)
    }

# **Export the key configuration**
__all__ = [
    'create_context_creator',
    'setup_agent_memory', 
    'get_memory',
    'get_chat_memory',
    'get_unlimited_memory',
    'patch_memory_token_limits',
    'get_model_info'
]