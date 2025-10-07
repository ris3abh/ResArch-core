"""
AI Language Code Parser Tool for SpinScribe

This tool parses the AI Language Code shorthand notation into structured parameters
that agents can use to generate content with precise stylistic control.

Example input: /TN/A3,EMP4/VL3/SC2/FL3/VS5/LF2/LD4/CF2/PS3/SE4/AU-prospective-students
"""

from crewai.tools import BaseTool
from typing import Type, Dict, Any, List, Optional
from pydantic import BaseModel, Field
import re


class AILanguageCodeInput(BaseModel):
    """Input schema for AI Language Code Parser."""
    
    code: str = Field(
        ...,
        description="The AI Language Code string to parse (e.g., /TN/A3,EMP4/VL3/SC2)"
    )


class AILanguageCodeParser(BaseTool):
    """
    Parses AI Language Code shorthand into structured content generation parameters.
    
    The AI Language Code is a compact notation system that defines precise stylistic
    attributes for content generation including tone, vocabulary, complexity, and more.
    
    Supported Parameters:
    - /TN (Tone): e.g., /TN/A3,EMP4 (Authoritative:3, Empathetic:4)
    - /VL (Vocabulary Level): 1-10 scale
    - /SC (Sentence Complexity): 1-5 scale
    - /FL (Figurative Language): 1-5 scale
    - /VS (Verb Strength): 1-10 scale
    - /LF (Language Formality): 1-5 scale
    - /LD (Level of Detail): 1-5 scale
    - /CF (Content Focus): 1-5 scale
    - /CRF-C (Conceptual Creative Freedom): 1-10 scale
    - /CRF-S (Structural Creative Freedom): 1-10 scale
    - /PS (Persuasiveness): 1-5 scale
    - /SE (Subject Expertise): 1-5 scale
    - /AU- (Audience): e.g., /AU-prospective-students
    """
    
    name: str = "AI Language Code Parser"
    description: str = (
        "Parses AI Language Code shorthand (like /TN/A3,EMP4/VL3/SC2) into "
        "structured parameters for content generation with precise stylistic control."
    )
    args_schema: Type[BaseModel] = AILanguageCodeInput
    
    # Tone code mappings
    TONE_CODES = {
        "A": "Authoritative",
        "AF": "Affluent",
        "AP": "Approachable",
        "B": "Bold",
        "BU": "Bubbly",
        "C": "Compassionate",
        "CB": "Cerebral",
        "CH": "Challenging",
        "EL": "Elegant",
        "EM": "Empowering",
        "EMP": "Empathetic",
        "EN": "Energetic",
        "ENC": "Encouraging",
        "ET": "Enthusiastic",
        "F": "Friendly",
        "FA": "Familiar",
        "H": "Humorous",
        "HE": "Helpful",
        "HF": "Heartfelt",
        "I": "Inspirational",
        "K": "Knowledgable",
        "L": "Learning",
        "N": "Neutral",
        "O": "Optimistic",
        "P": "Professional",
        "R": "Refined",
        "S": "Sincere",
        "SO": "Sophisticated",
        "SU": "Supportive",
        "T": "Thoughtful",
        "TH": "Thrilling",
        "U": "Urgent",
        "V": "Vibrant",
        "W": "Whimsical",
        "X": "Exclusive",
        "Y": "Youthful"
    }
    
    def _run(self, code: str) -> Dict[str, Any]:
        """
        Parse the AI Language Code string into structured parameters.
        
        Args:
            code: AI Language Code string (e.g., /TN/A3,EMP4/VL3/SC2/FL3)
            
        Returns:
            Dictionary containing parsed parameters with descriptions
        """
        parsed = {
            "raw_code": code,
            "parameters": {},
            "instructions": []
        }
        
        # Split by forward slash and process each segment
        segments = [s.strip() for s in code.split('/') if s.strip()]
        
        for segment in segments:
            # Parse Tone (TN)
            if segment.startswith('TN'):
                parsed["parameters"]["tone"] = self._parse_tone(segment)
                parsed["instructions"].append(self._generate_tone_instruction(
                    parsed["parameters"]["tone"]
                ))
            
            # Parse Vocabulary Level (VL)
            elif segment.startswith('VL'):
                level = self._extract_number(segment, 'VL')
                if level:
                    parsed["parameters"]["vocabulary_level"] = {
                        "level": level,
                        "description": self._get_vocabulary_description(level)
                    }
                    parsed["instructions"].append(
                        f"Use vocabulary at level {level}/10: {self._get_vocabulary_description(level)}"
                    )
            
            # Parse Sentence Complexity (SC)
            elif segment.startswith('SC'):
                level = self._extract_number(segment, 'SC')
                if level:
                    parsed["parameters"]["sentence_complexity"] = {
                        "level": level,
                        "description": self._get_sentence_complexity_description(level)
                    }
                    parsed["instructions"].append(
                        f"Sentence complexity level {level}/5: {self._get_sentence_complexity_description(level)}"
                    )
            
            # Parse Figurative Language (FL)
            elif segment.startswith('FL'):
                level = self._extract_number(segment, 'FL')
                if level:
                    parsed["parameters"]["figurative_language"] = {
                        "level": level,
                        "description": self._get_figurative_language_description(level)
                    }
                    parsed["instructions"].append(
                        f"Figurative language level {level}/5: {self._get_figurative_language_description(level)}"
                    )
            
            # Parse Verb Strength (VS)
            elif segment.startswith('VS'):
                level = self._extract_number(segment, 'VS')
                if level:
                    parsed["parameters"]["verb_strength"] = {
                        "level": level,
                        "description": self._get_verb_strength_description(level)
                    }
                    parsed["instructions"].append(
                        f"Verb strength level {level}/10: {self._get_verb_strength_description(level)}"
                    )
            
            # Parse Language Formality (LF)
            elif segment.startswith('LF'):
                level = self._extract_number(segment, 'LF')
                if level:
                    parsed["parameters"]["language_formality"] = {
                        "level": level,
                        "description": self._get_formality_description(level)
                    }
                    parsed["instructions"].append(
                        f"Language formality level {level}/5: {self._get_formality_description(level)}"
                    )
            
            # Parse Level of Detail (LD)
            elif segment.startswith('LD'):
                level = self._extract_number(segment, 'LD')
                if level:
                    parsed["parameters"]["level_of_detail"] = {
                        "level": level,
                        "description": self._get_detail_description(level)
                    }
                    parsed["instructions"].append(
                        f"Level of detail {level}/5: {self._get_detail_description(level)}"
                    )
            
            # Parse Content Focus (CF)
            elif segment.startswith('CF'):
                level = self._extract_number(segment, 'CF')
                if level:
                    parsed["parameters"]["content_focus"] = {
                        "level": level,
                        "description": self._get_content_focus_description(level)
                    }
                    parsed["instructions"].append(
                        f"Content focus level {level}/5: {self._get_content_focus_description(level)}"
                    )
            
            # Parse Conceptual Creative Freedom (CRF-C)
            elif 'CRF-C' in segment or 'CRFC' in segment:
                level = self._extract_number(segment, 'CRF-C', alt_prefix='CRFC')
                if level:
                    parsed["parameters"]["conceptual_creative_freedom"] = {
                        "level": level,
                        "description": self._get_conceptual_freedom_description(level)
                    }
                    parsed["instructions"].append(
                        f"Conceptual creative freedom {level}/10: {self._get_conceptual_freedom_description(level)}"
                    )
            
            # Parse Structural Creative Freedom (CRF-S)
            elif 'CRF-S' in segment or 'CRFS' in segment:
                level = self._extract_number(segment, 'CRF-S', alt_prefix='CRFS')
                if level:
                    parsed["parameters"]["structural_creative_freedom"] = {
                        "level": level,
                        "description": self._get_structural_freedom_description(level)
                    }
                    parsed["instructions"].append(
                        f"Structural creative freedom {level}/10: {self._get_structural_freedom_description(level)}"
                    )
            
            # Parse Persuasiveness (PS)
            elif segment.startswith('PS'):
                level = self._extract_number(segment, 'PS')
                if level:
                    parsed["parameters"]["persuasiveness"] = {
                        "level": level,
                        "description": self._get_persuasiveness_description(level)
                    }
                    parsed["instructions"].append(
                        f"Persuasiveness level {level}/5: {self._get_persuasiveness_description(level)}"
                    )
            
            # Parse Subject Expertise (SE)
            elif segment.startswith('SE'):
                level = self._extract_number(segment, 'SE')
                if level:
                    parsed["parameters"]["subject_expertise"] = {
                        "level": level,
                        "description": self._get_expertise_description(level)
                    }
                    parsed["instructions"].append(
                        f"Subject expertise level {level}/5: {self._get_expertise_description(level)}"
                    )
            
            # Parse Audience (AU)
            elif segment.startswith('AU-') or segment.startswith('AU_'):
                audience = segment[3:].strip().replace('-', ' ').replace('_', ' ')
                parsed["parameters"]["audience"] = audience
                parsed["instructions"].append(
                    f"Target audience: {audience}"
                )
        
        # Generate summary instruction
        parsed["summary"] = self._generate_summary(parsed["parameters"])
        
        return parsed
    
    def _parse_tone(self, segment: str) -> Dict[str, Any]:
        """Parse tone parameters like TN/A3,EMP4"""
        # Remove TN prefix and split by comma
        tones_str = segment.replace('TN', '').strip('/')
        tone_parts = [t.strip() for t in tones_str.split(',') if t.strip()]
        
        tones = []
        for part in tone_parts:
            # Extract tone code and level
            # Match patterns like A3, EMP4, etc.
            match = re.match(r'([A-Z]+)(\d+)', part)
            if match:
                tone_code = match.group(1)
                level = int(match.group(2))
                
                if tone_code in self.TONE_CODES:
                    tones.append({
                        "code": tone_code,
                        "name": self.TONE_CODES[tone_code],
                        "intensity": level
                    })
        
        return {
            "tones": tones,
            "primary": tones[0] if tones else None,
            "secondary": tones[1] if len(tones) > 1 else None
        }
    
    def _extract_number(self, segment: str, prefix: str, alt_prefix: Optional[str] = None) -> Optional[int]:
        """Extract numeric value from a parameter segment"""
        # Try main prefix
        if prefix in segment:
            num_str = segment.replace(prefix, '').strip('/')
            try:
                return int(num_str)
            except ValueError:
                pass
        
        # Try alternative prefix
        if alt_prefix and alt_prefix in segment:
            num_str = segment.replace(alt_prefix, '').strip('/')
            try:
                return int(num_str)
            except ValueError:
                pass
        
        return None
    
    def _generate_tone_instruction(self, tone_data: Dict) -> str:
        """Generate instruction text for tone"""
        tones_list = tone_data.get("tones", [])
        if not tones_list:
            return "Use neutral tone"
        
        instructions = []
        for i, tone in enumerate(tones_list):
            priority = "Primary" if i == 0 else "Secondary"
            instructions.append(
                f"{priority} tone: {tone['name']} at intensity {tone['intensity']}/5"
            )
        
        return "; ".join(instructions)
    
    def _get_vocabulary_description(self, level: int) -> str:
        """Get vocabulary level description"""
        descriptions = {
            1: "90-100% common everyday words - very basic, accessible to general audience",
            2: "80% common, 15% slightly uncommon terms - mostly simple with occasional specific terms",
            3: "70% common, 20% uncommon, 10% advanced - balanced accessible and sophisticated",
            4: "60% common, 25% uncommon, 15% advanced - refined vocabulary with technical terms",
            5: "50% common, 30% uncommon, 20% advanced - professional/academic level",
            6: "40% common, 35% uncommon, 25% advanced - educated/niche audience",
            7: "30% common, 40% uncommon, 30% advanced - highly sophisticated vocabulary",
            8: "20% common, 40% uncommon, 40% advanced - specialized expert language",
            9: "10% common, 40% uncommon, 50% advanced - expert-level with rich advanced terms",
            10: "0-5% common, 45% uncommon, 50-55% advanced - extremely technical/academic"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_sentence_complexity_description(self, level: int) -> str:
        """Get sentence complexity description"""
        descriptions = {
            1: "60-80% simple sentences, remainder split between compound and complex",
            2: "50-60% simple sentences, remainder split between compound and complex",
            3: "40-50% simple, 30% compound, 20-30% complex - balanced approach",
            4: "25-35% simple, 35% compound, 30-35% complex, 5% compound-complex",
            5: "5% simple, 50% compound, 35% complex, 10% compound-complex - sophisticated structure"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_figurative_language_description(self, level: int) -> str:
        """Get figurative language description"""
        descriptions = {
            1: "0-5% figurative language - minimal, straightforward and factual",
            2: "5-15% figurative language - rare use, mostly literal",
            3: "15-25% figurative language - moderate use for enhancement",
            4: "25-40% figurative language - frequent use adds depth and vividness",
            5: "40-60% figurative language - rich, integral to style with layered expressions"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_verb_strength_description(self, level: int) -> str:
        """Get verb strength description"""
        if level <= 2:
            return "Basic, common verbs (e.g., 'went', 'said', 'did')"
        elif level <= 4:
            return "Moderately descriptive verbs (e.g., 'walked', 'explained', 'completed')"
        elif level <= 6:
            return "Strong, specific verbs (e.g., 'strode', 'articulated', 'accomplished')"
        elif level <= 8:
            return "Dynamic, impactful verbs (e.g., 'surged', 'revolutionized', 'transformed')"
        else:
            return "Powerful, vivid verbs that elevate writing (e.g., 'annihilated', 'catalyzed', 'pioneered')"
    
    def _get_formality_description(self, level: int) -> str:
        """Get language formality description"""
        descriptions = {
            1: "Highly informal/colloquial - casual conversation style",
            2: "Informal but professional - friendly business communication",
            3: "Balanced formality - standard professional writing",
            4: "Formal - academic or technical writing",
            5: "Highly formal/academic - scholarly or legal documents"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_detail_description(self, level: int) -> str:
        """Get level of detail description"""
        descriptions = {
            1: "90-100% high-level overview - very concise, essential points only",
            2: "75-85% overview, 15-25% detail - brief with surface-level examples",
            3: "50-60% overview, 40-50% detail - balanced depth and breadth",
            4: "25-35% overview, 65-75% detail - comprehensive with thorough context",
            5: "0-10% overview, 90-100% detail - exhaustive, technical document level"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_content_focus_description(self, level: int) -> str:
        """Get content focus description"""
        descriptions = {
            1: "90-100% broad overview - high-level coverage, minimal depth",
            2: "75-85% broad, 15-25% specific - includes surface-level subtopic examples",
            3: "50-60% broad, 40-50% specific - highlights 2-3 subtopics with moderate depth",
            4: "25-35% broad, 65-75% specific - deep dive into specific subtopic",
            5: "90-100% niche focus - comprehensive coverage of narrow aspect"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_conceptual_freedom_description(self, level: int) -> str:
        """Get conceptual creative freedom description"""
        if level <= 3:
            return "Stick closely to given ideas and examples"
        elif level <= 6:
            return "Some flexibility to add related concepts and connections"
        else:
            return "High freedom to generate original, imaginative ideas beyond prompt scope"
    
    def _get_structural_freedom_description(self, level: int) -> str:
        """Get structural creative freedom description"""
        if level <= 3:
            return "Strict adherence to structural template"
        elif level <= 6:
            return "Moderate flexibility to adjust structure while maintaining framework"
        else:
            return "High freedom to reorganize and innovate structurally"
    
    def _get_persuasiveness_description(self, level: int) -> str:
        """Get persuasiveness description"""
        descriptions = {
            1: "Purely informative - neutral presentation of facts",
            2: "Mildly persuasive - subtle suggestions and recommendations",
            3: "Moderately persuasive - clear call to action with supporting arguments",
            4: "Highly persuasive - compelling arguments designed to influence",
            5: "Extremely persuasive - powerful rhetoric aimed at driving specific actions"
        }
        return descriptions.get(level, "Unknown level")
    
    def _get_expertise_description(self, level: int) -> str:
        """Get subject expertise description"""
        descriptions = {
            1: "Basic understanding - general population knowledge level",
            2: "Informed layperson - well-researched understanding",
            3: "Intermediate professional - solid working knowledge",
            4: "Advanced professional - years of specialized experience",
            5: "Expert-level - decades of deep industry expertise"
        }
        return descriptions.get(level, "Unknown level")
    
    def _generate_summary(self, parameters: Dict) -> str:
        """Generate a human-readable summary of all parameters"""
        summary_parts = []
        
        if "tone" in parameters:
            tone_data = parameters["tone"]
            if tone_data.get("primary"):
                primary = tone_data["primary"]
                summary_parts.append(
                    f"Primary tone: {primary['name']} (intensity {primary['intensity']})"
                )
        
        if "vocabulary_level" in parameters:
            summary_parts.append(
                f"Vocabulary: Level {parameters['vocabulary_level']['level']}"
            )
        
        if "sentence_complexity" in parameters:
            summary_parts.append(
                f"Sentence complexity: Level {parameters['sentence_complexity']['level']}"
            )
        
        if "audience" in parameters:
            summary_parts.append(f"Audience: {parameters['audience']}")
        
        return " | ".join(summary_parts) if summary_parts else "No parameters parsed"


# Create tool instance for import
ai_language_code_parser = AILanguageCodeParser()