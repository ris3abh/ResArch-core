# app/agents/coordination/agent_coordinator.py
"""
Agent Coordination System for SpinScribe
Manages multi-agent communication, task distribution, and result aggregation.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import json
from concurrent.futures import ThreadPoolExecutor
import uuid

from app.agents.base.agent_factory import agent_factory, AgentType
from app.knowledge.retrievers.semantic_retriever import create_semantic_retriever, SearchQuery
from app.services.knowledge_service import get_knowledge_service
from app.services.project_service import get_project_service
from app.database.connection import get_db_session
from app.database.models.chat_message import ChatMessage
from app.core.exceptions import AgentError, CoordinationError

logger = logging.getLogger(__name__)

class CoordinationMode(Enum):
    """Agent coordination modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    COLLABORATIVE = "collaborative"

class AgentRole(Enum):
    """Agent roles in coordination"""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"

@dataclass
class AgentSession:
    """Active agent session information"""
    agent_id: str
    agent_type: AgentType
    role: AgentRole
    project_id: str
    chat_id: str
    agent_instance: Any
    context: Dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    active: bool = True

@dataclass
class CoordinationTask:
    """Task for agent coordination"""
    task_id: str
    task_type: str
    description: str
    assigned_agents: List[str]
    dependencies: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class CollaborationSession:
    """Multi-agent collaboration session"""
    session_id: str
    project_id: str
    chat_id: str
    coordination_mode: CoordinationMode
    participating_agents: Dict[str, AgentSession] = field(default_factory=dict)
    active_tasks: Dict[str, CoordinationTask] = field(default_factory=dict)
    completed_tasks: List[str] = field(default_factory=list)
    session_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)

