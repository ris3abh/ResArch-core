# api/services/crewai.py
import httpx
from typing import Dict, Any, Optional
from api.config import settings

class CrewAIService:
    def __init__(self):
        self.base_url = settings.CREWAI_API_URL
        self.bearer_token = settings.CREWAI_BEARER_TOKEN
        self.user_bearer_token = settings.CREWAI_USER_BEARER_TOKEN
        self.webhook_base_url = settings.API_BASE_URL
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for CrewAI API"""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
    
    async def kickoff_crew(
        self,
        inputs: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Start a CrewAI crew execution
        
        Args:
            inputs: Input parameters for the crew
            execution_id: Our internal execution ID for tracking
        
        Returns:
            Response with kickoff_id from CrewAI
        """
        payload = {
            "inputs": inputs,
            "humanInputWebhook": {
                "url": f"{self.webhook_base_url}/api/v1/webhook/hitl",
                "authentication": {
                    "strategy": "bearer",
                    "token": settings.WEBHOOK_SECRET_TOKEN
                }
            },
            "webhooks": {
                "events": [
                    # Subscribe to ALL events
                    "crew_kickoff_started",
                    "crew_kickoff_completed",
                    "crew_kickoff_failed",
                    "task_started",
                    "task_completed",
                    "task_failed",
                    "agent_execution_started",
                    "agent_execution_completed",
                    "tool_usage_started",
                    "tool_usage_finished",
                    "llm_call_started",
                    "llm_call_completed",
                    "llm_stream_chunk"
                ],
                "url": f"{self.webhook_base_url}/api/v1/webhook/stream",
                "realtime": False,  # Batch events for better performance
                "authentication": {
                    "strategy": "bearer",
                    "token": settings.WEBHOOK_SECRET_TOKEN
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/kickoff",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def resume_crew(
        self,
        crewai_execution_id: str,
        task_id: str,
        human_feedback: str,
        is_approve: bool
    ) -> Dict[str, Any]:
        """
        Resume a crew execution after HITL checkpoint
        
        CRITICAL: Must re-provide webhook URLs!
        """
        payload = {
            "execution_id": crewai_execution_id,
            "task_id": task_id,
            "human_feedback": human_feedback,
            "is_approve": is_approve,
            # CRITICAL: Re-provide webhooks for continued notifications
            "taskWebhookUrl": f"{self.webhook_base_url}/api/v1/webhook/task",
            "stepWebhookUrl": f"{self.webhook_base_url}/api/v1/webhook/step",
            "crewWebhookUrl": f"{self.webhook_base_url}/api/v1/webhook/crew"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/resume",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def get_status(self, crewai_execution_id: str) -> Dict[str, Any]:
        """Get execution status from CrewAI"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/status/{crewai_execution_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def cancel_execution(self, crewai_execution_id: str) -> bool:
        """Cancel a running execution (if supported by CrewAI)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/cancel/{crewai_execution_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError:
            return False

# Singleton instance
crewai_service = CrewAIService()