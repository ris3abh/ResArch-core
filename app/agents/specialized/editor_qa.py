# app/agents/specialized/editor_qa.py
"""
Production Editor/QA Agent for SpinScribe
Built on CAMEL AI Framework

The Editor/QA Agent reviews and refines content for quality, accuracy,
and alignment with brand guidelines and project requirements.
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
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
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

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
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EditingReport:
    """Comprehensive editing and QA report"""
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
    """
    
    def __init__(self, project_id: str = None, **kwargs):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{project_id or 'standalone'}")
        
        # Initialize system message
        system_message = self._create_editor_system_message()
        super().__init__(system_message=system_message, **kwargs)
        
        # Initialize knowledge base connection
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
        
        # Quality thresholds and standards
        self.quality_standards = {
            "minimum_overall_score": 0.85,
            "minimum_grammar_score": 0.95,
            "minimum_brand_voice_score": 0.80,
            "minimum_clarity_score": 0.85,
            "minimum_seo_score": 0.75,
            "maximum_critical_issues": 0,
            "maximum_high_issues": 2
        }
        
        # Grammar and style rules
        self.grammar_rules = {
            "common_errors": [
                (r'\bthe the\b', 'the'),
                (r'\band and\b', 'and'),
                (r'\bof of\b', 'of'),
                (r'\bit\'s([^a-zA-Z])', r'its\1'),  # it's vs its
                (r'\byour\b(?=\s+going)', 'you\'re'),  # your vs you're
            ],
            "punctuation_fixes": [
                (r'\s+([,.!?;:])', r'\1'),  # Remove space before punctuation
                (r'([,.!?;:])\s*([,.!?;:])', r'\1\2'),  # Remove duplicate punctuation
                (r'\.{3,}', '...'),  # Fix multiple periods
            ]
        }
        
    def _create_editor_system_message(self) -> BaseMessage:
        """Create comprehensive system message for editor/QA role"""
        content = f"""
            You are the Production Editor/QA Agent for SpinScribe, specializing in comprehensive content review and quality assurance.

            CORE RESPONSIBILITIES:
            • Conduct thorough content reviews for grammar, spelling, clarity, and consistency
            • Ensure strict adherence to brand voice guidelines and style requirements
            • Verify SEO optimization and keyword integration quality
            • Identify and correct structural and flow issues
            • Provide detailed feedback and improvement recommendations
            • Ensure content meets all project requirements and quality standards

            EDITORIAL EXPERTISE:
            • Advanced grammar, punctuation, and spelling review
            • Brand voice consistency analysis and correction
            • Content structure optimization for readability and engagement
            • SEO compliance verification and enhancement
            • Tone and style alignment with brand guidelines
            • Cross-reference checking against project requirements

            QUALITY ASSURANCE METHODOLOGY:
            • Multi-pass review process (grammar → style → brand voice → SEO → overall quality)
            • Systematic issue identification with severity classification
            • Detailed improvement tracking and recommendation generation
            • Objective quality scoring across multiple dimensions
            • Comprehensive reporting with actionable feedback

            EDITORIAL STANDARDS:
            • Zero tolerance for grammatical errors and spelling mistakes
            • Brand voice consistency score must exceed 80%
            • Content must achieve minimum 85% overall quality score
            • All critical and high-severity issues must be resolved
            • SEO requirements must be met without compromising readability

            Project ID: {self.project_id or 'Not specified'}
            """
        
        return BaseMessage.make_assistant_message(
            role_name="editor_qa",
            content=content
        )
    
    async def review_content(self, 
                           content: str,
                           content_plan: Optional[Dict[str, Any]] = None,
                           style_guide: Optional[Dict[str, Any]] = None,
                           generation_metadata: Optional[Dict[str, Any]] = None) -> EditingReport:
        """
        Conduct comprehensive content review and generate editing report
        
        Args:
            content: Content to review and edit
            content_plan: Optional content plan for context
            style_guide: Optional style guide for brand voice reference
            generation_metadata: Optional metadata from content generation
            
        Returns:
            Complete EditingReport with analysis and edited content
        """
        self.logger.info("Starting comprehensive content review")
        
        try:
            content_title = content_plan.get('title', 'Untitled Content') if content_plan else 'Untitled Content'
            original_word_count = len(content.split())
            
            # Phase 1: Grammar and mechanics review
            grammar_issues, grammar_corrected = await self._review_grammar_mechanics(content)
            
            # Phase 2: Style and clarity review  
            style_issues, style_corrected = await self._review_style_clarity(grammar_corrected, style_guide)
            
            # Phase 3: Brand voice consistency review
            brand_voice_issues, brand_voice_corrected = await self._review_brand_voice(style_corrected, style_guide)
            
            # Phase 4: SEO optimization review
            seo_issues, seo_corrected = await self._review_seo_optimization(brand_voice_corrected, content_plan)
            
            # Phase 5: Final polish
            structure_issues, final_content = await self._final_polish(seo_corrected, content_plan)
            
            # Compile all issues
            all_issues = grammar_issues + style_issues + brand_voice_issues + seo_issues + structure_issues
            
            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(final_content, content_plan, style_guide, all_issues)
            
            # Generate improvements made summary
            improvements_made = self._generate_improvements_summary(content, final_content, all_issues)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(quality_metrics, all_issues, content_plan)
            
            # Determine approval status
            approval_status = self._determine_approval_status(quality_metrics, all_issues)
            
            # Create comprehensive editing report
            editing_report = EditingReport(
                content_title=content_title,
                review_date=datetime.now(),
                original_word_count=original_word_count,
                edited_word_count=len(final_content.split()),
                quality_metrics=quality_metrics,
                issues_identified=all_issues,
                improvements_made=improvements_made,
                recommendations=recommendations,
                edited_content=final_content,
                editor_notes=await self._generate_editor_notes(all_issues, quality_metrics),
                approval_status=approval_status
            )
            
            # Store report in knowledge base if available
            if self.knowledge_base:
                await self._store_editing_report(editing_report)
            
            self.logger.info(f"Content review completed. Quality score: {quality_metrics.overall_score:.2f}, Issues: {len(all_issues)}")
            
            return editing_report
            
        except Exception as e:
            self.logger.error(f"Content review failed: {e}")
            raise
    
    async def _review_grammar_mechanics(self, content: str) -> Tuple[List[ContentIssue], str]:
        """Review and correct grammar and mechanical errors"""
        
        issues = []
        corrected_content = content
        
        # Apply basic grammar fixes
        for pattern, replacement in self.grammar_rules["common_errors"]:
            matches = list(re.finditer(pattern, corrected_content, re.IGNORECASE))
            for match in reversed(matches):  # Reverse to maintain positions
                original_text = match.group(0)
                corrected_text = re.sub(pattern, replacement, original_text, flags=re.IGNORECASE)
                
                if original_text != corrected_text:
                    issue = ContentIssue(
                        issue_type=IssueType.GRAMMAR,
                        severity=IssueSeverity.MEDIUM,
                        description=f"Grammar error: '{original_text}' should be '{corrected_text}'",
                        location=f"Position {match.start()}-{match.end()}",
                        suggested_fix=f"Replace '{original_text}' with '{corrected_text}'",
                        original_text=original_text,
                        corrected_text=corrected_text
                    )
                    issues.append(issue)
                    
                    # Apply correction
                    corrected_content = corrected_content[:match.start()] + corrected_text + corrected_content[match.end():]
        
        # Apply punctuation fixes
        for pattern, replacement in self.grammar_rules["punctuation_fixes"]:
            old_content = corrected_content
            corrected_content = re.sub(pattern, replacement, corrected_content)
            
            if old_content != corrected_content:
                issue = ContentIssue(
                    issue_type=IssueType.GRAMMAR,
                    severity=IssueSeverity.LOW,
                    description="Punctuation spacing corrected",
                    location="Multiple locations",
                    suggested_fix="Fixed punctuation spacing",
                    original_text="Various punctuation issues",
                    corrected_text="Corrected punctuation"
                )
                issues.append(issue)
        
        # Advanced grammar check using LLM if needed
        if len(issues) > 5:  # Only if many issues found
            advanced_issues, llm_corrected = await self._llm_grammar_check(corrected_content)
            issues.extend(advanced_issues)
            corrected_content = llm_corrected
        
        return issues, corrected_content
    
    async def _llm_grammar_check(self, content: str) -> Tuple[List[ContentIssue], str]:
        """Use LLM for advanced grammar and spelling check"""
        
        grammar_prompt = f"""
            Review the following content for grammar, spelling, and mechanical errors. Provide corrections while preserving the original meaning and style.

            CONTENT TO REVIEW:
            {content[:2000]}  # Limit content length

            INSTRUCTIONS:
            1. Identify and correct any grammar errors
            2. Fix spelling mistakes
            3. Correct punctuation errors
            4. Maintain the original tone and style
            5. Preserve the author's voice and intent

            Provide the corrected content:
            """
        
        try:
            response = self.step(grammar_prompt)
            llm_response = response.msg.content if hasattr(response.msg, 'content') else str(response)
            
            # Clean up the response
            corrected_content = self._clean_llm_response(llm_response)
            
            # Create issue for LLM corrections
            issues = []
            if corrected_content != content and len(corrected_content) > 0:
                issue = ContentIssue(
                    issue_type=IssueType.GRAMMAR,
                    severity=IssueSeverity.MEDIUM,
                    description="Advanced grammar and spelling corrections applied",
                    location="Throughout content",
                    suggested_fix="Applied comprehensive grammar corrections",
                    original_text="Original content with errors",
                    corrected_text="Corrected content"
                )
                issues.append(issue)
            
            return issues, corrected_content if corrected_content else content
            
        except Exception as e:
            self.logger.error(f"LLM grammar check failed: {e}")
            return [], content
    
    async def _review_style_clarity(self, content: str, style_guide: Optional[Dict[str, Any]]) -> Tuple[List[ContentIssue], str]:
        """Review and improve content style and clarity"""
        
        issues = []
        
        # Check for passive voice
        passive_issues = self._identify_passive_voice(content)
        issues.extend(passive_issues)
        
        # Check readability
        readability_issues = await self._check_readability(content)
        issues.extend(readability_issues)
        
        # Apply basic style improvements
        improved_content = self._apply_basic_style_improvements(content)
        
        if improved_content != content:
            issue = ContentIssue(
                issue_type=IssueType.CLARITY,
                severity=IssueSeverity.LOW,
                description="Style and clarity improvements applied",
                location="Throughout content",
                suggested_fix="Enhanced clarity and readability",
                original_text="Original content",
                corrected_text="Improved content"
            )
            issues.append(issue)
        
        return issues, improved_content
    
    def _identify_passive_voice(self, content: str) -> List[ContentIssue]:
        """Identify passive voice constructions"""
        
        issues = []
        
        # Simple passive voice patterns
        passive_patterns = [
            r'\b(was|were|is|are|am|been|being)\s+\w+ed\b',
            r'\b(was|were|is|are|am|been|being)\s+\w+en\b'
        ]
        
        for pattern in passive_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            # Limit to avoid overwhelming feedback
            for match in matches[:3]:
                issue = ContentIssue(
                    issue_type=IssueType.CLARITY,
                    severity=IssueSeverity.LOW,
                    description=f"Passive voice detected: '{match.group(0)}'",
                    location=f"Position {match.start()}-{match.end()}",
                    suggested_fix="Consider using active voice for stronger writing",
                    original_text=match.group(0)
                )
                issues.append(issue)
        
        return issues
    
    async def _check_readability(self, content: str) -> List[ContentIssue]:
        """Check content readability and suggest improvements"""
        
        issues = []
        
        # Check sentence length
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        
        if long_sentences:
            issue = ContentIssue(
                issue_type=IssueType.CLARITY,
                severity=IssueSeverity.MEDIUM,
                description=f"Found {len(long_sentences)} overly long sentences (>30 words)",
                location="Various locations",
                suggested_fix="Break long sentences into shorter, clearer sentences",
                original_text=f"Sentences with {[len(s.split()) for s in long_sentences[:3]]} words"
            )
            issues.append(issue)
        
        # Check paragraph length
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(p.split()) > 150]
        
        if long_paragraphs:
            issue = ContentIssue(
                issue_type=IssueType.STRUCTURE,
                severity=IssueSeverity.LOW,
                description=f"Found {len(long_paragraphs)} overly long paragraphs (>150 words)",
                location="Various locations",
                suggested_fix="Break long paragraphs for better readability",
                original_text="Long paragraph content"
            )
            issues.append(issue)
        
        return issues
    
    def _apply_basic_style_improvements(self, content: str) -> str:
        """Apply basic style improvements"""
        
        improved = content
        
        # Fix double spaces
        improved = re.sub(r'\s+', ' ', improved)
        
        # Fix spacing around punctuation
        improved = re.sub(r'\s+([,.!?;:])', r'\1', improved)
        improved = re.sub(r'([,.!?;:])\s*([,.!?;:])', r'\1\2', improved)
        
        # Fix common style issues
        improved = re.sub(r'\b(very|really|quite|pretty)\s+', '', improved)  # Remove weak intensifiers
        
        return improved.strip()
    
    async def _review_brand_voice(self, content: str, style_guide: Optional[Dict[str, Any]]) -> Tuple[List[ContentIssue], str]:
        """Review and ensure brand voice consistency"""
        
        issues = []
        
        if not style_guide:
            # Cannot review brand voice without style guide
            return issues, content
        
        # Check brand voice consistency
        brand_voice_score = await self._evaluate_brand_voice_consistency(content, style_guide)
        
        if brand_voice_score < 0.8:
            issue = ContentIssue(
                issue_type=IssueType.BRAND_VOICE,
                severity=IssueSeverity.MEDIUM,
                description=f"Brand voice consistency score: {brand_voice_score:.2f}",
                location="Throughout content",
                suggested_fix="Improve alignment with brand voice guidelines",
                original_text="Brand voice inconsistency"
            )
            issues.append(issue)
        
        return issues, content
    
    async def _evaluate_brand_voice_consistency(self, content: str, style_guide: Dict[str, Any]) -> float:
        """Evaluate brand voice consistency"""
        
        try:
            # Extract brand voice requirements
            brand_voice_elements = style_guide.get('brand_voice_elements', {})
            personality_traits = brand_voice_elements.get('personality_traits', [])
            
            # Simple brand voice evaluation
            content_lower = content.lower()
            
            # Check for personality trait indicators
            trait_matches = 0
            for trait in personality_traits[:3]:
                if trait.lower() in content_lower:
                    trait_matches += 1
            
            # Calculate score based on trait presence
            if personality_traits:
                return trait_matches / min(len(personality_traits), 3)
            else:
                return 0.8  # Default score when no traits specified
                
        except Exception as e:
            self.logger.error(f"Brand voice evaluation failed: {e}")
            return 0.7
    
    async def _review_seo_optimization(self, content: str, content_plan: Optional[Dict[str, Any]]) -> Tuple[List[ContentIssue], str]:
        """Review and optimize SEO elements"""
        
        issues = []
        
        if not content_plan or 'seo_strategy' not in content_plan:
            return issues, content
        
        seo_strategy = content_plan['seo_strategy']
        
        # Check keyword density
        keyword_issues = await self._check_keyword_density(content, seo_strategy)
        issues.extend(keyword_issues)
        
        return issues, content
    
    async def _check_keyword_density(self, content: str, seo_strategy: Dict[str, Any]) -> List[ContentIssue]:
        """Check keyword density and distribution"""
        
        issues = []
        content_lower = content.lower()
        word_count = len(content.split())
        
        # Check primary keywords
        primary_keywords = seo_strategy.get('primary_keywords', [])
        for keyword in primary_keywords:
            keyword_count = content_lower.count(keyword.lower())
            density = (keyword_count / word_count) if word_count > 0 else 0
            
            if density < 0.01:  # Less than 1%
                issue = ContentIssue(
                    issue_type=IssueType.SEO,
                    severity=IssueSeverity.MEDIUM,
                    description=f"Low keyword density for '{keyword}': {density:.1%}",
                    location="Throughout content",
                    suggested_fix=f"Increase usage of '{keyword}' to reach 1-2% density",
                    original_text=f"Current density: {density:.1%}"
                )
                issues.append(issue)
            elif density > 0.025:  # More than 2.5%
                issue = ContentIssue(
                    issue_type=IssueType.SEO,
                    severity=IssueSeverity.MEDIUM,
                    description=f"High keyword density for '{keyword}': {density:.1%}",
                    location="Throughout content",
                    suggested_fix=f"Reduce usage of '{keyword}' to avoid keyword stuffing",
                    original_text=f"Current density: {density:.1%}"
                )
                issues.append(issue)
        
        return issues
    
    async def _final_polish(self, content: str, content_plan: Optional[Dict[str, Any]]) -> Tuple[List[ContentIssue], str]:
        """Apply final polish and check structure"""
        
        issues = []
        
        # Check content structure
        structure_issues = await self._check_content_structure(content)
        issues.extend(structure_issues)
        
        # Apply final formatting
        polished_content = self._apply_final_formatting(content)
        
        return issues, polished_content
    
    async def _check_content_structure(self, content: str) -> List[ContentIssue]:
        """Check content structure and organization"""
        
        issues = []
        
        # Check for headers/subheaders
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        if len(headers) < 2 and len(content.split()) > 500:
            issue = ContentIssue(
                issue_type=IssueType.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                description="Long content lacks sufficient headers for structure",
                location="Content organization",
                suggested_fix="Add headers and subheaders to improve content structure",
                original_text="Unstructured content"
            )
            issues.append(issue)
        
        return issues
    
    def _apply_final_formatting(self, content: str) -> str:
        """Apply final formatting improvements"""
        
        formatted = content
        
        # Ensure proper spacing
        formatted = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted)
        formatted = re.sub(r' +', ' ', formatted)
        
        return formatted.strip()
    
    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response to extract only the content"""
        
        # Remove common LLM response prefixes
        prefixes_to_remove = [
            "Here's the corrected content:",
            "Here is the corrected content:",
            "Corrected content:",
            "Here's the improved content:",
            "CORRECTED CONTENT:",
        ]
        
        cleaned = response.strip()
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned
    
    async def _calculate_quality_metrics(self, 
                                       content: str,
                                       content_plan: Optional[Dict[str, Any]],
                                       style_guide: Optional[Dict[str, Any]],
                                       issues: List[ContentIssue]) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""
        
        # Base scores
        grammar_score = 1.0 - (len([i for i in issues if i.issue_type == IssueType.GRAMMAR]) * 0.1)
        clarity_score = 1.0 - (len([i for i in issues if i.issue_type == IssueType.CLARITY]) * 0.1)
        brand_voice_score = 1.0 - (len([i for i in issues if i.issue_type == IssueType.BRAND_VOICE]) * 0.15)
        seo_score = 1.0 - (len([i for i in issues if i.issue_type == IssueType.SEO]) * 0.1)
        
        # Calculate engagement and readability scores
        engagement_score = await self._calculate_engagement_score(content)
        readability_score = await self._calculate_readability_score(content)
        
        # Adjust scores based on issue severity
        severity_weights = {
            IssueSeverity.CRITICAL: 0.3,
            IssueSeverity.HIGH: 0.2,
            IssueSeverity.MEDIUM: 0.1,
            IssueSeverity.LOW: 0.05
        }
        
        for issue in issues:
            penalty = severity_weights.get(issue.severity, 0.1)
            
            if issue.issue_type == IssueType.GRAMMAR:
                grammar_score = max(0, grammar_score - penalty)
            elif issue.issue_type == IssueType.CLARITY:
                clarity_score = max(0, clarity_score - penalty)
            elif issue.issue_type == IssueType.BRAND_VOICE:
                brand_voice_score = max(0, brand_voice_score - penalty)
            elif issue.issue_type == IssueType.SEO:
                seo_score = max(0, seo_score - penalty)
        
        # Cap all scores at 1.0
        grammar_score = min(1.0, grammar_score)
        clarity_score = min(1.0, clarity_score)
        brand_voice_score = min(1.0, brand_voice_score)
        seo_score = min(1.0, seo_score)
        engagement_score = min(1.0, engagement_score)
        readability_score = min(1.0, readability_score)
        
        # Calculate overall score (weighted average)
        overall_score = (
            grammar_score * 0.25 +
            clarity_score * 0.20 +
            brand_voice_score * 0.20 +
            seo_score * 0.15 +
            engagement_score * 0.10 +
            readability_score * 0.10
        )
        
        return QualityMetrics(
            overall_score=overall_score,
            grammar_score=grammar_score,
            clarity_score=clarity_score,
            brand_voice_score=brand_voice_score,
            seo_score=seo_score,
            engagement_score=engagement_score,
            readability_score=readability_score
        )
    
    async def _calculate_engagement_score(self, content: str) -> float:
        """Calculate content engagement score"""
        
        try:
            engagement_indicators = [
                '?',  # Questions engage readers
                '!',  # Exclamations show energy
                'you', 'your',  # Direct address
                'how', 'why', 'what',  # Question words
            ]
            
            content_lower = content.lower()
            engagement_count = sum(1 for indicator in engagement_indicators if indicator in content_lower)
            
            return min(1.0, engagement_count / 10)
            
        except Exception:
            return 0.7
    
    async def _calculate_readability_score(self, content: str) -> float:
        """Calculate content readability score"""
        
        try:
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            words = content.split()
            
            if not sentences or not words:
                return 0.5
            
            avg_sentence_length = len(words) / len(sentences)
            
            # Ideal range: 15-20 words per sentence
            if 15 <= avg_sentence_length <= 20:
                return 1.0
            else:
                return max(0.3, 1.0 - abs(avg_sentence_length - 17.5) / 20)
            
        except Exception:
            return 0.7
    
    def _generate_improvements_summary(self, original: str, edited: str, issues: List[ContentIssue]) -> List[str]:
        """Generate summary of improvements made"""
        
        improvements = []
        
        # Count improvements by type
        issue_counts = {}
        for issue in issues:
            issue_type = issue.issue_type.value
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        for issue_type, count in issue_counts.items():
            improvements.append(f"Resolved {count} {issue_type} issue{'s' if count > 1 else ''}")
        
        # Word count change
        original_words = len(original.split())
        edited_words = len(edited.split())
        
        if edited_words != original_words:
            if edited_words > original_words:
                improvements.append(f"Expanded content by {edited_words - original_words} words")
            else:
                improvements.append(f"Reduced content by {original_words - edited_words} words for better conciseness")
        
        if not improvements:
            improvements.append("Content quality maintained at high standard")
        
        return improvements
    
    async def _generate_recommendations(self, 
                                      quality_metrics: QualityMetrics,
                                      issues: List[ContentIssue],
                                      content_plan: Optional[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations for future content"""
        
        recommendations = []
        
        # Quality-based recommendations
        if quality_metrics.grammar_score < 0.9:
            recommendations.append("Consider using grammar checking tools during initial writing")
        
        if quality_metrics.brand_voice_score < 0.8:
            recommendations.append("Review brand voice guidelines before writing to ensure consistency")
        
        if quality_metrics.seo_score < 0.75:
            recommendations.append("Plan keyword integration strategy before writing to improve SEO performance")
        
        if quality_metrics.engagement_score < 0.8:
            recommendations.append("Include more questions, examples, and calls-to-action to increase engagement")
        
        # Issue-based recommendations
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
        
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical issues before publication")
        
        if high_issues:
            recommendations.append(f"Review and resolve {len(high_issues)} high-priority issues")
        
        if not recommendations:
            recommendations.append("Content meets all quality standards - excellent work!")
        
        return recommendations
    
    def _determine_approval_status(self, quality_metrics: QualityMetrics, issues: List[ContentIssue]) -> str:
        """Determine content approval status based on quality metrics and issues"""
        
        critical_issues = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == IssueSeverity.HIGH])
        
        # Check against quality standards
        meets_standards = (
            quality_metrics.overall_score >= self.quality_standards["minimum_overall_score"] and
            quality_metrics.grammar_score >= self.quality_standards["minimum_grammar_score"] and
            quality_metrics.brand_voice_score >= self.quality_standards["minimum_brand_voice_score"] and
            quality_metrics.clarity_score >= self.quality_standards["minimum_clarity_score"] and
            quality_metrics.seo_score >= self.quality_standards["minimum_seo_score"] and
            critical_issues <= self.quality_standards["maximum_critical_issues"] and
            high_issues <= self.quality_standards["maximum_high_issues"]
        )
        
        if meets_standards:
            return "approved"
        elif critical_issues > 0:
            return "requires_major_revision"
        elif high_issues > 2 or quality_metrics.overall_score < 0.7:
            return "requires_revision"
        else:
            return "approved_with_minor_changes"
    
    async def _generate_editor_notes(self, issues: List[ContentIssue], quality_metrics: QualityMetrics) -> str:
        """Generate comprehensive editor notes"""
        
        notes = []
        
        # Overall assessment
        overall_score = quality_metrics.overall_score
        if overall_score >= 0.9:
            notes.append("Excellent content quality with minimal issues identified.")
        elif overall_score >= 0.8:
            notes.append("Good content quality with some areas for improvement.")
        elif overall_score >= 0.7:
            notes.append("Acceptable content quality but requires attention to identified issues.")
        else:
            notes.append("Content requires significant improvement before publication.")
        
        # Specific area highlights
        if quality_metrics.grammar_score < 0.9:
            notes.append(f"Grammar and mechanics need attention (score: {quality_metrics.grammar_score:.2f}).")
        
        if quality_metrics.brand_voice_score < 0.8:
            notes.append(f"Brand voice consistency could be improved (score: {quality_metrics.brand_voice_score:.2f}).")
        
        if quality_metrics.seo_score < 0.75:
            notes.append(f"SEO optimization needs enhancement (score: {quality_metrics.seo_score:.2f}).")
        
        # Issue summary
        if issues:
            issue_summary = {}
            for issue in issues:
                severity = issue.severity.value
                issue_summary[severity] = issue_summary.get(severity, 0) + 1
            
            summary_parts = []
            for severity, count in issue_summary.items():
                summary_parts.append(f"{count} {severity}")
            
            notes.append(f"Issues identified: {', '.join(summary_parts)}.")
        
        # Positive feedback
        if quality_metrics.overall_score >= 0.85:
            notes.append("Content demonstrates strong adherence to brand guidelines and quality standards.")
        
        return " ".join(notes)
    
    async def _store_editing_report(self, report: EditingReport):
        """Store editing report in knowledge base"""
        try:
            report_data = {
                "title": f"Editing Report: {report.content_title}",
                "type": "editing_report",
                "content": json.dumps(report.to_dict(), indent=2),
                "metadata": {
                    "content_title": report.content_title,
                    "review_date": report.review_date.isoformat(),
                    "overall_quality_score": report.quality_metrics.overall_score,
                    "approval_status": report.approval_status,
                    "issues_count": len(report.issues_identified),
                    "word_count_change": report.edited_word_count - report.original_word_count
                }
            }
            
            await self.knowledge_base.store_document(report_data)
            self.logger.info(f"Editing report stored in knowledge base: {report.content_title}")
            
        except Exception as e:
            self.logger.error(f"Failed to store editing report: {e}")
    
    async def quick_review(self, content: str, focus_areas: List[str] = None) -> Dict[str, Any]:
        """Perform quick content review focusing on specific areas"""
        
        if focus_areas is None:
            focus_areas = ["grammar", "clarity", "brand_voice"]
        
        quick_issues = []
        
        # Quick grammar check
        if "grammar" in focus_areas:
            grammar_issues, _ = await self._review_grammar_mechanics(content)
            quick_issues.extend(grammar_issues)
        
        # Quick clarity check
        if "clarity" in focus_areas:
            readability_issues = await self._check_readability(content)
            quick_issues.extend(readability_issues)
        
        # Quick brand voice check (basic)
        if "brand_voice" in focus_areas:
            tone_score = await self._basic_tone_check(content)
            if tone_score < 0.7:
                issue = ContentIssue(
                    issue_type=IssueType.BRAND_VOICE,
                    severity=IssueSeverity.MEDIUM,
                    description=f"Tone consistency score: {tone_score:.2f}",
                    location="Throughout content",
                    suggested_fix="Review and improve tone consistency"
                )
                quick_issues.append(issue)
        
        # Calculate quick quality score
        total_score = 1.0 - (len(quick_issues) * 0.1)
        quality_score = max(0.0, min(1.0, total_score))
        
        return {
            "quality_score": quality_score,
            "issues_found": len(quick_issues),
            "issues": [issue.to_dict() for issue in quick_issues],
            "recommendation": "approved" if quality_score >= 0.8 else "needs_review"
        }
    
    async def _basic_tone_check(self, content: str) -> float:
        """Basic tone consistency check"""
        
        # Simple tone indicators
        professional_indicators = ['furthermore', 'moreover', 'consequently', 'therefore']
        casual_indicators = ['you\'ll', 'here\'s', 'let\'s', 'don\'t', 'can\'t']
        
        content_lower = content.lower()
        professional_count = sum(1 for indicator in professional_indicators if indicator in content_lower)
        casual_count = sum(1 for indicator in casual_indicators if indicator in content_lower)
        
        # Score based on consistency
        if professional_count == 0 and casual_count == 0:
            return 0.7  # Neutral tone
        elif professional_count > 0 and casual_count > 0:
            # Mixed tone - check balance
            total = professional_count + casual_count
            balance = min(professional_count, casual_count) / total
            return 0.5 + (balance * 0.3)  # Score between 0.5-0.8
        else:
            return 0.9  # Consistent tone (either professional or casual)
    
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