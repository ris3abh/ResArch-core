# backend/test_spinscribe_integration.py
"""
FIXED: Test script that properly loads environment BEFORE importing Spinscribe.
This solves the RuntimeError about missing OPENAI_API_KEY.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# CRITICAL: Load environment variables BEFORE any other imports
def load_environment_first():
    """Load environment variables before importing anything from Spinscribe."""
    
    print("🔧 Loading environment variables...")
    
    # Get paths
    backend_root = Path(__file__).parent
    project_root = backend_root.parent
    
    # Try to load python-dotenv
    try:
        from dotenv import load_dotenv
        
        # Load main project .env first (if exists)
        main_env = project_root / ".env"
        if main_env.exists():
            load_dotenv(main_env)
            print(f"✅ Loaded main project .env: {main_env}")
        else:
            print(f"⚠️ Main project .env not found: {main_env}")
        
        # Load backend .env second (overrides main project)
        backend_env = backend_root / ".env"
        if backend_env.exists():
            load_dotenv(backend_env, override=True)
            print(f"✅ Loaded backend .env: {backend_env}")
        else:
            print(f"❌ Backend .env not found: {backend_env}")
            print("💡 Make sure you created the backend/.env file with the Spinscribe variables")
            return False
            
    except ImportError:
        print("❌ python-dotenv not available. Install it with: pip install python-dotenv")
        return False
    
    # Verify critical environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("💡 Make sure your backend/.env file contains:")
        print("   OPENAI_API_KEY=your-api-key-here")
        return False
    
    if openai_key.startswith("sk-"):
        print("✅ OPENAI_API_KEY found and looks valid")
    else:
        print("⚠️ OPENAI_API_KEY found but doesn't look like a valid OpenAI key")
    
    # Set other required defaults if missing
    if not os.getenv("MODEL_PLATFORM"):
        os.environ["MODEL_PLATFORM"] = "openai"
        print("🔧 Set default MODEL_PLATFORM=openai")
    
    if not os.getenv("MODEL_TYPE"):
        os.environ["MODEL_TYPE"] = "gpt-4o-mini"
        print("🔧 Set default MODEL_TYPE=gpt-4o-mini")
    
    if not os.getenv("DEFAULT_TASK_ID"):
        os.environ["DEFAULT_TASK_ID"] = "spinscribe-content-task"
        print("🔧 Set default DEFAULT_TASK_ID=spinscribe-content-task")
    
    print("✅ Environment variables loaded successfully")
    return True

# Load environment FIRST, before any other imports
if not load_environment_first():
    print("\n❌ Failed to load environment variables. Exiting.")
    sys.exit(1)

# Add project root to path AFTER loading environment
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_spinscribe_integration():
    """Test the complete Spinscribe integration."""
    
    print("\n🧪 Testing Spinscribe Backend Integration")
    print("=" * 50)
    
    results = {
        "environment_loaded": True,  # We already verified this
        "spinscribe_import": False,
        "workflow_service_import": False,
        "health_check": False,
        "sample_workflow": False
    }
    
    # Test 1: Import Spinscribe modules (now that environment is loaded)
    try:
        print("\n1️⃣ Testing Spinscribe imports...")
        
        # Test enhanced process import
        from spinscribe.tasks.enhanced_process import run_enhanced_content_task
        print("   ✅ Enhanced process import successful")
        
        # Test basic process import
        from spinscribe.tasks.process import run_content_task
        print("   ✅ Basic process import successful")
        
        # Test utilities
        from spinscribe.utils.enhanced_logging import setup_enhanced_logging
        print("   ✅ Utilities import successful")
        
        results["spinscribe_import"] = True
        
    except ImportError as e:
        print(f"   ❌ Spinscribe import failed: {e}")
        print("   💡 Make sure CAMEL is installed: pip install camel-ai[all]")
    except Exception as e:
        print(f"   ❌ Spinscribe import failed with error: {e}")
        print("   💡 Check your environment variables and project structure")
    
    # Test 2: Import workflow service
    try:
        print("\n2️⃣ Testing workflow service imports...")
        
        from services.workflow.camel_workflow_service import workflow_service, health_check
        print("   ✅ Workflow service import successful")
        
        results["workflow_service_import"] = True
        
    except ImportError as e:
        print(f"   ❌ Workflow service import failed: {e}")
        print("   💡 Make sure the camel_workflow_service.py file is in services/workflow/")
    except Exception as e:
        print(f"   ❌ Workflow service import failed with error: {e}")
    
    # Test 3: Health check
    if results["workflow_service_import"]:
        try:
            print("\n3️⃣ Testing workflow service health...")
            
            health_status = await health_check()
            print(f"   ✅ Health check successful: {health_status['status']}")
            print(f"   📊 Spinscribe status: {health_status.get('spinscribe_available', 'unknown')}")
            print(f"   🔑 OpenAI configured: {health_status.get('openai_api_configured', 'unknown')}")
            
            results["health_check"] = True
            
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
    
    # Test 4: Sample workflow creation (if everything else works)
    if all([results["spinscribe_import"], results["workflow_service_import"], results["health_check"]]):
        try:
            print("\n4️⃣ Testing sample workflow creation...")
            
            # Import the request schema
            from app.schemas.workflow import WorkflowCreateRequest
            
            # Create a test request
            test_request = WorkflowCreateRequest(
                project_id="test-project",
                title="Integration Test Article",
                content_type="article",
                initial_draft=None,
                use_project_documents=False
            )
            
            print("   📝 Test request created successfully")
            print("   ⚠️  Skipping actual workflow execution (would consume API credits)")
            print("   ✅ Sample workflow structure test passed")
            
            results["sample_workflow"] = True
            
        except Exception as e:
            print(f"   ❌ Sample workflow test failed: {e}")
    
    # Final results
    print("\n" + "=" * 50)
    print("🎯 INTEGRATION TEST RESULTS")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your Spinscribe backend integration is ready!")
        print("\n📝 Next steps:")
        print("   1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("   2. Test the /api/v1/workflows/start endpoint")
        print("   3. Check /api/v1/workflows/health for service status")
        print("   4. Try creating a workflow via the API")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")
        print("\n🔧 Common fixes:")
        print("   1. Ensure backend/.env file exists with OPENAI_API_KEY")
        print("   2. Install requirements: pip install -r requirements.txt")
        print("   3. Check file paths and project structure")
        print("   4. Verify CAMEL-AI is properly installed")
    
    return passed == total

async def test_environment_details():
    """Test and display detailed environment information."""
    
    print("\n🔍 Environment Details")
    print("-" * 30)
    
    # Check critical environment variables
    env_vars = [
        "OPENAI_API_KEY",
        "MODEL_PLATFORM", 
        "MODEL_TYPE",
        "DEFAULT_TASK_ID",
        "LOG_LEVEL"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == "OPENAI_API_KEY":
                # Mask the API key for security
                masked_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: ❌ Not set")
    
    # Check file paths
    print(f"\n📁 File Paths:")
    backend_root = Path(__file__).parent
    project_root = backend_root.parent
    
    print(f"   Backend root: {backend_root}")
    print(f"   Project root: {project_root}")
    print(f"   Backend .env exists: {(backend_root / '.env').exists()}")
    print(f"   Main .env exists: {(project_root / '.env').exists()}")
    
    # Check if we can find Spinscribe
    spinscribe_path = project_root / "spinscribe"
    print(f"   Spinscribe folder exists: {spinscribe_path.exists()}")
    
    if spinscribe_path.exists():
        enhanced_process = spinscribe_path / "tasks" / "enhanced_process.py"
        print(f"   Enhanced process exists: {enhanced_process.exists()}")

if __name__ == "__main__":
    print("🚀 Spinscribe Backend Integration Test")
    print("=" * 50)
    
    # Show environment details first
    asyncio.run(test_environment_details())
    
    # Run the main integration test
    success = asyncio.run(test_spinscribe_integration())
    
    if success:
        print("\n🚀 Integration test completed successfully!")
    else:
        print("\n⚠️  Integration test had issues. Check the details above.")
    
    sys.exit(0 if success else 1)