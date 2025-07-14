# ─── FILE: config/checkpoint_settings.py ─────────────────────────────
"""
Dedicated checkpoint configuration file for easy testing setup.
Run this to enable/disable checkpoints and configure testing options.
"""

import os
from pathlib import Path

class CheckpointConfig:
    """Checkpoint configuration manager."""
    
    @staticmethod
    def enable_human_checkpoints():
        """Enable human checkpoints for testing."""
        os.environ["ENABLE_HUMAN_CHECKPOINTS"] = "true"
        os.environ["ENABLE_MOCK_REVIEWER"] = "false"
        print("✅ Human checkpoints ENABLED")
        print("❌ Mock reviewer DISABLED")
        
    @staticmethod
    def enable_mock_checkpoints():
        """Enable mock checkpoints for automated testing."""
        os.environ["ENABLE_HUMAN_CHECKPOINTS"] = "true"
        os.environ["ENABLE_MOCK_REVIEWER"] = "true"
        print("✅ Human checkpoints ENABLED")
        print("✅ Mock reviewer ENABLED")
        
    @staticmethod
    def disable_checkpoints():
        """Disable all checkpoints."""
        os.environ["ENABLE_HUMAN_CHECKPOINTS"] = "false"
        os.environ["ENABLE_MOCK_REVIEWER"] = "false"
        print("❌ Human checkpoints DISABLED")
        print("❌ Mock reviewer DISABLED")
        
    @staticmethod
    def set_checkpoint_timeout(seconds: int):
        """Set checkpoint timeout in seconds."""
        os.environ["CHECKPOINT_TIMEOUT"] = str(seconds)
        print(f"⏰ Checkpoint timeout set to {seconds} seconds")
        
    @staticmethod
    def display_current_config():
        """Display current checkpoint configuration."""
        print("\n🔧 CURRENT CHECKPOINT CONFIGURATION")
        print("=" * 50)
        print(f"Human Checkpoints: {os.getenv('ENABLE_HUMAN_CHECKPOINTS', 'false')}")
        print(f"Mock Reviewer: {os.getenv('ENABLE_MOCK_REVIEWER', 'false')}")
        print(f"Checkpoint Timeout: {os.getenv('CHECKPOINT_TIMEOUT', '300')}s")
        
        # Validate configuration
        human_enabled = os.getenv('ENABLE_HUMAN_CHECKPOINTS', 'false').lower() == 'true'
        mock_enabled = os.getenv('ENABLE_MOCK_REVIEWER', 'false').lower() == 'true'
        
        if human_enabled and not mock_enabled:
            print("✅ Configuration: Human review mode")
        elif human_enabled and mock_enabled:
            print("🤖 Configuration: Mock review mode") 
        else:
            print("❌ Configuration: Checkpoints disabled")

def setup_for_human_testing():
    """Quick setup for human checkpoint testing."""
    print("🚀 SETTING UP FOR HUMAN CHECKPOINT TESTING")
    print("=" * 50)
    
    config = CheckpointConfig()
    config.enable_human_checkpoints()
    config.set_checkpoint_timeout(600)  # 10 minutes
    config.display_current_config()
    
    print("\n📋 NEXT STEPS:")
    print("1. Run: python scripts/test_checkpoints.py")
    print("2. When checkpoints appear, use: python scripts/respond_to_checkpoint.py")
    print("3. Or run the checkpoint test in interactive mode")

def setup_for_mock_testing():
    """Quick setup for automated mock testing."""
    print("🤖 SETTING UP FOR MOCK CHECKPOINT TESTING")
    print("=" * 50)
    
    config = CheckpointConfig()
    config.enable_mock_checkpoints()
    config.set_checkpoint_timeout(60)  # 1 minute for faster testing
    config.display_current_config()
    
    print("\n📋 NEXT STEPS:")
    print("1. Run: python scripts/test_checkpoints.py")
    print("2. Mock reviewer will automatically respond to checkpoints")
    print("3. Check logs for checkpoint activity")

if __name__ == "__main__":
    import sys
    
    print("🔧 CHECKPOINT CONFIGURATION TOOL")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "human":
            setup_for_human_testing()
        elif mode == "mock":
            setup_for_mock_testing()
        elif mode == "disable":
            CheckpointConfig.disable_checkpoints()
        elif mode == "status":
            CheckpointConfig.display_current_config()
        else:
            print("❌ Invalid mode. Use: human, mock, disable, or status")
    else:
        print("Available modes:")
        print("  python config/checkpoint_settings.py human   - Enable human testing")
        print("  python config/checkpoint_settings.py mock    - Enable mock testing") 
        print("  python config/checkpoint_settings.py disable - Disable checkpoints")
        print("  python config/checkpoint_settings.py status  - Show current config")
        
        CheckpointConfig.display_current_config()