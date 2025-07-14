# ─── FILE: scripts/fix_production_checkpoints.py ─────────────────────
"""
Production-ready fix for checkpoint system issues.
This script fixes the missing Priority enum and ensures production readiness.
"""

import os
import sys
from pathlib import Path

def fix_checkpoint_manager():
    """Fix the checkpoint manager by adding the missing Priority enum."""
    
    project_root = Path(__file__).parent.parent
    checkpoint_file = project_root / "spinscribe" / "checkpoints" / "checkpoint_manager.py"
    
    if not checkpoint_file.exists():
        print(f"❌ File not found: {checkpoint_file}")
        return False
    
    # Read current content
    with open(checkpoint_file, 'r') as f:
        content = f.read()
    
    # Check if Priority already exists
    if "class Priority(Enum):" in content:
        print("✅ Priority enum already exists")
        return True
    
    # Add Priority enum
    priority_enum = '''class Priority(Enum):
    """Priority levels for checkpoints."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

'''
    
    # Find insertion point after CheckpointStatus
    insertion_point = content.find("@dataclass")
    if insertion_point == -1:
        print("❌ Could not find insertion point")
        return False
    
    # Insert Priority enum
    new_content = content[:insertion_point] + priority_enum + content[insertion_point:]
    
    # Update CheckpointData to include priority field
    dataclass_lines = new_content.split('\n')
    updated_lines = []
    in_dataclass = False
    
    for line in dataclass_lines:
        updated_lines.append(line)
        
        # Add priority field after status
        if "status: CheckpointStatus" in line and in_dataclass:
            updated_lines.append("    priority: Priority = Priority.MEDIUM")
            updated_lines.append("    assigned_to: Optional[str] = None")
            updated_lines.append("    due_hours: Optional[int] = None")
        
        if "@dataclass" in line:
            in_dataclass = True
        elif "class " in line and in_dataclass:
            in_dataclass = False
    
    # Write updated content
    try:
        with open(checkpoint_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        print("✅ Priority enum added to checkpoint_manager.py")
        return True
    except Exception as e:
        print(f"❌ Failed to write file: {e}")
        return False

def fix_workflow_integration():
    """Fix workflow integration imports."""
    
    project_root = Path(__file__).parent.parent
    workflow_file = project_root / "spinscribe" / "checkpoints" / "workflow_integration.py"
    
    if not workflow_file.exists():
        print("⚠️ workflow_integration.py not found - creating it")
        
        # Create the workflow integration file
        workflow_content = '''# ─── FILE: spinscribe/checkpoints/workflow_integration.py ───
"""
Workflow integration for checkpoints in the enhanced content creation system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from .checkpoint_manager import CheckpointManager, CheckpointType, CheckpointStatus, Priority

logger = logging.getLogger(__name__)

class WorkflowCheckpointIntegration:
    """
    Integrates checkpoints with the enhanced workflow system.
    """
    
    def __init__(self, checkpoint_manager: CheckpointManager, project_id: str):
        self.checkpoint_manager = checkpoint_manager
        self.project_id = project_id
        
    async def request_approval(
        self,
        checkpoint_type: CheckpointType,
        title: str,
        description: str,
        content: str,
        priority: Priority = Priority.MEDIUM,
        timeout_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Request human approval and wait for response.
        
        Args:
            checkpoint_type: Type of checkpoint
            title: Checkpoint title
            description: Description of what needs review
            content: Content to be reviewed
            priority: Priority level
            timeout_hours: Hours to wait before timeout
            
        Returns:
            Dict containing approval result and feedback
        """
        logger.info(f"🛑 Requesting approval: {title}")
        
        # Create checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            project_id=self.project_id,
            checkpoint_type=checkpoint_type,
            title=title,
            description=description,
            content=content,
            priority=priority,
            due_hours=timeout_hours
        )
        
        # Wait for response
        timeout_seconds = timeout_hours * 3600
        start_time = time.time()
        poll_interval = 5.0  # Check every 5 seconds
        
        while time.time() - start_time < timeout_seconds:
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
            
            if checkpoint and checkpoint.status != CheckpointStatus.PENDING:
                logger.info(f"✅ Checkpoint resolved: {checkpoint.status.value}")
                
                return {
                    "approved": checkpoint.status == CheckpointStatus.APPROVED,
                    "status": checkpoint.status.value,
                    "feedback": checkpoint.feedback,
                    "reviewer_id": checkpoint.reviewer_id,
                    "checkpoint_id": checkpoint_id
                }
            
            await asyncio.sleep(poll_interval)
        
        # Timeout
        logger.warning(f"⏰ Checkpoint timed out: {checkpoint_id}")
        return {
            "approved": False,
            "status": "timeout",
            "feedback": "Checkpoint timed out waiting for human response",
            "checkpoint_id": checkpoint_id
        }
'''
        
        try:
            with open(workflow_file, 'w') as f:
                f.write(workflow_content)
            print("✅ Created workflow_integration.py")
            return True
        except Exception as e:
            print(f"❌ Failed to create workflow_integration.py: {e}")
            return False
    
    else:
        # Fix existing file
        with open(workflow_file, 'r') as f:
            content = f.read()
        
        # Fix import order
        if "from .checkpoint_manager import CheckpointManager, CheckpointType, Priority, CheckpointStatus" in content:
            content = content.replace(
                "from .checkpoint_manager import CheckpointManager, CheckpointType, Priority, CheckpointStatus",
                "from .checkpoint_manager import CheckpointManager, CheckpointType, CheckpointStatus, Priority"
            )
            
            try:
                with open(workflow_file, 'w') as f:
                    f.write(content)
                print("✅ Fixed workflow_integration.py imports")
                return True
            except Exception as e:
                print(f"❌ Failed to fix workflow_integration.py: {e}")
                return False
        else:
            print("✅ workflow_integration.py imports already correct")
            return True

def fix_test_script():
    """Fix the test script import."""
    
    project_root = Path(__file__).parent.parent
    test_file = project_root / "scripts" / "test_checkpoints.py"
    
    if test_file.exists():
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Fix the import
        if "from spinscribe.enhanced_process import run_enhanced_content_task" in content:
            content = content.replace(
                "from spinscribe.enhanced_process import run_enhanced_content_task",
                "from spinscribe.tasks.enhanced_process import run_enhanced_content_task"
            )
            
            try:
                with open(test_file, 'w') as f:
                    f.write(content)
                print("✅ Fixed test_checkpoints.py import")
                return True
            except Exception as e:
                print(f"❌ Failed to fix test_checkpoints.py: {e}")
                return False
        else:
            print("✅ test_checkpoints.py import already correct")
            return True
    else:
        print("⚠️ test_checkpoints.py not found")
        return True

def verify_fixes():
    """Verify that all fixes work correctly."""
    
    print("\n🧪 VERIFYING FIXES")
    print("=" * 30)
    
    try:
        # Test Priority import
        from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType, CheckpointStatus, Priority
        print("✅ All checkpoint manager imports working")
        
        # Test checkpoint creation with priority
        manager = CheckpointManager()
        checkpoint_id = manager.create_checkpoint(
            project_id="test-fix",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Test Fix",
            description="Testing priority fix",
            priority=Priority.HIGH
        )
        print(f"✅ Checkpoint created with priority: {checkpoint_id}")
        
        # Test workflow integration import
        from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
        print("✅ Workflow integration import working")
        
        # Test enhanced process import
        from spinscribe.tasks.enhanced_process import run_enhanced_content_task
        print("✅ Enhanced process import working")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Apply all production fixes."""
    
    print("🔧 PRODUCTION CHECKPOINT SYSTEM FIX")
    print("=" * 40)
    
    success = True
    
    # Apply fixes
    print("\n1️⃣ Fixing checkpoint manager...")
    if not fix_checkpoint_manager():
        success = False
    
    print("\n2️⃣ Fixing workflow integration...")
    if not fix_workflow_integration():
        success = False
    
    print("\n3️⃣ Fixing test script...")
    if not fix_test_script():
        success = False
    
    print("\n4️⃣ Verifying fixes...")
    if not verify_fixes():
        success = False
    
    if success:
        print("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("✅ Production checkpoint system is ready")
        print("\n📋 NEXT STEPS:")
        print("   1. Run: ./scripts/quick_checkpoint_test.sh")
        print("   2. Or: python scripts/test_checkpoints.py")
        print("   3. Test human feedback workflow")
    else:
        print("\n❌ SOME FIXES FAILED")
        print("Please check the errors above and fix manually")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)