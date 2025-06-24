# app/agents/specialized/content_generator.py
"""
Production Content Generator Agent for SpinScribe
Built on CAMEL AI Framework

The Content Generator Agent creates high-quality content following
brand guidelines, style guides, and structured content plans.
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
    """Generated content section with metadata"""
    title: str
    content: str
    word_count: int
    keywords_used: List[str]
    tone_adherence_score: float
    subsections: List['ContentSection'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.subsections:
            result['subsections'] = [sub.to_dict() for sub in self.subsections]
        return result

@dataclass
class GeneratedContent:
    """Complete generated content with analysis"""
    title: str
    content_type: str
    sections: List[ContentSection]
    full_content: str
    total_word_count: int
    seo_analysis: Dict[str, Any]
    brand_voice_analysis: Dict[str, Any]
    quality_scores: Dict[str, float]
    generation_metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['sections'] = [section.to_dict() for section in self.sections]
        return result

class ProductionContentGeneratorAgent(ChatAgent):
    """
    Production-grade Content Generator Agent that creates high-quality content
    following brand guidelines and structured content plans.
    """
    
    def __init__(self, project_id: str = None, **kwargs):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id or 'standalone'}")
        
        # Initialize system message
        system_message = self._create_generator_system_message()
        super().__init__(system_message=system_message, **kwargs)
        
        # Initialize knowledge base connection
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
        
        # Content generation configuration
        self.generation_config = {
            "max_section_length": 500,
            "keyword_density_tolerance": 0.005,  # ±0.5%
            "tone_consistency_threshold": 0.8,
            "quality_threshold": 0.85,
            "max_retries": 3
        }
        
        # Writing style templates
        self.style_templates = {
            "professional": {
                "sentence_starters": ["Furthermore", "Additionally", "Moreover", "In conclusion", "Therefore"],
                "connectors": ["however", "nevertheless", "consequently", "subsequently", "accordingly"],
                "vocabulary_level": "advanced"
            },
            "conversational": {
                "sentence_starters": ["Now", "Here's the thing", "You know what", "Let's be honest", "Simply put"],
                "connectors": ["but", "so", "and", "plus", "actually"],
                "vocabulary_level": "simple"
            },
            "authoritative": {
                "sentence_starters": ["Research shows", "Data indicates", "Studies reveal", "Evidence suggests", "Analysis confirms"],
                "connectors": ["therefore", "thus", "consequently", "as a result", "accordingly"],
                "vocabulary_level": "technical"
            },
            "friendly": {
                "sentence_starters": ["You'll love this", "Here's something cool", "This is exciting", "Get ready", "You're going to find"],
                "connectors": ["and", "plus", "also", "not to mention", "what's more"],
                "vocabulary_level": "accessible"
            }
        }
        
    def _create_generator_system_message(self) -> BaseMessage:
        """Create comprehensive system message for content generator role"""
        content = f"""
You are the Production Content Generator Agent for SpinScribe, specializing in creating high-quality, brand-aligned content.

CORE RESPONSIBILITIES:
• Generate compelling, original content following detailed outlines and brand guidelines
• Maintain consistent brand voice and tone throughout all content pieces
• Integrate SEO keywords naturally while preserving readability and engagement
• Create content that resonates with target audiences and achieves specified objectives
• Ensure all content meets quality standards and client requirements
• Adapt writing style to match brand personality and communication preferences

CONTENT GENERATION EXPERTISE:
• Blog posts, landing pages, product descriptions, email sequences
• Case studies, whitepapers, social media content, and web copy
• SEO-optimized content with natural keyword integration
• Persuasive copy that drives engagement and conversions
• Technical content adapted for various audience levels
• Storytelling and narrative content that builds brand connection

GENERATION METHODOLOGY:
• Carefully analyze provided content plans and style guidelines
• Extract and apply brand voice characteristics consistently
• Follow content outlines precisely while adding creative value
• Integrate keywords naturally without compromising readability
• Create engaging hooks and compelling calls-to-action
• Ensure logical flow and smooth transitions between sections

