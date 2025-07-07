# spinscribe/spinscribe/memory/memory_setup.py

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
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_VECTOR_DIM,
)

def get_memory() -> LongtermAgentMemory:
    """
    Initialize long-term memory with chat history and a Qdrant vector database.
    """
    # 1) Create Qdrant storage using url_and_api_key tuple
    vector_storage = QdrantStorage(
        url_and_api_key=(QDRANT_HOST, QDRANT_API_KEY or None),
        vector_dim=QDRANT_VECTOR_DIM,
        collection_name=QDRANT_COLLECTION,
    )
    vector_block = VectorDBBlock(storage=vector_storage)

    # 2) Chat history block with custom keep_rate
    history_block = ChatHistoryBlock(keep_rate=MEMORY_KEEP_RATE)

    # 3) Context creator for scoring (no keep_rate here)
    context_creator = ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
        token_limit=MEMORY_TOKEN_LIMIT,
    )

    # 4) Combine into long-term memory
    memory = LongtermAgentMemory(
        context_creator=context_creator,
        chat_history_block=history_block,
        vector_db_block=vector_block,
    )
    return memory
