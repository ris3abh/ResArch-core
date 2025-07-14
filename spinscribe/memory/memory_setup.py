# File: spinscribe/memory/memory_setup.py (COMPLETE FIX)
"""
Memory setup with FIXED token limits for GPT-4o models.
This fixes the context truncation issues by using proper token limits.
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

# **FIXED: Use proper token limits for GPT-4o models**
try:
    from config.settings import (
        QDRANT_HOST, 
        QDRANT_PORT, 
        QDRANT_API_KEY, 
        QDRANT_COLLECTION,
        QDRANT_VECTOR_DIM,
        MODEL_TYPE
    )
except ImportError as e:
    # Fallback values
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_API_KEY = ""
    QDRANT_COLLECTION = "spinscribe"
    QDRANT_VECTOR_DIM = 1536
    MODEL_TYPE = "gpt-4o-mini"

# **CRITICAL FIX: Use appropriate token limits based on model capacity**
# GPT-4o models have 128K context window, use 80% for safety
MODEL_TOKEN_LIMITS = {
    "gpt-4o": 100000,        # 80% of 128K context
    "gpt-4o-mini": 100000,   # 80% of 128K context  
    "gpt-4": 6000,           # 80% of 8K context
    "gpt-3.5-turbo": 12000   # 80% of 16K context
}

# **FIXED: Get appropriate token limit based on model**
def get_token_limit_for_model(model_name: str) -> int:
    """Get appropriate token limit based on model capacity."""
    # Clean model name (remove version suffixes)
    clean_model = model_name.lower().replace('-0613', '').replace('-0314', '')
    
    if 'gpt-4o' in clean_model:
        return MODEL_TOKEN_LIMITS["gpt-4o"]
    elif 'gpt-4' in clean_model:
        return MODEL_TOKEN_LIMITS["gpt-4"]
    elif 'gpt-3.5' in clean_model:
        return MODEL_TOKEN_LIMITS["gpt-3.5-turbo"]
    else:
        # Default to GPT-4o limit for unknown models
        return MODEL_TOKEN_LIMITS["gpt-4o"]

logger = logging.getLogger(__name__)

def create_context_creator(model_name: str = "gpt-4o-mini", token_limit: int = None) -> ScoreBasedContextCreator:
    """Create a proper context creator for CAMEL memory with FIXED token limits."""
    
    # **CRITICAL FIX: Use model-appropriate token limit instead of hardcoded 2048**
    if token_limit is None:
        token_limit = get_token_limit_for_model(model_name)
        logger.info(f"🔧 Using token limit {token_limit} for model {model_name}")
    
    # Map model names to CAMEL ModelType
    model_type_map = {
        "gpt-4o": ModelType.GPT_4O,
        "gpt-4o-mini": ModelType.GPT_4O_MINI,
        "gpt-4": ModelType.GPT_4,
        "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO
    }
    
    clean_model = model_name.lower().replace('-0613', '').replace('-0314', '')
    if 'gpt-4o-mini' in clean_model:
        model_type = ModelType.GPT_4O_MINI
    elif 'gpt-4o' in clean_model:
        model_type = ModelType.GPT_4O
    elif 'gpt-4' in clean_model:
        model_type = ModelType.GPT_4
    else:
        model_type = ModelType.GPT_4O_MINI  # Default
    
    logger.info(f"🔧 Creating ScoreBasedContextCreator with token_limit={token_limit}, model_type={model_type}")
    
    return ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(model_type),
        token_limit=token_limit
    )

def setup_agent_memory(
    agent_id: str = None,
    model_name: str = "gpt-4o-mini",
    enable_vector_storage: bool = True,
    memory_type: str = "chat_history",  # "chat_history", "vector_db", or "longterm"
    token_limit: int = None  # **NEW: Allow override of token limit**
) -> Any:
    """
    Set up agent memory using correct CAMEL API with FIXED token limits.
    
    Args:
        agent_id: Unique identifier for the agent
        model_name: Model name for token counting
        enable_vector_storage: Whether to enable vector storage
        memory_type: Type of memory to create
        token_limit: Optional override for token limit
        
    Returns:
        Configured memory instance
    """
    if agent_id is None:
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Setting up {memory_type} memory for agent: {agent_id}")
    logger.info(f"Model: {model_name}, Token limit override: {token_limit}")
    
    try:
        # **FIXED: Create context creator with proper token limit**
        context_creator = create_context_creator(model_name, token_limit)
        
        if memory_type == "chat_history" or not enable_vector_storage:
            # Use simple chat history memory
            logger.info("Creating ChatHistoryMemory")
            
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info("✅ Memory system initialized with chat history only")
            
        elif memory_type == "longterm" and enable_vector_storage:
            # Use longterm memory with both chat history and vector DB
            logger.info("Creating LongtermAgentMemory with vector storage")
            
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
                logger.info("✅ Memory system initialized with chat history and vector storage")
                
            except Exception as e:
                logger.warning(f"⚠️ Vector storage failed, falling back to chat history: {e}")
                memory = ChatHistoryMemory(
                    context_creator=context_creator
                )
                logger.info("✅ Memory system initialized with chat history fallback")
        
        else:
            # Fallback to simple memory
            logger.info("Creating fallback ChatHistoryMemory")
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info("✅ Memory system initialized with fallback chat history")
        
        return memory
        
    except Exception as e:
        logger.error(f"❌ Failed to setup memory: {e}")
        # **FIXED: Emergency fallback with high token limit**
        emergency_context_creator = ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
            token_limit=100000  # High limit for emergency fallback
        )
        
        fallback_memory = ChatHistoryMemory(
            context_creator=emergency_context_creator
        )
        logger.warning("⚠️ Using emergency fallback memory with high token limit")
        return fallback_memory

def get_memory(agent_id: str = None, model_name: str = None):
    """Get enhanced memory with proper token limits."""
    if model_name is None:
        model_name = MODEL_TYPE
    
    return setup_agent_memory(
        agent_id=agent_id,
        model_name=model_name,
        enable_vector_storage=True,
        memory_type="longterm"
    )

def get_chat_memory(model_name: str = None, token_limit: int = None):
    """Get basic chat history memory with proper token limits."""
    if model_name is None:
        model_name = MODEL_TYPE
        
    context_creator = create_context_creator(model_name, token_limit)
    return ChatHistoryMemory(context_creator=context_creator)