QUALITY STANDARDS:
• Original, plagiarism-free content creation
• Error-free grammar, spelling, and punctuation
• Brand voice consistency throughout all sections
• Natural keyword integration meeting density targets
• Engaging, valuable content that serves the target audience
• Professional formatting and structure

BRAND VOICE ADAPTATION:
• Analyze provided style guides and language codes
• Adapt sentence structure, vocabulary, and tone accordingly
• Maintain personality traits and communication values
• Follow formality levels and vocabulary preferences
• Ensure content reflects brand's unique voice characteristics

You have access to project knowledge base containing brand guidelines, style analysis results, and content samples. Use this information to create content that perfectly matches the client's established voice and style.

Project ID: {self.project_id or 'Not specified'}
"""
        
        return BaseMessage.make_assistant_message(
            role_name="content_generator",
            content=content
        )
    
    async def generate_content(self, 
                             content_plan: Dict[str, Any],
                             style_guide: Optional[Dict[str, Any]] = None) -> GeneratedContent:
        """
        Generate complete content following the provided plan and style guide
        
        Args:
            content_plan: Detailed content plan from Content Planner
            style_guide: Optional style guide from Style Analyzer
            
        Returns:
            Complete GeneratedContent object
        """
        self.logger.info(f"Generating content: {content_plan.get('title', 'Untitled')}")
        
        try:
            # Extract generation parameters
            title = content_plan.get('title', 'Untitled Content')
            content_type = content_plan.get('content_type', 'blog_post')
            outline = content_plan.get('content_outline', [])
            seo_strategy = content_plan.get('seo_strategy', {})
            brand_voice = content_plan.get('brand_voice_integration', {})
            
            # Merge style guide information
            if style_guide:
                brand_voice = self._merge_brand_voice_data(brand_voice, style_guide)
            
            # Generate each content section
            generated_sections = []
            for section_plan in outline:
                section = await self._generate_section(section_plan, brand_voice, seo_strategy)
                generated_sections.append(section)
            
            # Combine sections into full content
            full_content = await self._combine_sections(generated_sections, content_type)
            
            # Analyze generated content
            seo_analysis = await self._analyze_seo_performance(full_content, seo_strategy)
            brand_voice_analysis = await self._analyze_brand_voice_consistency(full_content, brand_voice)
            quality_scores = await self._calculate_quality_scores(full_content, content_plan)
            
            # Calculate total word count
            total_words = sum(section.word_count for section in generated_sections)
            
            # Create generation metadata
            generation_metadata = {
                "generated_at": datetime.now().isoformat(),
                "generation_time": "Generated in real-time",
                "model_used": "CAMEL ChatAgent",
                "project_id": self.project_id,
                "style_guide_applied": style_guide is not None
            }
            
            # Create comprehensive result
            generated_content = GeneratedContent(
                title=title,
                content_type=content_type,
                sections=generated_sections,
                full_content=full_content,
                total_word_count=total_words,
                seo_analysis=seo_analysis,
                brand_voice_analysis=brand_voice_analysis,
                quality_scores=quality_scores,
                generation_metadata=generation_metadata
            )
            
            # Store in knowledge base if available
            if self.knowledge_base:
                await self._store_generated_content(generated_content)
            
            self.logger.info(f"Content generation completed: {total_words} words, quality score: {quality_scores.get('overall', 0):.2f}")
            
            return generated_content
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise
    
    def _merge_brand_voice_data(self, 
                               plan_voice_data: Dict[str, Any],
                               style_guide: Dict[str, Any]) -> Dict[str, Any]:
        """Merge brand voice data from content plan and style guide"""
        
        merged = plan_voice_data.copy()
        
        # Extract from style guide
        if 'brand_voice_elements' in style_guide:
            elements = style_guide['brand_voice_elements']
            merged.update({
                'personality_traits': elements.get('personality_traits', []),
                'communication_values': elements.get('communication_values', []),
                'persuasion_techniques': elements.get('persuasion_techniques', [])
            })
        
        if 'implementation_guidelines' in style_guide:
            guidelines = style_guide['implementation_guidelines']
            
            # Extract language code parameters
            if 'language_formality' in guidelines:
                formality = guidelines['language_formality'].replace('LF=', '')
                merged['formality_level'] = int(formality) if formality.isdigit() else 3
            
            if 'vocabulary_level' in guidelines:
                vocab = guidelines['vocabulary_level'].replace('VL=', '')
                merged['vocabulary_level'] = int(vocab) if vocab.isdigit() else 5
        
        return merged
    
    async def _generate_section(self, 
                              section_plan: Dict[str, Any],
                              brand_voice: Dict[str, Any],
                              seo_strategy: Dict[str, Any]) -> ContentSection:
        """Generate content for a single section"""
        
        section_title = section_plan.get('title', 'Untitled Section')
        description = section_plan.get('description', '')
        objectives = section_plan.get('objectives', [])
        keywords = section_plan.get('keywords', [])
        target_word_count = section_plan.get('estimated_word_count', 200)
        tone_guidance = section_plan.get('tone_guidance', '')
        
        self.logger.debug(f"Generating section: {section_title}")
        
        try:
            # Create generation prompt
            generation_prompt = self._create_section_prompt(
                section_title, description, objectives, keywords, 
                target_word_count, tone_guidance, brand_voice
            )
            
            # Generate content using LLM
            response = self.step(generation_prompt)
            section_content = response.msg.content if hasattr(response.msg, 'content') else str(response)
            
            # Clean and format content
            section_content = self._clean_generated_content(section_content)
            
            # Analyze section
            actual_word_count = len(section_content.split())
            keywords_used = self._extract_keywords_used(section_content, keywords)
            tone_score = await self._evaluate_tone_adherence(section_content, tone_guidance, brand_voice)
            
            # Handle subsections if they exist
            subsections = []
            if 'subsections' in section_plan:
                for subsection_plan in section_plan['subsections']:
                    subsection = await self._generate_section(subsection_plan, brand_voice, seo_strategy)
                    subsections.append(subsection)
                    # Add subsection content to main section content
                    section_content += f"\n\n### {subsection.title}\n\n{subsection.content}"
                    actual_word_count += subsection.word_count
                    keywords_used.extend(subsection.keywords_used)
            
            return ContentSection(
                title=section_title,
                content=section_content,
                word_count=actual_word_count,
                keywords_used=list(set(keywords_used)),  # Remove duplicates
                tone_adherence_score=tone_score,
                subsections=subsections if subsections else None
            )
            
        except Exception as e:
            self.logger.error(f"Section generation failed for {section_title}: {e}")
            # Return fallback section
            return ContentSection(
                title=section_title,
                content=f"Content generation failed for {section_title}. Please regenerate this section.",
                word_count=0,
                keywords_used=[],
                tone_adherence_score=0.0
            )
    
    def _create_section_prompt(self, 
                              title: str,
                              description: str,
                              objectives: List[str],
                              keywords: List[str],
                              target_word_count: int,
                              tone_guidance: str,
                              brand_voice: Dict[str, Any]) -> str:
        """Create detailed prompt for section generation"""
        
        # Extract brand voice characteristics
        personality_traits = brand_voice.get('personality_traits', [])
        formality_level = brand_voice.get('formality_level', 3)
        vocabulary_level = brand_voice.get('vocabulary_level', 5)
        tone = brand_voice.get('tone', 'professional')
        
        # Get style template based on tone
        style_template = self.style_templates.get(tone, self.style_templates['professional'])
        
        prompt = f"""
