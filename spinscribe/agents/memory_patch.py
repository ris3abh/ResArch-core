# File: spinscribe/agents/memory_patch.py (NEW FILE)
"""
Memory patch utility to fix token limits across all agent types.
This ensures consistent 100K token limits throughout the system.
"""

import logging
from typing import Any, Dict, Optional
from camel.memories import ScoreBasedContextCreator, ChatHistoryMemory, LongtermAgentMemory
from camel.types import ModelType
from camel.utils import OpenAITokenCounter

logger = logging.getLogger(__name__)

class MemoryTokenPatcher:
    """
    Utility class to patch memory objects with proper token limits.
    """
    
    @staticmethod
    def patch_agent_memory(agent: Any, token_limit: int = 100000) -> bool:
        """
        Patch an agent's memory to use the specified token limit.
        
        Args:
            agent: CAMEL agent object
            token_limit: New token limit (default 100K)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if hasattr(agent, 'memory') and agent.memory:
                return MemoryTokenPatcher.patch_memory_object(agent.memory, token_limit)
            else:
                logger.warning(f"Agent {type(agent).__name__} has no memory attribute")
                return False
                
        except Exception as e:
            logger.error(f"Failed to patch agent memory: {e}")
            return False
    
    @staticmethod
    def patch_memory_object(memory_obj: Any, token_limit: int = 100000) -> bool:
        """
        Patch a memory object to use the specified token limit.
        
        Args:
            memory_obj: Memory object to patch
            token_limit: New token limit
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Patch context creator if it exists
            if hasattr(memory_obj, 'context_creator') and memory_obj.context_creator:
                old_limit = getattr(memory_obj.context_creator, 'token_limit', 'unknown')
                memory_obj.context_creator.token_limit = token_limit
                logger.info(f"✅ Patched memory token limit: {old_limit} → {token_limit}")
                return True
            
            # Handle different memory types
            elif hasattr(memory_obj, '_context_creator') and memory_obj._context_creator:
                old_limit = getattr(memory_obj._context_creator, 'token_limit', 'unknown')
                memory_obj._context_creator.token_limit = token_limit
                logger.info(f"✅ Patched memory _context_creator token limit: {old_limit} → {token_limit}")
                return True
            
            else:
                logger.warning(f"Memory object {type(memory_obj).__name__} has no patchable context creator")
                return False
                
        except Exception as e:
            logger.error(f"Failed to patch memory object: {e}")
            return False
    
    @staticmethod
    def create_high_capacity_context_creator(
        model_type: ModelType = ModelType.GPT_4O_MINI,
        token_limit: int = 100000
    ) -> ScoreBasedContextCreator:
        """
        Create a new context creator with high token capacity.
        
        Args:
            model_type: Model type for token counting
            token_limit: Token limit (default 100K)
            
        Returns:
            ScoreBasedContextCreator with high capacity
        """
        logger.info(f"Creating high-capacity context creator: {token_limit} tokens")
        
        return ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(model_type),
            token_limit=token_limit
        )
    
    @staticmethod
    def patch_workforce_agents(workforce: Any, token_limit: int = 100000) -> int:
        """
        Patch all agents in a workforce with the specified token limit.
        
        Args:
            workforce: CAMEL Workforce object
            token_limit: New token limit
            
        Returns:
            Number of agents successfully patched
        """
        patched_count = 0
        
        try:
            # Try to access workforce agents
            if hasattr(workforce, 'agents') and workforce.agents:
                for agent_id, agent in workforce.agents.items():
                    if MemoryTokenPatcher.patch_agent_memory(agent, token_limit):
                        patched_count += 1
                        logger.info(f"✅ Patched agent {agent_id}")
            
            # Try alternative workforce structure
            elif hasattr(workforce, '_agents') and workforce._agents:
                for agent_id, agent in workforce._agents.items():
                    if MemoryTokenPatcher.patch_agent_memory(agent, token_limit):
                        patched_count += 1
                        logger.info(f"✅ Patched agent {agent_id}")
            
            # Try workers attribute
            elif hasattr(workforce, 'workers') and workforce.workers:
                for worker_id, worker in workforce.workers.items():
                    if MemoryTokenPatcher.patch_agent_memory(worker, token_limit):
                        patched_count += 1
                        logger.info(f"✅ Patched worker {worker_id}")
            
            else:
                logger.warning("Workforce has no accessible agents/workers")
            
            logger.info(f"✅ Successfully patched {patched_count} agents in workforce")
            return patched_count
            
        except Exception as e:
            logger.error(f"Failed to patch workforce agents: {e}")
            return patched_count

