#!/bin/bash
# SpinScribe Quick Run Script

echo "🚀 Running SpinScribe Enhanced Workflow"
echo "======================================"

python scripts/enhanced_run_workflow.py \
  --title "SpinScribe Test Article" \
  --type article \
  --project-id spinscribe-test \
  --client-docs examples/client_documents \
  --verbose \
  --timeout 600

echo ""
echo "✅ SpinScribe workflow completed!"
