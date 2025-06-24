# app/agents/tools/content_tools.py
"""
Content-focused tools for SpinScribe agents
Built using CAMEL's FunctionTool system
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from camel.toolkits import FunctionTool
from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class ContentAnalysisTool:
    """
    Tool for analyzing content characteristics and quality
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.ContentValidationTool")
        
        # Validation criteria
        self.validation_criteria = {
            "word_count_tolerance": 0.2,  # 20% tolerance
            "min_readability_score": 6.0,
            "min_engagement_score": 3.0,
            "required_elements": {
                "blog_post": ["introduction", "main_content", "conclusion"],
                "landing_page": ["headline", "benefits", "call_to_action"],
                "email": ["subject_line", "greeting", "main_message", "cta"]
            }
        }
    
    def validate_content_requirements(self, 
                                    content: str,
                                    requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate content against specified requirements
        
        Args:
            content (str): Content to validate
            requirements (dict): Requirements to validate against
            
        Returns:
            dict: Validation results with pass/fail and recommendations
        """
        
        try:
            validation_results = {
                "overall_pass": True,
                "tests": {},
                "score": 0,
                "recommendations": []
            }
            
            # Analyze content first
            content_analysis = ContentAnalysisTool(self.project_id).analyze_content_structure(content)
            
            # Word count validation
            if "target_word_count" in requirements:
                word_count_result = self._validate_word_count(
                    content_analysis["basic_metrics"]["word_count"],
                    requirements["target_word_count"]
                )
                validation_results["tests"]["word_count"] = word_count_result
                if not word_count_result["pass"]:
                    validation_results["overall_pass"] = False
            
            # Readability validation
            if "min_readability" in requirements:
                readability_result = self._validate_readability(
                    content_analysis["readability"]["readability_score"],
                    requirements["min_readability"]
                )
                validation_results["tests"]["readability"] = readability_result
                if not readability_result["pass"]:
                    validation_results["overall_pass"] = False
            
            # Content type specific validation
            if "content_type" in requirements:
                content_type_result = self._validate_content_type_requirements(
                    content, requirements["content_type"]
                )
                validation_results["tests"]["content_type"] = content_type_result
                if not content_type_result["pass"]:
                    validation_results["overall_pass"] = False
            
            # SEO validation
            if "seo_requirements" in requirements:
                seo_result = self._validate_seo_requirements(
                    content, requirements["seo_requirements"]
                )
                validation_results["tests"]["seo"] = seo_result
                if not seo_result["pass"]:
                    validation_results["overall_pass"] = False
            
            # Brand voice validation
            if "brand_voice" in requirements:
                brand_voice_result = self._validate_brand_voice(
                    content, requirements["brand_voice"]
                )
                validation_results["tests"]["brand_voice"] = brand_voice_result
                if not brand_voice_result["pass"]:
                    validation_results["overall_pass"] = False
            
            # Calculate overall score
            passed_tests = sum(1 for test in validation_results["tests"].values() if test["pass"])
            total_tests = len(validation_results["tests"])
            validation_results["score"] = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            # Generate recommendations
            validation_results["recommendations"] = self._generate_validation_recommendations(
                validation_results["tests"]
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Content validation failed: {e}")
            return {"error": str(e)}
    
    def _validate_word_count(self, actual_count: int, target_count: int) -> Dict[str, Any]:
        """Validate word count against target"""
        
        tolerance = int(target_count * self.validation_criteria["word_count_tolerance"])
        min_count = target_count - tolerance
        max_count = target_count + tolerance
        
        passed = min_count <= actual_count <= max_count
        
        return {
            "pass": passed,
            "actual": actual_count,
            "target": target_count,
            "range": f"{min_count}-{max_count}",
            "message": "Word count within acceptable range" if passed else f"Word count {actual_count} outside target range {min_count}-{max_count}"
        }
    
    def _validate_readability(self, actual_score: float, min_score: float) -> Dict[str, Any]:
        """Validate readability score"""
        
        passed = actual_score >= min_score
        
        return {
            "pass": passed,
            "actual": actual_score,
            "minimum": min_score,
            "message": "Readability meets requirements" if passed else f"Readability score {actual_score} below minimum {min_score}"
        }
    
    def _validate_content_type_requirements(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate content type specific requirements"""
        
        required_elements = self.validation_criteria["required_elements"].get(content_type, [])
        found_elements = []
        
        content_lower = content.lower()
        
        # Simple element detection (in production, this would be more sophisticated)
        element_patterns = {
            "introduction": r"\b(introduction|intro|begin|start|welcome)\b",
            "main_content": r"\b(main|content|body|discussion|analysis)\b",
            "conclusion": r"\b(conclusion|summary|end|final|wrap)\b",
            "headline": r"^#\s+.+|^.{1,100}$",  # H1 or short first line
            "benefits": r"\b(benefit|advantage|value|feature)\b",
            "call_to_action": r"\b(click|buy|subscribe|contact|learn more|get started)\b",
            "subject_line": r"^.{1,100}$",  # Assuming first line is subject
            "greeting": r"\b(hello|hi|dear|greetings)\b",
            "main_message": r".{100,}",  # Substantial content
            "cta": r"\b(click|buy|subscribe|contact|learn more|get started)\b"
        }
        
        for element in required_elements:
            pattern = element_patterns.get(element, r"\b" + element + r"\b")
            if re.search(pattern, content_lower, re.MULTILINE | re.IGNORECASE):
                found_elements.append(element)
        
        passed = len(found_elements) >= len(required_elements) * 0.8  # 80% of elements found
        
        return {
            "pass": passed,
            "required": required_elements,
            "found": found_elements,
            "missing": [elem for elem in required_elements if elem not in found_elements],
            "message": f"Found {len(found_elements)}/{len(required_elements)} required elements"
        }
    
    def _validate_seo_requirements(self, content: str, seo_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SEO requirements"""
        
        results = {
            "pass": True,
            "checks": {},
            "message": ""
        }
        
        # Keyword density check
        if "keywords" in seo_requirements:
            keywords = seo_requirements["keywords"]
            target_density = seo_requirements.get("keyword_density", 0.02)  # 2%
            
            word_count = len(content.split())
            keyword_results = {}
            
            for keyword in keywords:
                keyword_count = content.lower().count(keyword.lower())
                actual_density = keyword_count / word_count if word_count > 0 else 0
                
                keyword_pass = 0.005 <= actual_density <= 0.03  # 0.5% to 3%
                keyword_results[keyword] = {
                    "count": keyword_count,
                    "density": actual_density,
                    "pass": keyword_pass
                }
                
                if not keyword_pass:
                    results["pass"] = False
            
            results["checks"]["keywords"] = keyword_results
        
        # Meta title length (if present)
        if "meta_title" in seo_requirements:
            title_lines = [line.strip() for line in content.split('\n') if line.strip()]
            if title_lines:
                title_length = len(title_lines[0])
                title_pass = 30 <= title_length <= 60
                results["checks"]["title_length"] = {
                    "length": title_length,
                    "pass": title_pass
                }
                if not title_pass:
                    results["pass"] = False
        
        results["message"] = "SEO requirements met" if results["pass"] else "SEO requirements not fully met"
        
        return results
    
    def _validate_brand_voice(self, content: str, brand_voice: Dict[str, Any]) -> Dict[str, Any]:
        """Validate brand voice consistency"""
        
        # Simple brand voice validation (in production, this would use the style analyzer)
        results = {
            "pass": True,
            "checks": {},
            "message": ""
        }
        
        # Tone check
        if "tone" in brand_voice:
            expected_tone = brand_voice["tone"].lower()
            tone_indicators = {
                "professional": ["professional", "expertise", "solution", "service"],
                "casual": ["you", "we", "let's", "easy", "simple"],
                "friendly": ["welcome", "help", "great", "wonderful", "enjoy"],
                "authoritative": ["proven", "research", "data", "established", "leading"]
            }
            
            if expected_tone in tone_indicators:
                indicators = tone_indicators[expected_tone]
                content_lower = content.lower()
                found_indicators = sum(1 for indicator in indicators if indicator in content_lower)
                
                tone_pass = found_indicators >= 2  # At least 2 tone indicators
                results["checks"]["tone"] = {
                    "expected": expected_tone,
                    "indicators_found": found_indicators,
                    "pass": tone_pass
                }
                
                if not tone_pass:
                    results["pass"] = False
        
        # Formality check
        if "formality" in brand_voice:
            expected_formality = brand_voice["formality"]  # 1-10 scale
            
            # Count formal vs casual indicators
            formal_indicators = ["furthermore", "moreover", "consequently", "therefore"]
            casual_indicators = ["you'll", "don't", "can't", "let's"]
            
            content_lower = content.lower()
            formal_count = sum(1 for indicator in formal_indicators if indicator in content_lower)
            casual_count = sum(1 for indicator in casual_indicators if indicator in content_lower)
            
            # Simple formality scoring
            if expected_formality >= 7:  # High formality expected
                formality_pass = formal_count >= casual_count
            elif expected_formality <= 4:  # Low formality expected
                formality_pass = casual_count >= formal_count
            else:  # Moderate formality
                formality_pass = True  # More flexible
            
            results["checks"]["formality"] = {
                "expected_level": expected_formality,
                "formal_indicators": formal_count,
                "casual_indicators": casual_count,
                "pass": formality_pass
            }
            
            if not formality_pass:
                results["pass"] = False
        
        results["message"] = "Brand voice consistent" if results["pass"] else "Brand voice inconsistencies found"
        
        return results
    
    def _generate_validation_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        for test_name, result in test_results.items():
            if not result.get("pass", True):
                if test_name == "word_count":
                    actual = result["actual"]
                    target = result["target"]
                    if actual < target:
                        recommendations.append(f"Expand content by approximately {target - actual} words")
                    else:
                        recommendations.append(f"Reduce content by approximately {actual - target} words")
                
                elif test_name == "readability":
                    recommendations.append("Improve readability by using shorter sentences and simpler words")
                
                elif test_name == "content_type":
                    missing = result.get("missing", [])
                    if missing:
                        recommendations.append(f"Add missing content elements: {', '.join(missing)}")
                
                elif test_name == "seo":
                    if "keywords" in result["checks"]:
                        for keyword, data in result["checks"]["keywords"].items():
                            if not data["pass"]:
                                if data["density"] < 0.005:
                                    recommendations.append(f"Increase usage of keyword '{keyword}'")
                                else:
                                    recommendations.append(f"Reduce usage of keyword '{keyword}' to avoid stuffing")
                
                elif test_name == "brand_voice":
                    if "tone" in result["checks"] and not result["checks"]["tone"]["pass"]:
                        expected_tone = result["checks"]["tone"]["expected"]
                        recommendations.append(f"Adjust content tone to be more {expected_tone}")
                    
                    if "formality" in result["checks"] and not result["checks"]["formality"]["pass"]:
                        formality_level = result["checks"]["formality"]["expected_level"]
                        if formality_level >= 7:
                            recommendations.append("Use more formal language and professional terminology")
                        else:
                            recommendations.append("Use more casual, conversational language")
        
        return recommendations if recommendations else ["Content meets all validation criteria"]

# Create CAMEL FunctionTool instances
def create_content_analysis_tool(project_id: str = None) -> FunctionTool:
    """Create CAMEL FunctionTool for content analysis"""
    tool = ContentAnalysisTool(project_id)
    return FunctionTool(tool.analyze_content_structure)

def create_content_generation_tool(project_id: str = None) -> FunctionTool:
    """Create CAMEL FunctionTool for content generation"""
    tool = ContentGenerationTool(project_id)
    return FunctionTool(tool.generate_content_outline)

def create_content_validation_tool(project_id: str = None) -> FunctionTool:
    """Create CAMEL FunctionTool for content validation"""
    tool = ContentValidationTool(project_id)
    return FunctionTool(tool.validate_content_requirements)
    Logger(f"{__name__}.ContentAnalysisTool")
    
def analyze_content_structure(self, content: str) -> Dict[str, Any]:
    """
    Analyze the structure and characteristics of content
    
    Args:
        content (str): Content text to analyze
        
    Returns:
        dict: Analysis results including word count, readability, structure
    """
    
    try:
        if not content or not isinstance(content, str):
            return {"error": "Invalid content provided"}
        
        # Basic metrics
        word_count = len(content.split())
        char_count = len(content)
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        sentence_count = len([s for s in content.split('.') if s.strip()])
        
        # Readability analysis
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        avg_word_length = sum(len(word) for word in content.split()) / word_count if word_count > 0 else 0
        
        # Structure analysis
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        bullet_points = len(re.findall(r'^\s*[•\-\*]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        
        # Engagement elements
        questions = content.count('?')
        exclamations = content.count('!')
        
        # Keywords and themes (simple analysis)
        words = re.findall(r'\b\w+\b', content.lower())
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Focus on meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        analysis = {
            "basic_metrics": {
                "word_count": word_count,
                "character_count": char_count,
                "paragraph_count": paragraph_count,
                "sentence_count": sentence_count
            },
            "readability": {
                "average_sentence_length": round(avg_sentence_length, 1),
                "average_word_length": round(avg_word_length, 1),
                "readability_score": self._calculate_simple_readability(avg_sentence_length, avg_word_length)
            },
            "structure": {
                "headers_count": len(headers),
                "headers": headers,
                "bullet_points": bullet_points,
                "numbered_lists": numbered_lists
            },
            "engagement": {
                "questions": questions,
                "exclamations": exclamations,
                "engagement_score": min(10, (questions + exclamations) / max(1, sentence_count) * 100)
            },
            "keywords": {
                "top_keywords": [{"word": word, "frequency": freq} for word, freq in top_keywords],
                "unique_words": len(set(words)),
                "vocabulary_richness": len(set(words)) / len(words) if words else 0
            },
            "analyzed_at": datetime.now().isoformat()
        }
        
        return analysis
        
    except Exception as e:
        self.logger.error(f"Content analysis failed: {e}")
        return {"error": str(e)}

def _calculate_simple_readability(self, avg_sentence_length: float, avg_word_length: float) -> float:
    """Calculate a simple readability score"""
    
    # Simple formula based on sentence and word length
    # Lower score = easier to read
    if avg_sentence_length == 0 or avg_word_length == 0:
        return 5.0
    
    # Ideal ranges: 15-20 words per sentence, 4-6 chars per word
    sentence_penalty = abs(avg_sentence_length - 17.5) / 10
    word_penalty = abs(avg_word_length - 5) / 2
    
    readability = 10 - (sentence_penalty + word_penalty)
    return max(1, min(10, readability))

def compare_content_versions(self, original: str, revised: str) -> Dict[str, Any]:
    """
    Compare two versions of content
    
    Args:
        original (str): Original content
        revised (str): Revised content
        
    Returns:
        dict: Comparison results
    """
    
    try:
        original_analysis = self.analyze_content_structure(original)
        revised_analysis = self.analyze_content_structure(revised)
        
        # Calculate changes
        changes = {}
        
        for category in ["basic_metrics", "readability", "engagement"]:
            changes[category] = {}
            for metric, value in revised_analysis[category].items():
                if metric in original_analysis[category]:
                    original_value = original_analysis[category][metric]
                    if isinstance(value, (int, float)) and isinstance(original_value, (int, float)):
                        change = value - original_value
                        percent_change = (change / original_value * 100) if original_value != 0 else 0
                        changes[category][metric] = {
                            "original": original_value,
                            "revised": value,
                            "change": change,
                            "percent_change": round(percent_change, 1)
                        }
        
        return {
            "original_analysis": original_analysis,
            "revised_analysis": revised_analysis,
            "changes": changes,
            "improvement_summary": self._generate_improvement_summary(changes)
        }
        
    except Exception as e:
        self.logger.error(f"Content comparison failed: {e}")
        return {"error": str(e)}

def _generate_improvement_summary(self, changes: Dict[str, Any]) -> List[str]:
    """Generate summary of improvements between content versions"""
    
    improvements = []
    
    # Check basic metrics improvements
    if "basic_metrics" in changes:
        word_change = changes["basic_metrics"].get("word_count", {}).get("change", 0)
        if word_change > 50:
            improvements.append(f"Content expanded by {word_change} words")
        elif word_change < -50:
            improvements.append(f"Content shortened by {abs(word_change)} words")
    
    # Check readability improvements
    if "readability" in changes:
        readability_change = changes["readability"].get("readability_score", {}).get("change", 0)
        if readability_change > 0.5:
            improvements.append("Readability improved")
        elif readability_change < -0.5:
            improvements.append("Readability decreased")
    
    # Check engagement improvements
    if "engagement" in changes:
        engagement_change = changes["engagement"].get("engagement_score", {}).get("change", 0)
        if engagement_change > 1:
            improvements.append("Engagement elements increased")
        elif engagement_change < -1:
            improvements.append("Engagement elements decreased")
    
    return improvements if improvements else ["No significant changes detected"]

class ContentGenerationTool:
    """
    Tool for generating content snippets and templates
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.ContentGenerationTool")
    
    def generate_content_outline(self, 
                                topic: str,
                                content_type: str = "blog_post",
                                target_audience: str = "general",
                                word_count: int = 1000) -> Dict[str, Any]:
        """
        Generate a structured content outline
        
        Args:
            topic (str): Main topic for the content
            content_type (str): Type of content (blog_post, article, etc.)
            target_audience (str): Target audience description
            word_count (int): Target word count
            
        Returns:
            dict: Generated content outline
        """
        
        try:
            # Basic outline structure based on content type
            if content_type == "blog_post":
                outline = self._generate_blog_outline(topic, target_audience, word_count)
            elif content_type == "landing_page":
                outline = self._generate_landing_page_outline(topic, target_audience)
            elif content_type == "article":
                outline = self._generate_article_outline(topic, target_audience, word_count)
            else:
                outline = self._generate_generic_outline(topic, target_audience, word_count)
            
            return {
                "topic": topic,
                "content_type": content_type,
                "target_audience": target_audience,
                "estimated_word_count": word_count,
                "outline": outline,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Outline generation failed: {e}")
            return {"error": str(e)}
    
    def _generate_blog_outline(self, topic: str, audience: str, word_count: int) -> List[Dict[str, Any]]:
        """Generate blog post outline"""
        
        intro_words = max(100, int(word_count * 0.15))
        body_words = max(600, int(word_count * 0.70))
        conclusion_words = max(100, int(word_count * 0.15))
        
        return [
            {
                "section": "Introduction",
                "description": f"Hook readers and introduce {topic}. Establish relevance for {audience}.",
                "estimated_words": intro_words,
                "key_points": [
                    "Engaging opening statement",
                    f"Why {topic} matters to {audience}",
                    "Preview of what's covered"
                ]
            },
            {
                "section": "Main Content",
                "description": f"Comprehensive coverage of {topic} with practical insights",
                "estimated_words": body_words,
                "key_points": [
                    f"Core concepts of {topic}",
                    "Practical applications",
                    "Examples and case studies",
                    "Best practices and tips"
                ]
            },
            {
                "section": "Conclusion",
                "description": "Summarize key takeaways and provide next steps",
                "estimated_words": conclusion_words,
                "key_points": [
                    "Recap main points",
                    f"Actionable next steps for {audience}",
                    "Call to action"
                ]
            }
        ]
    
    def _generate_landing_page_outline(self, topic: str, audience: str) -> List[Dict[str, Any]]:
        """Generate landing page outline"""
        
        return [
            {
                "section": "Hero Section",
                "description": f"Compelling headline and value proposition for {topic}",
                "estimated_words": 50,
                "key_points": [
                    "Clear value proposition",
                    "Benefit-focused headline",
                    "Supporting subheadline"
                ]
            },
            {
                "section": "Problem/Solution",
                "description": f"Identify {audience} pain points and position {topic} as solution",
                "estimated_words": 200,
                "key_points": [
                    f"Pain points of {audience}",
                    f"How {topic} solves these problems",
                    "Unique advantages"
                ]
            },
            {
                "section": "Benefits & Features",
                "description": "Detailed benefits and key features",
                "estimated_words": 300,
                "key_points": [
                    "Primary benefits",
                    "Key features",
                    "Social proof elements"
                ]
            },
            {
                "section": "Call to Action",
                "description": "Clear, compelling action for visitors",
                "estimated_words": 50,
                "key_points": [
                    "Primary CTA",
                    "Urgency/scarcity elements",
                    "Risk reduction"
                ]
            }
        ]
    
    def _generate_article_outline(self, topic: str, audience: str, word_count: int) -> List[Dict[str, Any]]:
        """Generate article outline"""
        
        # More detailed structure for longer articles
        sections = [
            {
                "section": "Introduction",
                "description": f"Establish context and importance of {topic}",
                "estimated_words": int(word_count * 0.10)
            },
            {
                "section": "Background/Context",
                "description": f"Provide necessary background on {topic}",
                "estimated_words": int(word_count * 0.20)
            },
            {
                "section": "Main Analysis",
                "description": f"Deep dive into {topic} with analysis",
                "estimated_words": int(word_count * 0.50)
            },
            {
                "section": "Implications",
                "description": f"Discuss implications for {audience}",
                "estimated_words": int(word_count * 0.15)
            },
            {
                "section": "Conclusion",
                "description": "Summarize findings and future outlook",
                "estimated_words": int(word_count * 0.05)
            }
        ]
        
        return sections
    
    def _generate_generic_outline(self, topic: str, audience: str, word_count: int) -> List[Dict[str, Any]]:
        """Generate generic content outline"""
        
        section_count = max(3, min(6, word_count // 200))
        words_per_section = word_count // section_count
        
        sections = []
        for i in range(section_count):
            if i == 0:
                sections.append({
                    "section": "Introduction",
                    "description": f"Introduce {topic} to {audience}",
                    "estimated_words": words_per_section
                })
            elif i == section_count - 1:
                sections.append({
                    "section": "Conclusion",
                    "description": f"Wrap up discussion of {topic}",
                    "estimated_words": words_per_section
                })
            else:
                sections.append({
                    "section": f"Section {i}",
                    "description": f"Cover aspect {i} of {topic}",
                    "estimated_words": words_per_section
                })
        
        return sections

class ContentValidationTool:
    """
    Tool for validating content against requirements and standards
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.get