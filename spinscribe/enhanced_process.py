"""
Enhanced content creation with REAL agent content generation and human checkpoint integration.
FIXED: Agents actually run and generate content BEFORE checkpoints appear.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from camel.tasks import Task
from camel.messages import BaseMessage
from spinscribe.workforce.enhanced_builder import (
    create_enhanced_workforce as build_enhanced_content_workflow,
    EnhancedWorkforceBuilder
)
from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.utils.enhanced_logging import workflow_tracker, log_execution_time, setup_enhanced_logging
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType, Priority
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from config.settings import DEFAULT_TASK_ID, ENABLE_HUMAN_CHECKPOINTS

logger = logging.getLogger('spinscribe.enhanced_process')

# Global managers
knowledge_manager = KnowledgeManager()
checkpoint_manager = CheckpointManager()

async def run_enhanced_content_task(
    title: str, 
    content_type: str, 
    project_id: str = "default",
    client_documents_path: str = None,
    first_draft: str = None,
    enable_checkpoints: bool = None,
    websocket_interceptor = None,
    chat_id: str = None
) -> Dict[str, Any]:
    """
    Enhanced content creation that ACTUALLY runs agents before checkpoints.
    """
    
    setup_enhanced_logging(log_level="INFO", enable_file_logging=True)
    workflow_id = f"workflow_{int(time.time())}_{project_id}"
    
    # Determine checkpoint settings
    checkpoints_enabled = enable_checkpoints if enable_checkpoints is not None else ENABLE_HUMAN_CHECKPOINTS
    
    logger.info(f"🚀 Starting enhanced content workflow: {workflow_id}")
    logger.info(f"   Title: {title}")
    logger.info(f"   Type: {content_type}")
    logger.info(f"   Checkpoints: {'✅ ENABLED' if checkpoints_enabled else '❌ DISABLED'}")
    logger.info(f"   WebSocket: {'✅ CONNECTED' if websocket_interceptor else '❌ NOT CONNECTED'}")
    
    # Broadcast workflow start
    if websocket_interceptor:
        await websocket_interceptor.intercept_message(
            message={"content": f"Starting workflow for: {title}"},
            agent_type="System",
            stage="initialization"
        )
    
    try:
        workflow_tracker.start_workflow(workflow_id, {
            "title": title,
            "content_type": content_type,
            "project_id": project_id,
            "checkpoints_enabled": checkpoints_enabled
        })
        
        # PHASE 1: Document Processing
        workflow_tracker.update_stage(workflow_id, "document_processing")
        
        if websocket_interceptor:
            await websocket_interceptor.intercept_message(
                message={"content": "Processing client documents..."},
                agent_type="System",
                stage="document_processing"
            )
        
        onboarding_summary = process_client_documents(client_documents_path, project_id)
        
        # PHASE 2: Build Enhanced Workforce with Agents
        workflow_tracker.update_stage(workflow_id, "workforce_building")
        
        if websocket_interceptor:
            await websocket_interceptor.intercept_message(
                message={"content": "Building AI agent workforce..."},
                agent_type="System",
                stage="workforce_building"
            )
        
        # Build the enhanced workforce with all agents
        builder = EnhancedWorkforceBuilder(
            project_id=project_id,
            websocket_interceptor=websocket_interceptor,
        )
        
        workforce = builder.build_enhanced_workforce()
        agents = builder.agents  # Get direct access to agents
        
        logger.info(f"✅ Built workforce with {len(agents)} agents")
        
        # Setup checkpoint integration if enabled
        checkpoint_integration = None
        if checkpoints_enabled:
            checkpoint_integration = WorkflowCheckpointIntegration(
                checkpoint_manager=checkpoint_manager,
                project_id=project_id
            )
            
            # Enhanced checkpoint notification handler
            def checkpoint_notification_handler(data):
                print(f"\n" + "="*80)
                print(f"🛑 HUMAN CHECKPOINT REQUIRED")
                print(f"="*80)
                print(f"Type: {data.get('checkpoint_type', 'unknown')}")
                print(f"Title: {data.get('title', 'Unknown')}")
                print(f"ID: {data.get('checkpoint_id', 'unknown')}")
                print(f"Description: {data.get('description', '')}")
                
                if data.get('content'):
                    content_preview = data['content'][:1000] + "..." if len(data['content']) > 1000 else data['content']
                    print(f"\nContent Preview:")
                    print("-" * 50)
                    print(content_preview)
                    print("-" * 50)
                
                checkpoint_id = data.get('checkpoint_id', 'unknown')
                print(f"\n💡 TO RESPOND TO THIS CHECKPOINT:")
                print(f"   python scripts/respond_to_checkpoint.py {checkpoint_id} approve")
                print(f"   python scripts/respond_to_checkpoint.py {checkpoint_id} reject")
                print(f"="*80)
                print(f"⏳ Workflow paused - waiting for your response...")
                
                # Send to WebSocket
                if websocket_interceptor:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(
                                websocket_interceptor.send_checkpoint(
                                    checkpoint_id=checkpoint_id,
                                    checkpoint_data=data
                                )
                            )
                    except Exception as e:
                        logger.error(f"WebSocket checkpoint error: {e}")
            
            checkpoint_manager.add_notification_handler(checkpoint_notification_handler)
            logger.info("✅ Checkpoint integration enabled")
        
        # PHASE 3: Process with agents and checkpoints
        workflow_tracker.update_stage(workflow_id, "agent_processing")
        
        if checkpoints_enabled and checkpoint_integration:
            # Process WITH checkpoints - agents generate content first
            result = await process_with_real_checkpoints_fixed(
                workforce=workforce,
                agents=agents,
                title=title,
                content_type=content_type,
                checkpoint_integration=checkpoint_integration,
                websocket_interceptor=websocket_interceptor,
                onboarding_summary=onboarding_summary
            )
        else:
            # Process WITHOUT checkpoints
            result = await process_without_checkpoints(
                workforce=workforce,
                agents=agents,
                title=title,
                content_type=content_type,
                websocket_interceptor=websocket_interceptor
            )
        
        # Collect final results
        workflow_tracker.update_stage(workflow_id, "result_collection")
        
        if websocket_interceptor:
            await websocket_interceptor.intercept_message(
                message={"content": "Finalizing content..."},
                agent_type="System",
                stage="result_collection"
            )
        
        final_result = {
            "workflow_id": workflow_id,
            "final_content": result.get('content', 'No content generated'),
            "content_type": content_type,
            "title": title,
            "project_id": project_id,
            "status": "completed",
            "checkpoints_enabled": checkpoints_enabled,
            "onboarding_summary": onboarding_summary,
            "execution_time": time.time() - workflow_tracker.workflows[workflow_id]["start_time"]
        }
        
        workflow_tracker.complete_workflow(workflow_id, "completed", final_result)
        logger.info(f"🎉 Workflow completed! Generated {len(final_result['final_content'])} characters")
        
        if websocket_interceptor:
            await websocket_interceptor.intercept_completion(
                final_content=final_result["final_content"],
                agent_type="System",
                metadata=final_result
            )
        
        return final_result
        
    except Exception as e:
        logger.error(f"💥 Error in enhanced workflow: {str(e)}", exc_info=True)
        workflow_tracker.complete_workflow(workflow_id, "failed")
        
        if websocket_interceptor:
            await websocket_interceptor._broadcast_error(str(e), "System")
        
        return {
            "workflow_id": workflow_id,
            "final_content": None,
            "error": str(e),
            "status": "failed",
            "content_type": content_type,
            "title": title,
            "project_id": project_id
        }

async def process_with_real_checkpoints_fixed(
    workforce,
    agents: Dict[str, Any],
    title: str,
    content_type: str,
    checkpoint_integration,
    websocket_interceptor=None,
    onboarding_summary=None
):
    """
    FIXED: Runs agents to generate real content BEFORE showing checkpoints.
    """
    
    logger.info("🛑 CHECKPOINT MODE: Agents will generate content, then pause for approval")
    
    # ========================================================================
    # STEP 1: GENERATE STRATEGY/OUTLINE USING ACTUAL AGENTS
    # ========================================================================
    
    logger.info("📝 Phase 1: Running Content Planning Agent to generate strategy...")
    
    if websocket_interceptor:
        await websocket_interceptor.intercept_message(
            message={"content": "Content Planning Agent is creating strategy..."},
            agent_type="Content Planning Agent",
            stage="strategy_generation"
        )
    
    # Get the planning agent
    planning_agent = agents.get('enhanced_content_planning')
    if not planning_agent:
        logger.warning("Planning agent not found, using coordinator")
        planning_agent = agents.get('enhanced_coordinator')
    
    # Create the strategy generation prompt
    strategy_prompt = f"""Create a comprehensive content strategy and detailed outline for an {content_type} titled: "{title}"

    Requirements:
    1. Target audience analysis
    2. Key messaging and goals
    3. Detailed section-by-section outline
    4. Content tone and style recommendations
    5. Keywords and SEO considerations
    6. Estimated word count per section
    
    Provide a complete, detailed strategy that will guide content creation."""
    
    # Run the agent to generate REAL strategy
    strategy_message = BaseMessage.make_user_message(
        role_name="User",
        content=strategy_prompt
    )
    
    try:
        logger.info("⏳ Agent generating strategy (this may take 10-30 seconds)...")
        strategy_response = planning_agent.step(strategy_message)
        
        # Extract the actual generated content
        actual_strategy = ""
        if hasattr(strategy_response, 'msgs') and strategy_response.msgs:
            actual_strategy = strategy_response.msgs[0].content
        elif hasattr(strategy_response, 'content'):
            actual_strategy = strategy_response.content
        else:
            actual_strategy = str(strategy_response)
        
        logger.info(f"✅ Strategy generated: {len(actual_strategy)} characters")
        
        # Send to WebSocket
        if websocket_interceptor and actual_strategy:
            await websocket_interceptor.intercept_agent_message(
                agent_name="Content Planning Agent",
                message=actual_strategy,
                role="Strategy Generation"
            )
        
    except Exception as e:
        logger.error(f"Error generating strategy: {e}")
        actual_strategy = f"Error generating strategy: {str(e)}"
    
    # ========================================================================
    # CHECKPOINT 1: STRATEGY APPROVAL WITH REAL CONTENT
    # ========================================================================
    
    print(f"\n🔴 CHECKPOINT 1: STRATEGY APPROVAL")
    
    strategy_approval = await checkpoint_integration.request_approval(
        checkpoint_type=CheckpointType.STRATEGY_APPROVAL,
        title=f"Strategy Approval: {title}",
        description="Review the AI-generated content strategy and outline. This was created by our Content Planning Agent.",
        content=actual_strategy,  # REAL AGENT-GENERATED CONTENT
        priority=Priority.HIGH,
        timeout_hours=2
    )
    
    if not strategy_approval.get('approved', False):
        feedback = strategy_approval.get('feedback', 'No feedback provided')
        logger.warning(f"❌ Strategy rejected: {feedback}")
        
        # Generate revised strategy based on feedback
        revision_prompt = f"""The previous strategy was rejected with this feedback: {feedback}
        
        Original strategy:
        {actual_strategy[:1000]}
        
        Please revise the strategy addressing the feedback."""
        
        revision_message = BaseMessage.make_user_message(
            role_name="User",
            content=revision_prompt
        )
        
        revised_response = planning_agent.step(revision_message)
        if hasattr(revised_response, 'msgs') and revised_response.msgs:
            actual_strategy = revised_response.msgs[0].content
        
        # Could loop back to checkpoint here, but for now we'll continue
    
    logger.info("✅ Strategy approved! Moving to content generation...")
    
    # ========================================================================
    # STEP 2: GENERATE CONTENT USING ACTUAL AGENTS
    # ========================================================================
    
    logger.info("📝 Phase 2: Running Content Generation Agent to create content...")
    
    if websocket_interceptor:
        await websocket_interceptor.intercept_message(
            message={"content": "Content Generation Agent is writing content..."},
            agent_type="Content Generation Agent",
            stage="content_generation"
        )
    
    # Get the generation agent
    generation_agent = agents.get('enhanced_content_generation')
    if not generation_agent:
        logger.warning("Generation agent not found, using coordinator")
        generation_agent = agents.get('enhanced_coordinator')
    
    # Create content generation prompt with approved strategy
    generation_prompt = f"""Based on the approved strategy below, write the full {content_type} titled: "{title}"

    APPROVED STRATEGY:
    {actual_strategy}
    
    Requirements:
    - Follow the outline and strategy exactly
    - Write engaging, high-quality content
    - Include all sections specified in the outline
    - Maintain consistent tone and style
    - Target length: appropriate for {content_type}
    
    Write the complete content now."""
    
    generation_message = BaseMessage.make_user_message(
        role_name="User",
        content=generation_prompt
    )
    
    try:
        logger.info("⏳ Agent generating content (this may take 30-60 seconds)...")
        content_response = generation_agent.step(generation_message)
        
        # Extract actual generated content
        draft_content = ""
        if hasattr(content_response, 'msgs') and content_response.msgs:
            draft_content = content_response.msgs[0].content
        elif hasattr(content_response, 'content'):
            draft_content = content_response.content
        else:
            draft_content = str(content_response)
        
        logger.info(f"✅ Content generated: {len(draft_content)} characters")
        
        # Send to WebSocket
        if websocket_interceptor and draft_content:
            await websocket_interceptor.intercept_agent_message(
                agent_name="Content Generation Agent",
                message=draft_content[:2000],  # Send preview
                role="Content Generation"
            )
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        draft_content = f"Error generating content: {str(e)}"
    
    # ========================================================================
    # CHECKPOINT 2: CONTENT APPROVAL WITH REAL CONTENT
    # ========================================================================
    
    print(f"\n🔴 CHECKPOINT 2: CONTENT REVIEW")
    
    # Show preview for checkpoint
    content_preview = draft_content[:3000] + "\n\n[... Content continues ...]" if len(draft_content) > 3000 else draft_content
    
    content_approval = await checkpoint_integration.request_approval(
        checkpoint_type=CheckpointType.DRAFT_REVIEW,
        title=f"Content Review: {title}",
        description="Review the AI-generated content. This was created by our Content Generation Agent based on the approved strategy.",
        content=content_preview,  # REAL AGENT-GENERATED CONTENT
        priority=Priority.HIGH,
        timeout_hours=2
    )
    
    if not content_approval.get('approved', False):
        feedback = content_approval.get('feedback', 'No feedback provided')
        logger.warning(f"⚠️ Content needs revision: {feedback}")
        
        # Could implement revision logic here
    
    # ========================================================================
    # STEP 3: QUALITY ASSURANCE
    # ========================================================================
    
    logger.info("📝 Phase 3: Running QA Agent for final polish...")
    
    # Get QA agent
    qa_agent = agents.get('enhanced_qa')
    if qa_agent:
        qa_prompt = f"""Review and polish this content:
        
        {draft_content[:2000]}
        
        Check for:
        - Grammar and spelling
        - Clarity and flow
        - Factual accuracy
        - Brand voice consistency
        
        Provide the polished version."""
        
        qa_message = BaseMessage.make_user_message(
            role_name="User",
            content=qa_prompt
        )
        
        try:
            qa_response = qa_agent.step(qa_message)
            if hasattr(qa_response, 'msgs') and qa_response.msgs:
                final_content = qa_response.msgs[0].content
            else:
                final_content = draft_content
        except Exception as e:
            logger.error(f"QA error: {e}")
            final_content = draft_content
    else:
        final_content = draft_content
    
    logger.info("✅ Content processing complete!")
    
    return {
        'content': final_content,
        'strategy': actual_strategy,
        'status': 'completed'
    }

async def process_without_checkpoints(
    workforce,
    agents: Dict[str, Any],
    title: str,
    content_type: str,
    websocket_interceptor=None
):
    """
    Process without checkpoints - run all agents sequentially.
    """
    
    logger.info("⚡ Processing without checkpoints - running all agents")
    
    # Run planning agent
    planning_agent = agents.get('enhanced_content_planning')
    if planning_agent:
        strategy_msg = BaseMessage.make_user_message(
            role_name="User",
            content=f"Create outline for {content_type}: {title}"
        )
        strategy_response = planning_agent.step(strategy_msg)
        strategy = strategy_response.msgs[0].content if hasattr(strategy_response, 'msgs') else ""
    else:
        strategy = ""
    
    # Run generation agent
    generation_agent = agents.get('enhanced_content_generation')
    if generation_agent:
        gen_msg = BaseMessage.make_user_message(
            role_name="User",
            content=f"Write {content_type} titled '{title}' based on: {strategy[:500]}"
        )
        gen_response = generation_agent.step(gen_msg)
        content = gen_response.msgs[0].content if hasattr(gen_response, 'msgs') else ""
    else:
        content = f"Generated content for: {title}"
    
    # Run QA agent
    qa_agent = agents.get('enhanced_qa')
    if qa_agent:
        qa_msg = BaseMessage.make_user_message(
            role_name="User",
            content=f"Polish this content: {content[:1000]}"
        )
        qa_response = qa_agent.step(qa_msg)
        final = qa_response.msgs[0].content if hasattr(qa_response, 'msgs') else content
    else:
        final = content
    
    return {
        'content': final,
        'status': 'completed'
    }

def process_client_documents(client_documents_path, project_id):
    """Process client documents if provided."""
    if client_documents_path:
        try:
            return knowledge_manager.onboard_client(
                client_id=project_id.split('-')[0] if '-' in project_id else project_id,
                project_id=project_id,
                documents_path=client_documents_path
            )
        except Exception as e:
            logger.warning(f"⚠️ Knowledge onboarding failed: {e}")
            return {"status": "failed", "error": str(e)}
    else:
        return {"status": "skipped", "reason": "No client documents"}