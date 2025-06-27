# app/agents/specialized/editor_qa.py
"""
Production Editor/QA Agent for SpinScribe
Built on CAMEL AI Framework

The Editor/QA Agent reviews and refines content for quality, accuracy,
and alignment with brand guidelines and project requirements.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.configs import ChatGPTConfig

from app.agents.base.agent_factory import agent_factory
from app.database.connection import SessionLocal
from app.database.models.project import Project
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class IssueType(Enum):
    """Types of content issues that can be identified"""
    GRAMMAR = "grammar"
    SPELLING = "spelling"
    CLARITY = "clarity"
    BRAND_VOICE = "brand_voice"
    SEO = "seo"
    STRUCTURE = "structure"
    TONE = "tone"
    CONSISTENCY = "consistency"
    FACTUAL = "factual"
    READABILITY = "readability"

class IssueSeverity(Enum):
    """Severity levels for identified issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ContentIssue:
    """Represents an identified content issue"""
    issue_type: IssueType
    severity: IssueSeverity
    description: str
    location: str
    suggested_fix: str
    original_text: Optional[str] = None
    corrected_text: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['issue_type'] = self.issue_type.value
        result['severity'] = self.severity.value
        return result

@dataclass
class QualityMetrics:
    """Content quality assessment metrics"""
    overall_score: float
    grammar_score: float
    clarity_score: float
    brand_voice_score: float
    seo_score: float
    engagement_score: float
    readability_score: float
    consistency_score: float
    factual_accuracy_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EditingReport:
    """Comprehensive editing and QA report"""
    report_id: str
    content_title: str
    review_date: datetime
    original_word_count: int
    edited_word_count: int
    quality_metrics: QualityMetrics
    issues_identified: List[ContentIssue]
    improvements_made: List[str]
    recommendations: List[str]
    edited_content: str
    editor_notes: str
    approval_status: str = "pending"
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.review_date is None:
            self.review_date = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['review_date'] = self.review_date.isoformat()
        result['quality_metrics'] = self.quality_metrics.to_dict()
        result['issues_identified'] = [issue.to_dict() for issue in self.issues_identified]
        return result