def patch_all_system_memory(token_limit: int = 100000):
    """
    Global function to patch memory limits throughout the system.
    Call this after system initialization to ensure all components use high token limits.
    
    Args:
        token_limit: Token limit to apply (default 100K)
    """
    logger.info(f"🔧 Starting global memory patch with {token_limit} token limit")
    
    try:
        # Import SpinScribe components
        from spinscribe.memory.memory_setup import patch_memory_token_limits
        from spinscribe.memory.memory_setup import MODEL_TOKEN_LIMITS
        
        # Update global token limits
        for model_name in MODEL_TOKEN_LIMITS:
            MODEL_TOKEN_LIMITS[model_name] = token_limit
        
        logger.info(f"✅ Updated global token limits to {token_limit}")
        
        # Try to patch any existing global memory objects
        # This is a safety net for already-initialized components
        import gc
        
        patched_objects = 0
        for obj in gc.get_objects():
            if isinstance(obj, (ChatHistoryMemory, LongtermAgentMemory)):
                if MemoryTokenPatcher.patch_memory_object(obj, token_limit):
                    patched_objects += 1
        
        if patched_objects > 0:
            logger.info(f"✅ Patched {patched_objects} existing memory objects")
        
        logger.info("🎉 Global memory patch completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Global memory patch failed: {e}")

def validate_memory_limits(min_limit: int = 100000) -> Dict[str, Any]:
    """
    Validate that memory objects throughout the system have adequate token limits.
    
    Args:
        min_limit: Minimum required token limit
        
    Returns:
        Validation results
    """
    results = {
        "total_checked": 0,
        "compliant": 0,
        "non_compliant": 0,
        "errors": 0,
        "details": []
    }
    
    try:
        import gc
        
        for obj in gc.get_objects():
            if isinstance(obj, (ChatHistoryMemory, LongtermAgentMemory)):
                results["total_checked"] += 1
                
                try:
                    if hasattr(obj, 'context_creator') and obj.context_creator:
                        current_limit = getattr(obj.context_creator, 'token_limit', 0)
                        
                        if current_limit >= min_limit:
                            results["compliant"] += 1
                            results["details"].append({
                                "type": type(obj).__name__,
                                "limit": current_limit,
                                "status": "compliant"
                            })
                        else:
                            results["non_compliant"] += 1
                            results["details"].append({
                                "type": type(obj).__name__,
                                "limit": current_limit,
                                "status": "non_compliant",
                                "required": min_limit
                            })
                    
                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "type": type(obj).__name__,
                        "status": "error",
                        "error": str(e)
                    })
        
        # Log summary
        logger.info(f"Memory validation: {results['compliant']}/{results['total_checked']} compliant")
        if results["non_compliant"] > 0:
            logger.warning(f"Found {results['non_compliant']} non-compliant memory objects")
        
        return results
        
    except Exception as e:
        logger.error(f"Memory validation failed: {e}")
        results["errors"] += 1
        return results

# Convenience functions for common use cases
def quick_patch_100k():
    """Quick patch to set all memory to 100K tokens."""
    patch_all_system_memory(100000)

def quick_patch_unlimited():
    """Quick patch to set all memory to 200K tokens for unlimited context."""
    patch_all_system_memory(200000)

def emergency_memory_fix():
    """Emergency function to fix memory issues in running system."""
    logger.warning("🚨 Running emergency memory fix")
    
    try:
        # Force patch with very high limit
        patch_all_system_memory(150000)
        
        # Validate results
        results = validate_memory_limits(100000)
        
        if results["non_compliant"] == 0:
            logger.info("✅ Emergency memory fix successful")
            return True
        else:
            logger.error(f"❌ Emergency fix incomplete: {results['non_compliant']} objects still non-compliant")
            return False
            
    except Exception as e:
        logger.error(f"❌ Emergency memory fix failed: {e}")
        return False

# Export key functions
__all__ = [
    'MemoryTokenPatcher',
    'patch_all_system_memory',
    'validate_memory_limits',
    'quick_patch_100k',
    'quick_patch_unlimited',
    'emergency_memory_fix'
]