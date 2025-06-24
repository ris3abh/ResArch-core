# app/agents/prompts/language_codes/generators.py
"""
Language Code Generator for SpinScribe
Generates CF=X, LF=Y, VL=Z codes from style analysis and content requirements
"""

import logging
from typing import Dict, List, Any, Optional
import statistics

from .templates import LanguageCodeFormat, LanguageCodeTemplates

logger = logging.getLogger(__name__)

class LanguageCodeGenerator:
    """
    Generates language codes from style analysis and content requirements
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Parameter calculation weights
        self.weights = {
            "content_focus": {
                "content_type": 0.3,
                "objectives": 0.4,
                "audience": 0.3
            },
            "language_formality": {
                "audience": 0.4,
                "tone": 0.4,
                "content_type": 0.2
            },
            "vocabulary_level": {
                "audience": 0.5,
                "subject_expertise": 0.3,
                "content_type": 0.2
            },
            "subject_expertise": {
                "audience": 0.4,
                "content_type": 0.3,
                "objectives": 0.3
            }
        }
    
    def generate_from_style_analysis(self, 
                                   style_analysis: Dict[str, Any],
                                   content_requirements: Optional[Dict[str, Any]] = None) -> LanguageCodeFormat:
        """
        Generate language code from style analysis results
        
        Args:
            style_analysis: Results from style analyzer
            content_requirements: Optional content requirements
            
        Returns:
            LanguageCodeFormat instance
        """
        
        try:
            self.logger.info("Generating language code from style analysis")
            
            # Extract style analysis components
            linguistic_features = style_analysis.get("linguistic_features", {})
            semantic_features = style_analysis.get("semantic_features", {})
            statistical_features = style_analysis.get("statistical_features", {})
            llm_insights = style_analysis.get("llm_insights", {})
            
            # Calculate core parameters
            content_focus = self._calculate_content_focus(
                semantic_features, llm_insights, content_requirements
            )
            
            language_formality = self._calculate_language_formality(
                linguistic_features, statistical_features, llm_insights
            )
            
            vocabulary_level = self._calculate_vocabulary_level(
                linguistic_features, semantic_features
            )
            
            subject_expertise = self._calculate_subject_expertise(
                semantic_features, llm_insights, content_requirements
            )
            
            # Calculate optional parameters
            detail_level = self._calculate_detail_level(
                linguistic_features, semantic_features
            )
            
            sentence_complexity = self._calculate_sentence_complexity(
                linguistic_features
            )
            
            persuasiveness = self._calculate_persuasiveness(
                llm_insights, statistical_features
            )
            
            engagement = self._calculate_engagement(
                statistical_features, llm_insights
            )
            
            # Extract metadata
            audience = self._extract_audience(llm_insights, content_requirements)
            tone = self._extract_tone(llm_insights)
            
            # Create language code
            language_code = LanguageCodeFormat(
                content_focus=content_focus,
                language_formality=language_formality,
                vocabulary_level=vocabulary_level,
                subject_expertise=subject_expertise,
                detail_level=detail_level,
                sentence_complexity=sentence_complexity,
                persuasiveness=persuasiveness,
                engagement=engagement,
                audience=audience,
                tone=tone
            )
            
            self.logger.info(f"Generated language code: {language_code.to_code_string()}")
            
            return language_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate language code: {e}")
            # Return default code
            return self._get_default_code()
    
    def generate_from_requirements(self, 
                                 content_requirements: Dict[str, Any]) -> LanguageCodeFormat:
        """
        Generate language code from content requirements only
        
        Args:
            content_requirements: Content creation requirements
            
        Returns:
            LanguageCodeFormat instance
        """
        
        try:
            self.logger.info("Generating language code from requirements")
            
            content_type = content_requirements.get("content_type", "blog_post")
            target_audience = content_requirements.get("target_audience", "general")
            objectives = content_requirements.get("objectives", [])
            tone = content_requirements.get("tone", "professional")
            
            # Check if we have a matching template
            template = LanguageCodeTemplates.get_template_by_name(f"{content_type}_{tone}")
            if template:
                self.logger.info(f"Using template: {content_type}_{tone}")
                return template
            
            # Generate based on requirements
            content_focus = self._map_content_type_to_focus(content_type, objectives)
            language_formality = self._map_audience_to_formality(target_audience, tone)
            vocabulary_level = self._map_audience_to_vocabulary(target_audience)
            subject_expertise = self._map_audience_to_expertise(target_audience)
            
            # Optional parameters based on content type
            persuasiveness = self._map_content_type_to_persuasiveness(content_type)
            engagement = self._map_content_type_to_engagement(content_type)
            
            language_code = LanguageCodeFormat(
                content_focus=content_focus,
                language_formality=language_formality,
                vocabulary_level=vocabulary_level,
                subject_expertise=subject_expertise,
                persuasiveness=persuasiveness,
                engagement=engagement,
                audience=target_audience,
                tone=tone
            )
            
            self.logger.info(f"Generated language code: {language_code.to_code_string()}")
            
            return language_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate language code from requirements: {e}")
            return self._get_default_code()
    
    def refine_code_with_feedback(self, 
                                current_code: LanguageCodeFormat,
                                feedback: Dict[str, Any]) -> LanguageCodeFormat:
        """
        Refine language code based on feedback
        
        Args:
            current_code: Current language code
            feedback: Feedback for refinement
            
        Returns:
            Refined LanguageCodeFormat
        """
        
        try:
            self.logger.info("Refining language code with feedback")
            
            # Create a copy of current code
            refined_params = current_code.to_dict()
            
            # Apply feedback adjustments
            if "too_formal" in feedback:
                refined_params["language_formality"] = max(1, refined_params["language_formality"] - 2)
            elif "too_casual" in feedback:
                refined_params["language_formality"] = min(10, refined_params["language_formality"] + 2)
            
            if "too_complex" in feedback:
                refined_params["vocabulary_level"] = max(1, refined_params["vocabulary_level"] - 2)
                refined_params["sentence_complexity"] = max(1, refined_params.get("sentence_complexity", 5) - 1)
            elif "too_simple" in feedback:
                refined_params["vocabulary_level"] = min(10, refined_params["vocabulary_level"] + 2)
                refined_params["sentence_complexity"] = min(10, refined_params.get("sentence_complexity", 5) + 1)
            
            if "needs_more_engagement" in feedback:
                refined_params["engagement"] = min(10, refined_params.get("engagement", 5) + 2)
            elif "too_engaging" in feedback:
                refined_params["engagement"] = max(1, refined_params.get("engagement", 5) - 2)
            
            if "needs_more_focus" in feedback:
                refined_params["content_focus"] = min(10, refined_params["content_focus"] + 1)
            elif "too_focused" in feedback:
                refined_params["content_focus"] = max(1, refined_params["content_focus"] - 1)
            
            # Create refined code
            refined_code = LanguageCodeFormat(**refined_params)
            
            self.logger.info(f"Refined language code: {refined_code.to_code_string()}")
            
            return refined_code
            
        except Exception as e:
            self.logger.error(f"Failed to refine language code: {e}")
            return current_code
    
    # Parameter calculation methods
    def _calculate_content_focus(self, 
                               semantic_features: Dict[str, Any],
                               llm_insights: Dict[str, Any],
                               content_requirements: Optional[Dict[str, Any]] = None) -> int:
        """Calculate content focus parameter (1-10)"""
        
        factors = []
        
        # Topic consistency indicates focus
        topic_consistency = semantic_features.get("topic_consistency", 0.5)
        factors.append(int(topic_consistency * 10))
        
        # Number of primary themes (fewer = more focused)
        primary_themes = semantic_features.get("primary_themes", [])
        if len(primary_themes) <= 2:
            factors.append(8)
        elif len(primary_themes) <= 4:
            factors.append(6)
        else:
            factors.append(4)
        
        # Content type requirements
        if content_requirements:
            content_type = content_requirements.get("content_type", "")
            if content_type in ["landing_page", "email", "advertisement"]:
                factors.append(9)  # High focus needed
            elif content_type in ["blog_post", "article"]:
                factors.append(7)  # Moderate focus
            else:
                factors.append(5)  # Default
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_language_formality(self, 
                                    linguistic_features: Dict[str, Any],
                                    statistical_features: Dict[str, Any],
                                    llm_insights: Dict[str, Any]) -> int:
        """Calculate language formality parameter (1-10)"""
        
        factors = []
        
        # Passive voice usage (higher = more formal)
        passive_voice_ratio = statistical_features.get("passive_voice_ratio", 0.2)
        factors.append(int(passive_voice_ratio * 20) + 3)  # Scale to 3-7
        
        # Average sentence length (longer = more formal)
        avg_sentence_length = linguistic_features.get("avg_sentence_length", 15)
        if avg_sentence_length > 20:
            factors.append(7)
        elif avg_sentence_length > 15:
            factors.append(5)
        else:
            factors.append(3)
        
        # Contraction usage (fewer = more formal)
        contraction_usage = statistical_features.get("contraction_usage", 0.1)
        factors.append(int((1 - contraction_usage) * 8) + 2)
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_vocabulary_level(self, 
                                  linguistic_features: Dict[str, Any],
                                  semantic_features: Dict[str, Any]) -> int:
        """Calculate vocabulary level parameter (1-10)"""
        
        factors = []
        
        # Vocabulary richness
        vocab_richness = linguistic_features.get("vocabulary_richness", 0.5)
        factors.append(int(vocab_richness * 10))
        
        # Technical term density
        tech_density = linguistic_features.get("technical_term_density", 0.1)
        factors.append(int(tech_density * 20) + 3)
        
        # Average word length
        avg_word_length = linguistic_features.get("avg_word_length", 5)
        if avg_word_length > 6:
            factors.append(8)
        elif avg_word_length > 5:
            factors.append(6)
        else:
            factors.append(4)
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_subject_expertise(self, 
                                   semantic_features: Dict[str, Any],
                                   llm_insights: Dict[str, Any],
                                   content_requirements: Optional[Dict[str, Any]] = None) -> int:
        """Calculate subject expertise parameter (1-10)"""
        
        factors = []
        
        # Technical complexity from semantic analysis
        primary_themes = semantic_features.get("primary_themes", [])
        technical_terms = ["technology", "science", "medical", "finance", "engineering"]
        
        if any(term in " ".join(primary_themes).lower() for term in technical_terms):
            factors.append(7)
        else:
            factors.append(4)
        
        # Target audience from requirements
        if content_requirements:
            audience = content_requirements.get("target_audience", "").lower()
            if "expert" in audience or "professional" in audience:
                factors.append(8)
            elif "intermediate" in audience:
                factors.append(6)
            elif "beginner" in audience:
                factors.append(3)
            else:
                factors.append(5)
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_detail_level(self, 
                              linguistic_features: Dict[str, Any],
                              semantic_features: Dict[str, Any]) -> int:
        """Calculate detail level parameter (1-10)"""
        
        factors = []
        
        # Sentence length indicates detail
        avg_sentence_length = linguistic_features.get("avg_sentence_length", 15)
        factors.append(min(10, int(avg_sentence_length / 2)))
        
        # Number of themes (more themes = more detail)
        primary_themes = semantic_features.get("primary_themes", [])
        factors.append(min(10, len(primary_themes) + 3))
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_sentence_complexity(self, linguistic_features: Dict[str, Any]) -> int:
        """Calculate sentence complexity parameter (1-10)"""
        
        # Complex sentence ratio
        complex_ratio = linguistic_features.get("complex_sentence_ratio", 0.3)
        complexity_score = int(complex_ratio * 15) + 2
        
        return max(1, min(10, complexity_score))
    
    def _calculate_persuasiveness(self, 
                                llm_insights: Dict[str, Any],
                                statistical_features: Dict[str, Any]) -> int:
        """Calculate persuasiveness parameter (1-10)"""
        
        factors = []
        
        # Check for persuasive techniques from LLM insights
        persuasion_techniques = llm_insights.get("persuasion_techniques", [])
        factors.append(min(10, len(persuasion_techniques) + 3))
        
        # Exclamation usage (indicates enthusiasm/persuasion)
        exclamation_usage = statistical_features.get("exclamation_usage", 0.02)
        factors.append(int(exclamation_usage * 50) + 3)
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    def _calculate_engagement(self, 
                            statistical_features: Dict[str, Any],
                            llm_insights: Dict[str, Any]) -> int:
        """Calculate engagement parameter (1-10)"""
        
        factors = []
        
        # Question usage (engages readers)
        question_usage = statistical_features.get("question_usage", 0.05)
        factors.append(int(question_usage * 40) + 3)
        
        # Second person usage (direct address)
        second_person_usage = statistical_features.get("second_person_usage", 0.1)
        factors.append(int(second_person_usage * 30) + 3)
        
        # Engagement style from LLM
        engagement_style = llm_insights.get("engagement_style", "")
        if "highly engaging" in engagement_style.lower():
            factors.append(9)
        elif "engaging" in engagement_style.lower():
            factors.append(7)
        else:
            factors.append(5)
        
        return max(1, min(10, int(statistics.mean(factors))))
    
    # Helper methods for requirement-based generation
    def _map_content_type_to_focus(self, content_type: str, objectives: List[str]) -> int:
        """Map content type to focus level"""
        
        type_focus = {
            "landing_page": 9,
            "email": 8,
            "advertisement": 9,
            "blog_post": 7,
            "article": 6,
            "social_media": 5,
            "documentation": 8
        }
        
        base_focus = type_focus.get(content_type, 6)
        
        # Adjust based on objectives
        if "convert" in " ".join(objectives).lower():
            base_focus = min(10, base_focus + 1)
        
        return base_focus
    
    def _map_audience_to_formality(self, audience: str, tone: str) -> int:
        """Map audience and tone to formality level"""
        
        audience_lower = audience.lower()
        tone_lower = tone.lower()
        
        # Base formality by audience
        if "professional" in audience_lower or "expert" in audience_lower:
            base_formality = 7
        elif "business" in audience_lower:
            base_formality = 6
        elif "general" in audience_lower:
            base_formality = 5
        elif "young" in audience_lower or "casual" in audience_lower:
            base_formality = 3
        else:
            base_formality = 5
        
        # Adjust by tone
        if "formal" in tone_lower:
            base_formality = min(10, base_formality + 2)
        elif "casual" in tone_lower:
            base_formality = max(1, base_formality - 2)
        
        return base_formality
    
    def _map_audience_to_vocabulary(self, audience: str) -> int:
        """Map audience to vocabulary level"""
        
        audience_lower = audience.lower()
        
        if "expert" in audience_lower or "professional" in audience_lower:
            return 8
        elif "intermediate" in audience_lower:
            return 6
        elif "beginner" in audience_lower:
            return 4
        else:
            return 5
    
    def _map_audience_to_expertise(self, audience: str) -> int:
        """Map audience to subject expertise level"""
        
        audience_lower = audience.lower()
        
        if "expert" in audience_lower:
            return 9
        elif "professional" in audience_lower:
            return 7
        elif "intermediate" in audience_lower:
            return 5
        elif "beginner" in audience_lower:
            return 3
        else:
            return 5
    
    def _map_content_type_to_persuasiveness(self, content_type: str) -> int:
        """Map content type to persuasiveness level"""
        
        type_persuasion = {
            "landing_page": 9,
            "advertisement": 10,
            "email": 7,
            "blog_post": 5,
            "documentation": 2,
            "social_media": 6
        }
        
        return type_persuasion.get(content_type, 5)
    
    def _map_content_type_to_engagement(self, content_type: str) -> int:
        """Map content type to engagement level"""
        
        type_engagement = {
            "social_media": 10,
            "email": 8,
            "blog_post": 7,
            "landing_page": 8,
            "documentation": 4,
            "article": 6
        }
        
        return type_engagement.get(content_type, 6)
    
    def _extract_audience(self, 
                        llm_insights: Dict[str, Any],
                        content_requirements: Optional[Dict[str, Any]] = None) -> str:
        """Extract audience information"""
        
        if content_requirements and "target_audience" in content_requirements:
            return content_requirements["target_audience"]
        
        audience_positioning = llm_insights.get("audience_positioning", "")
        if audience_positioning:
            return audience_positioning
        
        return "general audience"
    
    def _extract_tone(self, llm_insights: Dict[str, Any]) -> str:
        """Extract tone information"""
        
        tone_analysis = llm_insights.get("tone_analysis", {})
        if tone_analysis:
            # Get the most prominent tone
            top_tone = max(tone_analysis.items(), key=lambda x: x[1])[0]
            return top_tone
        
        return "professional"
    
    def _get_default_code(self) -> LanguageCodeFormat:
        """Return default language code"""
        return LanguageCodeFormat(
            content_focus=6,
            language_formality=5,
            vocabulary_level=5,
            subject_expertise=5,
            audience="general audience",
            tone="professional"
        )