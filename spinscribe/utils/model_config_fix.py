# File: spinscribe/utils/model_config_fix.py (NEW FILE)
"""
Model configuration fix for CAMEL agents.
This ensures proper separation of context and completion token limits.
"""

import logging
from typing import Dict, Any, Optional
from camel.configs import ChatGPTConfig
from camel.types import ModelType

logger = logging.getLogger(__name__)

# **CORRECTED: Proper completion token limits by model**
MODEL_COMPLETION_LIMITS = {
    ModelType.GPT_4O: 16384,
    ModelType.GPT_4O_MINI: 16384,
    ModelType.GPT_4: 8192,
    ModelType.GPT_3_5_TURBO: 4096,
}

# **Context window limits (for memory/input)**
MODEL_CONTEXT_LIMITS = {
    ModelType.GPT_4O: 128000,
    ModelType.GPT_4O_MINI: 128000,
    ModelType.GPT_4: 8192,
    ModelType.GPT_3_5_TURBO: 16385,
}

def get_safe_completion_limit(model_type: ModelType) -> int:
    """Get safe completion token limit (80% of max for safety)."""
    base_limit = MODEL_COMPLETION_LIMITS.get(model_type, 4096)
    return int(base_limit * 0.8)

def get_safe_context_limit(model_type: ModelType) -> int:
    """Get safe context token limit (reserve space for completion)."""
    context_limit = MODEL_CONTEXT_LIMITS.get(model_type, 16385)
    completion_limit = MODEL_COMPLETION_LIMITS.get(model_type, 4096)
    
    # Reserve space for completion + buffer
    safe_context = context_limit - completion_limit - 2000
    return max(safe_context, 10000)  # Minimum 10K context

def create_safe_model_config(
    model_type: ModelType = ModelType.GPT_4O_MINI,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> ChatGPTConfig:
    """
    Create a safe model configuration with proper token limits.
    
    Args:
        model_type: The model type to configure
        temperature: Model temperature (0.0-2.0)
        max_tokens: Override completion token limit (optional)
        **kwargs: Additional configuration parameters
        
    Returns:
        ChatGPTConfig with safe token limits
    """
    
    # Use safe completion limit if not specified
    if max_tokens is None:
        max_tokens = get_safe_completion_limit(model_type)
    else:
        # Validate provided max_tokens doesn't exceed model limit
        model_limit = MODEL_COMPLETION_LIMITS.get(model_type, 4096)
        if max_tokens > model_limit:
            logger.warning(f"⚠️ max_tokens ({max_tokens}) exceeds model limit ({model_limit}), using {model_limit}")
            max_tokens = model_limit
    
    logger.info(f"🔧 Creating model config: {model_type} with {max_tokens:,} completion tokens")
    
    config_params = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }
    
    return ChatGPTConfig(**config_params)

def fix_model_config_in_dict(config_dict: Dict[str, Any], model_type: ModelType) -> Dict[str, Any]:
    """
    Fix token limits in an existing model config dictionary.
    
    Args:
        config_dict: Model configuration dictionary
        model_type: Model type for validation
        
    Returns:
        Fixed configuration dictionary
    """
    fixed_config = config_dict.copy()
    
    # Fix max_tokens if it's too high
    if "max_tokens" in fixed_config:
        current_max = fixed_config["max_tokens"]
        model_limit = MODEL_COMPLETION_LIMITS.get(model_type, 4096)
        
        if current_max > model_limit:
            fixed_config["max_tokens"] = model_limit
            logger.info(f"🔧 Fixed max_tokens: {current_max} → {model_limit}")
    
    # Ensure max_tokens is set if missing
    if "max_tokens" not in fixed_config:
        safe_limit = get_safe_completion_limit(model_type)
        fixed_config["max_tokens"] = safe_limit
        logger.info(f"🔧 Added max_tokens: {safe_limit}")
    
    return fixed_config

def validate_model_config(config: Dict[str, Any], model_type: ModelType) -> bool:
    """
    Validate that a model configuration has proper token limits.
    
    Args:
        config: Model configuration to validate
        model_type: Model type for validation
        
    Returns:
        True if configuration is valid
    """
    try:
        max_tokens = config.get("max_tokens")
        if max_tokens is None:
            logger.warning("⚠️ max_tokens not specified in config")
            return False
        
        model_limit = MODEL_COMPLETION_LIMITS.get(model_type, 4096)
        if max_tokens > model_limit:
            logger.error(f"❌ max_tokens ({max_tokens}) exceeds model limit ({model_limit})")
            return False
        
        logger.info(f"✅ Model config valid: {max_tokens:,} completion tokens for {model_type}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validating model config: {e}")
        return False

def get_model_info_summary(model_type: ModelType) -> Dict[str, int]:
    """Get summary of model token limits."""
    return {
        "model_type": str(model_type),
        "context_limit": MODEL_CONTEXT_LIMITS.get(model_type, 16385),
        "completion_limit": MODEL_COMPLETION_LIMITS.get(model_type, 4096),
        "safe_context": get_safe_context_limit(model_type),
        "safe_completion": get_safe_completion_limit(model_type),
    }

def print_model_limits():
    """Print all model limits for debugging."""
    print("\n🔧 Model Token Limits:")
    print("=" * 50)
    
    for model_type in [ModelType.GPT_4O, ModelType.GPT_4O_MINI, ModelType.GPT_4, ModelType.GPT_3_5_TURBO]:
        info = get_model_info_summary(model_type)
        print(f"\n{model_type}:")
        print(f"  Context Window: {info['context_limit']:,} tokens")
        print(f"  Completion Limit: {info['completion_limit']:,} tokens")
        print(f"  Safe Context: {info['safe_context']:,} tokens")
        print(f"  Safe Completion: {info['safe_completion']:,} tokens")
    
    print("=" * 50)

# **Quick fix functions for common issues**

def quick_fix_gpt4o_mini_config() -> ChatGPTConfig:
    """Quick fix for GPT-4o-mini configuration."""
    return create_safe_model_config(
        model_type=ModelType.GPT_4O_MINI,
        temperature=0.7
    )

def quick_fix_any_model_config(model_type: ModelType) -> ChatGPTConfig:
    """Quick fix for any model configuration."""
    return create_safe_model_config(
        model_type=model_type,
        temperature=0.7
    )

# **Export key functions**
__all__ = [
    'create_safe_model_config',
    'fix_model_config_in_dict',
    'validate_model_config',
    'get_model_info_summary',
    'get_safe_completion_limit',
    'get_safe_context_limit',
    'quick_fix_gpt4o_mini_config',
    'quick_fix_any_model_config',
    'print_model_limits'
]