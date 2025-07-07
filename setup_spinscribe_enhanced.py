# ─── NEW FILE: setup_spinscribe_enhanced.py ───────────────────
"""
Setup script for enhanced SpinScribe with RAG and checkpoints.
Run this to initialize the enhanced system.
"""

import asyncio
import os
import sys
from pathlib import Path
import logging

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager
from config.settings import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_enhanced_spinscribe():
    """Initialize enhanced SpinScribe system."""
    
    print("🚀 Setting up Enhanced SpinScribe System")
    print("=" * 50)
    
    # Step 1: Create necessary directories
    directories = [
        DOCUMENTS_STORAGE_PATH,
        KNOWLEDGE_INDEX_PATH,
        "./data/logs",
        "./data/checkpoints"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Step 2: Test Qdrant connection
    print("\n🔍 Testing Qdrant Vector Database Connection...")
    try:
        km = KnowledgeManager()
        print("✅ Vector database connection successful")
    except Exception as e:
        print(f"❌ Vector database connection failed: {e}")
        print("💡 Make sure Qdrant is running (docker-compose up qdrant)")
        return False
    
    # Step 3: Test checkpoint system
    print("\n✋ Testing Checkpoint System...")
    try:
        cm = CheckpointManager()
        test_checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.BRIEF_REVIEW,
            title="System Test Checkpoint",
            description="Testing checkpoint system initialization"
        )
        print(f"✅ Checkpoint system working (ID: {test_checkpoint_id})")
    except Exception as e:
        print(f"❌ Checkpoint system failed: {e}")
        return False
    
    # Step 4: Create example client project
    print("\n📚 Setting up example client project...")
    try:
        example_docs_path = Path("./examples/client_documents")
        example_docs_path.mkdir(parents=True, exist_ok=True)
        
        # Create example documents
        example_brand_guide = example_docs_path / "brand_guidelines.md"
        example_brand_guide.write_text("""
# TechCorp Brand Guidelines

## Brand Voice
- Professional yet approachable
- Clear and concise communication
- Innovation-focused language
- Customer-centric messaging

## Tone Characteristics
- Confident but not arrogant
- Helpful and educational
- Forward-thinking
- Trustworthy and reliable

## Key Vocabulary
- "Innovative solutions"
- "Streamlined processes"
- "Customer success"
- "Digital transformation"
- "Cutting-edge technology"

## Style Guidelines
- Use active voice
- Keep sentences under 20 words
- Include specific examples
- Maintain consistency across all content
        """)
        
        example_style_guide = example_docs_path / "style_guide.txt"
        example_style_guide.write_text("""
TechCorp Style Guide

Writing Style:
- Conversational yet professional
- Use second person (you/your) to engage readers
- Include industry expertise while remaining accessible
- Focus on benefits and outcomes for customers

Formatting:
- Use bullet points for easy scanning
- Include subheadings every 2-3 paragraphs
- Bold key concepts and takeaways
- Include call-to-action in conclusions

Content Types:
- Blog posts: 800-1200 words, educational focus
- Landing pages: 500-800 words, conversion-focused
- Case studies: 1000-1500 words, story-driven
        """)
        
        print(f"✅ Example documents created in: {example_docs_path}")
        
    except Exception as e:
        print(f"❌ Failed to create example project: {e}")
    
    print("\n🎉 Enhanced SpinScribe Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Run: python scripts/enhanced_run_workflow.py --help")
    print("2. Try: python scripts/enhanced_run_workflow.py --title 'AI Innovation' --type article --project-id techcorp-demo --client-docs ./examples/client_documents")
    print("3. Check the comprehensive output with RAG knowledge and checkpoint approvals")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_enhanced_spinscribe())
    if not success:
        sys.exit(1)