# ─── FILE: scripts/respond_to_checkpoint.py ─────────────────────────
"""
Interactive tool to respond to checkpoints with human feedback.
Use this script to approve/reject checkpoints and provide feedback.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from spinscribe.utils.enhanced_logging import setup_enhanced_logging

class CheckpointResponder:
    """Interactive checkpoint response tool."""
    
    def __init__(self):
        self.checkpoint_manager = CheckpointManager()
        setup_enhanced_logging(log_level="INFO")
        
    def list_pending_checkpoints(self):
        """List all pending checkpoints."""
        pending = []
        for checkpoint_id, checkpoint in self.checkpoint_manager.checkpoints.items():
            if checkpoint.status.value == 'pending':
                pending.append((checkpoint_id, checkpoint))
                
        if not pending:
            print("✅ No pending checkpoints found")
            return []
            
        print(f"\n📋 PENDING CHECKPOINTS ({len(pending)})")
        print("=" * 60)
        
        for i, (checkpoint_id, checkpoint) in enumerate(pending, 1):
            elapsed = time.time() - checkpoint.created_at.timestamp()
            print(f"{i}. {checkpoint_id[:12]}...")
            print(f"   Type: {checkpoint.checkpoint_type.value}")
            print(f"   Title: {checkpoint.title}")
            print(f"   Project: {checkpoint.project_id}")
            print(f"   Age: {elapsed:.1f}s")
            print(f"   Description: {checkpoint.description}")
            print("-" * 40)
            
        return pending
        
    def display_checkpoint_details(self, checkpoint):
        """Display detailed checkpoint information."""
        print(f"\n📄 CHECKPOINT DETAILS")
        print("=" * 60)
        print(f"ID: {checkpoint.id}")
        print(f"Type: {checkpoint.checkpoint_type.value}")
        print(f"Title: {checkpoint.title}")
        print(f"Project: {checkpoint.project_id}")
        print(f"Created: {checkpoint.created_at}")
        print(f"Status: {checkpoint.status.value}")
        print(f"\nDescription:")
        print(checkpoint.description)
        
        if checkpoint.content:
            print(f"\nContent to Review:")
            print("-" * 40)
            print(checkpoint.content)
            print("-" * 40)
            
    def get_user_decision(self):
        """Get user's approval decision and feedback."""
        print(f"\n💬 YOUR REVIEW")
        print("=" * 30)
        
        while True:
            decision = input("Decision (approve/reject/skip): ").strip().lower()
            if decision in ['approve', 'reject', 'skip']:
                break
            print("❌ Please enter 'approve', 'reject', or 'skip'")
            
        if decision == 'skip':
            return None, None
            
        feedback = input("\nFeedback (optional): ").strip()
        if not feedback:
            if decision == 'approve':
                feedback = "Approved without specific feedback"
            else:
                feedback = "Rejected - please see review comments"
                
        return decision, feedback
        
    def submit_response(self, checkpoint_id: str, decision: str, feedback: str):
        """Submit response to checkpoint."""
        try:
            success = self.checkpoint_manager.submit_response(
                checkpoint_id=checkpoint_id,
                reviewer_id="human-reviewer",
                decision=decision,
                feedback=feedback,
                decision_data={
                    "review_type": "human",
                    "timestamp": time.time(),
                    "tool": "checkpoint_responder"
                }
            )
            
            if success:
                print(f"✅ Response submitted successfully")
                print(f"   Decision: {decision}")
                print(f"   Feedback: {feedback}")
                return True
            else:
                print(f"❌ Failed to submit response")
                return False
                
        except Exception as e:
            print(f"❌ Error submitting response: {e}")
            return False
            
    def respond_to_checkpoint(self, checkpoint_id: str):
        """Respond to a specific checkpoint by ID."""
        checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
        
        if not checkpoint:
            print(f"❌ Checkpoint not found: {checkpoint_id}")
            return False
            
        if checkpoint.status.value != 'pending':
            print(f"❌ Checkpoint is not pending (status: {checkpoint.status.value})")
            return False
            
        self.display_checkpoint_details(checkpoint)
        decision, feedback = self.get_user_decision()
        
        if decision is None:
            print("⏭️ Checkpoint skipped")
            return False
            
        return self.submit_response(checkpoint_id, decision, feedback)
        
    def interactive_mode(self):
        """Interactive mode to review all pending checkpoints."""
        print(f"🔄 INTERACTIVE CHECKPOINT REVIEW MODE")
        
        while True:
            pending = self.list_pending_checkpoints()
            
            if not pending:
                print("✅ All checkpoints reviewed!")
                break
                
            print(f"\nOptions:")
            print(f"  1-{len(pending)}: Review checkpoint by number")
            print(f"  r: Refresh list")
            print(f"  q: Quit")
            
            choice = input("\nSelect option: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'r':
                continue
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(pending):
                    checkpoint_id, checkpoint = pending[idx]
                    self.respond_to_checkpoint(checkpoint_id)
                else:
                    print("❌ Invalid checkpoint number")
            else:
                print("❌ Invalid option")

def main():
    """Main execution function."""
    responder = CheckpointResponder()
    
    print("🛑 CHECKPOINT RESPONSE TOOL")
    print("=" * 40)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        checkpoint_id = sys.argv[1]
        print(f"Responding to checkpoint: {checkpoint_id}")
        success = responder.respond_to_checkpoint(checkpoint_id)
        if not success:
            sys.exit(1)
    else:
        print("No checkpoint ID provided - entering interactive mode")
        responder.interactive_mode()
        
    print("✅ Checkpoint response completed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)