Generate a {target_word_count}-word section titled "{title}" for content creation.

SECTION REQUIREMENTS:
Description: {description}

Objectives:
{chr(10).join(f"• {obj}" for obj in objectives)}

TARGET KEYWORDS TO INTEGRATE NATURALLY:
{', '.join(keywords) if keywords else 'No specific keywords'}

BRAND VOICE GUIDELINES:
• Tone: {tone.title()}
• Formality Level: {formality_level}/10 (1=very casual, 10=very formal)
• Vocabulary Level: {vocabulary_level}/10 (1=simple, 10=advanced)
• Personality Traits: {', '.join(personality_traits[:3]) if personality_traits else 'Professional, helpful'}

TONE GUIDANCE:
{tone_guidance}

STYLE PREFERENCES:
• Use sentence starters like: {', '.join(style_template['sentence_starters'][:3])}
• Connect ideas with: {', '.join(style_template['connectors'][:3])}
• Vocabulary level: {style_template['vocabulary_level']}

CONTENT GENERATION INSTRUCTIONS:
1. Create engaging, original content that perfectly matches the brand voice
2. Integrate keywords naturally - they should feel like a natural part of the writing
3. Follow the tone guidance precisely
4. Meet the word count target (±20 words is acceptable)
5. Ensure content serves the stated objectives
6. Write in a way that flows naturally and engages the target audience
7. Use proper formatting with paragraphs and subheadings as appropriate
8. Include specific examples or details where relevant
9. End sections with smooth transitions or strong conclusions as appropriate

