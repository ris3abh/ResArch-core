# app/agents/specialized/content_planner.py
"""
Production Content Planner Agent for SpinScribe
Built on CAMEL AI Framework

The Content Planner Agent creates detailed, structured content outlines
and strategies based on project requirements and brand guidelines.
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.configs import ChatGPTConfig

from app.agents.base.agent_factory import agent_factory
from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

@dataclass
class ContentSection:
    """Represents a section in the content outline"""
    title: str
    description: str
    objectives: List[str]
    keywords: List[str]
    estimated_word_count: int
    tone_guidance: str
    subsections: Optional[List['ContentSection']] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.subsections:
            result['subsections'] = [sub.to_dict() for sub in self.subsections]
        return result

@dataclass
class SEOStrategy:
    """SEO strategy for content"""
    primary_keywords: List[str]
    secondary_keywords: List[str]
    long_tail_keywords: List[str]
    keyword_density_targets: Dict[str, float]
    meta_title: str
    meta_description: str
    header_structure: List[str]
    internal_link_opportunities: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ContentPlan:
    """Complete content plan with all components"""
    title: str
    content_type: str
    target_audience: str
    primary_objectives: List[str]
    brand_voice_integration: Dict[str, Any]
    seo_strategy: SEOStrategy
    content_outline: List[ContentSection]
    estimated_total_words: int
    estimated_completion_time: str
    quality_criteria: List[str]
    success_metrics: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['seo_strategy'] = self.seo_strategy.to_dict()
        result['content_outline'] = [section.to_dict() for section in self.content_outline]
        return result

class ProductionContentPlannerAgent(ChatAgent):
    """
    Production-grade Content Planner Agent that creates comprehensive
    content strategies and detailed outlines for content creation.
    """
    
    def __init__(self, project_id: str = None, **kwargs):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id or 'standalone'}")
        
        # Initialize system message
        system_message = self._create_planner_system_message()
        super().__init__(system_message=system_message, **kwargs)
        
        # Initialize knowledge base connection
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
        
        # Content type templates
        self.content_templates = self._initialize_content_templates()
        
        # SEO configuration
        self.seo_config = {
            "primary_keyword_density": 0.015,  # 1.5%
            "secondary_keyword_density": 0.01,  # 1%
            "long_tail_density": 0.005,  # 0.5%
            "max_title_length": 60,
            "max_meta_description": 160,
            "header_hierarchy": ["H1", "H2", "H3", "H4", "H5", "H6"]
        }
        
    def _create_planner_system_message(self) -> BaseMessage:
        """Create comprehensive system message for content planner role"""
        content = f"""
            You are the Production Content Planner Agent for SpinScribe, specializing in creating detailed, strategic content plans and outlines.

            CORE RESPONSIBILITIES:
            • Analyze project requirements and brand guidelines to create targeted content strategies
            • Develop comprehensive content outlines with clear sections, objectives, and guidance
            • Integrate SEO best practices and keyword strategies into content planning
            • Ensure content plans align with brand voice and target audience preferences
            • Create structured frameworks that guide efficient content generation
            • Plan content flow, logical progression, and engagement optimization

            CONTENT PLANNING EXPERTISE:
            • Blog posts, landing pages, product descriptions, email sequences
            • Case studies, whitepapers, social media content, and web copy
            • SEO optimization including keyword research and meta tag planning
            • Content structure design for maximum engagement and conversion
            • Brand voice integration and tone guidance for consistent messaging

            PLANNING METHODOLOGY:
            • Start with thorough analysis of project context and requirements
            • Research target audience characteristics and content preferences
            • Develop strategic objectives aligned with business goals
            • Create detailed section-by-section outlines with specific guidance
            • Integrate SEO keywords naturally throughout the content structure
            • Provide clear implementation guidelines for content creators

            OUTPUT STANDARDS:
            • Comprehensive content plans with detailed outlines
            • SEO strategy including primary, secondary, and long-tail keywords
            • Clear section objectives and tone guidance
            • Estimated word counts and completion timelines
            • Quality criteria and success metrics
            • Brand voice integration guidelines

            Project ID: {self.project_id or 'Not specified'}
            """
        
        return BaseMessage.make_assistant_message(
            role_name="content_planner",
            content=content
        )
    
    def _initialize_content_templates(self) -> Dict[str, Any]:
        """Initialize content type templates"""
        return {
            "blog_post": {
                "content_type": "blog_post",
                "sections": [
                    {
                        "title": "Introduction",
                        "type": "introduction",
                        "description": "Engaging opening that hooks readers and introduces the topic",
                        "objectives": ["Capture attention", "Establish relevance", "Preview key points"],
                        "word_count": 150
                    },
                    {
                        "title": "Main Content",
                        "type": "body",
                        "description": "Core content covering the main topic in depth",
                        "objectives": ["Provide valuable information", "Support key points", "Maintain engagement"],
                        "word_count": 800
                    },
                    {
                        "title": "Conclusion",
                        "type": "conclusion",
                        "description": "Summarize key takeaways and provide clear next steps",
                        "objectives": ["Reinforce main points", "Provide actionable next steps", "Encourage engagement"],
                        "word_count": 100
                    }
                ]
            },
            "landing_page": {
                "content_type": "landing_page",
                "sections": [
                    {
                        "title": "Hero Section",
                        "type": "introduction",
                        "description": "Compelling headline and value proposition",
                        "objectives": ["Capture immediate attention", "Communicate core value"],
                        "word_count": 50
                    },
                    {
                        "title": "Benefits & Features",
                        "type": "body",
                        "description": "Detailed breakdown of key benefits",
                        "objectives": ["Demonstrate value", "Address objections", "Build desire"],
                        "word_count": 300
                    },
                    {
                        "title": "Call to Action",
                        "type": "conclusion",
                        "description": "Clear, compelling CTA",
                        "objectives": ["Drive conversion", "Make action easy"],
                        "word_count": 50
                    }
                ]
            }
        }
    
    async def create_content_plan(self, 
                                content_request: Dict[str, Any],
                                style_analysis: Optional[Dict[str, Any]] = None) -> ContentPlan:
        """
        Create a comprehensive content plan based on requirements
        
        Args:
            content_request: Dictionary containing content requirements
            style_analysis: Optional style analysis results from Style Analyzer
            
        Returns:
            Complete ContentPlan object
        """
        self.logger.info(f"Creating content plan for: {content_request.get('title', 'Untitled')}")
        
        try:
            # Get project context from database
            project_context = await self._get_project_context()
            
            # Extract key information
            content_type = content_request.get('content_type', 'blog_post')
            title = content_request.get('title', 'Untitled Content')
            objectives = content_request.get('objectives', [])
            target_audience = content_request.get('target_audience', 
                                               project_context.get('configuration', {}).get('target_audience', 'General audience'))
            
            # Get brand voice information
            brand_voice_data = await self._extract_brand_voice_data(style_analysis, project_context)
            
            # Research keywords and SEO strategy
            seo_strategy = await self._develop_seo_strategy(content_request, project_context)
            
            # Create content outline based on type
            content_outline = await self._create_content_outline(content_request, brand_voice_data, seo_strategy)
            
            # Calculate estimates
            estimated_words = sum(section.estimated_word_count for section in content_outline)
            estimated_time = self._calculate_completion_time(estimated_words, content_type)
            
            # Define quality criteria and success metrics
            quality_criteria = self._define_quality_criteria(content_type, brand_voice_data)
            success_metrics = self._define_success_metrics(content_request, content_type)
            
            # Create comprehensive content plan
            content_plan = ContentPlan(
                title=title,
                content_type=content_type,
                target_audience=target_audience,
                primary_objectives=objectives,
                brand_voice_integration=brand_voice_data,
                seo_strategy=seo_strategy,
                content_outline=content_outline,
                estimated_total_words=estimated_words,
                estimated_completion_time=estimated_time,
                quality_criteria=quality_criteria,
                success_metrics=success_metrics
            )
            
            # Store plan in knowledge base if available
            if self.knowledge_base:
                await self._store_content_plan(content_plan)
            
            self.logger.info(f"Content plan created successfully: {estimated_words} words, {len(content_outline)} sections")
            
            return content_plan
            
        except Exception as e:
            self.logger.error(f"Failed to create content plan: {e}")
            raise
    
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get project context from database"""
        if not self.project_id:
            return {}
            
        try:
            db = SessionLocal()
            project = db.query(Project).filter(Project.project_id == self.project_id).first()
            
            if not project:
                return {}
            
            context = {
                "project_id": project.project_id,
                "client_name": project.client_name,
                "description": project.description,
                "configuration": project.configuration or {},
                "status": project.status
            }
            
            db.close()
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get project context: {e}")
            if 'db' in locals():
                db.close()
            return {}
    
    async def _extract_brand_voice_data(self, 
                                       style_analysis: Optional[Dict[str, Any]], 
                                       project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and compile brand voice information"""
        brand_voice_data = {
            "tone": "professional",
            "formality_level": 3,
            "vocabulary_level": 5,
            "sentence_complexity": 3,
            "personality_traits": [],
            "communication_values": [],
            "language_code": None
        }
        
        # Extract from project configuration
        config = project_context.get('configuration', {})
        if 'brand_voice' in config:
            brand_voice_data["tone"] = config['brand_voice']
        
        # Extract from style analysis if available
        if style_analysis:
            if 'language_code' in style_analysis:
                brand_voice_data["language_code"] = style_analysis['language_code']
            
            if 'brand_voice_elements' in style_analysis:
                elements = style_analysis['brand_voice_elements']
                brand_voice_data["personality_traits"] = elements.get('personality_traits', [])
                brand_voice_data["communication_values"] = elements.get('communication_values', [])
        
        return brand_voice_data
    
    async def _develop_seo_strategy(self, 
                                  content_request: Dict[str, Any], 
                                  project_context: Dict[str, Any]) -> SEOStrategy:
        """Develop comprehensive SEO strategy for content"""
        
        # Extract target keywords from request
        primary_keywords = content_request.get('primary_keywords', [])
        secondary_keywords = content_request.get('secondary_keywords', [])
        
        # Generate keywords if not provided
        if not primary_keywords:
            primary_keywords = await self._generate_primary_keywords(content_request)
        
        if not secondary_keywords:
            secondary_keywords = await self._generate_secondary_keywords(content_request, primary_keywords)
        
        # Generate long-tail keywords
        long_tail_keywords = await self._generate_long_tail_keywords(content_request, primary_keywords)
        
        # Create keyword density targets
        keyword_density_targets = {
            "primary": self.seo_config["primary_keyword_density"],
            "secondary": self.seo_config["secondary_keyword_density"],
            "long_tail": self.seo_config["long_tail_density"]
        }
        
        # Generate meta tags
        meta_title = await self._generate_meta_title(content_request, primary_keywords)
        meta_description = await self._generate_meta_description(content_request, primary_keywords)
        
        # Plan header structure
        header_structure = await self._plan_header_structure(content_request, primary_keywords)
        
        # Identify internal link opportunities
        internal_links = await self._identify_internal_link_opportunities(content_request, project_context)
        
        return SEOStrategy(
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
            long_tail_keywords=long_tail_keywords,
            keyword_density_targets=keyword_density_targets,
            meta_title=meta_title,
            meta_description=meta_description,
            header_structure=header_structure,
            internal_link_opportunities=internal_links
        )
    
    async def _create_content_outline(self, 
                                    content_request: Dict[str, Any],
                                    brand_voice_data: Dict[str, Any],
                                    seo_strategy: SEOStrategy) -> List[ContentSection]:
        """Create detailed content outline based on content type"""
        
        content_type = content_request.get('content_type', 'blog_post')
        
        # Get appropriate template
        template = self.content_templates.get(content_type, self.content_templates['blog_post'])
        
        # Customize template based on specific requirements
        outline = await self._customize_template(template, content_request, brand_voice_data, seo_strategy)
        
        return outline
    
    async def _customize_template(self, 
                                template: Dict[str, Any],
                                content_request: Dict[str, Any],
                                brand_voice_data: Dict[str, Any],
                                seo_strategy: SEOStrategy) -> List[ContentSection]:
        """Customize content template based on specific requirements"""
        
        sections = []
        
        # Process each section in template
        for section_template in template['sections']:
            # Assign keywords to section
            section_keywords = await self._assign_section_keywords(section_template, seo_strategy)
            
            # Generate tone guidance
            tone_guidance = await self._generate_tone_guidance(section_template, brand_voice_data)
            
            # Create section
            section = ContentSection(
                title=section_template['title'],
                description=await self._customize_section_description(
                    section_template['description'], 
                    content_request, 
                    brand_voice_data
                ),
                objectives=section_template.get('objectives', []),
                keywords=section_keywords,
                estimated_word_count=section_template.get('word_count', 200),
                tone_guidance=tone_guidance
            )
            
            sections.append(section)
        
        return sections
    
    async def _customize_section_description(self, 
                                           template_description: str,
                                           content_request: Dict[str, Any],
                                           brand_voice_data: Dict[str, Any]) -> str:
        """Customize section description based on requirements"""
        
        description = template_description
        
        # Replace common placeholders
        replacements = {
            '{title}': content_request.get('title', 'the topic'),
            '{audience}': content_request.get('target_audience', 'the target audience'),
            '{tone}': brand_voice_data.get('tone', 'professional'),
            '{objectives}': ', '.join(content_request.get('objectives', ['engage readers']))
        }
        
        for placeholder, value in replacements.items():
            description = description.replace(placeholder, value)
        
        return description
    
    async def _assign_section_keywords(self, 
                                     section_template: Dict[str, Any],
                                     seo_strategy: SEOStrategy) -> List[str]:
        """Assign relevant keywords to content section"""
        
        section_type = section_template.get('type', 'body')
        keywords = []
        
        if section_type == 'introduction':
            keywords.extend(seo_strategy.primary_keywords[:2])
        elif section_type == 'conclusion':
            keywords.extend(seo_strategy.primary_keywords[:1])
            keywords.extend(seo_strategy.secondary_keywords[:1])
        else:
            keywords.extend(seo_strategy.secondary_keywords[:2])
            keywords.extend(seo_strategy.long_tail_keywords[:1])
        
        return keywords
    
    async def _generate_tone_guidance(self, 
                                    section_template: Dict[str, Any],
                                    brand_voice_data: Dict[str, Any]) -> str:
        """Generate specific tone guidance for section"""
        
        base_tone = brand_voice_data.get('tone', 'professional')
        section_type = section_template.get('type', 'body')
        formality_level = brand_voice_data.get('formality_level', 3)
        
        if section_type == 'introduction':
            if formality_level <= 2:
                return f"Start with an engaging, {base_tone} hook that immediately captures attention."
            else:
                return f"Begin with a {base_tone} introduction that clearly establishes the topic's importance."
        
        elif section_type == 'conclusion':
            return f"End with a {base_tone} conclusion that reinforces key points and provides clear next steps."
        
        else:
            personality_traits = brand_voice_data.get('personality_traits', [])
            if personality_traits:
                return f"Maintain {base_tone} tone while incorporating {', '.join(personality_traits[:2])} characteristics."
            else:
                return f"Use {base_tone} tone while ensuring content is informative and engaging."
    
    # Helper methods for keyword generation and SEO
    async def _generate_primary_keywords(self, content_request: Dict[str, Any]) -> List[str]:
        """Generate primary keywords based on content topic"""
        title = content_request.get('title', '')
        topic = content_request.get('topic', '')
        
        # Simple keyword extraction
        text = f"{title} {topic}".lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Filter meaningful words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        meaningful_words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        return meaningful_words[:3] if meaningful_words else ['content', 'guide', 'tips']
    
    async def _generate_secondary_keywords(self, 
                                         content_request: Dict[str, Any], 
                                         primary_keywords: List[str]) -> List[str]:
        """Generate secondary keywords related to primary keywords"""
        
        secondary = []
        
        for primary in primary_keywords:
            # Add variations
            if not primary.endswith('s'):
                secondary.append(f"{primary}s")
            secondary.append(f"how to {primary}")
            secondary.append(f"best {primary}")
        
        # Add content-type specific keywords
        content_type = content_request.get('content_type', 'blog_post')
        if content_type == 'blog_post':
            secondary.extend(['tips', 'guide', 'tutorial'])
        elif content_type == 'landing_page':
            secondary.extend(['solution', 'service', 'benefits'])
        
        return secondary[:5]
    
    async def _generate_long_tail_keywords(self, 
                                         content_request: Dict[str, Any], 
                                         primary_keywords: List[str]) -> List[str]:
        """Generate long-tail keyword phrases"""
        
        long_tail = []
        
        for primary in primary_keywords:
            long_tail.extend([
                f"what is {primary}",
                f"how to use {primary}",
                f"best practices for {primary}"
            ])
        
        return long_tail[:6]
    
    async def _generate_meta_title(self, 
                                 content_request: Dict[str, Any], 
                                 primary_keywords: List[str]) -> str:
        """Generate SEO-optimized meta title"""
        
        title = content_request.get('title', '')
        if not title:
            title = f"{primary_keywords[0].title()} Guide" if primary_keywords else "Content Guide"
        
        # Ensure title is within character limit
        max_length = self.seo_config["max_title_length"]
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title
    
    async def _generate_meta_description(self, 
                                       content_request: Dict[str, Any], 
                                       primary_keywords: List[str]) -> str:
        """Generate SEO-optimized meta description"""
        
        description = content_request.get('description', '')
        
        if not description:
            primary_keyword = primary_keywords[0] if primary_keywords else "topics"
            description = f"Learn about {primary_keyword} with our comprehensive guide."
        
        # Ensure description is within character limit
        max_length = self.seo_config["max_meta_description"]
        if len(description) > max_length:
            description = description[:max_length-3] + "..."
        
        return description
    
    async def _plan_header_structure(self, 
                                   content_request: Dict[str, Any], 
                                   primary_keywords: List[str]) -> List[str]:
        """Plan header hierarchy for SEO"""
        
        headers = []
        content_type = content_request.get('content_type', 'blog_post')
        
        # H1 - Main title
        if primary_keywords:
            headers.append(f"H1: {content_request.get('title', primary_keywords[0].title())}")
        
        # H2s for main sections
        if content_type == 'blog_post':
            headers.extend([
                "H2: Introduction",
                "H2: Main Content",
                "H2: Conclusion"
            ])
        elif content_type == 'landing_page':
            headers.extend([
                "H2: Benefits",
                "H2: How It Works",
                "H2: Get Started"
            ])
        
        return headers
    
    async def _identify_internal_link_opportunities(self, 
                                                  content_request: Dict[str, Any], 
                                                  project_context: Dict[str, Any]) -> List[str]:
        """Identify opportunities for internal linking"""
        
        opportunities = [
            "Link to main service/product pages",
            "Reference related blog posts or guides",
            "Link to contact or consultation pages",
            "Reference case studies or testimonials"
        ]
        
        return opportunities[:4]
    
    def _calculate_completion_time(self, word_count: int, content_type: str) -> str:
        """Calculate estimated completion time"""
        
        writing_speeds = {
            'blog_post': 300,
            'landing_page': 200,
            'product_description': 400,
            'email_sequence': 350,
            'social_media': 500,
            'case_study': 250,
            'whitepaper': 200,
            'web_copy': 300
        }
        
        speed = writing_speeds.get(content_type, 300)
        hours = word_count / speed
        total_hours = hours * 1.5  # Add buffer time
        
        if total_hours < 1:
            return f"{int(total_hours * 60)} minutes"
        elif total_hours < 8:
            return f"{total_hours:.1f} hours"
        else:
            days = total_hours / 8
            return f"{days:.1f} working days"
    
    def _define_quality_criteria(self, 
                               content_type: str, 
                               brand_voice_data: Dict[str, Any]) -> List[str]:
        """Define quality criteria for content evaluation"""
        
        criteria = [
            "Content aligns with brand voice and tone",
            "Information is accurate and well-researched",
            "Writing is clear, engaging, and error-free",
            "Content provides genuine value to target audience",
            "SEO keywords are naturally integrated"
        ]
        
        return criteria
    
    def _define_success_metrics(self, 
                              content_request: Dict[str, Any], 
                              content_type: str) -> List[str]:
        """Define success metrics for content performance"""
        
        metrics = [
            "Content completion within estimated timeframe",
            "Brand voice consistency score > 85%",
            "SEO keyword integration meets density targets"
        ]
        
        # Add content-type specific metrics
        if content_type == 'blog_post':
            metrics.extend([
                "Average time on page > 2 minutes",
                "Social shares and engagement"
            ])
        elif content_type == 'landing_page':
            metrics.extend([
                "Conversion rate improvement",
                "Lead generation increase"
            ])
        
        return metrics
    
    async def _store_content_plan(self, content_plan: ContentPlan):
        """Store content plan in knowledge base"""
        try:
            plan_data = {
                "title": f"Content Plan: {content_plan.title}",
                "type": "content_plan",
                "content": json.dumps(content_plan.to_dict(), indent=2),
                "metadata": {
                    "content_type": content_plan.content_type,
                    "estimated_words": content_plan.estimated_total_words,
                    "created_at": datetime.now().isoformat()
                }
            }
            
            await self.knowledge_base.store_document(plan_data)
            self.logger.info(f"Content plan stored: {content_plan.title}")
            
        except Exception as e:
            self.logger.error(f"Failed to store content plan: {e}")
    
    def process_task(self, task):
        """Process planning task - legacy method for backwards compatibility"""
        response = self.step(task)
        return response


# Backwards compatibility class (matches existing naming convention)
class contentplannerAgent(ProductionContentPlannerAgent):
    """Backwards compatibility wrapper for existing code"""
    pass


# Factory function for easy instantiation
async def create_content_planner_agent(project_id: str = None) -> ProductionContentPlannerAgent:
    """
    Factory function to create and initialize a ProductionContentPlannerAgent
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionContentPlannerAgent instance
    """
    planner = ProductionContentPlannerAgent(project_id)
    return planner


# Export main classes
__all__ = [
    'ProductionContentPlannerAgent',
    'contentplannerAgent',  # For backwards compatibility
    'ContentPlan',
    'ContentSection',
    'SEOStrategy',
    'create_content_planner_agent'
]