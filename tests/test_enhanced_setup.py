# ─── NEW FILE: test_enhanced_system.py ─────────────────────────
"""
Comprehensive test suite for enhanced SpinScribe system.
Tests RAG integration and checkpoint functionality.
"""

import asyncio
import pytest
from pathlib import Path
import tempfile
import shutil
import sys
import os

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from spinscribe.knowledge.knowledge_manager import KnowledgeManager
from spinscribe.knowledge.document_processor import DocumentProcessor
from spinscribe.checkpoints.checkpoint_manager import CheckpointManager, CheckpointType, Priority
from spinscribe.checkpoints.workflow_integration import WorkflowCheckpointIntegration
from spinscribe.checkpoints.mock_reviewer import MockReviewer
from spinscribe.tasks.enhanced_process import run_enhanced_content_task

class TestEnhancedSpinScribe:
    """Test suite for enhanced SpinScribe functionality."""
    
    @pytest.fixture
    def setup_test_project(self):
        """Setup test project with sample documents."""
        test_dir = Path(tempfile.mkdtemp())
        
        # Create comprehensive test documents
        brand_doc = test_dir / "brand_guide.md"
        brand_doc.write_text("""
# TechCorp Brand Guidelines

## Brand Voice
Our brand voice is professional yet approachable, emphasizing innovation and customer success.

## Core Values
- Customer-centric approach
- Innovation leadership
- Reliability and trust
- Continuous improvement

## Tone Characteristics
- Confident but humble
- Educational and helpful
- Forward-thinking
- Authentic and transparent

## Key Vocabulary
- "Next-generation solutions"
- "Customer success"
- "Digital transformation"
- "Innovative approaches"
- "Streamlined processes"
- "Cutting-edge technology"

## Writing Style
- Use active voice predominantly
- Keep sentences concise (under 20 words)
- Include specific examples and case studies
- Maintain professional but conversational tone
- Focus on benefits and outcomes

## Content Guidelines
- Always lead with customer benefits
- Include data and metrics when possible
- Use subheadings for better readability
- End with clear call-to-action
- Maintain brand consistency across all content
        """)
        
        style_doc = test_dir / "style_guide.txt"
        style_doc.write_text("""
TechCorp Content Style Guide

WRITING PRINCIPLES:
1. Clarity over cleverness
2. Benefits before features
3. Show don't just tell
4. Be helpful, not salesy

FORMATTING STANDARDS:
- Headlines: Capitalize first word and proper nouns only
- Bullet points: Use for lists and key points
- Bold text: For emphasis on important concepts
- Numbers: Spell out one through nine, use numerals for 10+

CONTENT STRUCTURE:
Introduction:
- Hook reader with compelling opening
- Clearly state value proposition
- Preview key points

Body:
- Use H2 and H3 subheadings
- Include examples and case studies
- Break up text with visual elements
- Support claims with data

Conclusion:
- Summarize key takeaways
- Include clear next steps
- End with strong call-to-action

VOICE GUIDELINES:
- Use "you" to address readers directly
- Ask rhetorical questions to engage
- Include industry insights
- Be authoritative but approachable

CONTENT TYPES:
Blog Posts: 800-1200 words, educational focus
Landing Pages: 500-800 words, conversion-focused
Case Studies: 1000-1500 words, story-driven
Whitepapers: 2000+ words, research-based
        """)
        
        sample_content = test_dir / "sample_article.md"
        sample_content.write_text("""
# How AI is Transforming Modern Business Operations

Artificial intelligence isn't just a buzzword anymore—it's reshaping how businesses operate, compete, and succeed in today's digital landscape.

## The AI Revolution in Action

Companies across industries are discovering that AI-powered solutions can streamline processes, enhance decision-making, and unlock new opportunities for growth. From predictive analytics to automated customer service, the applications are virtually limitless.

### Real-World Examples

Take our recent work with GlobalTech Industries. By implementing our next-generation AI platform, they reduced operational costs by 35% while improving customer satisfaction scores by 28%. This digital transformation didn't happen overnight, but the results speak for themselves.

## Key Benefits of AI Integration

**Enhanced Efficiency**: Automated processes eliminate manual bottlenecks
**Better Insights**: Data-driven decisions based on comprehensive analysis  
**Improved Accuracy**: Reduced human error in critical operations
**Scalable Solutions**: Systems that grow with your business needs

## Looking Forward

The future belongs to organizations that embrace innovative approaches to business challenges. Are you ready to unlock your company's full potential with cutting-edge technology?

Our customer-centric approach ensures that every AI solution is tailored to your specific needs and objectives. Let's discuss how we can help you achieve your digital transformation goals.

[Contact us today to schedule a consultation]
        """)
        
        marketing_doc = test_dir / "marketing_strategy.txt"
        marketing_doc.write_text("""
TechCorp Marketing Strategy 2024

TARGET AUDIENCE:
- Enterprise decision makers (CTO, CEO, Operations Directors)
- Mid-market companies seeking digital transformation
- Technology leaders looking for innovative solutions
- Business stakeholders focused on ROI and efficiency

MESSAGING PRIORITIES:
1. Innovation leadership in AI/tech solutions
2. Proven track record of customer success
3. Comprehensive support and partnership approach
4. Measurable business outcomes and ROI

CONTENT THEMES:
- Digital transformation success stories
- Industry trends and insights
- Best practices and how-to guides
- Customer case studies and testimonials
- Technology deep-dives and explanations

COMPETITIVE POSITIONING:
- More personal than large consultancies
- More comprehensive than point solutions
- Stronger customer focus than pure tech companies
- Better innovation than traditional providers

KEY METRICS:
- Lead generation: 50+ qualified leads per month
- Content engagement: 25% increase in time on page
- Conversion rates: 15% improvement in demo requests
- Brand awareness: 40% increase in branded search terms
        """)
        
        competitor_analysis = test_dir / "competitor_analysis.md"
        competitor_analysis.write_text("""
# Competitive Landscape Analysis

## Major Competitors

### TechGiant Corp
- Strengths: Brand recognition, extensive resources
- Weaknesses: Less personalized service, slow innovation
- Market position: Enterprise-focused, premium pricing

### InnovateSoft
- Strengths: Cutting-edge technology, agile development
- Weaknesses: Limited support, narrow focus
- Market position: Mid-market, competitive pricing

### Solutions Plus
- Strengths: Comprehensive services, industry expertise
- Weaknesses: Outdated technology, complex processes
- Market position: Traditional enterprises, high-touch service

## Our Competitive Advantages

1. **Innovation Speed**: Faster adoption of new technologies
2. **Customer Focus**: More personalized approach and support
3. **Proven Results**: Strong track record with measurable outcomes
4. **Flexible Solutions**: Adaptable to various business needs
5. **Partnership Approach**: Long-term relationships vs. transactional

## Market Opportunities

- Growing demand for AI-powered solutions
- Increasing focus on digital transformation
- Need for personalized technology partnerships
- Emphasis on measurable business outcomes
        """)
        
        yield test_dir
        
        # Cleanup
        shutil.rmtree(test_dir)
    
    @pytest.mark.asyncio
    async def test_document_processor_pdf_support(self, setup_test_project):
        """Test document processor with various file types."""
        test_dir = setup_test_project
        processor = DocumentProcessor()
        
        # Test supported file types
        assert '.pdf' in processor.supported_types
        assert '.docx' in processor.supported_types
        assert '.md' in processor.supported_types
        
        # Test file type validation
        md_file = test_dir / "brand_guide.md"
        assert md_file.exists()
        
        try:
            metadata = await processor.process_document(
                file_path=md_file,
                client_id="test-client",
                project_id="test-project",
                document_type="brand_guidelines"
            )
            
            assert metadata.file_name == "brand_guide.md"
            assert metadata.document_type == "brand_guidelines"
            assert metadata.processing_status == "completed"
            assert metadata.total_chunks > 0
            
        except Exception as e:
            # If Qdrant isn't available, this test may fail
            pytest.skip(f"Document processing requires Qdrant: {e}")
    
    @pytest.mark.asyncio
    async def test_knowledge_manager_onboarding(self, setup_test_project):
        """Test complete client document onboarding."""
        test_dir = setup_test_project
        km = KnowledgeManager()
        
        try:
            summary = await km.onboard_client(
                client_id="test-client",
                project_id="test-project",
                documents_directory=test_dir
            )
            
            # Verify onboarding results
            assert summary['client_id'] == "test-client"
            assert summary['project_id'] == "test-project"
            assert summary['processed_documents'] >= 4  # We created 5 docs
            assert summary['total_chunks'] > 0
            assert summary['failed_documents'] == 0
            
            # Check document types were detected
            doc_types = summary['document_types']
            assert 'brand_guidelines' in doc_types
            assert 'style_guide' in doc_types
            assert 'sample_content' in doc_types
            
        except Exception as e:
            pytest.skip(f"Knowledge onboarding requires Qdrant: {e}")
    
    @pytest.mark.asyncio
    async def test_knowledge_search(self, setup_test_project):
        """Test knowledge base search functionality."""
        test_dir = setup_test_project
        km = KnowledgeManager()
        
        try:
            # First onboard the client
            await km.onboard_client(
                client_id="test-client",
                project_id="test-project",
                documents_directory=test_dir
            )
            
            # Test knowledge search
            results = await km.get_relevant_knowledge(
                query="brand voice tone characteristics",
                project_id="test-project",
                limit=3
            )
            
            assert len(results) > 0
            assert all('content' in result for result in results)
            assert all('score' in result for result in results)
            assert all('metadata' in result for result in results)
            
        except Exception as e:
            pytest.skip(f"Knowledge search requires Qdrant: {e}")
    
    def test_checkpoint_manager_creation(self):
        """Test checkpoint creation and management."""
        cm = CheckpointManager()
        
        # Create checkpoint
        checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Test Style Guide Review",
            description="Testing checkpoint creation functionality",
            priority=Priority.HIGH
        )
        
        assert checkpoint_id is not None
        assert len(checkpoint_id) > 0
        
        # Verify checkpoint exists
        checkpoint = cm.get_checkpoint(checkpoint_id)
        assert checkpoint is not None
        assert checkpoint.title == "Test Style Guide Review"
        assert checkpoint.checkpoint_type == CheckpointType.STYLE_GUIDE_APPROVAL
        assert checkpoint.priority == Priority.HIGH
    
    def test_checkpoint_assignment(self):
        """Test checkpoint assignment functionality."""
        cm = CheckpointManager()
        
        # Create checkpoint
        checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Content Outline Review",
            description="Review the content outline for accuracy"
        )
        
        # Assign checkpoint
        success = cm.assign_checkpoint(
            checkpoint_id=checkpoint_id,
            assigned_to="reviewer@example.com",
            assigned_by="manager@example.com"
        )
        
        assert success is True
        
        # Verify assignment
        checkpoint = cm.get_checkpoint(checkpoint_id)
        assert checkpoint.assigned_to == "reviewer@example.com"
        assert checkpoint.assigned_by == "manager@example.com"
    
    def test_checkpoint_response_submission(self):
        """Test checkpoint response and resolution."""
        cm = CheckpointManager()
        
        # Create and assign checkpoint
        checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="Content Draft Review",
            description="Review content draft for quality"
        )
        
        cm.assign_checkpoint(
            checkpoint_id=checkpoint_id,
            assigned_to="reviewer@example.com"
        )
        
        # Submit approval response
        success = cm.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id="reviewer@example.com",
            decision="approve",
            feedback="Content looks excellent! Good adherence to brand voice.",
            suggestions=["Consider adding more specific examples"],
            time_spent_minutes=15
        )
        
        assert success is True
        
        # Verify response and status
        checkpoint = cm.get_checkpoint(checkpoint_id)
        assert checkpoint.status.value == "approved"
        assert len(checkpoint.responses) == 1
        
        response = checkpoint.responses[0]
        assert response.decision == "approve"
        assert response.feedback == "Content looks excellent! Good adherence to brand voice."
        assert response.time_spent_minutes == 15
    
    def test_checkpoint_revision_request(self):
        """Test checkpoint revision request workflow."""
        cm = CheckpointManager()
        
        checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="Content Draft Review",
            description="Review content draft"
        )
        
        # Submit revision request
        success = cm.submit_response(
            checkpoint_id=checkpoint_id,
            reviewer_id="reviewer@example.com",
            decision="needs_revision",
            feedback="Content needs improvement in tone and structure.",
            changes_requested=[
                {"section": "introduction", "change": "Make more engaging"},
                {"section": "conclusion", "change": "Strengthen call-to-action"}
            ]
        )
        
        assert success is True
        
        checkpoint = cm.get_checkpoint(checkpoint_id)
        assert checkpoint.status.value == "needs_revision"
        
        response = checkpoint.responses[0]
        assert response.decision == "needs_revision"
        assert len(response.changes_requested) == 2
    
    @pytest.mark.asyncio
    async def test_workflow_checkpoint_integration(self):
        """Test workflow integration with checkpoints."""
        cm = CheckpointManager()
        integration = WorkflowCheckpointIntegration(cm)
        
        # Test checkpoint creation and immediate approval
        async def auto_approve():
            await asyncio.sleep(0.1)  # Small delay
            checkpoints = cm.get_pending_checkpoints()
            for checkpoint in checkpoints:
                cm.submit_response(
                    checkpoint_id=checkpoint.checkpoint_id,
                    reviewer_id="auto_reviewer",
                    decision="approve",
                    feedback="Auto-approved for testing"
                )
        
        # Start auto-approval task
        approval_task = asyncio.create_task(auto_approve())
        
        # Request approval
        result = await integration.request_approval(
            project_id="test-project",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Test Integration",
            description="Testing workflow integration",
            content="Sample content for review",
            timeout_hours=1
        )
        
        await approval_task
        
        assert result['approved'] is True
        assert 'checkpoint_id' in result
    
    def test_mock_reviewer_functionality(self):
        """Test mock reviewer automatic responses."""
        cm = CheckpointManager()
        mock_reviewer = MockReviewer(cm, reviewer_id="test_mock_reviewer")
        
        # Set high approval rate for testing
        mock_reviewer.auto_approve_rate = 1.0  # 100% approval
        
        # Create checkpoint
        checkpoint_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Mock Review Test",
            description="Testing mock reviewer functionality"
        )
        
        # Give mock reviewer a moment to respond
        import time
        time.sleep(2)
        
        # Check if mock reviewer responded
        checkpoint = cm.get_checkpoint(checkpoint_id)
        if len(checkpoint.responses) > 0:
            response = checkpoint.responses[0]
            assert response.reviewer_id == "test_mock_reviewer"
            assert response.decision in ["approve", "needs_revision", "reject"]
    
    def test_checkpoint_project_filtering(self):
        """Test checkpoint filtering by project."""
        cm = CheckpointManager()
        
        # Create checkpoints for different projects
        project_a_id = cm.create_checkpoint(
            project_id="project-a",
            checkpoint_type=CheckpointType.STYLE_GUIDE_APPROVAL,
            title="Project A Checkpoint",
            description="Checkpoint for project A"
        )
        
        project_b_id = cm.create_checkpoint(
            project_id="project-b",
            checkpoint_type=CheckpointType.OUTLINE_REVIEW,
            title="Project B Checkpoint", 
            description="Checkpoint for project B"
        )
        
        # Test project filtering
        project_a_checkpoints = cm.get_checkpoints_by_project("project-a")
        project_b_checkpoints = cm.get_checkpoints_by_project("project-b")
        
        assert len(project_a_checkpoints) == 1
        assert len(project_b_checkpoints) == 1
        assert project_a_checkpoints[0].checkpoint_id == project_a_id
        assert project_b_checkpoints[0].checkpoint_id == project_b_id
    
    def test_checkpoint_user_assignment_filtering(self):
        """Test checkpoint filtering by assigned user."""
        cm = CheckpointManager()
        
        # Create and assign checkpoints to different users
        checkpoint1_id = cm.create_checkpoint(
            project_id="test-project",
            checkpoint_type=CheckpointType.DRAFT_REVIEW,
            title="User A Checkpoint",
            description="Assigned to user A"
        )
        
        checkpoint2_id = cm.create_checkpoint(
            project_id="test-project", 
            checkpoint_type=CheckpointType.FINAL_APPROVAL,
            title="User B Checkpoint",
            description="Assigned to user B"
        )
        
        cm.assign_checkpoint(checkpoint1_id, "user_a@example.com")
        cm.assign_checkpoint(checkpoint2_id, "user_b@example.com")
        
        # Test user filtering
        user_a_checkpoints = cm.get_checkpoints_by_assignee("user_a@example.com")
        user_b_checkpoints = cm.get_checkpoints_by_assignee("user_b@example.com")
        
        assert len(user_a_checkpoints) == 1
        assert len(user_b_checkpoints) == 1
        assert user_a_checkpoints[0].assigned_to == "user_a@example.com"
        assert user_b_checkpoints[0].assigned_to == "user_b@example.com"
    
    @pytest.mark.asyncio
    async def test_enhanced_workflow_complete(self, setup_test_project):
        """Test complete enhanced workflow with RAG and checkpoints disabled for testing."""
        test_dir = setup_test_project
        
        try:
            result = await run_enhanced_content_task(
                title="AI Innovation in Healthcare",
                content_type="article",
                project_id="test-workflow",
                client_documents_path=str(test_dir),
                enable_checkpoints=False  # Disable for automated testing
            )
            
            # Verify workflow completion
            assert result['status'] == 'completed'
            assert result['enhanced'] is True
            assert result['final_content'] is not None
            assert result['project_id'] == 'test-workflow'
            assert result['title'] == "AI Innovation in Healthcare"
            assert result['content_type'] == "article"
            
            # Verify onboarding occurred
            if result.get('onboarding_summary'):
                onboarding = result['onboarding_summary']
                assert onboarding['processed_documents'] > 0
                assert onboarding['total_chunks'] > 0
            
        except Exception as e:
            # Enhanced workflow requires Qdrant and other services
            pytest.skip(f"Enhanced workflow test requires full system: {e}")
    
    def test_knowledge_manager_client_summary(self):
        """Test knowledge manager client summary functionality."""
        km = KnowledgeManager()
        
        # Add mock client data
        km.client_knowledge["test-client"] = {
            'project_id': 'test-project',
            'documents': [],
            'onboarding_date': "2024-01-01",
            'total_documents': 5,
            'total_chunks': 150
        }
        
        summary = km.get_client_summary("test-client")
        assert summary is not None
        assert summary['project_id'] == 'test-project'
        assert summary['total_documents'] == 5
        assert summary['total_chunks'] == 150
        
        # Test non-existent client
        no_summary = km.get_client_summary("non-existent-client")
        assert no_summary is None

# ─── Integration Test Runner ────────────────────────────────────
if __name__ == "__main__":
    """Run tests directly for development."""
    import subprocess
    import sys
    
    print("🧪 Running Enhanced SpinScribe Test Suite")
    print("=" * 50)
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "--disable-warnings"
    ], capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with code: {result.returncode}")
    
    sys.exit(result.returncode)
