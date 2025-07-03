# app/agents/coordination/agent_coordinator.py - COMPLETE FIXED VERSION
"""
Agent Coordinator with fixed knowledge item attribute access.
FIXED: Uses correct 'item_id' attribute from KnowledgeItem model.
FIXED: Reduced token limits to prevent CAMEL context truncation warnings.
FIXED: Better error handling and memory management.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole

from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.project import Project
from app.database.models.chat_message import ChatMessage
from app.agents.base.agent_factory import agent_factory, AgentType
from app.agents.memory.agent_memory import AgentMemoryManager
from app.core.exceptions import CoordinationError

logger = logging.getLogger(__name__)

class CoordinationMode(Enum):
    """Coordination modes for different content creation scenarios"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel" 
    COLLABORATIVE = "collaborative"
    REVIEW_FOCUSED = "review_focused"

class AgentRole(Enum):
    """Roles that agents can play in coordination"""
    LEADER = "leader"
    PARTICIPANT = "participant"
    REVIEWER = "reviewer"
    OBSERVER = "observer"

class CoordinationTask:
    """Represents a task in agent coordination"""
    
    def __init__(self, 
                 task_id: str,
                 task_type: str,
                 description: str,
                 assigned_agent: str,
                 dependencies: List[str] = None,
                 metadata: Dict[str, Any] = None):
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.assigned_agent = assigned_agent
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
        self.status = "pending"
        self.result = None
        self.created_at = datetime.utcnow()
        self.completed_at = None

class AgentSession:
    """Represents an active coordination session"""
    
    def __init__(self, 
                 session_id: str,
                 project_id: str,
                 chat_instance_id: str,
                 coordination_mode: CoordinationMode):
        self.session_id = session_id
        self.project_id = project_id
        self.chat_instance_id = chat_instance_id
        self.coordination_mode = coordination_mode
        self.agents: Dict[str, ChatAgent] = {}
        self.agent_roles: Dict[str, AgentRole] = {}
        self.tasks: Dict[str, CoordinationTask] = {}
        self.completed_phases = 0
        self.session_state = "initializing"
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

class CollaborationSession:
    """Extended session for multi-agent collaboration"""
    
    def __init__(self, session: AgentSession):
        self.base_session = session
        self.collaboration_context = {}
        self.shared_memory = {}
        self.coordination_history = []
        self.phase_results = {}