Generate the content now, focusing on quality, brand voice consistency, and natural keyword integration:
"""
        
        return prompt
    
    def _clean_generated_content(self, content: str) -> str:
        """Clean and format generated content"""
        
        # Remove common AI-generated prefixes/suffixes
        prefixes_to_remove = [
            "Here's the content:",
            "Here is the content:",
            "Content:",
            "Generated content:",
            "Section content:"
        ]
        
        for prefix in prefixes_to_remove:
            if content.strip().startswith(prefix):
                content = content.replace(prefix, "").strip()
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Fix common formatting issues
        content = content.strip()
        
        return content
    
    def _extract_keywords_used(self, content: str, target_keywords: List[str]) -> List[str]:
        """Extract which target keywords were actually used in the content"""
        
        used_keywords = []
        content_lower = content.lower()
        
        for keyword in target_keywords:
            if keyword.lower() in content_lower:
                used_keywords.append(keyword)
                
        return used_keywords
    
    async def _evaluate_tone_adherence(self, 
                                     content: str,
                                     tone_guidance: str,
                                     brand_voice: Dict[str, Any]) -> float:
        """Evaluate how well content adheres to tone guidelines"""
        
        try:
            # Simple tone evaluation based on word choice and sentence structure
            score = 0.0
            
            # Check formality level
            formality_level = brand_voice.get('formality_level', 3)
            formal_indicators = ['furthermore', 'moreover', 'consequently', 'therefore', 'subsequently']
            casual_indicators = ['you\'ll', 'here\'s', 'let\'s', 'don\'t', 'can\'t']
            
            content_lower = content.lower()
            formal_count = sum(1 for indicator in formal_indicators if indicator in content_lower)
            casual_count = sum(1 for indicator in casual_indicators if indicator in content_lower)
            
            # Score based on formality match
            if formality_level >= 7:  # Very formal
                score += 0.3 if formal_count > casual_count else 0.1
            elif formality_level <= 3:  # Very casual  
                score += 0.3 if casual_count > formal_count else 0.1
            else:  # Balanced
                score += 0.3
            
            # Check for personality traits
            personality_traits = brand_voice.get('personality_traits', [])
            if personality_traits:
                # Simple check for trait-related words
                trait_matches = 0
                for trait in personality_traits[:3]:
                    if trait.lower() in content_lower:
                        trait_matches += 1
                score += (trait_matches / len(personality_traits[:3])) * 0.3
            else:
                score += 0.3
            
            # Check vocabulary level
            vocabulary_level = brand_voice.get('vocabulary_level', 5)
            words = content.split()
            complex_words = [word for word in words if len(word) > 7]
            complex_ratio = len(complex_words) / len(words) if words else 0
            
            if vocabulary_level >= 7:  # Advanced vocabulary expected
                score += 0.4 if complex_ratio > 0.15 else 0.2
            elif vocabulary_level <= 3:  # Simple vocabulary expected
                score += 0.4 if complex_ratio < 0.08 else 0.2
            else:  # Moderate vocabulary
                score += 0.4 if 0.08 <= complex_ratio <= 0.15 else 0.2
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.warning(f"Tone evaluation failed: {e}")
            return 0.7  # Return neutral score on failure
    
    async def _combine_sections(self, 
                              sections: List[ContentSection],
                              content_type: str) -> str:
        """Combine sections into cohesive full content"""
        
        combined_content = ""
        
        for i, section in enumerate(sections):
            # Add section title as header
            if content_type in ['blog_post', 'whitepaper', 'case_study']:
                # Use H2 headers for main sections
                combined_content += f"## {section.title}\n\n"
            elif content_type in ['landing_page', 'web_copy']:
                # Use different formatting for landing pages
                if i == 0:  # First section (hero)
                    combined_content += f"# {section.title}\n\n"
                else:
                    combined_content += f"## {section.title}\n\n"
            else:
                # Default formatting
                combined_content += f"**{section.title}**\n\n"
            
            # Add section content
            combined_content += section.content + "\n\n"
            
            # Add subsections if they exist
            if section.subsections:
                for subsection in section.subsections:
                    combined_content += f"### {subsection.title}\n\n"
                    combined_content += subsection.content + "\n\n"
        
        # Clean up excessive whitespace
        combined_content = re.sub(r'\n\s*\n\s*\n', '\n\n', combined_content)
        
        return combined_content.strip()
    
    async def _analyze_seo_performance(self, 
                                     content: str,
                                     seo_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SEO performance of generated content"""
        
        analysis = {
            "keyword_density": {},
            "keyword_distribution": {},
            "seo_score": 0.0,
            "recommendations": []
        }
        
        try:
            content_lower = content.lower()
            word_count = len(content.split())
            
            # Analyze primary keywords
            primary_keywords = seo_strategy.get('primary_keywords', [])
            for keyword in primary_keywords:
                keyword_count = content_lower.count(keyword.lower())
                density = (keyword_count / word_count) if word_count > 0 else 0
                analysis["keyword_density"][keyword] = {
                    "count": keyword_count,
                    "density": density,
                    "target_density": 0.015,  # 1.5% target
                    "meets_target": 0.01 <= density <= 0.02
                }
            
            # Analyze secondary keywords
            secondary_keywords = seo_strategy.get('secondary_keywords', [])
            for keyword in secondary_keywords:
                keyword_count = content_lower.count(keyword.lower())
                density = (keyword_count / word_count) if word_count > 0 else 0
                analysis["keyword_density"][keyword] = {
                    "count": keyword_count,
                    "density": density,
                    "target_density": 0.01,  # 1% target
                    "meets_target": 0.005 <= density <= 0.015
                }
            
            # Calculate overall SEO score
            keyword_scores = []
            for keyword_data in analysis["keyword_density"].values():
                if keyword_data["meets_target"]:
                    keyword_scores.append(1.0)
                elif keyword_data["count"] > 0:
                    keyword_scores.append(0.5)
                else:
                    keyword_scores.append(0.0)
            
            analysis["seo_score"] = sum(keyword_scores) / len(keyword_scores) if keyword_scores else 0.0
            
            # Generate recommendations
            recommendations = []
            for keyword, data in analysis["keyword_density"].items():
                if data["count"] == 0:
                    recommendations.append(f"Add '{keyword}' to the content")
                elif data["density"] < 0.005:
                    recommendations.append(f"Increase usage of '{keyword}' (current: {data['density']:.1%})")
                elif data["density"] > 0.025:
                    recommendations.append(f"Reduce usage of '{keyword}' (current: {data['density']:.1%})")
            
            if not recommendations:
                recommendations.append("SEO keyword integration looks good!")
            
            analysis["recommendations"] = recommendations
            
        except Exception as e:
            self.logger.error(f"SEO analysis failed: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_brand_voice_consistency(self, 
                                             content: str,
                                             brand_voice: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze brand voice consistency in generated content"""
        
        analysis = {
            "consistency_score": 0.0,
            "tone_match": 0.0,
            "formality_match": 0.0,
            "vocabulary_match": 0.0,
            "personality_match": 0.0,
            "recommendations": []
        }
        
        try:
            # Analyze tone consistency
            tone = brand_voice.get('tone', 'professional')
            tone_score = await self._evaluate_tone_adherence(content, f"Use {tone} tone", brand_voice)
            analysis["tone_match"] = tone_score
            
            # Analyze formality level
            formality_level = brand_voice.get('formality_level', 3)
            formality_score = self._evaluate_formality_match(content, formality_level)
            analysis["formality_match"] = formality_score
            
            # Analyze vocabulary complexity
            vocabulary_level = brand_voice.get('vocabulary_level', 5)
            vocabulary_score = self._evaluate_vocabulary_match(content, vocabulary_level)
            analysis["vocabulary_match"] = vocabulary_score
            
            # Analyze personality traits
            personality_traits = brand_voice.get('personality_traits', [])
            personality_score = self._evaluate_personality_match(content, personality_traits)
            analysis["personality_match"] = personality_score
            
            # Calculate overall consistency score
            scores = [tone_score, formality_score, vocabulary_score, personality_score]
            analysis["consistency_score"] = sum(scores) / len(scores)
            
            # Generate recommendations
            recommendations = []
            if tone_score < 0.7:
                recommendations.append(f"Improve {tone} tone consistency")
            if formality_score < 0.7:
                recommendations.append(f"Adjust formality to level {formality_level}/10")
            if vocabulary_score < 0.7:
                recommendations.append(f"Adjust vocabulary complexity to level {vocabulary_level}/10")
            if personality_score < 0.7 and personality_traits:
                recommendations.append(f"Better incorporate personality traits: {', '.join(personality_traits[:2])}")
            
            if not recommendations:
                recommendations.append("Brand voice consistency is excellent!")
            
            analysis["recommendations"] = recommendations
            
        except Exception as e:
            self.logger.error(f"Brand voice analysis failed: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def _evaluate_formality_match(self, content: str, target_formality: int) -> float:
        """Evaluate formality level match"""
        
        content_lower = content.lower()
        
        # Formal indicators
        formal_indicators = [
            'furthermore', 'moreover', 'consequently', 'therefore', 'subsequently',
            'nevertheless', 'accordingly', 'additionally', 'specifically', 'particularly'
        ]
        
        # Casual indicators
        casual_indicators = [
            "you'll", "here's", "let's", "don't", "can't", "won't", "we're",
            "that's", "it's", "what's", "how's", "there's"
        ]
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in content_lower)
        casual_count = sum(1 for indicator in casual_indicators if indicator in content_lower)
        
        total_sentences = len([s for s in content.split('.') if s.strip()])
        formal_ratio = formal_count / max(total_sentences, 1)
        casual_ratio = casual_count / max(total_sentences, 1)
        
        if target_formality >= 7:  # Very formal expected
            return min(1.0, formal_ratio * 2) * 0.7 + (0.3 if casual_ratio < 0.1 else 0.1)
        elif target_formality <= 3:  # Very casual expected
            return min(1.0, casual_ratio * 2) * 0.7 + (0.3 if formal_ratio < 0.05 else 0.1)
        else:  # Balanced
            balance_score = 1.0 - abs(formal_ratio - casual_ratio)
            return max(0.5, balance_score)
    
    def _evaluate_vocabulary_match(self, content: str, target_vocabulary: int) -> float:
        """Evaluate vocabulary complexity match"""
        
        words = [word.strip('.,!?;:"()[]') for word in content.split()]
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        # Calculate metrics
        long_words = [word for word in words if len(word) > 6]
        very_long_words = [word for word in words if len(word) > 10]
        
        long_word_ratio = len(long_words) / total_words
        very_long_word_ratio = len(very_long_words) / total_words
        avg_word_length = sum(len(word) for word in words) / total_words
        
        # Score based on target vocabulary level
        if target_vocabulary >= 8:  # Very advanced
            score = 0.0
            if long_word_ratio > 0.2:
                score += 0.4
            if very_long_word_ratio > 0.05:
                score += 0.3
            if avg_word_length > 5.5:
                score += 0.3
        elif target_vocabulary <= 3:  # Very simple
            score = 0.0
            if long_word_ratio < 0.1:
                score += 0.4
            if very_long_word_ratio < 0.02:
                score += 0.3
            if avg_word_length < 4.5:
                score += 0.3
        else:  # Moderate
            score = 0.0
            if 0.1 <= long_word_ratio <= 0.2:
                score += 0.4
            if 0.02 <= very_long_word_ratio <= 0.05:
                score += 0.3
            if 4.5 <= avg_word_length <= 5.5:
                score += 0.3
        
        return min(score, 1.0)
    
    def _evaluate_personality_match(self, content: str, personality_traits: List[str]) -> float:
        """Evaluate personality traits expression"""
        
        if not personality_traits:
            return 1.0  # No traits to match
        
        content_lower = content.lower()
        trait_indicators = {
            'helpful': ['help', 'assist', 'support', 'guide', 'tip', 'advice'],
            'friendly': ['welcome', 'great', 'awesome', 'wonderful', 'excited'],
            'professional': ['experience', 'expertise', 'solution', 'approach', 'strategy'],
            'authoritative': ['research', 'data', 'study', 'proven', 'evidence'],
            'innovative': ['new', 'cutting-edge', 'advanced', 'breakthrough', 'revolutionary'],
            'trustworthy': ['reliable', 'proven', 'trusted', 'guarantee', 'secure'],
            'approachable': ['easy', 'simple', 'straightforward', 'accessible', 'clear']
        }
        
        matches = 0
        for trait in personality_traits[:3]:  # Check top 3 traits
            trait_lower = trait.lower()
            if trait_lower in trait_indicators:
                indicators = trait_indicators[trait_lower]
                if any(indicator in content_lower for indicator in indicators):
                    matches += 1
            else:
                # Direct trait word check
                if trait_lower in content_lower:
                    matches += 1
        
        return matches / min(len(personality_traits), 3)
    
    async def _calculate_quality_scores(self, 
                                      content: str,
                                      content_plan: Dict[str, Any]) -> Dict[str, float]:
        """Calculate various quality scores for the content"""
        
        scores = {
            "overall": 0.0,
            "readability": 0.0,
            "engagement": 0.0,
            "completeness": 0.0,
            "originality": 0.0
        }
        
        try:
            # Readability score (simple metrics)
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            words = content.split()
            
            if len(sentences) > 0 and len(words) > 0:
                avg_sentence_length = len(words) / len(sentences)
                # Good readability: 15-20 words per sentence
                if 10 <= avg_sentence_length <= 25:
                    scores["readability"] = 0.9
                elif 8 <= avg_sentence_length <= 30:
                    scores["readability"] = 0.7
                else:
                    scores["readability"] = 0.5
            
            # Engagement score (based on content elements)
            engagement_indicators = [
                '?',  # Questions engage readers
                '!',  # Exclamations show energy
                'you', 'your',  # Direct address
                'how', 'why', 'what',  # Question words
                'tip', 'secret', 'discover'  # Engaging words
            ]
            
            content_lower = content.lower()
            engagement_count = sum(1 for indicator in engagement_indicators if indicator in content_lower)
            scores["engagement"] = min(1.0, engagement_count / 10)
            
            # Completeness score (based on meeting word count targets)
            target_words = content_plan.get('estimated_total_words', 1000)
            actual_words = len(words)
            word_ratio = actual_words / target_words if target_words > 0 else 0
            
            if 0.8 <= word_ratio <= 1.2:  # Within 20% of target
                scores["completeness"] = 1.0
            elif 0.6 <= word_ratio <= 1.4:  # Within 40% of target
                scores["completeness"] = 0.8
            else:
                scores["completeness"] = 0.6
            
            # Originality score (simple uniqueness check)
            unique_words = len(set(word.lower() for word in words))
            uniqueness_ratio = unique_words / len(words) if len(words) > 0 else 0
            scores["originality"] = min(1.0, uniqueness_ratio * 2)
            
            # Calculate overall score
            scores["overall"] = sum(scores.values()) / (len(scores) - 1)  # Exclude overall from calculation
            
        except Exception as e:
            self.logger.error(f"Quality score calculation failed: {e}")
            # Return default scores
            scores = {k: 0.7 for k in scores.keys()}
        
        return scores
    
    async def _store_generated_content(self, generated_content: GeneratedContent):
        """Store generated content in knowledge base"""
        try:
            content_data = {
                "title": f"Generated Content: {generated_content.title}",
                "type": "generated_content",
                "content": generated_content.full_content,
                "metadata": {
                    "content_type": generated_content.content_type,
                    "word_count": generated_content.total_word_count,
                    "quality_scores": generated_content.quality_scores,
                    "seo_analysis": generated_content.seo_analysis,
                    "brand_voice_analysis": generated_content.brand_voice_analysis,
                    "generated_at": generated_content.generation_metadata["generated_at"]
                }
            }
            
            await self.knowledge_base.store_document(content_data)
            self.logger.info(f"Generated content stored in knowledge base: {generated_content.title}")
            
        except Exception as e:
            self.logger.error(f"Failed to store generated content: {e}")
    
    async def refine_content_section(self, 
                                   section_content: str,
                                   refinement_instructions: str,
                                   brand_voice: Dict[str, Any]) -> str:
        """Refine a specific content section based on feedback"""
        
        refinement_prompt = f"""
Refine the following content section based on the provided instructions while maintaining brand voice consistency.

CURRENT CONTENT:
{section_content}

REFINEMENT INSTRUCTIONS:
{refinement_instructions}

BRAND VOICE GUIDELINES:
• Tone: {brand_voice.get('tone', 'professional')}
• Formality Level: {brand_voice.get('formality_level', 3)}/10
• Vocabulary Level: {brand_voice.get('vocabulary_level', 5)}/10
• Personality Traits: {', '.join(brand_voice.get('personality_traits', [])[:3])}

REFINEMENT REQUIREMENTS:
1. Address all points in the refinement instructions
2. Maintain the established brand voice and tone
3. Keep the core message and value intact
4. Improve clarity, engagement, and readability
5. Ensure smooth flow and natural transitions
6. Preserve any important keywords or key phrases

Provide the refined content:
"""
        
        try:
            response = self.step(refinement_prompt)
            refined_content = response.msg.content if hasattr(response.msg, 'content') else str(response)
            return self._clean_generated_content(refined_content)
            
        except Exception as e:
            self.logger.error(f"Content refinement failed: {e}")
            return section_content  # Return original content if refinement fails
    
    async def generate_content_variations(self, 
                                        content: str,
                                        num_variations: int = 3,
                                        brand_voice: Dict[str, Any] = None) -> List[str]:
        """Generate multiple variations of content for A/B testing"""
        
        variations = []
        
        for i in range(num_variations):
            variation_prompt = f"""
Create a variation of the following content that maintains the same core message but with different phrasing, structure, or approach.

ORIGINAL CONTENT:
{content}

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
                variation = response.msg.content if hasattr(response.msg, 'content') else str(response)
                variations.append(self._clean_generated_content(variation))
                
            except Exception as e:
                self.logger.error(f"Variation {i+1} generation failed: {e}")
                continue
        
        return variations
    
    def process_task(self, task):
        """Process generation task - legacy method for backwards compatibility"""
        response = self.step(task)
        return response


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
    'GeneratedContent',
    'ContentSection',
    'create_content_generator_agent'
]