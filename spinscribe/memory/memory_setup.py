# File: spinscribe/memory/memory_setup.py
from camel.memories import (
    LongtermAgentMemory,
    ScoreBasedContextCreator,
    ChatHistoryBlock,
    VectorDBBlock,
)
from camel.utils import OpenAITokenCounter
from camel.storages import QdrantStorage
from camel.types import ModelType
from config.settings import (
    MEMORY_TOKEN_LIMIT,
    MEMORY_KEEP_RATE,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_VECTOR_DIM,
    MODEL_TYPE,
)
import logging

logger = logging.getLogger(__name__)

def get_memory() -> LongtermAgentMemory:
    """
    Initialize long-term memory with chat history and Qdrant vector database.
    Fixed based on CAMEL documentation requirements.
    """
    try:
        # Fix 1: Construct proper Qdrant URL format as per CAMEL docs
        if QDRANT_HOST.startswith(('http://', 'https://')):
            qdrant_url = QDRANT_HOST
        else:
            qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        
        logger.info(f"Connecting to Qdrant at: {qdrant_url}")
        
        # Fix 2: Create Qdrant storage with proper URL format and error handling
        vector_storage = QdrantStorage(
            url_and_api_key=(qdrant_url, QDRANT_API_KEY if QDRANT_API_KEY else None),
            vector_dim=QDRANT_VECTOR_DIM,
            collection_name=QDRANT_COLLECTION,
        )
        
        # Fix 3: Test the connection before proceeding
        try:
            # Test if we can create the vector block
            vector_block = VectorDBBlock(storage=vector_storage)
            logger.info("Vector storage connection successful")
        except Exception as ve:
            logger.warning(f"Vector storage failed: {ve}. Falling back to chat-only memory.")
            vector_block = None
        
        # Fix 4: Chat history block with proper configuration
        history_block = ChatHistoryBlock(keep_rate=MEMORY_KEEP_RATE)
        
        # Fix 5: Use correct token counter based on actual model being used
        model_type_mapping = {
            "gpt-4o": ModelType.GPT_4O,
            "gpt-4o-mini": ModelType.GPT_4O_MINI,
            "gpt-4": ModelType.GPT_4,
            "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO,
        }
        
        token_counter_model = model_type_mapping.get(MODEL_TYPE, ModelType.GPT_4O)
        logger.info(f"Using token counter for model: {token_counter_model}")
        
        context_creator = ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(token_counter_model),
            token_limit=MEMORY_TOKEN_LIMIT,
        )
        
        # Fix 6: Create memory with proper error handling
        memory = LongtermAgentMemory(
            context_creator=context_creator,
            chat_history_block=history_block,
            vector_db_block=vector_block,  # This could be None if vector storage failed
        )
        
        if vector_block is None:
            logger.info("Memory system initialized with chat history only")
        else:
            logger.info("Memory system initialized with chat history and vector storage")
            
        return memory
        
    except Exception as e:
        logger.error(f"Failed to initialize memory system: {str(e)}")
        logger.info("Attempting fallback to chat-history-only memory...")
        
        # Fallback: chat history only
        try:
            history_block = ChatHistoryBlock(keep_rate=MEMORY_KEEP_RATE)
            context_creator = ScoreBasedContextCreator(
                token_counter=OpenAITokenCounter(ModelType.GPT_4O),
                token_limit=MEMORY_TOKEN_LIMIT,
            )
            
            memory = LongtermAgentMemory(
                context_creator=context_creator,
                chat_history_block=history_block,
                vector_db_block=None,
            )
            
            logger.info("Fallback memory system initialized successfully (chat history only)")
            return memory
            
        except Exception as fallback_error:
            logger.error(f"Even fallback memory failed: {str(fallback_error)}")
            raise RuntimeError(f"Complete memory initialization failure: {str(fallback_error)}")