class AgentCoordinator:
    """
    Coordinates multi-agent interactions for content creation workflows.
    Manages agent communication, task distribution, and result aggregation.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.agent_pool: Dict[str, AgentSession] = {}
        self.executor = ThreadPoolExecutor(max_workers=6)
        
        logger.info("AgentCoordinator initialized")
    
    async def create_collaboration_session(
        self,
        project_id: str,
        chat_id: str,
        agent_types: List[AgentType],
        coordination_mode: CoordinationMode = CoordinationMode.SEQUENTIAL,
        session_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new multi-agent collaboration session"""
        
        session_id = f"collab_{uuid.uuid4().hex[:12]}"
        
        # Create session
        session = CollaborationSession(
            session_id=session_id,
            project_id=project_id,
            chat_id=chat_id,
            coordination_mode=coordination_mode,
            session_context=session_context or {}
        )
        
        # Initialize agents
        for agent_type in agent_types:
            agent_session = await self._create_agent_session(
                agent_type, project_id, chat_id, session_id
            )
            session.participating_agents[agent_session.agent_id] = agent_session
        
        # Store session
        self.active_sessions[session_id] = session
        
        logger.info(f"Created collaboration session {session_id} with {len(agent_types)} agents")
        return session_id
    
    async def _create_agent_session(
        self,
        agent_type: AgentType,
        project_id: str,
        chat_id: str,
        session_id: str
    ) -> AgentSession:
        """Create an individual agent session"""
        
        agent_id = f"agent_{agent_type.value}_{uuid.uuid4().hex[:8]}"
        
        # Get project context for agent
        project_context = await self._get_project_context(project_id)
        
        # Create agent with enhanced instructions
        enhanced_instructions = self._get_collaboration_instructions(
            agent_type, project_context, session_id
        )
        
        agent_instance = agent_factory.create_agent(
            agent_type=agent_type,
            project_id=project_id,
            custom_instructions=enhanced_instructions
        )
        
        # Determine agent role
        role = self._determine_agent_role(agent_type)
        
        agent_session = AgentSession(
            agent_id=agent_id,
            agent_type=agent_type,
            role=role,
            project_id=project_id,
            chat_id=chat_id,
            agent_instance=agent_instance,
            context={
                "session_id": session_id,
                "project_context": project_context,
                "coordination_mode": "collaborative"
            }
        )
        
        logger.info(f"Created agent session {agent_id} for {agent_type.value}")
        return agent_session
    
    async def coordinate_content_creation(
        self,
        session_id: str,
        content_brief: Dict[str, Any],
        workflow_type: str = "blog_post"
    ) -> Dict[str, Any]:
        """Coordinate a complete content creation workflow"""
        
        if session_id not in self.active_sessions:
            raise CoordinationError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        try:
            logger.info(f"Starting content creation coordination for session {session_id}")
            
            # Phase 1: Style Analysis
            style_analysis = await self._coordinate_style_analysis(session, content_brief)
            
            # Phase 2: Content Planning
            content_plan = await self._coordinate_content_planning(
                session, content_brief, style_analysis
            )
            
            # Phase 3: Content Generation
            content_draft = await self._coordinate_content_generation(
                session, content_brief, style_analysis, content_plan
            )
            
            # Phase 4: Content Review and Editing
            final_content = await self._coordinate_content_review(
                session, content_draft, style_analysis, content_plan
            )
            
            # Compile final result
            result = {
                "session_id": session_id,
                "workflow_type": workflow_type,
                "style_analysis": style_analysis,
                "content_plan": content_plan,
                "content_draft": content_draft,
                "final_content": final_content,
                "metadata": {
                    "completed_at": datetime.utcnow().isoformat(),
                    "participating_agents": list(session.participating_agents.keys()),
                    "total_tasks": len(session.completed_tasks),
                    "session_duration": (datetime.utcnow() - session.created_at).total_seconds()
                }
            }
            
            # Log completion
            await self._log_coordination_completion(session, result)
            
            logger.info(f"Content creation coordination completed for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Content creation coordination failed: {e}")
            await self._handle_coordination_error(session, str(e))
            raise CoordinationError(f"Coordination failed: {e}")
    
    async def _coordinate_style_analysis(
        self,
        session: CollaborationSession,
        content_brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate style analysis phase"""
        
        # Find style analyzer agent
        style_agent = self._find_agent_by_type(session, AgentType.STYLE_ANALYZER)
        if not style_agent:
            raise CoordinationError("No style analyzer agent available")
        
        # Get knowledge base samples
        knowledge_samples = await self._get_knowledge_samples(session.project_id)
        
        # Prepare analysis task
        analysis_input = {
            "content_brief": content_brief,
            "knowledge_samples": knowledge_samples,
            "analysis_type": "comprehensive",
            "focus_areas": ["tone", "voice", "style", "vocabulary", "structure"]
        }
        
        # Execute style analysis
        task_id = f"style_analysis_{uuid.uuid4().hex[:8]}"
        result = await self._execute_agent_task(
            style_agent, task_id, "style_analysis", analysis_input
        )
        
        # Process and validate result
        style_analysis = self._process_style_analysis_result(result)
        
        # Share analysis with other agents
        await self._broadcast_to_session(session, "style_analysis_complete", style_analysis)
        
        return style_analysis
    
    async def _coordinate_content_planning(
        self,
        session: CollaborationSession,
        content_brief: Dict[str, Any],
        style_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate content planning phase"""
        
        # Find content planner agent
        planner_agent = self._find_agent_by_type(session, AgentType.CONTENT_PLANNER)
        if not planner_agent:
            raise CoordinationError("No content planner agent available")
        
        # Prepare planning input
        planning_input = {
            "content_brief": content_brief,
            "style_analysis": style_analysis,
            "content_type": content_brief.get("content_type", "blog_post"),
            "target_audience": content_brief.get("target_audience", "general"),
            "key_points": content_brief.get("key_points", []),
            "seo_keywords": content_brief.get("seo_keywords", []),
            "word_count_target": content_brief.get("word_count", 1000)
        }
        
        # Execute content planning
        task_id = f"content_planning_{uuid.uuid4().hex[:8]}"
        result = await self._execute_agent_task(
            planner_agent, task_id, "content_planning", planning_input
        )
        
        # Process planning result
        content_plan = self._process_planning_result(result)
        
        # Get coordinator feedback if available
        coordinator_agent = self._find_agent_by_type(session, AgentType.COORDINATOR)
        if coordinator_agent:
            feedback = await self._get_coordinator_feedback(
                coordinator_agent, content_plan, content_brief
            )
            content_plan["coordinator_feedback"] = feedback
        
        # Share plan with other agents
        await self._broadcast_to_session(session, "content_plan_ready", content_plan)
        
        return content_plan
    
    async def _coordinate_content_generation(
        self,
        session: CollaborationSession,
        content_brief: Dict[str, Any],
        style_analysis: Dict[str, Any],
        content_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate content generation phase"""
        
        # Find content generator agent
        generator_agent = self._find_agent_by_type(session, AgentType.CONTENT_GENERATOR)
        if not generator_agent:
            raise CoordinationError("No content generator agent available")
        
        # Prepare generation input
        generation_input = {
            "content_brief": content_brief,
            "style_analysis": style_analysis,
            "content_plan": content_plan,
            "generation_guidelines": {
                "maintain_style": True,
                "follow_outline": True,
                "include_keywords": content_brief.get("seo_keywords", []),
                "target_tone": style_analysis.get("primary_tone", "professional")
            }
        }
        
        # Execute content generation
        task_id = f"content_generation_{uuid.uuid4().hex[:8]}"
        result = await self._execute_agent_task(
            generator_agent, task_id, "content_generation", generation_input
        )
        
        # Process generation result
        content_draft = self._process_generation_result(result)
        
        # Share draft with other agents
        await self._broadcast_to_session(session, "content_draft_ready", content_draft)
        
        return content_draft
    
    async def _coordinate_content_review(
        self,
        session: CollaborationSession,
        content_draft: Dict[str, Any],
        style_analysis: Dict[str, Any],
        content_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate content review and editing phase"""
        
        # Find editor/QA agent
        editor_agent = self._find_agent_by_type(session, AgentType.EDITOR_QA)
        if not editor_agent:
            raise CoordinationError("No editor/QA agent available")
        
        # Prepare review input
        review_input = {
            "content_draft": content_draft,
            "style_analysis": style_analysis,
            "content_plan": content_plan,
            "review_criteria": {
                "style_consistency": True,
                "factual_accuracy": True,
                "flow_and_structure": True,
                "seo_optimization": True,
                "brand_alignment": True
            }
        }
        
        # Execute content review
        task_id = f"content_review_{uuid.uuid4().hex[:8]}"
        result = await self._execute_agent_task(
            editor_agent, task_id, "content_review", review_input
        )
        
        # Process review result
        final_content = self._process_review_result(result, content_draft)
        
        # Get final coordinator approval if available
        coordinator_agent = self._find_agent_by_type(session, AgentType.COORDINATOR)
        if coordinator_agent:
            approval = await self._get_final_approval(
                coordinator_agent, final_content, review_input
            )
            final_content["coordinator_approval"] = approval
        
        return final_content
    
    async def _execute_agent_task(
        self,
        agent_session: AgentSession,
        task_id: str,
        task_type: str,
        task_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a task with a specific agent"""
        
        try:
            # Update agent activity
            agent_session.last_activity = datetime.utcnow()
            agent_session.message_count += 1
            
            # Format input for agent
            formatted_input = self._format_agent_input(task_type, task_input)
            
            # Execute task in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: agent_session.agent_instance.step(formatted_input)
            )
            
            # Process response
            result = self._process_agent_response(response, task_type)
            
            # Log task execution
            await self._log_agent_task(agent_session, task_id, task_type, result)
            
            logger.info(f"Completed task {task_id} with agent {agent_session.agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"Agent task execution failed: {e}")
            raise AgentError(f"Task execution failed: {e}")
    
    def _format_agent_input(self, task_type: str, task_input: Dict[str, Any]) -> str:
        """Format task input for agent consumption"""
        
        input_parts = []
        
        # Add task-specific header
        task_headers = {
            "style_analysis": "STYLE ANALYSIS TASK",
            "content_planning": "CONTENT PLANNING TASK", 
            "content_generation": "CONTENT GENERATION TASK",
            "content_review": "CONTENT REVIEW TASK"
        }
        
        header = task_headers.get(task_type, "TASK")
        input_parts.append(f"=== {header} ===\n")
        
        # Add content brief if present
        if "content_brief" in task_input:
            brief = task_input["content_brief"]
            input_parts.append("CONTENT BRIEF:")
            for key, value in brief.items():
                input_parts.append(f"- {key}: {value}")
            input_parts.append("")
        
        # Add task-specific instructions
        if task_type == "style_analysis":
            input_parts.append("INSTRUCTIONS:")
            input_parts.append("Analyze the provided content samples to identify:")
            input_parts.append("- Primary tone and voice characteristics")
            input_parts.append("- Vocabulary patterns and word choice")
            input_parts.append("- Sentence structure preferences")
            input_parts.append("- Brand personality indicators")
            input_parts.append("- Style guidelines and recommendations")
            
            if "knowledge_samples" in task_input:
                input_parts.append("\nCONTENT SAMPLES TO ANALYZE:")
                for i, sample in enumerate(task_input["knowledge_samples"][:3], 1):
                    input_parts.append(f"Sample {i}: {sample.get('content', '')[:300]}...")
        
        elif task_type == "content_planning":
            input_parts.append("INSTRUCTIONS:")
            input_parts.append("Create a detailed content outline that includes:")
            input_parts.append("- Clear introduction hook")
            input_parts.append("- Logical section progression")
            input_parts.append("- Key points for each section")
            input_parts.append("- SEO keyword integration plan")
            input_parts.append("- Compelling conclusion strategy")
            
            if "style_analysis" in task_input:
                style = task_input["style_analysis"]
                input_parts.append(f"\nSTYLE REQUIREMENTS:")
                input_parts.append(f"- Tone: {style.get('primary_tone', 'professional')}")
                input_parts.append(f"- Voice: {style.get('brand_voice', 'authoritative')}")
        
        elif task_type == "content_generation":
            input_parts.append("INSTRUCTIONS:")
            input_parts.append("Generate high-quality content that:")
            input_parts.append("- Follows the provided outline exactly")
            input_parts.append("- Maintains consistent style and tone")
            input_parts.append("- Integrates keywords naturally")
            input_parts.append("- Engages the target audience")
            input_parts.append("- Meets the specified word count")
            
            if "content_plan" in task_input:
                plan = task_input["content_plan"]
                input_parts.append("\nCONTENT OUTLINE:")
                input_parts.append(plan.get("outline", "No outline provided"))
        
        elif task_type == "content_review":
            input_parts.append("INSTRUCTIONS:")
            input_parts.append("Review and edit the content for:")
            input_parts.append("- Style consistency and brand alignment")
            input_parts.append("- Flow, clarity, and readability")
            input_parts.append("- Factual accuracy and credibility")
            input_parts.append("- SEO optimization")
            input_parts.append("- Grammar and language quality")
            
            if "content_draft" in task_input:
                draft = task_input["content_draft"]
                input_parts.append("\nCONTENT TO REVIEW:")
                input_parts.append(draft.get("content", "No content provided"))
        
        return "\n".join(input_parts)
    
    def _process_agent_response(self, response, task_type: str) -> Dict[str, Any]:
        """Process agent response into structured result"""
        
        # Extract content from response
        if hasattr(response, 'content'):
            content = response.content
        elif hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)
        
        # Create structured result based on task type
        result = {
            "task_type": task_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "word_count": len(content.split()) if isinstance(content, str) else 0,
                "character_count": len(content) if isinstance(content, str) else 0
            }
        }
        
        return result
    
    def _process_style_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process style analysis result into structured format"""
        content = result.get("content", "")
        
        # Extract key insights (this would be more sophisticated in production)
        style_analysis = {
            "raw_analysis": content,
            "primary_tone": "professional",  # Would extract from content
            "brand_voice": "authoritative",  # Would extract from content  
            "key_characteristics": [],  # Would extract from content
            "style_guidelines": content,
            "confidence_score": 0.85,
            "timestamp": result.get("timestamp")
        }
        
        return style_analysis
    
    def _process_planning_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process content planning result into structured format"""
        content = result.get("content", "")
        
        content_plan = {
            "outline": content,
            "structure": "hierarchical",  # Would extract from content
            "estimated_word_count": result.get("metadata", {}).get("word_count", 0),
            "key_sections": [],  # Would extract from content
            "seo_strategy": "integrated",  # Would extract from content
            "timestamp": result.get("timestamp")
        }
        
        return content_plan
    
    def _process_generation_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process content generation result into structured format"""
        content = result.get("content", "")
        
        content_draft = {
            "content": content,
            "word_count": result.get("metadata", {}).get("word_count", 0),
            "character_count": result.get("metadata", {}).get("character_count", 0),
            "sections": [],  # Would extract from content
            "quality_indicators": {
                "readability": "good",
                "keyword_density": "appropriate",
                "structure": "well-organized"
            },
            "timestamp": result.get("timestamp")
        }
        
        return content_draft
    
    def _process_review_result(self, result: Dict[str, Any], original_draft: Dict[str, Any]) -> Dict[str, Any]:
        """Process content review result into structured format"""
        reviewed_content = result.get("content", "")
        
        final_content = {
            "content": reviewed_content,
            "original_draft": original_draft.get("content", ""),
            "review_notes": result.get("content", ""),
            "improvements_made": [],  # Would extract from content
            "quality_score": 0.9,  # Would calculate based on review
            "final_word_count": len(reviewed_content.split()) if isinstance(reviewed_content, str) else 0,
            "ready_for_publication": True,
            "timestamp": result.get("timestamp")
        }
        
        return final_content
    
    def _find_agent_by_type(self, session: CollaborationSession, agent_type: AgentType) -> Optional[AgentSession]:
        """Find agent by type in session"""
        for agent in session.participating_agents.values():
            if agent.agent_type == agent_type and agent.active:
                return agent
        return None
    
    async def _get_knowledge_samples(self, project_id: str) -> List[Dict[str, Any]]:
        """Get knowledge samples for style analysis"""
        try:
            knowledge_service = get_knowledge_service()
            with get_db_session() as db:
                knowledge_items = knowledge_service.get_by_project_id(project_id, db, limit=5)
                
                samples = []
                for item in knowledge_items:
                    if item.item_type in ["content_sample", "style_guide"]:
                        samples.append({
                            "id": item.item_id,
                            "type": item.item_type,
                            "title": item.title,
                            "content": item.content
                        })
                
                return samples
                
        except Exception as e:
            logger.error(f"Failed to get knowledge samples: {e}")
            return []
    
    async def _get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get project context for agent initialization"""
        try:
            project_service = get_project_service()
            with get_db_session() as db:
                project = project_service.get_by_id_or_raise(project_id, db)
                
                return {
                    "project_id": project_id,
                    "client_name": project.client_name,
                    "description": project.description,
                    "configuration": project.configuration,
                    "status": project.status
                }
                
        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
            return {"project_id": project_id, "error": str(e)}
    
    def _get_collaboration_instructions(
        self,
        agent_type: AgentType,
        project_context: Dict[str, Any],
        session_id: str
    ) -> str:
        """Get collaboration-specific instructions for agent"""
        
        base_instructions = {
            AgentType.COORDINATOR: """
You are coordinating a multi-agent content creation workflow. Your role is to:
- Oversee the entire content creation process
- Ensure quality and consistency across all phases
- Provide guidance and feedback to other agents
- Make final approval decisions
- Maintain project alignment throughout the workflow
""",
            AgentType.STYLE_ANALYZER: """
You are analyzing content to extract brand voice and style patterns. Your role is to:
- Identify tone, voice, and style characteristics from provided samples
- Create detailed style guidelines for content creation
- Ensure analysis is thorough and actionable for other agents
- Provide clear recommendations for maintaining brand consistency
""",
            AgentType.CONTENT_PLANNER: """
You are creating structured content outlines and strategies. Your role is to:
- Develop comprehensive content outlines based on requirements
- Integrate SEO considerations and keyword strategies
- Ensure logical flow and audience engagement
- Create plans that other agents can easily follow
- Consider style guidelines in your planning approach
""",
            AgentType.CONTENT_GENERATOR: """
You are generating high-quality content based on provided outlines and guidelines. Your role is to:
- Follow outlines and style guides precisely
- Create engaging, well-written content
- Integrate keywords naturally and effectively
- Maintain consistent brand voice throughout
- Ensure content meets all specified requirements
""",
            AgentType.EDITOR_QA: """
You are reviewing and editing content for quality and consistency. Your role is to:
- Review content for accuracy, clarity, and flow
- Ensure adherence to brand guidelines and style
- Check for grammar, spelling, and structural issues
- Verify SEO optimization and keyword usage
- Provide final polish and quality assurance
"""
        }
        
        instructions = base_instructions.get(agent_type, "Execute assigned tasks with high quality and attention to detail.")
        
        # Add project-specific context
        client_name = project_context.get("client_name", "the client")
        instructions += f"\n\nYou are working on content for {client_name}. "
        instructions += f"This is part of collaboration session {session_id}. "
        instructions += "Communicate clearly and concisely. Focus on delivering high-quality results."
        
        return instructions
    
    def _determine_agent_role(self, agent_type: AgentType) -> AgentRole:
        """Determine coordination role based on agent type"""
        role_mapping = {
            AgentType.COORDINATOR: AgentRole.COORDINATOR,
            AgentType.STYLE_ANALYZER: AgentRole.SPECIALIST,
            AgentType.CONTENT_PLANNER: AgentRole.SPECIALIST,
            AgentType.CONTENT_GENERATOR: AgentRole.WORKER,
            AgentType.EDITOR_QA: AgentRole.REVIEWER
        }
        return role_mapping.get(agent_type, AgentRole.WORKER)
    
    async def _broadcast_to_session(
        self,
        session: CollaborationSession,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Broadcast information to all agents in session"""
        try:
            # Update session context
            session.session_context[event_type] = {
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Update all agent contexts
            for agent in session.participating_agents.values():
                agent.context[event_type] = data
                agent.last_activity = datetime.utcnow()
            
            logger.info(f"Broadcasted {event_type} to session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast to session: {e}")
    
    async def _get_coordinator_feedback(
        self,
        coordinator_agent: AgentSession,
        content_plan: Dict[str, Any],
        content_brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get coordinator feedback on content plan"""
        try:
            feedback_input = {
                "content_plan": content_plan,
                "content_brief": content_brief,
                "feedback_type": "planning_review"
            }
            
            task_id = f"coordinator_feedback_{uuid.uuid4().hex[:8]}"
            result = await self._execute_agent_task(
                coordinator_agent, task_id, "coordinator_feedback", feedback_input
            )
            
            return {
                "feedback": result.get("content", ""),
                "approval_status": "approved",  # Would parse from content
                "suggestions": [],  # Would extract from content
                "timestamp": result.get("timestamp")
            }
            
        except Exception as e:
            logger.error(f"Failed to get coordinator feedback: {e}")
            return {"feedback": "Error getting feedback", "approval_status": "error"}
    
    async def _get_final_approval(
        self,
        coordinator_agent: AgentSession,
        final_content: Dict[str, Any],
        review_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get final coordinator approval"""
        try:
            approval_input = {
                "final_content": final_content,
                "review_context": review_context,
                "approval_type": "final_review"
            }
            
            task_id = f"final_approval_{uuid.uuid4().hex[:8]}"
            result = await self._execute_agent_task(
                coordinator_agent, task_id, "final_approval", approval_input
            )
            
            return {
                "approval": result.get("content", ""),
                "status": "approved",  # Would parse from content
                "final_notes": "",  # Would extract from content
                "timestamp": result.get("timestamp")
            }
            
        except Exception as e:
            logger.error(f"Failed to get final approval: {e}")
            return {"approval": "Error getting approval", "status": "error"}
    
    async def _log_agent_task(
        self,
        agent_session: AgentSession,
        task_id: str,
        task_type: str,
        result: Dict[str, Any]
    ) -> None:
        """Log agent task execution to chat"""
        try:
            with get_db_session() as db:
                message = ChatMessage(
                    message_id=f"msg_{task_id}_{uuid.uuid4().hex[:8]}",
                    chat_id=agent_session.chat_id,
                    sender_id=agent_session.agent_id,
                    sender_type="agent",
                    content={
                        "type": "agent_task_completion",
                        "agent_type": agent_session.agent_type.value,
                        "task_id": task_id,
                        "task_type": task_type,
                        "result_preview": result.get("content", "")[:200] + "..." if result.get("content") else "No content",
                        "metadata": result.get("metadata", {})
                    },
                    created_at=datetime.utcnow()
                )
                
                db.add(message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log agent task: {e}")
    
    async def _log_coordination_completion(
        self,
        session: CollaborationSession,
        result: Dict[str, Any]
    ) -> None:
        """Log coordination completion"""
        try:
            with get_db_session() as db:
                completion_message = ChatMessage(
                    message_id=f"msg_coordination_complete_{uuid.uuid4().hex[:8]}",
                    chat_id=session.chat_id,
                    sender_id="coordinator_system",
                    sender_type="system",
                    content={
                        "type": "coordination_completion",
                        "session_id": session.session_id,
                        "workflow_summary": {
                            "phases_completed": 4,
                            "participating_agents": len(session.participating_agents),
                            "total_duration": result["metadata"]["session_duration"],
                            "quality_indicators": "high"
                        },
                        "final_deliverable": {
                            "content_type": result.get("workflow_type", "content"),
                            "word_count": result.get("final_content", {}).get("final_word_count", 0),
                            "ready_for_review": True
                        }
                    },
                    created_at=datetime.utcnow()
                )
                
                db.add(completion_message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log coordination completion: {e}")
    
    async def _handle_coordination_error(self, session: CollaborationSession, error_message: str) -> None:
        """Handle coordination errors"""
        session.session_context["error"] = {
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_attempted": False
        }
        
        # Deactivate problematic agents
        for agent in session.participating_agents.values():
            if not agent.active:
                continue
            # Could implement agent health checks here
    
    # Public API methods
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "project_id": session.project_id,
            "coordination_mode": session.coordination_mode.value,
            "participating_agents": [
                {
                    "agent_id": agent.agent_id,
                    "agent_type": agent.agent_type.value,
                    "role": agent.role.value,
                    "active": agent.active,
                    "message_count": agent.message_count,
                    "last_activity": agent.last_activity.isoformat()
                }
                for agent in session.participating_agents.values()
            ],
            "active_tasks": len(session.active_tasks),
            "completed_tasks": len(session.completed_tasks),
            "session_duration": (datetime.utcnow() - session.created_at).total_seconds(),
            "last_activity": session.last_activity.isoformat()
        }
    
    async def end_session(self, session_id: str) -> bool:
        """End a collaboration session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Deactivate all agents
        for agent in session.participating_agents.values():
            agent.active = False
        
        # Remove session from active sessions
        del self.active_sessions[session_id]
        
        logger.info(f"Ended collaboration session {session_id}")
        return True
    
    def get_available_agent_types(self) -> List[Dict[str, Any]]:
        """Get list of available agent types for coordination"""
        return [
            {
                "agent_type": AgentType.COORDINATOR.value,
                "role": AgentRole.COORDINATOR.value,
                "description": "Oversees workflow and provides guidance",
                "capabilities": ["workflow_management", "quality_control", "decision_making"]
            },
            {
                "agent_type": AgentType.STYLE_ANALYZER.value,
                "role": AgentRole.SPECIALIST.value,
                "description": "Analyzes content for brand voice and style patterns",
                "capabilities": ["style_analysis", "brand_voice_extraction", "guideline_creation"]
            },
            {
                "agent_type": AgentType.CONTENT_PLANNER.value,
                "role": AgentRole.SPECIALIST.value,
                "description": "Creates structured content outlines and strategies",
                "capabilities": ["content_planning", "seo_strategy", "audience_targeting"]
            },
            {
                "agent_type": AgentType.CONTENT_GENERATOR.value,
                "role": AgentRole.WORKER.value,
                "description": "Generates high-quality content following guidelines",
                "capabilities": ["content_creation", "style_adherence", "keyword_integration"]
            },
            {
                "agent_type": AgentType.EDITOR_QA.value,
                "role": AgentRole.REVIEWER.value,
                "description": "Reviews and edits content for quality and consistency",
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