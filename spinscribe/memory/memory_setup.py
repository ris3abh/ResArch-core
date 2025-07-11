# File: spinscribe/memory/memory_setup.py (CORRECT CAMEL API VERSION)
"""
Memory setup with correct CAMEL API usage.
Based on CAMEL 0.2.70 memory API documentation.
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

# **Use actual config variables from your settings**
try:
    from config.settings import (
        QDRANT_HOST, 
        QDRANT_PORT, 
        QDRANT_API_KEY, 
        QDRANT_COLLECTION,
        QDRANT_VECTOR_DIM,
        MEMORY_TOKEN_LIMIT,
        MEMORY_KEEP_RATE
    )
except ImportError as e:
    # Fallback values
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_API_KEY = ""
    QDRANT_COLLECTION = "spinscribe"
    QDRANT_VECTOR_DIM = 1536
    MEMORY_TOKEN_LIMIT = 2048
    MEMORY_KEEP_RATE = 0.9

logger = logging.getLogger(__name__)

def create_context_creator(model_name: str = "gpt-4o", token_limit: int = None) -> ScoreBasedContextCreator:
    """Create a proper context creator for CAMEL memory."""
    if token_limit is None:
        token_limit = MEMORY_TOKEN_LIMIT
    
    # Map model names to CAMEL ModelType
    model_type_map = {
        "gpt-4o": ModelType.GPT_4O,
        "gpt-4o-mini": ModelType.GPT_4O_MINI,
        "gpt-4": ModelType.GPT_4,
        "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO
    }
    
    model_type = model_type_map.get(model_name, ModelType.GPT_4O)
    
    return ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(model_type),
        token_limit=token_limit
    )

def setup_agent_memory(
    agent_id: str = None,
    model_name: str = "gpt-4o",
    enable_vector_storage: bool = True,
    memory_type: str = "chat_history"  # "chat_history", "vector_db", or "longterm"
) -> Any:
    """
    Set up agent memory using correct CAMEL API.
    
    Args:
        agent_id: Unique identifier for the agent
        model_name: Model name for token counting
        enable_vector_storage: Whether to enable vector storage
        memory_type: Type of memory to create
        
    Returns:
        Configured memory instance
    """
    if agent_id is None:
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Setting up {memory_type} memory for agent: {agent_id}")
    
    try:
        # Create context creator
        context_creator = create_context_creator(model_name, MEMORY_TOKEN_LIMIT)
        
        if memory_type == "chat_history" or not enable_vector_storage:
            # Use simple chat history memory
            logger.info("Creating ChatHistoryMemory")
            
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info("Memory system initialized with chat history only")
            
        elif memory_type == "longterm" and enable_vector_storage:
            # Use longterm memory with both chat history and vector DB
            logger.info("Creating LongtermAgentMemory with vector storage")
            
            try:
                # Test Qdrant connection first
                from qdrant_client import QdrantClient
                client = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")
                collections = client.get_collections()
                logger.info("Vector storage connection successful")
                
                # Create memory blocks
                chat_history_block = ChatHistoryBlock()
                vector_db_block = VectorDBBlock()
                
                memory = LongtermAgentMemory(
                    context_creator=context_creator,
                    chat_history_block=chat_history_block,
                    vector_db_block=vector_db_block
                )
                logger.info("Memory system initialized with chat history and vector storage")
                
            except Exception as e:
                logger.warning(f"Vector storage failed, falling back to chat history: {e}")
                memory = ChatHistoryMemory(
                    context_creator=context_creator
                )
                logger.info("Memory system initialized with chat history only")
        else:
            # Default to chat history
            memory = ChatHistoryMemory(
                context_creator=context_creator
            )
            logger.info("Memory system initialized with chat history only")
        
        return memory
        
    except Exception as e:
        logger.error(f"Failed to setup memory for {agent_id}: {e}")
        logger.info("Creating basic chat history memory as fallback")
        
        # **FINAL FALLBACK: Basic chat history memory**
        try:
            context_creator = create_context_creator(model_name, 1024)  # Smaller limit for fallback
            return ChatHistoryMemory(context_creator=context_creator)
        except Exception as fallback_error:
            logger.error(f"Even fallback memory failed: {fallback_error}")
            raise Exception(f"Could not create any memory type: {e}, fallback: {fallback_error}")

# **Backward compatibility functions with correct API**
def get_memory(agent_id: str = None, model_name: str = "gpt-4o"):
    """Backward compatibility function for existing code."""
    return setup_agent_memory(
        agent_id=agent_id, 
        model_name=model_name, 
        enable_vector_storage=False,  # Start with simple memory
        memory_type="chat_history"
    )

def create_agent_memory(agent_id: str = None, model_name: str = "gpt-4o"):
    """Alternative backward compatibility function."""
    return setup_agent_memory(
        agent_id=agent_id,
        model_name=model_name,
        enable_vector_storage=False,
        memory_type="chat_history"
    )

def get_enhanced_memory(agent_id: str = None, model_name: str = "gpt-4o"):
    """Get enhanced memory with vector storage."""
    return setup_agent_memory(
        agent_id=agent_id,
        model_name=model_name,
        enable_vector_storage=True,
        memory_type="longterm"
    )

def get_chat_memory():
    """Get basic chat history memory."""
    context_creator = create_context_creator("gpt-4o", 1024)
    return ChatHistoryMemory(context_creator=context_creator)

# **Health check function**
def check_memory_health() -> Dict[str, Any]:
    """Check the health of the memory system."""
    health = {
        "camel_memory_available": False,
        "qdrant_available": False,
        "errors": []
    }
    
    try:
        # Test CAMEL memory creation
        test_memory = get_memory()
        health["camel_memory_available"] = True
    except Exception as e:
        health["errors"].append(f"CAMEL memory: {str(e)}")
    
    try:
        # Test Qdrant connection
        from qdrant_client import QdrantClient
        client = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")
        collections = client.get_collections()
        health["qdrant_available"] = True
    except Exception as e:
        health["errors"].append(f"Qdrant: {str(e)}")
    
    return health

# **Initialize on import**
def initialize_memory_system():
    """Initialize the memory system and perform health checks."""
    logger.info("Initializing SpinScribe memory system...")
    
    # Check health
    health = check_memory_health()
    if health["camel_memory_available"]:
        logger.info("✅ CAMEL memory system available")
    else:
        logger.warning("⚠️ CAMEL memory system issues detected")
    
    if health["qdrant_available"]:
        logger.info("✅ Qdrant vector database available")
    else:
        logger.warning("⚠️ Qdrant not available - using chat history only")
    
    if health["errors"]:
        for error in health["errors"]:
            logger.warning(f"   Error: {error}")
    
    return health

# Initialize on import
try:
    initialize_memory_system()
except Exception as e:
    logger.warning(f"Memory system initialization warning: {e}")