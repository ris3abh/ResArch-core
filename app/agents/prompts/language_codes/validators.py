# app/agents/prompts/language_codes/validators.py
"""
Language Code Validator for SpinScribe
Validates and ensures consistency of language codes
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
import re

from .templates import LanguageCodeFormat, LanguageCodeParameter

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of language code validation"""
    
    def __init__(self, 
                 is_valid: bool,
                 errors: List[str] = None,
                 warnings: List[str] = None,
                 suggestions: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.suggestions = suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }

class LanguageCodeValidator:
    """
    Validates language codes for consistency and correctness
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Parameter ranges
        self.parameter_ranges = {
            "content_focus": (1, 10),
            "language_formality": (1, 10),
            "vocabulary_level": (1, 10),
            "subject_expertise": (1, 10),
            "detail_level": (1, 10),
            "sentence_complexity": (1, 10),
            "persuasiveness": (1, 10),
            "creativity": (1, 10),
            "engagement": (1, 10),
            "figurative_language": (1, 10)
        }
        
        # Logical consistency rules
        self.consistency_rules = [
            self._check_formality_vocabulary_consistency,
            self._check_expertise_vocabulary_consistency,
            self._check_engagement_formality_consistency,
            self._check_persuasiveness_consistency,
            self._check_audience_consistency
        ]
    
    def validate_code(self, code: LanguageCodeFormat) -> ValidationResult:
        """
        Validate a language code for correctness and consistency
        
        Args:
            code: Language code to validate
            
        Returns:
            ValidationResult with validation details
        """
        
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Check parameter ranges
            range_errors = self._check_parameter_ranges(code)
            errors.extend(range_errors)
            
            # Check logical consistency
            consistency_issues = self._check_logical_consistency(code)
            warnings.extend(consistency_issues)
            
            # Generate suggestions
            code_suggestions = self._generate_suggestions(code)
            suggestions.extend(code_suggestions)
            
            # Overall validation
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    def validate_code_string(self, code_string: str) -> ValidationResult:
        """
        Validate a language code string format
        
        Args:
            code_string: Code string in CF=X, LF=Y format
            
        Returns:
            ValidationResult with validation details
        """
        
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Check string format
            format_errors = self._check_string_format(code_string)
            errors.extend(format_errors)
            
            if not format_errors:
                # Parse and validate the code
                try:
                    code = LanguageCodeFormat.from_code_string(code_string)
                    validation_result = self.validate_code(code)
                    
                    errors.extend(validation_result.errors)
                    warnings.extend(validation_result.warnings)
                    suggestions.extend(validation_result.suggestions)
                    
                except Exception as e:
                    errors.append(f"Failed to parse code string: {str(e)}")
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            self.logger.error(f"String validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"String validation error: {str(e)}"]
            )
    
    def _check_parameter_ranges(self, code: LanguageCodeFormat) -> List[str]:
        """Check if all parameters are within valid ranges"""
        
        errors = []
        code_dict = code.to_dict()
        
        for param, value in code_dict.items():
            if param in self.parameter_ranges and isinstance(value, int):
                min_val, max_val = self.parameter_ranges[param]
                
                if value < min_val or value > max_val:
                    errors.append(
                        f"Parameter '{param}' value {value} is outside valid range {min_val}-{max_val}"
                    )
        
        return errors
    
    def _check_string_format(self, code_string: str) -> List[str]:
        """Check if code string follows proper format"""
        
        errors = []
        
        # Check for valid parameter format (XX=Y)
        pattern = r'^[A-Z]{2}=\d+(?:,\s*[A-Z]{2}=\d+)*$'
        
        if not re.match(pattern, code_string.strip()):
            errors.append("Code string format is invalid. Expected format: CF=X, LF=Y, VL=Z, ...")
            return errors
        
        # Check for required parameters
        required_params = ['CF', 'LF', 'VL', 'SE']
        
        for param in required_params:
            if f"{param}=" not in code_string:
                errors.append(f"Required parameter '{param}' is missing")
        
        # Check for duplicate parameters
        parts = [part.strip() for part in code_string.split(',')]
        param_codes = [part.split('=')[0] for part in parts if '=' in part]
        
        if len(param_codes) != len(set(param_codes)):
            errors.append("Duplicate parameters found in code string")
        
        return errors
    
    def _check_logical_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check logical consistency between parameters"""
        
        warnings = []
        
        for rule in self.consistency_rules:
            try:
                rule_warnings = rule(code)
                warnings.extend(rule_warnings)
            except Exception as e:
                self.logger.warning(f"Consistency check failed: {e}")
        
        return warnings
    
    def _check_formality_vocabulary_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check consistency between formality and vocabulary levels"""
        
        warnings = []
        
        # High formality should generally correspond to higher vocabulary
        if code.language_formality >= 8 and code.vocabulary_level <= 4:
            warnings.append(
                "High formality (LF>=8) with low vocabulary (VL<=4) may be inconsistent"
            )
        
        # Very casual formality with very high vocabulary is unusual
        if code.language_formality <= 3 and code.vocabulary_level >= 8:
            warnings.append(
                "Very casual formality (LF<=3) with high vocabulary (VL>=8) may be inconsistent"
            )
        
        return warnings
    
    def _check_expertise_vocabulary_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check consistency between expertise and vocabulary levels"""
        
        warnings = []
        
        # High expertise should generally have higher vocabulary
        if code.subject_expertise >= 8 and code.vocabulary_level <= 5:
            warnings.append(
                "High expertise (SE>=8) with moderate vocabulary (VL<=5) may limit technical communication"
            )
        
        # Low expertise with very high vocabulary may be inaccessible
        if code.subject_expertise <= 3 and code.vocabulary_level >= 8:
            warnings.append(
                "Low expertise (SE<=3) with high vocabulary (VL>=8) may be too complex for audience"
            )
        
        return warnings
    
    def _check_engagement_formality_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check consistency between engagement and formality"""
        
        warnings = []
        
        if code.engagement is not None:
            # Very high engagement with very high formality is difficult
            if code.engagement >= 9 and code.language_formality >= 9:
                warnings.append(
                    "Very high engagement (EG>=9) with very high formality (LF>=9) may be contradictory"
                )
            
            # Very low engagement with content that should be engaging
            if code.engagement <= 3 and code.persuasiveness and code.persuasiveness >= 7:
                warnings.append(
                    "Low engagement (EG<=3) with high persuasiveness (PS>=7) may reduce effectiveness"
                )
        
        return warnings
    
    def _check_persuasiveness_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check persuasiveness consistency with other parameters"""
        
        warnings = []
        
        if code.persuasiveness is not None:
            # High persuasiveness with very high formality may be less effective
            if code.persuasiveness >= 8 and code.language_formality >= 9:
                warnings.append(
                    "High persuasiveness (PS>=8) with very high formality (LF>=9) may reduce persuasive impact"
                )
            
            # High persuasiveness should have reasonable engagement
            if code.persuasiveness >= 8 and code.engagement and code.engagement <= 4:
                warnings.append(
                    "High persuasiveness (PS>=8) with low engagement (EG<=4) may be ineffective"
                )
        
        return warnings
    
    def _check_audience_consistency(self, code: LanguageCodeFormat) -> List[str]:
        """Check consistency with stated audience"""
        
        warnings = []
        
        if code.audience:
            audience_lower = code.audience.lower()
            
            # Professional audience checks
            if "professional" in audience_lower or "expert" in audience_lower:
                if code.language_formality <= 4:
                    warnings.append(
                        f"Professional audience with low formality (LF={code.language_formality}) may be inappropriate"
                    )
                if code.subject_expertise <= 4:
                    warnings.append(
                        f"Professional audience with low expertise level (SE={code.subject_expertise}) may be too basic"
                    )
            
            # Beginner audience checks
            elif "beginner" in audience_lower or "novice" in audience_lower:
                if code.vocabulary_level >= 8:
                    warnings.append(
                        f"Beginner audience with high vocabulary (VL={code.vocabulary_level}) may be too complex"
                    )
                if code.subject_expertise >= 8:
                    warnings.append(
                        f"Beginner audience with high expertise (SE={code.subject_expertise}) may be inaccessible"
                    )
            
            # General audience checks
            elif "general" in audience_lower:
                if code.vocabulary_level >= 9 or code.subject_expertise >= 9:
                    warnings.append(
                        "General audience with very high complexity may limit accessibility"
                    )
        
        return warnings
    
    def _generate_suggestions(self, code: LanguageCodeFormat) -> List[str]:
        """Generate suggestions for improving the language code"""
        
        suggestions = []
        
        # Suggest parameter additions if missing
        if code.detail_level is None:
            suggestions.append("Consider adding Detail Level (DL) parameter for more precise guidance")
        
        if code.engagement is None and (code.persuasiveness and code.persuasiveness >= 6):
            suggestions.append("Consider adding Engagement (EG) parameter for persuasive content")
        
        if code.sentence_complexity is None and code.vocabulary_level >= 7:
            suggestions.append("Consider adding Sentence Complexity (SC) for high vocabulary content")
        
        # Content-type specific suggestions
        if code.audience:
            audience_lower = code.audience.lower()
            
            if "social media" in audience_lower and not code.engagement:
                suggestions.append("Social media content typically benefits from high engagement (EG=8-10)")
            
            if "email" in audience_lower and not code.persuasiveness:
                suggestions.append("Email content often benefits from moderate persuasiveness (PS=6-8)")
        
        # Balance suggestions
        formality_vocab_diff = abs(code.language_formality - code.vocabulary_level)
        if formality_vocab_diff >= 4:
            suggestions.append(
                "Consider balancing formality and vocabulary levels for better consistency"
            )
        
        expertise_vocab_diff = abs(code.subject_expertise - code.vocabulary_level)
        if expertise_vocab_diff >= 4:
            suggestions.append(
                "Consider aligning expertise and vocabulary levels for appropriate complexity"
            )
        
        return suggestions
    
    def suggest_improvements(self, 
                           code: LanguageCodeFormat,
                           performance_feedback: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Suggest improvements based on validation and performance feedback
        
        Args:
            code: Current language code
            performance_feedback: Optional feedback on content performance
            
        Returns:
            List of improvement suggestions
        """
        
        suggestions = []
        
        try:
            # Get validation suggestions
            validation_result = self.validate_code(code)
            suggestions.extend(validation_result.suggestions)
            
            # Add performance-based suggestions
            if performance_feedback:
                perf_suggestions = self._analyze_performance_feedback(code, performance_feedback)
                suggestions.extend(perf_suggestions)
            
            # Remove duplicates while preserving order
            unique_suggestions = []
            for suggestion in suggestions:
                if suggestion not in unique_suggestions:
                    unique_suggestions.append(suggestion)
            
            return unique_suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate improvement suggestions: {e}")
            return ["Unable to generate suggestions due to error"]
    
    def _analyze_performance_feedback(self, 
                                    code: LanguageCodeFormat,
                                    feedback: Dict[str, Any]) -> List[str]:
        """Analyze performance feedback to suggest improvements"""
        
        suggestions = []
        
        # Engagement metrics
        if "engagement_low" in feedback:
            if code.engagement and code.engagement < 7:
                suggestions.append("Increase engagement level (EG) to improve reader interaction")
            if code.language_formality > 7:
                suggestions.append("Reduce formality (LF) to improve engagement")
        
        # Comprehension issues
        if "too_complex" in feedback:
            if code.vocabulary_level > 6:
                suggestions.append("Reduce vocabulary level (VL) for better comprehension")
            if code.sentence_complexity and code.sentence_complexity > 6:
                suggestions.append("Reduce sentence complexity (SC) for clearer communication")
        
        # Conversion issues
        if "low_conversion" in feedback:
            if code.persuasiveness and code.persuasiveness < 6:
                suggestions.append("Increase persuasiveness (PS) to improve conversion rates")
            if code.content_focus < 8:
                suggestions.append("Increase content focus (CF) for better conversion messaging")
        
        # Tone feedback
        if "too_formal" in feedback:
            suggestions.append("Reduce language formality (LF) for more approachable tone")
        elif "too_casual" in feedback:
            suggestions.append("Increase language formality (LF) for more professional tone")
        
        return suggestions
    
    def compare_codes(self, 
                     code1: LanguageCodeFormat,
                     code2: LanguageCodeFormat) -> Dict[str, Any]:
        """
        Compare two language codes and highlight differences
        
        Args:
            code1: First language code
            code2: Second language code
            
        Returns:
            Comparison analysis
        """
        
        try:
            dict1 = code1.to_dict()
            dict2 = code2.to_dict()
            
            differences = {}
            similarities = {}
            
            # Find all parameters
            all_params = set(dict1.keys()) | set(dict2.keys())
            
            for param in all_params:
                val1 = dict1.get(param)
                val2 = dict2.get(param)
                
                if val1 != val2:
                    differences[param] = {
                        "code1": val1,
                        "code2": val2,
                        "difference": abs(val1 - val2) if isinstance(val1, int) and isinstance(val2, int) else None
                    }
                else:
                    similarities[param] = val1
            
            # Calculate overall similarity
            numeric_diffs = [diff["difference"] for diff in differences.values() if diff["difference"] is not None]
            avg_difference = sum(numeric_diffs) / len(numeric_diffs) if numeric_diffs else 0
            similarity_score = max(0, 1 - (avg_difference / 10))  # Normalized to 0-1
            
            return {
                "differences": differences,
                "similarities": similarities,
                "similarity_score": similarity_score,
                "significant_differences": [
                    param for param, diff in differences.items() 
                    if diff["difference"] and diff["difference"] >= 3
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Code comparison failed: {e}")
            return {"error": str(e)}
    
    def validate_for_content_type(self, 
                                code: LanguageCodeFormat,
                                content_type: str) -> ValidationResult:
        """
        Validate language code for specific content type
        
        Args:
            code: Language code to validate
            content_type: Target content type
            
        Returns:
            ValidationResult with content-type specific validation
        """
        
        # Start with general validation
        result = self.validate_code(code)
        
        # Add content-type specific checks
        content_warnings = self._check_content_type_appropriateness(code, content_type)
        result.warnings.extend(content_warnings)
        
        # Add content-type suggestions
        content_suggestions = self._suggest_for_content_type(code, content_type)
        result.suggestions.extend(content_suggestions)
        
        return result
    
    def _check_content_type_appropriateness(self, 
                                          code: LanguageCodeFormat,
                                          content_type: str) -> List[str]:
        """Check if code is appropriate for content type"""
        
        warnings = []
        
        if content_type == "landing_page":
            if code.persuasiveness and code.persuasiveness < 6:
                warnings.append("Landing pages typically benefit from higher persuasiveness (PS>=6)")
            if code.content_focus < 7:
                warnings.append("Landing pages should have high content focus (CF>=7)")
        
        elif content_type == "social_media":
            if code.engagement and code.engagement < 7:
                warnings.append("Social media content should have high engagement (EG>=7)")
            if code.language_formality > 6:
                warnings.append("Social media content is typically more casual (LF<=6)")
        
        elif content_type == "documentation":
            if code.language_formality < 6:
                warnings.append("Documentation should be more formal (LF>=6)")
            if code.content_focus < 8:
                warnings.append("Documentation requires high content focus (CF>=8)")
        
        elif content_type == "email":
            if code.engagement and code.engagement < 5:
                warnings.append("Email content should maintain reasonable engagement (EG>=5)")
        
        return warnings
    
    def _suggest_for_content_type(self, 
                                code: LanguageCodeFormat,
                                content_type: str) -> List[str]:
        """Generate content-type specific suggestions"""
        
        suggestions = []
        
        type_recommendations = {
            "blog_post": {
                "engagement": (6, 8),
                "content_focus": (6, 8),
                "language_formality": (4, 7)
            },
            "landing_page": {
                "persuasiveness": (7, 10),
                "content_focus": (8, 10),
                "engagement": (7, 9)
            },
            "social_media": {
                "engagement": (8, 10),
                "language_formality": (2, 5),
                "creativity": (6, 9)
            },
            "email": {
                "engagement": (6, 8),
                "persuasiveness": (5, 8),
                "language_formality": (3, 6)
            },
            "documentation": {
                "content_focus": (8, 10),
                "language_formality": (6, 9),
                "detail_level": (7, 10)
            }
        }
        
        if content_type in type_recommendations:
            recs = type_recommendations[content_type]
            code_dict = code.to_dict()
            
            for param, (min_rec, max_rec) in recs.items():
                current_val = code_dict.get(param)
                if isinstance(current_val, int):
                    if current_val < min_rec:
                        suggestions.append(
                            f"Consider increasing {param} to {min_rec}-{max_rec} for {content_type} content"
                        )
                    elif current_val > max_rec:
                        suggestions.append(
                            f"Consider reducing {param} to {min_rec}-{max_rec} for {content_type} content"
                        )
        
        return suggestions