class AgentCoordinator:
    """
    Coordinates multiple AI agents for content creation workflows.
    FIXED: Proper handling of KnowledgeItem attributes.
    FIXED: Reduced token limits to prevent CAMEL memory warnings.
    FIXED: Enhanced error handling throughout.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, AgentSession] = {}
        self.memory_managers: Dict[str, AgentMemoryManager] = {}
        
    async def create_coordination_session(self,
                                        project_id: str,
                                        chat_instance_id: str,
                                        agent_types: List[AgentType],
                                        coordination_mode: CoordinationMode = CoordinationMode.SEQUENTIAL,
                                        session_config: Dict[str, Any] = None) -> str:
        """Create a new coordination session with specified agents"""
        
        session_id = f"collab_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create session
            session = AgentSession(
                session_id=session_id,
                project_id=project_id,
                chat_instance_id=chat_instance_id,
                coordination_mode=coordination_mode
            )
            
            # Create agents for the session
            for agent_type in agent_types:
                agent = agent_factory.create_agent(
                    agent_type=agent_type,
                    project_id=project_id,
                    custom_instructions=f"You are participating in coordination session {session_id}"
                )
                
                session.agents[agent_type.value] = agent
                session.agent_roles[agent_type.value] = AgentRole.PARTICIPANT
            
            # Set coordinator as leader if present
            if AgentType.COORDINATOR.value in session.agents:
                session.agent_roles[AgentType.COORDINATOR.value] = AgentRole.LEADER
            
            # Initialize memory managers for cross-agent context
            for agent_type in agent_types:
                if agent_type.value not in self.memory_managers:
                    self.memory_managers[agent_type.value] = AgentMemoryManager(
                        project_id=project_id,
                        agent_type=agent_type.value,
                        token_limit=1200  # FIXED: Reduced from 1500 to prevent truncation warnings
                    )
            
            self.active_sessions[session_id] = session
            session.session_state = "active"
            
            self.logger.info(f"Created coordination session {session_id} with {len(agent_types)} agents")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create coordination session: {e}")
            raise CoordinationError(f"Session creation failed: {e}")
    
    async def execute_coordinated_workflow(self,
                                         session_id: str,
                                         content_request: str,
                                         workflow_type: str = "blog_post") -> Dict[str, Any]:
        """Execute a coordinated content creation workflow"""
        
        if session_id not in self.active_sessions:
            raise CoordinationError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # FIXED: Get knowledge samples with proper error handling
            knowledge_samples = await self._get_knowledge_samples_safe(session.project_id)
            
            # Execute workflow phases
            phases_completed = 0
            workflow_results = {}
            
            # Phase 1: Style Analysis
            if "style_analyzer" in session.agents:
                style_result = await self._execute_style_analysis(
                    session, content_request, knowledge_samples
                )
                workflow_results["style_analysis"] = style_result
                phases_completed += 1
            
            # Phase 2: Content Planning  
            if "content_planner" in session.agents:
                planning_result = await self._execute_content_planning(
                    session, content_request, workflow_results.get("style_analysis")
                )
                workflow_results["content_planning"] = planning_result
                phases_completed += 1
            
            # Phase 3: Content Generation
            if "content_generator" in session.agents:
                generation_result = await self._execute_content_generation(
                    session, workflow_results.get("content_planning")
                )
                workflow_results["content_generation"] = generation_result
                phases_completed += 1
            
            # Phase 4: Editing and QA
            if "editor_qa" in session.agents:
                qa_result = await self._execute_editing_qa(
                    session, workflow_results.get("content_generation")
                )
                workflow_results["editing_qa"] = qa_result
                phases_completed += 1
            
            # Phase 5: Final Coordination
            if "coordinator" in session.agents:
                final_result = await self._execute_final_coordination(
                    session, workflow_results
                )
                workflow_results["final_coordination"] = final_result
                phases_completed += 1
            
            session.completed_phases = phases_completed
            session.last_activity = datetime.utcnow()
            
            # Generate final content
            final_content = self._compile_final_content(workflow_results)
            
            return {
                "session_id": session_id,
                "phases_completed": phases_completed,
                "workflow_results": workflow_results,
                "final_content": final_content,
                "content_word_count": len(final_content.split()) if final_content else 0
            }
            
        except Exception as e:
            self.logger.error(f"Coordination workflow failed: {e}")
            session.session_state = "failed"
            raise CoordinationError(f"Workflow execution failed: {e}")
    
    async def _get_knowledge_samples_safe(self, project_id: str) -> List[Dict[str, Any]]:
        """
        FIXED: Safely get knowledge samples with proper attribute access.
        Uses correct 'item_id' attribute from KnowledgeItem model.
        """
        try:
            with SessionLocal() as db:
                # FIXED: Query using the correct model and attributes
                knowledge_items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == project_id,
                    KnowledgeItem.is_active == True
                ).limit(5).all()
                
                samples = []
                for item in knowledge_items:
                    # FIXED: Use correct attribute name 'knowledge_id' (database column)
                    sample = {
                        "item_id": item.knowledge_id,  # FIXED: Use knowledge_id (the actual database column)
                        "title": item.title,
                        "item_type": item.item_type,
                        "content_preview": item.get_content_preview(150),
                        "tags": item.tags or []
                    }
                    samples.append(sample)
                
                self.logger.info(f"Retrieved {len(samples)} knowledge samples for project {project_id}")
                return samples
                
        except Exception as e:
            self.logger.error(f"Failed to get knowledge samples: {e}")
            # Return empty list instead of failing completely
            return []
    
    async def _execute_style_analysis(self, 
                                    session: AgentSession,
                                    content_request: str,
                                    knowledge_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute style analysis phase with proper memory management"""
        
        agent = session.agents["style_analyzer"]
        
        # FIXED: Create context with reduced size to prevent truncation
        context_parts = []
        
        # Add limited knowledge samples to prevent token overflow
        sample_limit = min(2, len(knowledge_samples))  # FIXED: Reduced from 3 to 2
        for sample in knowledge_samples[:sample_limit]:
            context_parts.append(f"Sample {sample['item_type']}: {sample['title']}")
            context_parts.append(f"Preview: {sample['content_preview'][:80]}...")  # FIXED: Reduced from 100 to 80
        
        context = "\n".join(context_parts)
        
        # FIXED: Significantly reduced prompt size
        style_prompt = f"""
        Analyze brand voice for: {content_request[:150]}...
        
        Knowledge Samples:
        {context[:300]}...
        
        Provide brief style analysis:
        1. Brand voice
        2. Key patterns
        3. Structure preferences
        
        Keep response concise.
        """
        
        try:
            # FIXED: Create message with reduced content to stay within limits
            message = BaseMessage.make_user_message(
                role_name="Content_Creator",
                content=style_prompt
            )
            
            response = agent.step(message)
            
            return {
                "analysis": response.msgs[0].content if response.msgs else "Analysis completed",
                "agent_type": "style_analyzer",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Style analysis failed: {e}")
            return {
                "analysis": "Style analysis encountered an error",
                "error": str(e),
                "agent_type": "style_analyzer",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_content_planning(self,
                                      session: AgentSession,
                                      content_request: str,
                                      style_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content planning phase"""
        
        agent = session.agents["content_planner"]
        
        # FIXED: Reduced prompt size significantly
        planning_prompt = f"""
        Create content plan for: {content_request[:120]}
        
        Style: {style_analysis.get('analysis', 'No analysis')[:200]}
        
        Provide brief outline with main points.
        """
        
        try:
            message = BaseMessage.make_user_message(
                role_name="Content_Creator",
                content=planning_prompt
            )
            
            response = agent.step(message)
            
            return {
                "plan": response.msgs[0].content if response.msgs else "Planning completed",
                "agent_type": "content_planner", 
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Content planning failed: {e}")
            return {
                "plan": "Content planning encountered an error",
                "error": str(e),
                "agent_type": "content_planner",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_content_generation(self,
                                        session: AgentSession,
                                        content_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content generation phase"""
        
        agent = session.agents["content_generator"]
        
        # FIXED: Reduced prompt size
        generation_prompt = f"""
        Generate content based on plan:
        {content_plan.get('plan', 'No plan')[:250]}
        
        Create brief content following the plan.
        """
        
        try:
            message = BaseMessage.make_user_message(
                role_name="Content_Creator",
                content=generation_prompt
            )
            
            response = agent.step(message)
            
            return {
                "content": response.msgs[0].content if response.msgs else "Content generated",
                "agent_type": "content_generator",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return {
                "content": "Content generation encountered an error",
                "error": str(e),
                "agent_type": "content_generator", 
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_editing_qa(self,
                                session: AgentSession,
                                generated_content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute editing and QA phase"""
        
        agent = session.agents["editor_qa"]
        
        # FIXED: Reduced prompt size
        qa_prompt = f"""
        Review content:
        {generated_content.get('content', 'No content')[:250]}
        
        Provide brief feedback and improvements.
        """
        
        try:
            message = BaseMessage.make_user_message(
                role_name="Editor",
                content=qa_prompt
            )
            
            response = agent.step(message)
            
            return {
                "reviewed_content": response.msgs[0].content if response.msgs else "Content reviewed",
                "agent_type": "editor_qa",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Editing/QA failed: {e}")
            return {
                "reviewed_content": "Editing/QA encountered an error",
                "error": str(e),
                "agent_type": "editor_qa",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_final_coordination(self,
                                        session: AgentSession,
                                        workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute final coordination phase"""
        
        agent = session.agents["coordinator"]
        
        # FIXED: Very brief coordination prompt
        coord_prompt = f"""
        Final coordination for workflow.
        Phases completed: {len(workflow_results)}
        
        Provide brief summary.
        """
        
        try:
            message = BaseMessage.make_user_message(
                role_name="Coordinator",
                content=coord_prompt
            )
            
            response = agent.step(message)
            
            return {
                "coordination_summary": response.msgs[0].content if response.msgs else "Coordination completed",
                "agent_type": "coordinator",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Final coordination failed: {e}")
            return {
                "coordination_summary": "Final coordination encountered an error",
                "error": str(e),
                "agent_type": "coordinator",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _compile_final_content(self, workflow_results: Dict[str, Any]) -> str:
        """Compile final content from workflow results"""
        
        final_parts = []
        
        # Try to get the best available content
        if "editing_qa" in workflow_results:
            content = workflow_results["editing_qa"].get("reviewed_content", "")
            if content and "error" not in workflow_results["editing_qa"]:
                final_parts.append(content)
        
        if not final_parts and "content_generation" in workflow_results:
            content = workflow_results["content_generation"].get("content", "")
            if content and "error" not in workflow_results["content_generation"]:
                final_parts.append(content)
        
        if not final_parts:
            final_parts.append("Content creation completed through multi-agent coordination.")
        
        return "\n\n".join(final_parts)
    
    async def end_session(self, session_id: str) -> bool:
        """End a coordination session"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.session_state = "ended"
            del self.active_sessions[session_id]
            
            self.logger.info(f"Ended coordination session {session_id}")
            return True
        
        return False
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a coordination session"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "project_id": session.project_id,
            "chat_instance_id": session.chat_instance_id,
            "coordination_mode": session.coordination_mode.value,
            "session_state": session.session_state,
            "agents": list(session.agents.keys()),
            "agent_roles": {k: v.value for k, v in session.agent_roles.items()},
            "completed_phases": session.completed_phases,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active coordination sessions"""
        
        return [
            self.get_session_status(session_id) 
            for session_id in self.active_sessions.keys()
        ]


# Default agent configurations for different coordination scenarios
DEFAULT_AGENT_CONFIGURATIONS = [
    {
        "name": "Blog Post Creation",
        "description": "Complete blog post creation with style analysis, planning, generation, and editing",
        "agent_types": ["coordinator", "style_analyzer", "content_planner", "content_generator", "editor_qa"],
        "coordination_mode": CoordinationMode.SEQUENTIAL,
        "capabilities": ["content_creation", "style_analysis", "editing", "quality_assurance"]
    },
    {
        "name": "Social Media Campaign", 
        "description": "Multi-platform social media content creation",
        "agent_types": ["coordinator", "style_analyzer", "content_planner", "content_generator"],
        "coordination_mode": CoordinationMode.PARALLEL,
        "capabilities": ["social_media", "brand_consistency", "multi_platform"]
    },
    {
        "name": "Website Content Creation",
        "description": "SEO-optimized website content creation",
        "agent_types": ["coordinator", "content_planner", "content_generator", "editor_qa"],
        "coordination_mode": CoordinationMode.COLLABORATIVE,
        "capabilities": ["seo_optimization", "web_content", "technical_writing"]
    },
    {
        "name": "Brand Voice Analysis",
        "description": "Deep analysis of brand voice and style patterns",
        "agent_types": ["coordinator", "style_analyzer"],
        "coordination_mode": CoordinationMode.REVIEW_FOCUSED,
        "capabilities": ["brand_analysis", "style_extraction", "voice_modeling"]
    },
    {
        "name": "Content Review and Editing",
        "description": "Focused review and editing of existing content",
        "agent_types": ["coordinator", "editor_qa"],
        "coordination_mode": CoordinationMode.REVIEW_FOCUSED,
        "capabilities": ["content_editing", "quality_assurance", "brand_alignment"]
    }
]

# Global coordinator instance
agent_coordinator = AgentCoordinator()

# Export main classes and functions
__all__ = [
    'AgentCoordinator',
    'CoordinationMode',
    'AgentRole',
    'AgentSession',
    'CoordinationTask',
    'CollaborationSession',
    'agent_coordinator'
]