# app/agents/specialized/content_generator.py
"""
Production Content Generator Agent for SpinScribe
Built on CAMEL AI Framework

The Content Generator Agent creates high-quality content following
brand guidelines, style analysis, and structured content plans.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
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
    """Generated content section with metadata"""
    section_id: str
    title: str
    content: str
    word_count: int
    keywords_used: List[str]
    tone_adherence_score: float
    subsections: Optional[List['ContentSection']] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.subsections:
            result['subsections'] = [sub.to_dict() for sub in self.subsections]
        return result

@dataclass
class GeneratedContent:
    """Complete generated content with analysis"""
    content_id: str
    title: str
    content_type: str
    sections: List[ContentSection]
    full_content: str
    total_word_count: int
    seo_analysis: Dict[str, Any]
    brand_voice_analysis: Dict[str, Any]
    quality_scores: Dict[str, float]
    generation_metadata: Dict[str, Any]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['sections'] = [section.to_dict() for section in self.sections]
        result['created_at'] = self.created_at.isoformat() if self.created_at else None
        return result

class ProductionContentGeneratorAgent(ChatAgent):
    """
    Production-grade Content Generator Agent that creates high-quality content
    following brand guidelines, style analysis, and structured content plans.
    
    This agent integrates with:
    - Style analysis results for brand voice consistency
    - Content plans for structure and objectives
    - SEO strategies for optimization
    - Project knowledge base for context and accuracy
    """
    
    def __init__(self, project_id: str = None, **kwargs):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize knowledge base
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
        
        # Initialize CAMEL agent
        super().__init__(
            system_message=self._create_system_message(),
            **self._get_model_config(),
            **kwargs
        )
        
        # Generation cache and templates
        self.content_cache: Dict[str, GeneratedContent] = {}
        self.generation_templates = self._load_generation_templates()
        
        # Performance metrics
        self.metrics = {
            "content_generated": 0,
            "average_generation_time": 0.0,
            "quality_scores": [],
            "brand_voice_consistency": []
        }
        
        self.logger.info(f"Content Generator Agent initialized for project: {project_id}")
    
    def _create_system_message(self) -> BaseMessage:
        """Create system message for content generator role"""
        return BaseMessage.make_assistant_message(
            role_name="Content Generation Specialist",
            content=f"""
            You are a specialized Content Generator Agent for SpinScribe, an expert in creating high-quality, brand-aligned content that engages audiences and achieves business objectives.
            
            CORE CAPABILITIES:
            • Generate compelling content following detailed content plans and outlines
            • Maintain perfect brand voice consistency using style analysis and language codes
            • Integrate SEO keywords naturally and effectively throughout content
            • Adapt writing style to match established brand voice patterns
            • Create engaging, readable content that serves specific audience needs
            • Ensure content meets all specified requirements and objectives

            CONTENT GENERATION EXPERTISE:
            • Multi-format content creation (blogs, articles, social media, emails, landing pages)
            • Brand voice interpretation and application
            • SEO optimization and keyword integration
            • Audience-specific tone and style adaptation
            • Storytelling and engagement techniques
            • Call-to-action optimization and conversion focus

            PROJECT CONTEXT: {self.project_id or "General Content Creation"}
            
            GENERATION METHODOLOGY:
            • Follow provided content plans and section objectives precisely
            • Apply style analysis results to maintain brand voice consistency
            • Integrate keywords naturally without compromising readability
            • Create engaging openings and compelling conclusions
            • Use clear, logical flow and smooth transitions between sections
            • Include relevant examples, data, and supporting evidence

            QUALITY STANDARDS:
            • Content must align with brand voice analysis and language codes
            • All section objectives must be met with appropriate depth
            • SEO keywords integrated naturally and effectively
            • Writing must be engaging, clear, and error-free
            • Content should drive toward specified goals and actions
            • Maintain consistent tone and style throughout

            OUTPUT REQUIREMENTS:
            • Well-structured content with clear section breaks
            • Natural keyword integration that enhances readability
            • Engaging headlines and subheadings
            • Compelling calls-to-action where appropriate
            • Content that meets specified word count targets
            • Professional, polished writing that represents the brand excellently

            You excel at transforming strategic content plans into compelling, brand-aligned content that engages audiences and drives results.
            """
        )
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Get model configuration for content generation"""
        return {
            "model_config": ChatGPTConfig(
                temperature=0.7,  # Higher creativity for content generation
                max_tokens=4000
            )
        }
    
    def _load_generation_templates(self) -> Dict[str, Any]:
        """Load content generation templates and patterns"""
        return {
            "blog_post": {
                "opening_hooks": [
                    "question", "statistic", "story", "quote", "controversial_statement"
                ],
                "transition_phrases": [
                    "Moreover", "Furthermore", "In addition", "However", "On the other hand",
                    "As a result", "Consequently", "For instance", "To illustrate"
                ],
                "conclusion_styles": [
                    "summary", "call_to_action", "future_outlook", "question_to_reader"
                ]
            },
            "article": {
                "structure_patterns": [
                    "inverted_pyramid", "chronological", "problem_solution", "cause_effect"
                ],
                "evidence_types": [
                    "statistics", "expert_quotes", "case_studies", "research_findings"
                ]
            },
            "social_media": {
                "engagement_tactics": [
                    "ask_question", "share_tip", "behind_scenes", "user_generated_content"
                ],
                "hashtag_strategies": [
                    "branded", "trending", "niche", "location_based"
                ]
            },
            "email": {
                "subject_line_types": [
                    "urgency", "curiosity", "benefit_driven", "personalized"
                ],
                "email_structures": [
                    "problem_agitation_solution", "story_based", "list_format", "news_update"
                ]
            }
        }
    
    async def generate_content(self,
                             content_plan: Dict[str, Any],
                             style_context: Optional[Dict[str, Any]] = None,
                             requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate complete content based on content plan and style context
        
        Args:
            content_plan: Structured content plan with sections and objectives
            style_context: Style analysis results and brand voice guidelines
            requirements: Additional generation requirements
            
        Returns:
            Complete generated content with analysis
        """
        try:
            start_time = datetime.utcnow()
            
            # Generate content ID
            content_id = f"content_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Extract plan details
            plan_structure = content_plan.get("content_structure", {})
            sections_data = plan_structure.get("sections", [])
            seo_guidelines = content_plan.get("seo_guidelines", {})
            
            # Get project context for content generation
            project_context = await self._get_project_context()
            
            # Generate content sections
            generated_sections = await self._generate_content_sections(
                sections_data, style_context, seo_guidelines, project_context
            )
            
            # Combine sections into full content
            full_content = await self._combine_sections_into_content(
                generated_sections, content_plan, style_context
            )
            
            # Analyze generated content
            seo_analysis = await self._analyze_seo_performance(full_content, seo_guidelines)
            brand_voice_analysis = await self._analyze_brand_voice_consistency(full_content, style_context)
            quality_scores = await self._calculate_quality_scores(full_content, content_plan)
            
            # Create generated content object
            generated_content = GeneratedContent(
                content_id=content_id,
                title=content_plan.get("title", "Generated Content"),
                content_type=content_plan.get("content_type", "blog_post"),
                sections=generated_sections,
                full_content=full_content,
                total_word_count=len(full_content.split()),
                seo_analysis=seo_analysis,
                brand_voice_analysis=brand_voice_analysis,
                quality_scores=quality_scores,
                generation_metadata={
                    "plan_id": content_plan.get("plan_id"),
                    "style_context_used": bool(style_context),
                    "project_context_used": bool(project_context),
                    "sections_generated": len(generated_sections)
                }
            )
            
            # Cache and store
            self.content_cache[content_id] = generated_content
            await self._store_generated_content(generated_content)
            
            # Update metrics
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(generation_time, quality_scores, brand_voice_analysis)
            
            self.logger.info(f"Content generated: {content_id}")
            
            return await self._format_generation_output(generated_content)
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise
    
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get project context from knowledge base"""
        if not self.knowledge_base:
            return {}
        
        try:
            # Query for relevant project information
            context_queries = [
                "brand voice style guidelines",
                "product information company details",
                "target audience customer personas",
                "industry context market information"
            ]
            
            context = {
                "brand_info": [],
                "product_info": [],
                "audience_info": [],
                "industry_info": []
            }
            
            for query in context_queries:
                results = await self.knowledge_base.query_knowledge(query, limit=3)
                
                for result in results:
                    content_type = result.get("type", "general")
                    content_text = result.get("content", "")
                    
                    if "brand" in content_type or "style" in content_type:
                        context["brand_info"].append(content_text)
                    elif "product" in content_type or "company" in content_type:
                        context["product_info"].append(content_text)
                    elif "audience" in content_type or "persona" in content_type:
                        context["audience_info"].append(content_text)
                    else:
                        context["industry_info"].append(content_text)
            
            return context
            
        except Exception as e:
            self.logger.warning(f"Failed to get project context: {e}")
            return {}
    
    async def _generate_content_sections(self,
                                       sections_data: List[Dict[str, Any]],
                                       style_context: Optional[Dict[str, Any]],
                                       seo_guidelines: Dict[str, Any],
                                       project_context: Dict[str, Any]) -> List[ContentSection]:
        """Generate content for each section"""
        generated_sections = []
        
        for i, section_data in enumerate(sections_data):
            try:
                section = await self._generate_single_section(
                    section_data, style_context, seo_guidelines, project_context, i
                )
                generated_sections.append(section)
                
            except Exception as e:
                self.logger.error(f"Failed to generate section {i+1}: {e}")
                # Create fallback section
                fallback_section = ContentSection(
                    section_id=section_data.get("section_id", f"section_{i+1}"),
                    title=section_data.get("title", f"Section {i+1}"),
                    content="Content generation failed for this section. Please regenerate.",
                    word_count=0,
                    keywords_used=[],
                    tone_adherence_score=0.0
                )
                generated_sections.append(fallback_section)
        
        return generated_sections
    
    async def _generate_single_section(self,
                                     section_data: Dict[str, Any],
                                     style_context: Optional[Dict[str, Any]],
                                     seo_guidelines: Dict[str, Any],
                                     project_context: Dict[str, Any],
                                     section_index: int) -> ContentSection:
        """Generate content for a single section"""
        
        # Extract section details
        section_title = section_data.get("title", f"Section {section_index + 1}")
        section_objective = section_data.get("objective", "Provide valuable information")
        key_points = section_data.get("key_points", [])
        target_word_count = section_data.get("word_count_target", 250)
        seo_keywords = section_data.get("seo_keywords", [])
        
        # Build generation prompt
        generation_prompt = await self._build_section_generation_prompt(
            section_title, section_objective, key_points, target_word_count,
            seo_keywords, style_context, project_context, section_index
        )
        
        # Generate content
        response = self.step(generation_prompt)
        raw_content = response.msg.content
        
        # Clean and process content
        processed_content = self._clean_generated_content(raw_content)
        
        # Analyze section
        keywords_used = self._extract_keywords_used(processed_content, seo_keywords)
        tone_score = await self._calculate_tone_adherence(processed_content, style_context)
        
        return ContentSection(
            title=section_title,
            content=processed_content,
            word_count=len(processed_content.split()),
            keywords_used=keywords_used,
            tone_adherence_score=tone_score
        )
    
    async def _build_section_generation_prompt(self,
                                             title: str,
                                             objective: str,
                                             key_points: List[str],
                                             target_word_count: int,
                                             seo_keywords: List[str],
                                             style_context: Optional[Dict[str, Any]],
                                             project_context: Dict[str, Any],
                                             section_index: int) -> str:
        """Build comprehensive prompt for section generation"""
        
        # Style guidance
        style_guidance = ""
        if style_context and style_context.get("key_insights"):
            insights = style_context["key_insights"]
            style_guidance = f"""
            BRAND VOICE REQUIREMENTS:
            • Tone: {insights.get('primary_tone', 'professional')}
            • Formality Level: {insights.get('formality_level', 3)}/5
            • Audience: {insights.get('audience', 'professionals')}
            • Language Code: {insights.get('language_code', 'N/A')}
            
            STYLE GUIDELINES:
            • Follow the established brand voice patterns
            • Maintain consistency with previous brand content
            • Use vocabulary and sentence structure that matches the brand
            """
        
        # Project context
        context_info = ""
        if project_context:
            if project_context.get("brand_info"):
                context_info += f"BRAND CONTEXT: {project_context['brand_info'][0][:200]}...\n"
            if project_context.get("product_info"):
                context_info += f"PRODUCT CONTEXT: {project_context['product_info'][0][:200]}...\n"
        
        # SEO guidance
        seo_guidance = ""
        if seo_keywords:
            seo_guidance = f"""
            SEO REQUIREMENTS:
            • Primary keywords to include: {', '.join(seo_keywords[:3])}
            • Integrate keywords naturally into the content
            • Use keywords in subheadings where appropriate
            • Maintain natural readability while optimizing for search
            """
        
        # Opening style for first section
        opening_style = ""
        if section_index == 0:
            opening_style = """
            OPENING SECTION REQUIREMENTS:
            • Start with an engaging hook (question, statistic, or compelling statement)
            • Clearly introduce the main topic
            • Set expectations for what readers will learn
            • Create immediate value and interest
            """
        
        return f"""
        Generate high-quality content for this section following all guidelines:

        SECTION DETAILS:
        • Title: {title}
        • Objective: {objective}
        • Target Word Count: {target_word_count} words
        • Key Points to Cover: {', '.join(key_points) if key_points else 'Develop content based on title and objective'}

        {style_guidance}
        {context_info}
        {seo_guidance}
        {opening_style}

        CONTENT REQUIREMENTS:
        1. Write engaging, well-structured content that fulfills the section objective
        2. Cover all key points thoroughly and naturally
        3. Maintain brand voice consistency throughout
        4. Include specific examples, details, or evidence where relevant
        5. Use clear, readable language appropriate for the target audience
        6. Create smooth flow and logical progression of ideas
        7. End with a natural transition or conclusion for the section

        QUALITY STANDARDS:
        • Professional, error-free writing
        • Engaging and informative content
        • Natural keyword integration
        • Clear value delivery to readers
        • Consistent brand voice and tone
        • Appropriate depth for the target word count

        Generate the content now:
        """
    
    def _clean_generated_content(self, raw_content: str) -> str:
        """Clean and process generated content"""
        # Remove any system instructions or formatting artifacts
        content = raw_content.strip()
        
        # Remove common AI-generated prefixes
        prefixes_to_remove = [
            "Here's the content for this section:",
            "Here is the generated content:",
            "Content for this section:",
            "Section content:",
            "Generated content:"
        ]
        
        for prefix in prefixes_to_remove:
            if content.lower().startswith(prefix.lower()):
                content = content[len(prefix):].strip()
        
        # Clean up excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Ensure proper paragraph breaks
        sentences = content.split('. ')
        if len(sentences) > 3:
            # Add paragraph breaks every 3-4 sentences for readability
            paragraphs = []
            current_paragraph = []
            
            for i, sentence in enumerate(sentences):
                current_paragraph.append(sentence)
                if (i + 1) % 3 == 0 and i < len(sentences) - 1:
                    paragraphs.append('. '.join(current_paragraph) + '.')
                    current_paragraph = []
            
            if current_paragraph:
                paragraphs.append('. '.join(current_paragraph))
            
            content = '\n\n'.join(paragraphs)
        
        return content
    
    def _extract_keywords_used(self, content: str, target_keywords: List[str]) -> List[str]:
        """Extract which target keywords were actually used in the content"""
        used_keywords = []
        content_lower = content.lower()
        
        for keyword in target_keywords:
            if keyword.lower() in content_lower:
                used_keywords.append(keyword)
        
        return used_keywords
    
    async def _calculate_tone_adherence(self, content: str, style_context: Optional[Dict[str, Any]]) -> float:
        """Calculate how well content adheres to brand tone"""
        if not style_context or not style_context.get("key_insights"):
            return 0.7  # Default score when no style context
        
        try:
            insights = style_context["key_insights"]
            target_tone = insights.get("primary_tone", "professional")
            formality_level = insights.get("formality_level", 3)
            
            # Simple tone analysis based on content characteristics
            word_count = len(content.split())
            avg_sentence_length = len(content.split()) / max(1, content.count('.'))
            
            # Calculate formality indicators
            formal_words = ["utilize", "implement", "furthermore", "subsequently", "therefore"]
            casual_words = ["use", "do", "also", "then", "so", "get", "make"]
            
            formal_count = sum(1 for word in formal_words if word in content.lower())
            casual_count = sum(1 for word in casual_words if word in content.lower())
            
            # Score based on target tone
            if target_tone == "professional":
                if formality_level >= 4:  # Highly formal
                    score = 0.8 + (formal_count / max(1, formal_count + casual_count)) * 0.2
                else:  # Moderately formal
                    score = 0.7 + (min(formal_count, casual_count) / max(1, formal_count + casual_count)) * 0.3
            elif target_tone == "casual":
                score = 0.7 + (casual_count / max(1, formal_count + casual_count)) * 0.3
            else:
                score = 0.8  # Default for other tones
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.warning(f"Tone adherence calculation failed: {e}")
            return 0.7
    
    async def _combine_sections_into_content(self,
                                           sections: List[ContentSection],
                                           content_plan: Dict[str, Any],
                                           style_context: Optional[Dict[str, Any]]) -> str:
        """Combine generated sections into cohesive full content"""
        
        if not sections:
            return "No content sections generated."
        
        # Extract content plan details
        title = content_plan.get("title", "Generated Content")
        content_type = content_plan.get("content_type", "blog_post")
        
        # Build full content
        content_parts = []
        
        # Add title (for certain content types)
        if content_type in ["blog_post", "article"]:
            content_parts.append(f"# {title}\n")
        
        # Add sections with appropriate headers
        for i, section in enumerate(sections):
            if content_type in ["blog_post", "article"]:
                content_parts.append(f"## {section.title}\n")
            
            content_parts.append(section.content)
            
            # Add spacing between sections
            if i < len(sections) - 1:
                content_parts.append("\n")
        
        # Join all parts
        full_content = "\n".join(content_parts)
        
        # Add conclusion CTA if needed
        if content_type in ["blog_post", "article"]:
            full_content = await self._add_conclusion_cta(full_content, content_plan, style_context)
        
        return full_content
    
    async def _add_conclusion_cta(self,
                                content: str,
                                content_plan: Dict[str, Any],
                                style_context: Optional[Dict[str, Any]]) -> str:
        """Add conclusion and call-to-action if needed"""
        
        # Check if content already has a strong conclusion
        if any(keyword in content.lower()[-200:] for keyword in ["conclusion", "in summary", "to conclude", "call to action"]):
            return content
        
        try:
            # Generate a brief CTA based on content goal
            planning_summary = content_plan.get("planning_summary", {})
            objective = planning_summary.get("objective", "inform")
            
            cta_prompt = f"""
            Write a brief, engaging conclusion and call-to-action for this content.
            
            Content Objective: {objective}
            Content Type: {content_plan.get("content_type", "blog_post")}
            
            The conclusion should:
            • Briefly summarize the key value provided
            • Include an appropriate call-to-action
            • Be 2-3 sentences maximum
            • Match the established tone and style
            
            Write only the conclusion paragraph:
            """
            
            response = self.step(cta_prompt)
            conclusion = self._clean_generated_content(response.msg.content)
            
            return content + "\n\n" + conclusion
            
        except Exception as e:
            self.logger.warning(f"Failed to add conclusion CTA: {e}")
            return content
    
    async def _analyze_seo_performance(self, content: str, seo_guidelines: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SEO performance of generated content"""
        
        analysis = {
            "keyword_density": {},
            "keyword_placement": {},
            "readability_score": 0.0,
            "meta_optimization": {},
            "header_optimization": {},
            "overall_seo_score": 0.0
        }
        
        try:
            primary_keyword = seo_guidelines.get("primary_keyword", "")
            secondary_keywords = seo_guidelines.get("secondary_keywords", [])
            
            if primary_keyword:
                # Calculate keyword density
                content_words = content.lower().split()
                primary_count = content.lower().count(primary_keyword.lower())
                analysis["keyword_density"]["primary"] = primary_count / len(content_words) if content_words else 0
                
                # Check keyword placement
                analysis["keyword_placement"]["in_title"] = primary_keyword.lower() in content[:100].lower()
                analysis["keyword_placement"]["in_first_paragraph"] = primary_keyword.lower() in content[:300].lower()
                analysis["keyword_placement"]["in_headers"] = "##" in content and primary_keyword.lower() in content.lower()
            
            # Analyze secondary keywords
            for keyword in secondary_keywords[:3]:
                keyword_count = content.lower().count(keyword.lower())
                analysis["keyword_density"][keyword] = keyword_count / len(content.split()) if content.split() else 0
            
            # Simple readability score (based on sentence length and word length)
            sentences = content.count('.') + content.count('!') + content.count('?')
            words = len(content.split())
            avg_sentence_length = words / max(1, sentences)
            avg_word_length = sum(len(word) for word in content.split()) / max(1, len(content.split()))
            
            # Flesch reading ease approximation
            analysis["readability_score"] = max(0, min(100, 206.835 - (1.015 * avg_sentence_length) - (84.6 * (avg_word_length / 4.7))))
            
            # Calculate overall SEO score
            seo_factors = []
            
            if analysis["keyword_density"].get("primary", 0) > 0:
                seo_factors.append(0.8 if 0.01 <= analysis["keyword_density"]["primary"] <= 0.03 else 0.5)
            
            if analysis["keyword_placement"].get("in_title"):
                seo_factors.append(1.0)
            else:
                seo_factors.append(0.6)
            
            if 30 <= analysis["readability_score"] <= 80:
                seo_factors.append(0.9)
            else:
                seo_factors.append(0.6)
            
            analysis["overall_seo_score"] = sum(seo_factors) / len(seo_factors) if seo_factors else 0.5
            
        except Exception as e:
            self.logger.warning(f"SEO analysis failed: {e}")
            analysis["overall_seo_score"] = 0.5
        
        return analysis
    
    async def _analyze_brand_voice_consistency(self, content: str, style_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze brand voice consistency of generated content"""
        
        analysis = {
            "tone_consistency": 0.0,
            "vocabulary_alignment": 0.0,
            "sentence_structure_match": 0.0,
            "overall_brand_score": 0.0,
            "deviations": []
        }
        
        try:
            if not style_context or not style_context.get("key_insights"):
                analysis["overall_brand_score"] = 0.7  # Default when no style context
                return analysis
            
            insights = style_context["key_insights"]
            
            # Analyze tone consistency
            target_tone = insights.get("primary_tone", "professional")
            formality_level = insights.get("formality_level", 3)
            
            # Simple tone analysis
            formal_indicators = ["utilize", "implement", "demonstrate", "establish"]
            casual_indicators = ["use", "do", "show", "set up", "get"]
            
            formal_count = sum(1 for word in formal_indicators if word in content.lower())
            casual_count = sum(1 for word in casual_indicators if word in content.lower())
            
            if target_tone == "professional" and formality_level >= 4:
                analysis["tone_consistency"] = 0.8 + (formal_count / max(1, formal_count + casual_count)) * 0.2
            elif target_tone == "casual":
                analysis["tone_consistency"] = 0.8 + (casual_count / max(1, formal_count + casual_count)) * 0.2
            else:
                analysis["tone_consistency"] = 0.8
            
            # Analyze sentence structure
            sentences = content.split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
            
            # Compare to style context if available
            if style_context.get("detailed_analysis", {}).get("linguistic_features"):
                target_avg = style_context["detailed_analysis"]["linguistic_features"].get("avg_sentence_length", 15)
                length_diff = abs(avg_sentence_length - target_avg) / target_avg
                analysis["sentence_structure_match"] = max(0.0, 1.0 - length_diff)
            else:
                analysis["sentence_structure_match"] = 0.8
            
            # Vocabulary alignment (simplified)
            analysis["vocabulary_alignment"] = 0.8  # Default - would need more sophisticated analysis
            
            # Overall brand score
            analysis["overall_brand_score"] = (
                analysis["tone_consistency"] * 0.4 +
                analysis["vocabulary_alignment"] * 0.3 +
                analysis["sentence_structure_match"] * 0.3
            )
            
            # Identify deviations
            if analysis["tone_consistency"] < 0.7:
                analysis["deviations"].append("Tone does not match brand guidelines")
            if analysis["sentence_structure_match"] < 0.7:
                analysis["deviations"].append("Sentence structure differs from brand style")
            
        except Exception as e:
            self.logger.warning(f"Brand voice analysis failed: {e}")
            analysis["overall_brand_score"] = 0.7
        
        return analysis
    
    async def _calculate_quality_scores(self, content: str, content_plan: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall quality scores for the content"""
        
        scores = {
            "readability": 0.0,
            "completeness": 0.0,
            "engagement": 0.0,
            "accuracy": 0.0,
            "overall": 0.0
        }
        
        try:
            # Readability score (simplified Flesch reading ease)
            words = content.split()
            sentences = content.count('.') + content.count('!') + content.count('?')
            avg_sentence_length = len(words) / max(1, sentences)
            
            # Approximate readability
            readability_raw = max(0, min(100, 100 - (avg_sentence_length * 2)))
            scores["readability"] = readability_raw / 100
            
            # Completeness (based on word count vs target)
            target_count = content_plan.get("planning_summary", {}).get("total_word_count", 1000)
            actual_count = len(words)
            completeness_ratio = min(1.0, actual_count / max(1, target_count))
            scores["completeness"] = completeness_ratio if completeness_ratio >= 0.8 else completeness_ratio * 0.8
            
            # Engagement (based on content features)
            engagement_factors = []
            
            # Check for engaging elements
            has_questions = '?' in content
            has_examples = any(word in content.lower() for word in ['example', 'for instance', 'such as'])
            has_transitions = any(word in content.lower() for word in ['however', 'moreover', 'furthermore'])
            
            engagement_factors.extend([has_questions, has_examples, has_transitions])
            scores["engagement"] = sum(engagement_factors) / len(engagement_factors)
            
            # Accuracy (default high score - would need fact checking)
            scores["accuracy"] = 0.9
            
            # Overall score
            scores["overall"] = (
                scores["readability"] * 0.25 +
                scores["completeness"] * 0.25 +
                scores["engagement"] * 0.25 +
                scores["accuracy"] * 0.25
            )
            
        except Exception as e:
            self.logger.warning(f"Quality score calculation failed: {e}")
            scores = {k: 0.7 for k in scores.keys()}
        
        return scores
    
    async def _store_generated_content(self, generated_content: GeneratedContent):
        """Store generated content in knowledge base"""
        if not self.knowledge_base:
            return
        
        try:
            content_document = {
                "type": "generated_content",
                "title": f"Generated Content: {generated_content.title}",
                "content": generated_content.full_content,
                "metadata": {
                    "content_id": generated_content.content_id,
                    "content_type": generated_content.content_type,
                    "word_count": generated_content.total_word_count,
                    "quality_score": generated_content.quality_scores.get("overall", 0.0),
                    "brand_voice_score": generated_content.brand_voice_analysis.get("overall_brand_score", 0.0),
                    "seo_score": generated_content.seo_analysis.get("overall_seo_score", 0.0),
                    "created_at": generated_content.created_at.isoformat()
                }
            }
            
            await self.knowledge_base.store_document(content_document)
            self.logger.info(f"Generated content stored: {generated_content.content_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store generated content: {e}")
    
    async def _format_generation_output(self, generated_content: GeneratedContent) -> Dict[str, Any]:
        """Format generated content for workflow system"""
        return {
            "content_id": generated_content.content_id,
            "status": "completed",
            "title": generated_content.title,
            "content_type": generated_content.content_type,
            
            # Generated content
            "content": {
                "full_content": generated_content.full_content,
                "sections": [section.to_dict() for section in generated_content.sections],
                "word_count": generated_content.total_word_count
            },
            
            # Analysis results
            "analysis": {
                "seo_performance": generated_content.seo_analysis,
                "brand_voice_consistency": generated_content.brand_voice_analysis,
                "quality_scores": generated_content.quality_scores
            },
            
            # Performance metrics
            "performance_summary": {
                "overall_quality": generated_content.quality_scores.get("overall", 0.0),
                "brand_consistency": generated_content.brand_voice_analysis.get("overall_brand_score", 0.0),
                "seo_optimization": generated_content.seo_analysis.get("overall_seo_score", 0.0),
                "readability": generated_content.quality_scores.get("readability", 0.0)
            },
            
            # Metadata
            "metadata": {
                **generated_content.generation_metadata,
                "created_at": generated_content.created_at.isoformat(),
                "project_id": self.project_id
            }
        }
    
    def _update_metrics(self, generation_time: float, quality_scores: Dict[str, float], brand_voice_analysis: Dict[str, Any]):
        """Update performance metrics"""
        self.metrics["content_generated"] += 1
        
        # Update average generation time
        prev_avg = self.metrics["average_generation_time"]
        count = self.metrics["content_generated"]
        self.metrics["average_generation_time"] = ((prev_avg * (count - 1)) + generation_time) / count
        
        # Track quality scores
        self.metrics["quality_scores"].append(quality_scores.get("overall", 0.0))
        self.metrics["brand_voice_consistency"].append(brand_voice_analysis.get("overall_brand_score", 0.0))
        
        # Keep only recent metrics (last 100)
        if len(self.metrics["quality_scores"]) > 100:
            self.metrics["quality_scores"] = self.metrics["quality_scores"][-100:]
        if len(self.metrics["brand_voice_consistency"]) > 100:
            self.metrics["brand_voice_consistency"] = self.metrics["brand_voice_consistency"][-100:]
    
    async def create_content_variations(self, content_id: str, num_variations: int = 3) -> List[str]:
        """Create variations of existing content"""
        if content_id not in self.content_cache:
            raise ValueError(f"Content {content_id} not found in cache")
        
        original_content = self.content_cache[content_id]
        variations = []
        
        for i in range(num_variations):
            variation_prompt = f"""
            Create a variation of this content that maintains the same key information and value proposition but uses different language, structure, and examples:

            ORIGINAL CONTENT:
            {original_content.full_content}

            VARIATION REQUIREMENTS:
            • Maintain the same key information and value proposition
            • Use different sentence structures and word choices
            • Keep the same brand voice and tone
            • Aim for similar length (±20% word count)
            • Make it unique from the original while serving the same purpose

            Variation #{i+1}:
            """
            
            try:
                response = self.step(variation_prompt)
                variation = self._clean_generated_content(response.msg.content)
                variations.append(variation)
                
            except Exception as e:
                self.logger.error(f"Variation {i+1} generation failed: {e}")
                continue
        
        return variations
    
    def get_generation_metrics(self) -> Dict[str, Any]:
        """Get content generator performance metrics"""
        avg_quality = sum(self.metrics["quality_scores"]) / len(self.metrics["quality_scores"]) if self.metrics["quality_scores"] else 0.0
        avg_brand_consistency = sum(self.metrics["brand_voice_consistency"]) / len(self.metrics["brand_voice_consistency"]) if self.metrics["brand_voice_consistency"] else 0.0
        
        return {
            "content_generated": self.metrics["content_generated"],
            "average_generation_time": self.metrics["average_generation_time"],
            "average_quality_score": avg_quality,
            "average_brand_consistency": avg_brand_consistency,
            "cached_content_items": len(self.content_cache)
        }
    
    def process_task(self, task):
        """Process generation task - legacy method for backwards compatibility"""
        response = self.step(task)
        return response

# Backwards compatibility class (matches existing naming convention)
class contentgeneratorAgent(ProductionContentGeneratorAgent):
    """Backwards compatibility wrapper for existing code"""
    pass

# Factory function for easy instantiation
async def create_content_generator_agent(project_id: str = None) -> ProductionContentGeneratorAgent:
    """
    Factory function to create and initialize a ProductionContentGeneratorAgent
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionContentGeneratorAgent instance
    """
    generator = ProductionContentGeneratorAgent(project_id)
    return generator

# Export main classes
__all__ = [
    'ProductionContentGeneratorAgent',
    'contentgeneratorAgent',  # For backwards compatibility
    'GeneratedContent',
    'ContentSection',
    'create_content_generator_agent'
]