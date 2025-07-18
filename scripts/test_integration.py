#!/usr/bin/env python3
"""
Integration test script for Spinscribe Service Wrapper
Tests the integration between existing CAMEL system and new web interface
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

class SpinscribeIntegrationTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self):
        """Test basic health check endpoint."""
        print("🏥 Testing health check...")
        async with self.session.get(f"{self.base_url}/health") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "healthy"
            print("✅ Health check passed")
    
    async def test_workflow_creation(self):
        """Test workflow creation using existing CAMEL system."""
        print("🔄 Testing workflow creation...")
        
        workflow_data = {
            "project_id": "test-integration",
            "title": "Test Article",
            "content_type": "article",
            "task_description": "Create a test article about AI technology",
            "workflow_type": "enhanced",
            "enable_checkpoints": True
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/workflows",
            json=workflow_data
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            workflow_id = data["workflow_id"]
            print(f"✅ Workflow created: {workflow_id}")
            return workflow_id
    
    async def test_workflow_status(self, workflow_id: str):
        """Test workflow status monitoring."""
        print("📊 Testing workflow status...")
        
        async with self.session.get(
            f"{self.base_url}/api/v1/workflows/{workflow_id}"
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["workflow_id"] == workflow_id
            print(f"✅ Workflow status: {data['status']}")
            return data
    
    async def test_system_status(self):
        """Test system status endpoint."""
        print("⚙️ Testing system status...")
        
        async with self.session.get(
            f"{self.base_url}/api/v1/system/status"
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            print(f"✅ System status: {data}")
            return data
    
    async def run_integration_tests(self):
        """Run complete integration test suite."""
        print("🧪 Starting Spinscribe Integration Tests")
        print("=" * 50)
        
        try:
            # Basic health check
            await self.test_health_check()
            
            # System status
            await self.test_system_status()
            
            # Workflow creation and monitoring
            workflow_id = await self.test_workflow_creation()
            await asyncio.sleep(2)  # Give workflow time to start
            await self.test_workflow_status(workflow_id)
            
            print("=" * 50)
            print("🎉 All integration tests passed!")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            raise

async def main():
    """Run integration tests."""
    async with SpinscribeIntegrationTest() as test_runner:
        await test_runner.run_integration_tests()

if __name__ == "__main__":
    asyncio.run(main())
