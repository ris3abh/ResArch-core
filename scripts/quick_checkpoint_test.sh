#!/bin/bash
# ─── FILE: scripts/quick_checkpoint_test.sh ───────────────────────────
# Quick checkpoint testing script - run this to test everything!

echo "🚀 SPINSCRIBE CHECKPOINT TESTING - QUICK START"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "config/settings.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Make scripts executable
chmod +x scripts/*.py 2>/dev/null || true

echo ""
echo "🔧 SETUP OPTIONS:"
echo "1. Human Review Testing (you respond manually)"
echo "2. Mock Review Testing (automated responses)"
echo "3. Show current configuration"
echo "4. Full workflow test with checkpoints"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🛑 SETTING UP HUMAN REVIEW TESTING"
        echo "=================================="
        python config/checkpoint_settings.py human
        echo ""
        echo "🚀 Starting checkpoint test..."
        echo "⚠️  You'll need to respond to checkpoints as they appear!"
        echo ""
        read -p "Press Enter to start, or Ctrl+C to cancel..."
        python scripts/test_checkpoints.py
        ;;
    2)
        echo ""
        echo "🤖 SETTING UP MOCK REVIEW TESTING"
        echo "================================="
        python config/checkpoint_settings.py mock
        echo ""
        echo "🚀 Starting automated checkpoint test..."
        python scripts/test_checkpoints.py
        ;;
    3)
        echo ""
        python config/checkpoint_settings.py status
        ;;
    4)
        echo ""
        echo "🚀 FULL WORKFLOW TEST WITH CHECKPOINTS"
        echo "======================================"
        echo "This will run the complete SpinScribe workflow with checkpoints enabled."
        echo ""
        python config/checkpoint_settings.py human
        echo ""
        read -p "Enter article title (default: 'Checkpoint Testing Article'): " title
        title=${title:-"Checkpoint Testing Article"}
        echo ""
        echo "Starting workflow: $title"
        echo "⚠️  Respond to checkpoints in another terminal with:"
        echo "   python scripts/respond_to_checkpoint.py <checkpoint_id>"
        echo ""
        read -p "Press Enter to start..."
        
        # Run the actual workflow
        python run.py \
            --title "$title" \
            --type article \
            --project-id checkpoint-test \
            --enable-checkpoints \
            --client-docs examples/client_documents \
            --verbose
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "✅ Checkpoint testing completed!"
echo ""
echo "📋 USEFUL COMMANDS:"
echo "  - List pending checkpoints: python scripts/respond_to_checkpoint.py"
echo "  - Respond to specific checkpoint: python scripts/respond_to_checkpoint.py <id>"
echo "  - Change config: python config/checkpoint_settings.py <mode>"
echo "  - View logs: tail -f logs/spinscribe.log"