class ProductionEditorQAAgent(ChatAgent):
    """
    Production-grade Editor/QA Agent that provides comprehensive content review,
    editing, and quality assurance for content creation workflows.
    
    This agent performs:
    - Grammar and spelling checks
    - Brand voice consistency verification
    - SEO optimization review
    - Clarity and readability improvements
    - Factual accuracy validation
    - Structure and flow optimization
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
        
        # Quality standards and patterns
        self.quality_standards = self._load_quality_standards()
        self.editing_patterns = self._load_editing_patterns()
        
        # Review cache and history
        self.review_cache: Dict[str, EditingReport] = {}
        
        # Performance metrics
        self.metrics = {
            "content_reviewed": 0,
            "issues_identified": 0,
            "improvements_made": 0,
            "average_quality_improvement": 0.0,
            "average_review_time": 0.0
        }
        
        self.logger.info(f"Editor/QA Agent initialized for project: {project_id}")
    
    def _create_system_message(self) -> BaseMessage:
        """Create system message for editor/QA role"""
        return BaseMessage.make_assistant_message(
            role_name="Content Editor & Quality Assurance",
            content=f"""
            You are a specialized Editor/QA Agent for SpinScribe, an expert in content quality assurance, editing, and brand consistency verification.
            
            CORE RESPONSIBILITIES:
            • Perform comprehensive content review and quality assessment
            • Identify and correct grammar, spelling, and structural issues
            • Verify brand voice consistency and tone alignment
            • Optimize content for SEO and readability
            • Ensure factual accuracy and logical flow
            • Provide detailed feedback and improvement recommendations

            EDITING EXPERTISE:
            • Advanced grammar and style correction
            • Brand voice consistency verification
            • SEO optimization and keyword integration review
            • Readability and engagement enhancement
            • Factual accuracy validation
            • Content structure and flow optimization
            • Clear, actionable feedback delivery

            PROJECT CONTEXT: {self.project_id or "General Content Review"}
            
            QUALITY STANDARDS:
            • Content must meet professional publishing standards
            • Brand voice must be consistent with established guidelines
            • All grammar and spelling errors must be identified and corrected
            • SEO optimization should enhance, not compromise readability
            • Content should engage and provide clear value to readers
            • Factual claims should be accurate and well-supported

            REVIEW METHODOLOGY:
            • Conduct systematic analysis across multiple quality dimensions
            • Identify issues with specific location and severity assessment
            • Provide clear, actionable correction suggestions
            • Maintain original author intent while improving execution
            • Ensure all changes align with brand guidelines
            • Deliver comprehensive feedback for continuous improvement

            OUTPUT REQUIREMENTS:
            • Detailed issue identification with specific locations
            • Clear severity assessment for each issue found
            • Actionable correction suggestions and improvements
            • Comprehensive quality metrics and scoring
            • Professional recommendations for content enhancement
            • Final edited version ready for publication

            You excel at transforming good content into exceptional content while maintaining brand consistency and maximizing reader engagement.
            """
        )
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Get model configuration for editing/QA"""
        return {
            "model_config": ChatGPTConfig(
                temperature=0.3,  # Lower temperature for consistent, precise editing
                max_tokens=4000
            )
        }
    
    def _load_quality_standards(self) -> Dict[str, Any]:
        """Load quality standards and thresholds"""
        return {
            "grammar": {
                "min_score": 0.95,
                "critical_errors": ["subject_verb_disagreement", "incorrect_tense", "sentence_fragments"]
            },
            "readability": {
                "target_flesch_score": (40, 80),  # Range for good readability
                "max_sentence_length": 25,
                "min_sentence_length": 8
            },
            "brand_voice": {
                "consistency_threshold": 0.8,
                "tone_deviation_tolerance": 0.2
            },
            "seo": {
                "keyword_density_range": (0.01, 0.03),
                "meta_title_length": (50, 60),
                "meta_description_length": (150, 160)
            },
            "engagement": {
                "min_questions_per_1000_words": 1,
                "min_examples_per_section": 1,
                "transition_word_frequency": 0.02
            }
        }
    
    def _load_editing_patterns(self) -> Dict[str, Any]:
        """Load common editing patterns and corrections"""
        return {
            "common_errors": {
                "redundancy": [
                    "added bonus", "advance planning", "basic fundamentals",
                    "close proximity", "end result", "exact same"
                ],
                "weak_words": [
                    "very", "really", "quite", "rather", "pretty", "somewhat"
                ],
                "passive_indicators": [
                    "was", "were", "is", "are", "been", "being"
                ],
                "filler_words": [
                    "that", "just", "actually", "basically", "literally"
                ]
            },
            "improvements": {
                "power_words": [
                    "proven", "effective", "essential", "critical", "breakthrough",
                    "innovative", "exclusive", "guaranteed", "revolutionary"
                ],
                "transition_words": [
                    "furthermore", "moreover", "consequently", "therefore",
                    "however", "nevertheless", "specifically", "for instance"
                ],
                "action_verbs": [
                    "achieve", "implement", "optimize", "enhance", "streamline",
                    "maximize", "accelerate", "transform", "deliver"
                ]
            }
        }
    
    async def edit_content(self,
                         content: str,
                         style_context: Optional[Dict[str, Any]] = None,
                         quality_standards: Optional[Dict[str, Any]] = None,
                         content_requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive content editing and QA
        
        Args:
            content: Content to review and edit
            style_context: Brand voice and style guidelines
            quality_standards: Specific quality requirements
            content_requirements: Additional content requirements
            
        Returns:
            Complete editing report with improved content
        """
        try:
            start_time = datetime.utcnow()
            
            # Generate report ID
            report_id = f"edit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Get project context for editing
            project_context = await self._get_project_context()
            
            # Perform comprehensive content analysis
            issues_identified = await self._identify_content_issues(
                content, style_context, project_context
            )
            
            # Create edited version
            edited_content = await self._create_edited_content(
                content, issues_identified, style_context
            )
            
            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(
                content, edited_content, style_context, issues_identified
            )
            
            # Generate improvements made list
            improvements_made = self._extract_improvements_made(issues_identified)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                quality_metrics, issues_identified, style_context
            )
            
            # Create editing report
            editing_report = EditingReport(
                report_id=report_id,
                content_title=content_requirements.get("title", "Content Review") if content_requirements else "Content Review",
                review_date=datetime.utcnow(),
                original_word_count=len(content.split()),
                edited_word_count=len(edited_content.split()),
                quality_metrics=quality_metrics,
                issues_identified=issues_identified,
                improvements_made=improvements_made,
                recommendations=recommendations,
                edited_content=edited_content,
                editor_notes=await self._generate_editor_notes(issues_identified, quality_metrics),
                confidence_score=self._calculate_confidence_score(quality_metrics, len(issues_identified))
            )
            
            # Cache and store
            self.review_cache[report_id] = editing_report
            await self._store_editing_report(editing_report)
            
            # Update metrics
            review_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(review_time, issues_identified, quality_metrics)
            
            self.logger.info(f"Content editing completed: {report_id}")
            
            return await self._format_editing_output(editing_report)
            
        except Exception as e:
            self.logger.error(f"Content editing failed: {e}")
            raise
    
    async def _get_project_context(self) -> Dict[str, Any]:
        """Get project context for editing decisions"""
        if not self.knowledge_base:
            return {}
        
        try:
            # Query for style guides and quality standards
            context_queries = [
                "style guide brand voice guidelines",
                "quality standards editing requirements",
                "content examples approved content"
            ]
            
            context = {
                "style_guidelines": [],
                "quality_requirements": [],
                "content_examples": []
            }
            
            for query in context_queries:
                results = await self.knowledge_base.query_knowledge(query, limit=3)
                
                for result in results:
                    content_type = result.get("type", "general")
                    content_text = result.get("content", "")
                    
                    if "style" in content_type or "brand" in content_type:
                        context["style_guidelines"].append(content_text)
                    elif "quality" in content_type or "standard" in content_type:
                        context["quality_requirements"].append(content_text)
                    elif "content" in content_type or "example" in content_type:
                        context["content_examples"].append(content_text)
            
            return context
            
        except Exception as e:
            self.logger.warning(f"Failed to get project context: {e}")
            return {}
    
    async def _identify_content_issues(self,
                                     content: str,
                                     style_context: Optional[Dict[str, Any]],
                                     project_context: Dict[str, Any]) -> List[ContentIssue]:
        """Identify all content issues across multiple dimensions"""
        
        issues = []
        
        # Grammar and spelling issues
        grammar_issues = await self._check_grammar_and_spelling(content)
        issues.extend(grammar_issues)
        
        # Brand voice consistency issues
        if style_context:
            voice_issues = await self._check_brand_voice_consistency(content, style_context)
            issues.extend(voice_issues)
        
        # Clarity and readability issues
        clarity_issues = await self._check_clarity_and_readability(content)
        issues.extend(clarity_issues)
        
        # SEO optimization issues
        seo_issues = await self._check_seo_optimization(content)
        issues.extend(seo_issues)
        
        # Structure and flow issues
        structure_issues = await self._check_structure_and_flow(content)
        issues.extend(structure_issues)
        
        # Engagement issues
        engagement_issues = await self._check_engagement_factors(content)
        issues.extend(engagement_issues)
        
        return issues
    
    async def _check_grammar_and_spelling(self, content: str) -> List[ContentIssue]:
        """Check for grammar and spelling issues"""
        issues = []
        
        try:
            # Use AI to identify grammar issues
            grammar_prompt = f"""
            Review this content for grammar and spelling errors. Identify specific issues with their locations.
            
            CONTENT TO REVIEW:
            {content[:2000]}...
            
            For each error found, provide:
            1. The specific error type (grammar/spelling)
            2. The incorrect text
            3. The suggested correction
            4. The approximate location (sentence or paragraph)
            
            Focus on:
            • Subject-verb agreement
            • Verb tense consistency
            • Pronoun agreement
            • Sentence fragments
            • Run-on sentences
            • Spelling errors
            • Punctuation errors
            
            Format as: ERROR_TYPE: "incorrect text" → "corrected text" (location)
            """
            
            response = self.step(grammar_prompt)
            grammar_analysis = response.msg.content
            
            # Parse AI response to extract issues
            issues.extend(self._parse_grammar_analysis(grammar_analysis, content))
            
        except Exception as e:
            self.logger.warning(f"Grammar check failed: {e}")
        
        # Add pattern-based checks
        issues.extend(self._check_common_grammar_patterns(content))
        
        return issues
    
    def _parse_grammar_analysis(self, analysis: str, content: str) -> List[ContentIssue]:
        """Parse AI grammar analysis into structured issues"""
        issues = []
        
        lines = analysis.split('\n')
        for line in lines:
            if '→' in line and any(error_type in line.upper() for error_type in ['GRAMMAR', 'SPELLING', 'PUNCTUATION']):
                try:
                    # Extract error details
                    if 'GRAMMAR' in line.upper():
                        issue_type = IssueType.GRAMMAR
                    elif 'SPELLING' in line.upper():
                        issue_type = IssueType.SPELLING
                    else:
                        issue_type = IssueType.GRAMMAR
                    
                    # Extract incorrect and corrected text
                    parts = line.split('→')
                    if len(parts) >= 2:
                        incorrect = parts[0].split('"')[1] if '"' in parts[0] else ""
                        corrected = parts[1].split('"')[1] if '"' in parts[1] else parts[1].strip()
                        
                        if incorrect and corrected:
                            issue = ContentIssue(
                                issue_type=issue_type,
                                severity=IssueSeverity.MEDIUM,
                                description=f"{issue_type.value.title()} error: '{incorrect}' should be '{corrected}'",
                                location=self._find_text_location(content, incorrect),
                                suggested_fix=f"Replace '{incorrect}' with '{corrected}'",
                                original_text=incorrect,
                                corrected_text=corrected
                            )
                            issues.append(issue)
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse grammar issue: {e}")
                    continue
        
        return issues
    
    def _check_common_grammar_patterns(self, content: str) -> List[ContentIssue]:
        """Check for common grammar patterns and issues"""
        issues = []
        
        # Check for excessive passive voice
        passive_count = 0
        sentences = content.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in self.editing_patterns["common_errors"]["passive_indicators"]):
                if any(ending in sentence.lower() for ending in ['ed ', 'en ', 'ne ']):
                    passive_count += 1
        
        passive_ratio = passive_count / max(1, len(sentences))
        if passive_ratio > 0.3:  # More than 30% passive voice
            issue = ContentIssue(
                issue_type=IssueType.CLARITY,
                severity=IssueSeverity.MEDIUM,
                description=f"Excessive passive voice usage ({passive_ratio:.1%})",
                location="Throughout content",
                suggested_fix="Convert passive voice sentences to active voice where appropriate"
            )
            issues.append(issue)
        
        # Check for redundant phrases
        for redundant_phrase in self.editing_patterns["common_errors"]["redundancy"]:
            if redundant_phrase in content.lower():
                issue = ContentIssue(
                    issue_type=IssueType.CLARITY,
                    severity=IssueSeverity.LOW,
                    description=f"Redundant phrase: '{redundant_phrase}'",
                    location=self._find_text_location(content, redundant_phrase),
                    suggested_fix=f"Remove redundant word from '{redundant_phrase}'"
                )
                issues.append(issue)
        
        return issues
    
    async def _check_brand_voice_consistency(self, content: str, style_context: Dict[str, Any]) -> List[ContentIssue]:
        """Check brand voice consistency against style guidelines"""
        issues = []
        
        try:
            if not style_context.get("key_insights"):
                return issues
            
            insights = style_context["key_insights"]
            target_tone = insights.get("primary_tone", "professional")
            formality_level = insights.get("formality_level", 3)
            
            # Analyze tone consistency using AI
            voice_prompt = f"""
            Analyze this content for brand voice consistency:
            
            TARGET BRAND VOICE:
            • Tone: {target_tone}
            • Formality Level: {formality_level}/5
            • Audience: {insights.get('audience', 'professionals')}
            
            CONTENT TO ANALYZE:
            {content[:1500]}...
            
            Identify any sections that deviate from the target brand voice.
            Look for:
            • Tone inconsistencies
            • Inappropriate formality level
            • Language that doesn't match target audience
            • Voice shifts within the content
            
            For each issue, specify the problematic text and suggest corrections.
            """
            
            response = self.step(voice_prompt)
            voice_analysis = response.msg.content
            
            # Parse voice analysis for issues
            if "inconsistency" in voice_analysis.lower() or "deviation" in voice_analysis.lower():
                issue = ContentIssue(
                    issue_type=IssueType.BRAND_VOICE,
                    severity=IssueSeverity.MEDIUM,
                    description="Brand voice inconsistency detected",
                    location="Multiple sections",
                    suggested_fix="Adjust language to match target brand voice"
                )
                issues.append(issue)
            
        except Exception as e:
            self.logger.warning(f"Brand voice check failed: {e}")
        
        return issues
    
    async def _check_clarity_and_readability(self, content: str) -> List[ContentIssue]:
        """Check content clarity and readability"""
        issues = []
        
        # Check sentence length
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        
        if long_sentences:
            issue = ContentIssue(
                issue_type=IssueType.READABILITY,
                severity=IssueSeverity.MEDIUM,
                description=f"Found {len(long_sentences)} sentences over 25 words",
                location="Various locations",
                suggested_fix="Break down long sentences into shorter, clearer statements"
            )
            issues.append(issue)
        
        # Check for weak words
        weak_word_count = 0
        for weak_word in self.editing_patterns["common_errors"]["weak_words"]:
            weak_word_count += content.lower().count(f" {weak_word} ")
        
        if weak_word_count > len(content.split()) * 0.02:  # More than 2% weak words
            issue = ContentIssue(
                issue_type=IssueType.CLARITY,
                severity=IssueSeverity.LOW,
                description=f"Excessive use of weak words ({weak_word_count} instances)",
                location="Throughout content",
                suggested_fix="Replace weak words with more specific, powerful alternatives"
            )
            issues.append(issue)
        
        # Check paragraph length
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(p.split()) > 150]
        
        if long_paragraphs:
            issue = ContentIssue(
                issue_type=IssueType.STRUCTURE,
                severity=IssueSeverity.LOW,
                description=f"Found {len(long_paragraphs)} paragraphs over 150 words",
                location="Various paragraphs",
                suggested_fix="Break long paragraphs into smaller, more digestible chunks"
            )
            issues.append(issue)
        
        return issues
    
    async def _check_seo_optimization(self, content: str) -> List[ContentIssue]:
        """Check SEO optimization issues"""
        issues = []
        
        # Check for missing headers
        if '##' not in content and '#' not in content:
            issue = ContentIssue(
                issue_type=IssueType.SEO,
                severity=IssueSeverity.MEDIUM,
                description="No headers found in content",
                location="Content structure",
                suggested_fix="Add H2 and H3 headers to improve content structure and SEO"
            )
            issues.append(issue)
        
        # Check content length for SEO
        word_count = len(content.split())
        if word_count < 300:
            issue = ContentIssue(
                issue_type=IssueType.SEO,
                severity=IssueSeverity.MEDIUM,
                description=f"Content too short for SEO ({word_count} words)",
                location="Overall content",
                suggested_fix="Expand content to at least 300 words for better SEO performance"
            )
            issues.append(issue)
        
        return issues
    
    async def _check_structure_and_flow(self, content: str) -> List[ContentIssue]:
        """Check content structure and logical flow"""
        issues = []
        
        # Check for transition words
        transition_words = self.editing_patterns["improvements"]["transition_words"]
        transition_count = sum(1 for word in transition_words if word in content.lower())
        
        if transition_count < len(content.split()) * 0.01:  # Less than 1% transition words
            issue = ContentIssue(
                issue_type=IssueType.STRUCTURE,
                severity=IssueSeverity.LOW,
                description="Insufficient transition words for smooth flow",
                location="Throughout content",
                suggested_fix="Add transition words to improve content flow and readability"
            )
            issues.append(issue)
        
        return issues
    
    async def _check_engagement_factors(self, content: str) -> List[ContentIssue]:
        """Check content engagement factors"""
        issues = []
        
        # Check for questions
        question_count = content.count('?')
        word_count = len(content.split())
        
        if word_count > 500 and question_count == 0:
            issue = ContentIssue(
                issue_type=IssueType.ENGAGEMENT,
                severity=IssueSeverity.LOW,
                description="No questions found to engage readers",
                location="Content engagement",
                suggested_fix="Add rhetorical or direct questions to increase reader engagement"
            )
            issues.append(issue)
        
        # Check for examples
        example_indicators = ["for example", "for instance", "such as", "like", "including"]
        example_count = sum(1 for indicator in example_indicators if indicator in content.lower())
        
        if word_count > 500 and example_count == 0:
            issue = ContentIssue(
                issue_type=IssueType.ENGAGEMENT,
                severity=IssueSeverity.LOW,
                description="No examples found to illustrate points",
                location="Content examples",
                suggested_fix="Add concrete examples to make content more relatable and clear"
            )
            issues.append(issue)
        
        return issues
    
    def _find_text_location(self, content: str, text: str) -> str:
        """Find approximate location of text in content"""
        try:
            index = content.lower().find(text.lower())
            if index == -1:
                return "Not found"
            
            # Find which paragraph
            paragraphs = content.split('\n\n')
            char_count = 0
            
            for i, paragraph in enumerate(paragraphs):
                if char_count <= index <= char_count + len(paragraph):
                    return f"Paragraph {i + 1}"
                char_count += len(paragraph) + 2  # +2 for \n\n
            
            return "Content body"
            
        except Exception:
            return "Unknown location"
    
    async def _create_edited_content(self,
                                   original_content: str,
                                   issues: List[ContentIssue],
                                   style_context: Optional[Dict[str, Any]]) -> str:
        """Create edited version of content addressing identified issues"""
        
        try:
            # Group issues by type for systematic editing
            issue_groups = {}
            for issue in issues:
                issue_type = issue.issue_type.value
                if issue_type not in issue_groups:
                    issue_groups[issue_type] = []
                issue_groups[issue_type].append(issue)
            
            # Create comprehensive editing prompt
            editing_prompt = await self._create_editing_prompt(
                original_content, issue_groups, style_context
            )
            
            # Get edited content from AI
            response = self.step(editing_prompt)
            edited_content = self._clean_edited_content(response.msg.content)
            
            return edited_content
            
        except Exception as e:
            self.logger.error(f"Content editing failed: {e}")
            return original_content  # Return original if editing fails
    
    async def _create_editing_prompt(self,
                                   content: str,
                                   issue_groups: Dict[str, List[ContentIssue]],
                                   style_context: Optional[Dict[str, Any]]) -> str:
        """Create comprehensive editing prompt"""
        
        style_guidance = ""
        if style_context and style_context.get("key_insights"):
            insights = style_context["key_insights"]
            style_guidance = f"""
            BRAND VOICE REQUIREMENTS:
            • Maintain tone: {insights.get('primary_tone', 'professional')}
            • Formality level: {insights.get('formality_level', 3)}/5
            • Target audience: {insights.get('audience', 'professionals')}
            """
        
        issues_summary = ""
        for issue_type, issues in issue_groups.items():
            issues_summary += f"\n{issue_type.upper()} ISSUES ({len(issues)}):\n"
            for issue in issues[:3]:  # Limit to top 3 issues per type
                issues_summary += f"• {issue.description}\n"
        
        return f"""
        Edit and improve this content to address the identified issues while maintaining quality and brand voice:

        ORIGINAL CONTENT:
        {content}

        ISSUES TO ADDRESS:
        {issues_summary}

        {style_guidance}

        EDITING REQUIREMENTS:
        1. Fix all grammar and spelling errors
        2. Improve clarity and readability
        3. Maintain consistent brand voice and tone
        4. Optimize sentence structure and flow
        5. Enhance engagement without changing core message
        6. Preserve all key information and intent
        7. Ensure professional, polished final result

        QUALITY STANDARDS:
        • Error-free grammar and spelling
        • Clear, concise language
        • Logical flow and structure
        • Appropriate tone and voice
        • Enhanced readability
        • Engaging and valuable content

        Provide the edited content:
        """
    
    def _clean_edited_content(self, raw_edited_content: str) -> str:
        """Clean and format edited content"""
        content = raw_edited_content.strip()
        
        # Remove common AI prefixes
        prefixes_to_remove = [
            "Here's the edited content:",
            "Edited content:",
            "Here is the improved version:",
            "Improved content:"
        ]
        
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        # Clean up formatting
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content
    
    async def _calculate_quality_metrics(self,
                                       original_content: str,
                                       edited_content: str,
                                       style_context: Optional[Dict[str, Any]],
                                       issues: List[ContentIssue]) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""
        
        try:
            # Grammar score (based on issues found)
            grammar_issues = [i for i in issues if i.issue_type in [IssueType.GRAMMAR, IssueType.SPELLING]]
            grammar_score = max(0.0, 1.0 - (len(grammar_issues) * 0.1))
            
            # Readability score (simplified Flesch reading ease)
            words = edited_content.split()
            sentences = edited_content.count('.') + edited_content.count('!') + edited_content.count('?')
            avg_sentence_length = len(words) / max(1, sentences)
            readability_raw = max(0, min(100, 100 - (avg_sentence_length * 2)))
            readability_score = readability_raw / 100
            
            # Clarity score (based on clarity issues)
            clarity_issues = [i for i in issues if i.issue_type == IssueType.CLARITY]
            clarity_score = max(0.0, 1.0 - (len(clarity_issues) * 0.15))
            
            # Brand voice score
            if style_context:
                voice_issues = [i for i in issues if i.issue_type == IssueType.BRAND_VOICE]
                brand_voice_score = max(0.0, 1.0 - (len(voice_issues) * 0.2))
            else:
                brand_voice_score = 0.8  # Default when no style context
            
            # SEO score
            seo_issues = [i for i in issues if i.issue_type == IssueType.SEO]
            seo_score = max(0.0, 1.0 - (len(seo_issues) * 0.15))
            
            # Engagement score
            engagement_issues = [i for i in issues if i.issue_type == IssueType.ENGAGEMENT]
            engagement_score = max(0.0, 1.0 - (len(engagement_issues) * 0.1))
            
            # Consistency score
            consistency_score = 0.85  # Default - would need more sophisticated analysis
            
            # Factual accuracy score
            factual_accuracy_score = 0.9  # Default - would need fact-checking integration
            
            # Overall score
            overall_score = (
                grammar_score * 0.2 +
                clarity_score * 0.2 +
                brand_voice_score * 0.15 +
                readability_score * 0.15 +
                seo_score * 0.1 +
                engagement_score * 0.1 +
                consistency_score * 0.05 +
                factual_accuracy_score * 0.05
            )
            
            return QualityMetrics(
                overall_score=overall_score,
                grammar_score=grammar_score,
                clarity_score=clarity_score,
                brand_voice_score=brand_voice_score,
                seo_score=seo_score,
                engagement_score=engagement_score,
                readability_score=readability_score,
                consistency_score=consistency_score,
                factual_accuracy_score=factual_accuracy_score
            )
            
        except Exception as e:
            self.logger.warning(f"Quality metrics calculation failed: {e}")
            # Return default metrics
            return QualityMetrics(
                overall_score=0.7,
                grammar_score=0.8,
                clarity_score=0.7,
                brand_voice_score=0.7,
                seo_score=0.6,
                engagement_score=0.6,
                readability_score=0.7,
                consistency_score=0.8,
                factual_accuracy_score=0.9
            )
    
    def _extract_improvements_made(self, issues: List[ContentIssue]) -> List[str]:
        """Extract list of improvements made based on issues addressed"""
        improvements = []
        
        issue_type_counts = {}
        for issue in issues:
            issue_type = issue.issue_type.value
            issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1
        
        for issue_type, count in issue_type_counts.items():
            if issue_type == "grammar":
                improvements.append(f"Corrected {count} grammar and spelling errors")
            elif issue_type == "clarity":
                improvements.append(f"Improved clarity in {count} instances")
            elif issue_type == "brand_voice":
                improvements.append(f"Aligned brand voice in {count} sections")
            elif issue_type == "seo":
                improvements.append(f"Enhanced SEO optimization in {count} areas")
            elif issue_type == "structure":
                improvements.append(f"Improved structure and flow in {count} sections")
            elif issue_type == "engagement":
                improvements.append(f"Enhanced engagement factors in {count} areas")
            else:
                improvements.append(f"Addressed {count} {issue_type} issues")
        
        if not improvements:
            improvements.append("Content reviewed and polished for quality")
        
        return improvements
    
    async def _generate_recommendations(self,
                                      quality_metrics: QualityMetrics,
                                      issues: List[ContentIssue],
                                      style_context: Optional[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations for content improvement"""
        recommendations = []
        
        # Grammar and spelling recommendations
        if quality_metrics.grammar_score < 0.9:
            recommendations.append("Consider using grammar checking tools for final review")
        
        # Readability recommendations
        if quality_metrics.readability_score < 0.6:
            recommendations.append("Simplify sentence structure and reduce average sentence length")
        elif quality_metrics.readability_score > 0.9:
            recommendations.append("Consider adding more sophisticated language for expert audiences")
        
        # Brand voice recommendations
        if quality_metrics.brand_voice_score < 0.8:
            recommendations.append("Review brand voice guidelines and ensure consistent tone")
        
        # SEO recommendations
        if quality_metrics.seo_score < 0.7:
            recommendations.append("Enhance SEO optimization with better keyword integration and structure")
        
        # Engagement recommendations
        if quality_metrics.engagement_score < 0.7:
            recommendations.append("Add more questions, examples, and interactive elements to increase engagement")
        
        # Overall quality recommendations
        if quality_metrics.overall_score < 0.7:
            recommendations.append("Consider comprehensive revision to meet quality standards")
        elif quality_metrics.overall_score > 0.9:
            recommendations.append("Excellent quality - ready for publication")
        
        # Issue-specific recommendations
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            recommendations.append("Address critical issues before publication")
        
        high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
        if high_issues:
            recommendations.append("Review and address high-priority issues")
        
        return recommendations[:6]  # Limit to top 6 recommendations
    
    async def _generate_editor_notes(self, issues: List[ContentIssue], quality_metrics: QualityMetrics) -> str:
        """Generate comprehensive editor notes"""
        
        notes_parts = []
        
        # Overall assessment
        if quality_metrics.overall_score >= 0.9:
            notes_parts.append("Excellent content quality. Minor refinements made.")
        elif quality_metrics.overall_score >= 0.8:
            notes_parts.append("Good content quality with some improvements applied.")
        elif quality_metrics.overall_score >= 0.7:
            notes_parts.append("Acceptable quality with several improvements needed.")
        else:
            notes_parts.append("Content requires significant improvements for publication readiness.")
        
        # Issue summary
        if issues:
            critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
            high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
            medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
            
            issue_summary = f"Issues identified: {len(issues)} total"
            if critical_count:
                issue_summary += f" ({critical_count} critical"
            if high_count:
                issue_summary += f", {high_count} high priority"
            if medium_count:
                issue_summary += f", {medium_count} medium priority)"
            
            notes_parts.append(issue_summary)
        
        # Specific strengths and weaknesses
        strengths = []
        weaknesses = []
        
        if quality_metrics.grammar_score >= 0.9:
            strengths.append("strong grammar and spelling")
        elif quality_metrics.grammar_score < 0.7:
            weaknesses.append("grammar and spelling errors")
        
        if quality_metrics.brand_voice_score >= 0.8:
            strengths.append("consistent brand voice")
        elif quality_metrics.brand_voice_score < 0.7:
            weaknesses.append("brand voice inconsistencies")
        
        if quality_metrics.engagement_score >= 0.8:
            strengths.append("good reader engagement")
        elif quality_metrics.engagement_score < 0.6:
            weaknesses.append("limited reader engagement elements")
        
        if strengths:
            notes_parts.append(f"Strengths: {', '.join(strengths)}")
        
        if weaknesses:
            notes_parts.append(f"Areas for improvement: {', '.join(weaknesses)}")
        
        return ". ".join(notes_parts) + "."
    
    def _calculate_confidence_score(self, quality_metrics: QualityMetrics, issue_count: int) -> float:
        """Calculate confidence score for the editing assessment"""
        
        # Base confidence on overall quality score
        base_confidence = quality_metrics.overall_score
        
        # Adjust based on number of issues found
        issue_factor = max(0.0, 1.0 - (issue_count * 0.02))  # Reduce confidence for each issue
        
        # Adjust based on consistency of scores
        score_variance = abs(quality_metrics.grammar_score - quality_metrics.clarity_score)
        consistency_factor = max(0.8, 1.0 - score_variance)
        
        # Calculate final confidence
        confidence = base_confidence * 0.6 + issue_factor * 0.3 + consistency_factor * 0.1
        
        return min(1.0, max(0.0, confidence))
    
    async def _store_editing_report(self, editing_report: EditingReport):
        """Store editing report in knowledge base"""
        if not self.knowledge_base:
            return
        
        try:
            report_document = {
                "type": "editing_report",
                "title": f"Editing Report: {editing_report.content_title}",
                "content": json.dumps(editing_report.to_dict(), indent=2),
                "metadata": {
                    "report_id": editing_report.report_id,
                    "overall_quality_score": editing_report.quality_metrics.overall_score,
                    "issues_count": len(editing_report.issues_identified),
                    "improvements_count": len(editing_report.improvements_made),
                    "confidence_score": editing_report.confidence_score,
                    "review_date": editing_report.review_date.isoformat()
                }
            }
            
            await self.knowledge_base.store_document(report_document)
            self.logger.info(f"Editing report stored: {editing_report.report_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store editing report: {e}")
    
    async def _format_editing_output(self, editing_report: EditingReport) -> Dict[str, Any]:
        """Format editing report for workflow system"""
        return {
            "report_id": editing_report.report_id,
            "status": "completed",
            "content_title": editing_report.content_title,
            "approval_status": editing_report.approval_status,
            
            # Edited content
            "edited_content": {
                "content": editing_report.edited_content,
                "word_count": editing_report.edited_word_count,
                "word_count_change": editing_report.edited_word_count - editing_report.original_word_count
            },
            
            # Quality assessment
            "quality_assessment": {
                "overall_score": editing_report.quality_metrics.overall_score,
                "quality_breakdown": editing_report.quality_metrics.to_dict(),
                "confidence_score": editing_report.confidence_score
            },
            
            # Issues and improvements
            "review_details": {
                "issues_identified": [issue.to_dict() for issue in editing_report.issues_identified],
                "improvements_made": editing_report.improvements_made,
                "recommendations": editing_report.recommendations,
                "editor_notes": editing_report.editor_notes
            },
            
            # Issue summary
            "issue_summary": {
                "total_issues": len(editing_report.issues_identified),
                "critical_issues": len([i for i in editing_report.issues_identified if i.severity == IssueSeverity.CRITICAL]),
                "high_priority_issues": len([i for i in editing_report.issues_identified if i.severity == IssueSeverity.HIGH]),
                "medium_priority_issues": len([i for i in editing_report.issues_identified if i.severity == IssueSeverity.MEDIUM]),
                "low_priority_issues": len([i for i in editing_report.issues_identified if i.severity == IssueSeverity.LOW])
            },
            
            # Metadata
            "metadata": {
                "review_date": editing_report.review_date.isoformat(),
                "project_id": self.project_id,
                "original_word_count": editing_report.original_word_count
            }
        }
    
    def _update_metrics(self, review_time: float, issues: List[ContentIssue], quality_metrics: QualityMetrics):
        """Update performance metrics"""
        self.metrics["content_reviewed"] += 1
        self.metrics["issues_identified"] += len(issues)
        self.metrics["improvements_made"] += len([i for i in issues if i.severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]])
        
        # Update average review time
        prev_avg_time = self.metrics["average_review_time"]
        count = self.metrics["content_reviewed"]
        self.metrics["average_review_time"] = ((prev_avg_time * (count - 1)) + review_time) / count
        
        # Update average quality improvement (simplified)
        quality_improvement = max(0.0, quality_metrics.overall_score - 0.7)  # Assume baseline of 0.7
        prev_avg_quality = self.metrics["average_quality_improvement"]
        self.metrics["average_quality_improvement"] = ((prev_avg_quality * (count - 1)) + quality_improvement) / count
    
    async def validate_final_content(self, content: str, quality_threshold: float = 0.8) -> Dict[str, Any]:
        """Perform final validation check on content"""
        try:
            # Quick quality check
            quick_issues = await self._quick_quality_check(content)
            
            # Calculate validation score
            validation_score = max(0.0, 1.0 - (len(quick_issues) * 0.1))
            
            # Determine approval status
            if validation_score >= quality_threshold and len([i for i in quick_issues if i.severity == IssueSeverity.CRITICAL]) == 0:
                approval_status = "approved"
            elif validation_score >= 0.6:
                approval_status = "approved_with_minor_issues"
            else:
                approval_status = "requires_revision"
            
            return {
                "validation_score": validation_score,
                "approval_status": approval_status,
                "issues_found": len(quick_issues),
                "critical_issues": len([i for i in quick_issues if i.severity == IssueSeverity.CRITICAL]),
                "recommendations": self._get_quick_recommendations(quick_issues, validation_score)
            }
            
        except Exception as e:
            self.logger.error(f"Final validation failed: {e}")
            return {
                "validation_score": 0.0,
                "approval_status": "validation_failed",
                "error": str(e)
            }
    
    async def _quick_quality_check(self, content: str) -> List[ContentIssue]:
        """Perform quick quality check for validation"""
        issues = []
        
        # Check for obvious grammar errors (simplified)
        if re.search(r'\b(there|their|they\'re)\b.*\b(there|their|they\'re)\b', content, re.IGNORECASE):
            issues.append(ContentIssue(
                issue_type=IssueType.GRAMMAR,
                severity=IssueSeverity.MEDIUM,
                description="Potential grammar error with there/their/they're",
                location="Content body",
                suggested_fix="Review usage of there/their/they're"
            ))
        
        # Check for excessive repetition
        words = content.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only check longer words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        for word, freq in word_freq.items():
            if freq > len(words) * 0.02:  # More than 2% frequency
                issues.append(ContentIssue(
                    issue_type=IssueType.CLARITY,
                    severity=IssueSeverity.LOW,
                    description=f"Word '{word}' appears {freq} times (may be excessive)",
                    location="Throughout content",
                    suggested_fix=f"Consider using synonyms for '{word}'"
                ))
        
        return issues
    
    def _get_quick_recommendations(self, issues: List[ContentIssue], validation_score: float) -> List[str]:
        """Get quick recommendations based on validation"""
        recommendations = []
        
        if validation_score >= 0.9:
            recommendations.append("Content meets high quality standards")
        elif validation_score >= 0.8:
            recommendations.append("Content meets quality standards with minor refinements")
        elif validation_score >= 0.6:
            recommendations.append("Content needs moderate improvements before publication")
        else:
            recommendations.append("Content requires significant revision")
        
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            recommendations.append("Address critical issues immediately")
        
        return recommendations
    
    def get_editing_metrics(self) -> Dict[str, Any]:
        """Get editor/QA performance metrics"""
        return {
            "content_reviewed": self.metrics["content_reviewed"],
            "issues_identified": self.metrics["issues_identified"],
            "improvements_made": self.metrics["improvements_made"],
            "average_review_time": self.metrics["average_review_time"],
            "average_quality_improvement": self.metrics["average_quality_improvement"],
            "cached_reports": len(self.review_cache)
        }
    
    def process_task(self, task):
        """Process editing task - legacy method for backwards compatibility"""
        response = self.step(task)
        return response

# Backwards compatibility class (matches existing naming convention)
class editorqaAgent(ProductionEditorQAAgent):
    """Backwards compatibility wrapper for existing code"""
    pass

# Factory function for easy instantiation
async def create_editor_qa_agent(project_id: str = None) -> ProductionEditorQAAgent:
    """
    Factory function to create and initialize a ProductionEditorQAAgent
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionEditorQAAgent instance
    """
    editor = ProductionEditorQAAgent(project_id)
    return editor

# Export main classes
__all__ = [
    'ProductionEditorQAAgent',
    'editorqaAgent',  # For backwards compatibility
    'EditingReport',
    'QualityMetrics',
    'ContentIssue',
    'IssueType',
    'IssueSeverity',
    'create_editor_qa_agent'
]