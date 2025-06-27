#!/bin/bash
# Final dependency fix for SpinScribe

echo "🔧 FINAL SPINSCRIBE DEPENDENCY FIX"
echo "=================================="
echo ""

# Remove conflicting packages that aren't needed for SpinScribe
echo "🗑️ Removing conflicting packages..."
pip uninstall -y thinc pandasai spacy || echo "   (packages not found - that's OK)"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

echo ""
echo "🧪 Testing SpinScribe imports..."

# Test the imports that were previously failing
python3 -c "
import sys
print(f'Python: {sys.version.split()[0]}')
print()

# Test numpy/pandas that were problematic
try:
    import numpy as np
    print(f'✅ numpy {np.__version__}')
except Exception as e:
    print(f'❌ numpy: {e}')

try:
    import pandas as pd
    print(f'✅ pandas {pd.__version__}')
except Exception as e:
    print(f'❌ pandas: {e}')

try:
    import sentence_transformers
    print(f'✅ sentence-transformers available')
except Exception as e:
    print(f'❌ sentence-transformers: {e}')

print()
print('Testing SpinScribe core modules...')

# Test SpinScribe imports
test_results = []

try:
    from app.database.connection import init_db
    print('✅ Database connection module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Database connection: {e}')
    test_results.append(False)

try:
    from app.services.project_service import get_project_service
    print('✅ Project service module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Project service: {e}')
    test_results.append(False)

try:
    from app.agents.base.agent_factory import agent_factory
    print('✅ Agent factory module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Agent factory: {e}')
    test_results.append(False)

try:
    from app.knowledge.retrievers.semantic_retriever import create_semantic_retriever
    print('✅ Semantic retriever module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Semantic retriever: {e}')
    test_results.append(False)

try:
    from app.services.chat_service import get_chat_service
    print('✅ Chat service module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Chat service: {e}')
    test_results.append(False)

try:
    from app.workflows.workflow_execution_engine import workflow_engine
    print('✅ Workflow engine module')
    test_results.append(True)
except Exception as e:
    print(f'❌ Workflow engine: {e}')
    test_results.append(False)

print()
if all(test_results):
    print('🎉 ALL SPINSCRIBE IMPORTS WORKING!')
    print('Ready to run integration test.')
else:
    print('⚠️ Some imports failed, but let\\'s try the test anyway.')
"

echo ""
echo "🎯 DEPENDENCY FIX STATUS"
echo "======================="

# Check if imports worked
if python3 -c "from app.database.connection import init_db; from app.services.project_service import get_project_service" 2>/dev/null; then
    echo "✅ Core SpinScribe modules are working!"
    echo ""
    echo "🧪 Next step: Run the integration test"
    echo "   python tests/test_integration_complete.py"
    echo ""
    echo "🚀 If test passes, start the server:"
    echo "   python -m app.main"
    echo "   Visit: http://localhost:8000/docs"
else
    echo "❌ Still having import issues"
    echo ""
    echo "💡 Try this manual test:"
    echo "   python3 -c \"from app.database.connection import init_db; print('Database works!')\""
fi