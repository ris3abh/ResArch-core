#!/usr/bin/env python3
# tests/individual_tests/run_tests.py
"""
Test runner for individual component tests
"""
import subprocess
import sys
from pathlib import Path

def run_individual_tests():
    """Run all individual component tests"""
    test_dir = Path(__file__).parent
    
    tests = [
        "test_agent_factory.py",
        "test_database_models.py", 
        "test_knowledge_management.py",
        "test_chat_system.py",
        "test_workflow_engine.py"
    ]
    
    print("🧪 Running SpinScribe Individual Component Tests")
    print("=" * 60)
    
    results = {}
    
    for test_file in tests:
        test_path = test_dir / test_file
        if test_path.exists():
            print(f"\n📋 Running {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(test_path), "-v", "--tb=short"
                ], capture_output=True, text=True, cwd=test_dir.parent.parent)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} PASSED")
                    results[test_file] = "PASSED"
                else:
                    print(f"❌ {test_file} FAILED")
                    print(f"Error output: {result.stderr}")
                    results[test_file] = "FAILED"
                    
            except Exception as e:
                print(f"❌ {test_file} ERROR: {e}")
                results[test_file] = "ERROR"
        else:
            print(f"⚠️ {test_file} not found, skipping...")
            results[test_file] = "SKIPPED"
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test, status in results.items():
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "ERROR": "💥",
            "SKIPPED": "⚠️"
        }.get(status, "❓")
        print(f"{status_icon} {test}: {status}")
    
    passed = sum(1 for status in results.values() if status == "PASSED")
    total = len([r for r in results.values() if r != "SKIPPED"])
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = run_individual_tests()
    sys.exit(0 if success else 1)
