# app/agents/specialized/style_analyzer.py
"""
Production Style Analyzer Agent for SpinScribe - Integrated Version
Uses the existing ProductionStyleAnalyzer with workflow integration

This integrates your excellent ProductionStyleAnalyzer into the CAMEL workflow system.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig

# Import your existing production-grade analyzer
from app.knowledge.analyzers.style_analyzer import (
    ProductionStyleAnalyzer,
    create_style_analyzer,
    StyleProfile,
    LanguageCode
)
from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.database.models.knowledge_item import KnowledgeItem

# Set up logging
logger = logging.getLogger(__name__)

class ProductionStyleAnalyzerAgent:
    """
    Production-ready Style Analyzer Agent that wraps your existing analyzer
    and integrates it into the CAMEL workflow system.
    
    This agent serves as the interface between the coordinator workflow
    and your comprehensive ProductionStyleAnalyzer.
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize CAMEL agent for communication
        self.agent = self._initialize_camel_agent()
        
        # Initialize your production analyzer (lazy loading)
        self._analyzer = None
        
        # Cache for analysis results
        self.analysis_cache: Dict[str, StyleProfile] = {}
        
        self.logger.info(f"Style Analyzer Agent initialized for project: {project_id}")
    
    def _initialize_camel_agent(self) -> ChatAgent:
        """Initialize CAMEL agent for workflow communication"""
        try:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                model_config_dict=ChatGPTConfig(
                    temperature=0.1,
                    max_tokens=2000
                ).as_dict()
            )
            
            system_message = BaseMessage.make_assistant_message(
                role_name="Brand Voice & Style Analyst",
                content=f"""
                You are the Style Analyzer Agent for SpinScribe, integrating advanced style analysis
                into the content creation workflow.
                
                CORE CAPABILITIES:
                • Multi-model linguistic analysis (spaCy + transformers + statistical)
                • Comprehensive brand voice extraction and characterization
                • Dynamic language code generation compatible with existing format
                • Style consistency validation and recommendations
                • Integration with project knowledge base and workflow system

                PROJECT CONTEXT: {self.project_id or "General Analysis"}
                
                WORKFLOW INTEGRATION:
                • Receive analysis requests from coordinator agent
                • Process content samples using production-grade analyzer
                • Return structured results for downstream workflow steps
                • Store analysis results in project knowledge base
                • Provide style consistency validation for new content

                You leverage the most advanced NLP techniques while maintaining
                seamless integration with the broader content creation workflow.
                """
            )
            
            agent = ChatAgent(
                system_message=system_message,
                model=model,
                message_window_size=30
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CAMEL agent: {e}")
            raise
    
    async def _get_analyzer(self) -> ProductionStyleAnalyzer:
        """Lazy initialization of the production analyzer"""
        if self._analyzer is None:
            self._analyzer = await create_style_analyzer(self.project_id)
        return self._analyzer
    
    async def analyze_style(self, 
                          content_samples: List[str],
                          analysis_depth: str = "comprehensive") -> Dict[str, Any]:
        """
        Main entry point for style analysis (called by coordinator)
        
        Args:
            content_samples: List of content strings to analyze
            analysis_depth: Level of analysis (quick, standard, comprehensive)
            
        Returns:
            Formatted analysis results for workflow system
        """
        try:
            if not content_samples:
                raise ValueError("No content samples provided for analysis")
            
            self.logger.info(f"Starting style analysis for {len(content_samples)} samples")
            
            # Get the production analyzer
            analyzer = await self._get_analyzer()
            
            # Run comprehensive analysis using your existing system
            style_profile = await analyzer.analyze_content_corpus(content_samples)
            
            # Cache the results
            self.analysis_cache[style_profile.analysis_id] = style_profile
            
            # Format results for workflow system
            formatted_results = await self._format_workflow_results(style_profile)
            
            self.logger.info(f"Analysis completed: {style_profile.analysis_id}")
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Style analysis failed: {e}")
            raise
    
    async def _format_workflow_results(self, style_profile: StyleProfile) -> Dict[str, Any]:
        """Format analysis results for the workflow system"""
        
        # Extract key insights for workflow decisions
        key_insights = {
            "language_code": style_profile.language_code.to_code_string(),
            "primary_tone": style_profile.llm_insights.voice_characteristics.get('primary_voice', 'professional'),
            "formality_level": style_profile.language_code.language_formality,
            "audience": style_profile.language_code.audience,
            "expertise_level": style_profile.llm_insights.expertise_level,
            "confidence_score": style_profile.analysis_confidence
        }
        
        # Create actionable recommendations
        recommendations = await self._generate_workflow_recommendations(style_profile)
        
        # Return structured results
        return {
            "analysis_id": style_profile.analysis_id,
            "analysis_type": "comprehensive_style_analysis",
            "status": "completed",
            "confidence_score": style_profile.analysis_confidence,
            
            # Key insights for workflow decisions
            "key_insights": key_insights,
            
            # Detailed analysis results
            "detailed_analysis": {
                "linguistic_features": {
                    "readability_score": style_profile.linguistic_features.flesch_reading_ease,
                    "grade_level": style_profile.linguistic_features.flesch_kincaid_grade,
                    "avg_sentence_length": style_profile.linguistic_features.avg_sentence_length,
                    "vocabulary_richness": style_profile.linguistic_features.vocabulary_richness,
                    "complexity_ratio": style_profile.linguistic_features.complex_sentence_ratio
                },
                
                "semantic_features": {
                    "primary_themes": style_profile.semantic_features.primary_themes,
                    "topic_consistency": style_profile.semantic_features.topic_consistency,
                    "semantic_coherence": style_profile.semantic_features.semantic_coherence,
                    "theme_distribution": style_profile.semantic_features.theme_distribution
                },
                
                "voice_characteristics": {
                    "tone_analysis": style_profile.llm_insights.tone_analysis,
                    "personality_traits": style_profile.llm_insights.personality_traits,
                    "communication_style": style_profile.llm_insights.engagement_style,
                    "persuasion_techniques": style_profile.llm_insights.persuasion_techniques
                }
            },
            
            # Language code for content generation
            "language_code": {
                "code_string": style_profile.language_code.to_code_string(),
                "parameters": {
                    "content_focus": style_profile.language_code.content_focus,
                    "formality": style_profile.language_code.language_formality,
                    "vocabulary_level": style_profile.language_code.vocabulary_level,
                    "subject_expertise": style_profile.language_code.subject_expertise,
                    "audience": style_profile.language_code.audience,
                    "tone": style_profile.language_code.tone
                }
            },
            
            # Style guide for content creation
            "style_guide": style_profile.style_guide,
            
            # Actionable recommendations
            "recommendations": recommendations,
            
            # Metadata
            "metadata": {
                "samples_analyzed": style_profile.content_samples_analyzed,
                "total_word_count": style_profile.total_word_count,
                "created_at": style_profile.created_at.isoformat(),
                "project_id": self.project_id
            }
        }
    
    async def _generate_workflow_recommendations(self, style_profile: StyleProfile) -> List[str]:
        """Generate recommendations for the workflow system"""
        recommendations = []
        
        # Confidence-based recommendations
        if style_profile.analysis_confidence < 0.6:
            recommendations.append("Consider providing more content samples for higher confidence analysis")
        
        # Readability recommendations
        if style_profile.linguistic_features.flesch_reading_ease < 30:
            recommendations.append("Content has low readability - consider simplifying language for broader audience")
        elif style_profile.linguistic_features.flesch_reading_ease > 90:
            recommendations.append("Content is very easy to read - consider adding more sophisticated language if targeting experts")
        
        # Consistency recommendations
        if style_profile.semantic_features.topic_consistency < 0.5:
            recommendations.append("Low topic consistency detected - ensure content stays focused on main themes")
        
        # Voice recommendations
        formality = style_profile.language_code.language_formality
        if formality >= 4 and 'casual' in style_profile.llm_insights.personality_traits:
            recommendations.append("Mismatch between formal language and casual personality - consider adjusting tone")
        
        # Audience alignment
        if style_profile.llm_insights.expertise_level == 'advanced' and style_profile.linguistic_features.flesch_reading_ease > 70:
            recommendations.append("Content may be too simple for the advanced expertise level detected")
        
        return recommendations
    
    async def validate_content_consistency(self, 
                                         content: str,
                                         reference_analysis_id: str = None) -> Dict[str, Any]:
        """
        Validate new content against established style patterns
        
        Args:
            content: New content to validate
            reference_analysis_id: ID of reference analysis (latest if not provided)
            
        Returns:
            Style consistency validation results
        """
        try:
            # Get reference analysis
            if reference_analysis_id and reference_analysis_id in self.analysis_cache:
                reference_profile = self.analysis_cache[reference_analysis_id]
            else:
                # Get the most recent analysis
                if not self.analysis_cache:
                    raise ValueError("No reference analysis available")
                reference_profile = max(self.analysis_cache.values(), key=lambda x: x.created_at)
            
            # Use your existing consistency scoring
            analyzer = await self._get_analyzer()
            consistency_score = await analyzer.get_style_consistency_score(content, reference_profile)
            
            # Generate detailed feedback
            feedback = await self._generate_consistency_feedback(consistency_score, reference_profile)
            
            return {
                "consistency_score": consistency_score,
                "reference_analysis_id": reference_profile.analysis_id,
                "validation_status": "passed" if consistency_score >= 0.7 else "needs_revision",
                "feedback": feedback,
                "recommendations": await self._generate_consistency_recommendations(consistency_score),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Consistency validation failed: {e}")
            raise
    
    async def _generate_consistency_feedback(self, 
                                           consistency_score: float,
                                           reference_profile: StyleProfile) -> str:
        """Generate human-readable consistency feedback"""
        
        if consistency_score >= 0.9:
            return "Excellent consistency with established brand voice"
        elif consistency_score >= 0.8:
            return "Good consistency with minor variations in style"
        elif consistency_score >= 0.7:
            return "Acceptable consistency with some notable differences"
        elif consistency_score >= 0.5:
            return "Moderate consistency - style differs significantly in some areas"
        else:
            return "Low consistency - content does not match established brand voice"
    
    async def _generate_consistency_recommendations(self, consistency_score: float) -> List[str]:
        """Generate recommendations based on consistency score"""
        
        if consistency_score >= 0.8:
            return ["Content maintains good brand voice consistency", "Ready for review or publication"]
        elif consistency_score >= 0.6:
            return [
                "Minor adjustments needed to improve brand voice alignment",
                "Review sentence structure and vocabulary choices",
                "Consider referencing established style guide"
            ]
        else:
            return [
                "Significant revision needed to align with brand voice",
                "Review language code parameters and style guidelines",
                "Consider rewriting sections that deviate most from established patterns",
                "Consult with content strategist for brand voice alignment"
            ]
    
    async def get_style_guidelines(self, analysis_id: str = None) -> Dict[str, Any]:
        """
        Get comprehensive style guidelines based on analysis
        
        Args:
            analysis_id: Specific analysis ID (latest if not provided)
            
        Returns:
            Comprehensive style guidelines for content creation
        """
        try:
            # Get analysis
            if analysis_id and analysis_id in self.analysis_cache:
                style_profile = self.analysis_cache[analysis_id]
            else:
                if not self.analysis_cache:
                    raise ValueError("No analysis available")
                style_profile = max(self.analysis_cache.values(), key=lambda x: x.created_at)
            
            # Your existing style guide is already comprehensive, so we'll use it
            # and add some workflow-specific elements
            guidelines = style_profile.style_guide.copy()
            
            # Add workflow-specific guidance
            guidelines["workflow_integration"] = {
                "language_code_reference": style_profile.language_code.to_code_string(),
                "content_generation_parameters": {
                    "target_sentence_length": f"{style_profile.linguistic_features.avg_sentence_length:.0f} words",
                    "formality_level": style_profile.language_code.language_formality,
                    "vocabulary_complexity": style_profile.language_code.vocabulary_level,
                    "persuasiveness": style_profile.language_code.persuasiveness
                },
                "quality_thresholds": {
                    "consistency_minimum": 0.7,
                    "readability_range": [30, 80],  # Flesch Reading Ease
                    "confidence_minimum": 0.6
                }
            }
            
            return {
                "analysis_id": style_profile.analysis_id,
                "guidelines": guidelines,
                "created_at": style_profile.created_at.isoformat(),
                "confidence_score": style_profile.analysis_confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get style guidelines: {e}")
            raise
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of all analyses performed"""
        return {
            "total_analyses": len(self.analysis_cache),
            "analyses": [
                {
                    "analysis_id": profile.analysis_id,
                    "created_at": profile.created_at.isoformat(),
                    "confidence_score": profile.analysis_confidence,
                    "samples_analyzed": profile.content_samples_analyzed,
                    "primary_tone": profile.llm_insights.voice_characteristics.get('primary_voice', 'unknown'),
                    "language_code": profile.language_code.to_code_string()
                }
                for profile in sorted(self.analysis_cache.values(), 
                                    key=lambda x: x.created_at, reverse=True)
            ]
        }

# Backwards compatibility wrapper
class styleanalyzerAgent(ProductionStyleAnalyzerAgent):
    """Backwards compatibility wrapper for existing code"""
    pass

# Factory function for easy instantiation
async def create_style_analyzer_agent(project_id: str = None) -> ProductionStyleAnalyzerAgent:
    """
    Factory function to create and initialize a ProductionStyleAnalyzerAgent
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionStyleAnalyzerAgent instance
    """
    agent = ProductionStyleAnalyzerAgent(project_id)
    return agent

# Export main classes
__all__ = [
    'ProductionStyleAnalyzerAgent',
    'styleanalyzerAgent',  # For backwards compatibility
    'create_style_analyzer_agent'
]