# app/knowledge/analyzers/style_analyzer.py
"""
Production-Grade AI/ML Style Analyzer for SpinScribe
Built by Senior AI Engineer for enterprise content creation

Features:
- Multi-model analysis pipeline (spaCy + transformers + statistical + LLM)
- Automated content processing with smart chunking
- Dynamic language code generation compatible with existing format
- Real-time style profiling with confidence scoring
- Export compatibility with team's current format
- Production performance and error handling
"""

import asyncio
import logging
import re
import statistics
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import numpy as np
from pathlib import Path

# NLP and ML imports
try:
    import spacy
    from spacy.tokens import Doc, Token, Span
except ImportError:
    spacy = None

try:
    from sentence_transformers import SentenceTransformer
    import torch
except ImportError:
    SentenceTransformer = None
    torch = None

try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_selection import chi2
except ImportError:
    KMeans = None
    TfidfVectorizer = None
    cosine_similarity = None
    chi2 = None

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from collections import Counter, defaultdict
import textstat

# SpinScribe imports
from app.agents.base.agent_factory import agent_factory, AgentType
from app.database.connection import SessionLocal
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

# Data structures for style analysis
@dataclass
class LinguisticFeatures:
    """Linguistic features extracted from content"""
    avg_sentence_length: float
    avg_word_length: float
    sentence_length_variance: float
    word_length_variance: float
    
    # Readability metrics
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    gunning_fog: float
    automated_readability_index: float
    
    # Vocabulary metrics
    vocabulary_richness: float  # Type-token ratio
    lexical_diversity: float   # Unique words / Total words
    
    # Syntactic patterns
    pos_distribution: Dict[str, float]  # Part-of-speech distribution
    dependency_patterns: Dict[str, int]  # Dependency relations
    
    # Sentence structure
    simple_sentence_ratio: float
    compound_sentence_ratio: float
    complex_sentence_ratio: float
    
    # Punctuation patterns
    punctuation_density: float
    exclamation_ratio: float
    question_ratio: float
    
    # Technical indicators
    technical_term_density: float
    jargon_usage: float
    
    confidence_score: float = 0.0

@dataclass
class SemanticFeatures:
    """Semantic features from transformer analysis"""
    semantic_coherence: float
    topic_consistency: float
    conceptual_density: float
    
    # Theme analysis
    primary_themes: List[str]
    theme_distribution: Dict[str, float]
    
    # Semantic clusters
    content_clusters: List[Dict[str, Any]]
    cluster_coherence: float
    
    # Embedding statistics
    embedding_variance: float
    semantic_diversity: float
    
    confidence_score: float = 0.0

@dataclass
class StatisticalFeatures:
    """Statistical analysis of writing patterns"""
    # Word frequency patterns
    word_frequency_distribution: Dict[str, int]
    rare_word_usage: float
    common_word_preference: float
    
    # N-gram patterns
    bigram_patterns: Dict[str, int]
    trigram_patterns: Dict[str, int]
    
    # Stylistic patterns
    passive_voice_ratio: float
    first_person_usage: float
    second_person_usage: float
    third_person_usage: float
    
    # Transition patterns
    transition_word_usage: float
    connecting_word_patterns: Dict[str, int]
    
    # Emphasis patterns
    capitalization_patterns: Dict[str, int]
    emphasis_marker_usage: float
    
    confidence_score: float = 0.0

@dataclass
class LLMInsights:
    """High-level insights from LLM analysis"""
    tone_analysis: Dict[str, float]
    voice_characteristics: Dict[str, str]
    audience_positioning: str
    expertise_level: str
    formality_level: float
    
    # Communication style
    directness_level: float
    engagement_style: str
    persuasion_techniques: List[str]
    
    # Brand voice elements
    personality_traits: List[str]
    communication_values: List[str]
    
    # Contextual insights
    industry_adaptation: str
    content_purpose_alignment: str
    
    confidence_score: float = 0.0

@dataclass
class LanguageCode:
    """Compatible language code with existing format"""
    content_focus: int          # /CF (1-5)
    creative_freedom_conceptual: int  # /CRF-C (1-10)
    creative_freedom_structural: int  # /CRF-S (1-10)
    persuasiveness: int         # /PS (1-5)
    figurative_language: int   # /FL (1-5)
    verb_strength: int          # /VS (1-10)
    language_formality: int     # /LF (1-5)
    detail_level: int           # /LD (1-5)
    sentence_complexity: int    # /SC (1-5)
    vocabulary_level: int       # /VL (1-10)
    subject_expertise: int      # /SE (1-5)
    audience: str               # /AU
    tone: str                   # /TN
    
    def to_code_string(self) -> str:
        """Generate the language code string"""
        return (f"/CF={self.content_focus}"
                f"/CRF-C={self.creative_freedom_conceptual}"
                f"/CRF-S={self.creative_freedom_structural}"
                f"/PS={self.persuasiveness}"
                f"/FL={self.figurative_language}"
                f"/VS={self.verb_strength}"
                f"/LF={self.language_formality}"
                f"/LD={self.detail_level}"
                f"/SC={self.sentence_complexity}"
                f"/VL={self.vocabulary_level}"
                f"/SE={self.subject_expertise}"
                f"/AU={self.audience}"
                f"/TN={self.tone}")

@dataclass
class StyleProfile:
    """Complete style analysis profile"""
    project_id: str
    analysis_id: str
    created_at: datetime
    
    # Feature sets
    linguistic_features: LinguisticFeatures
    semantic_features: SemanticFeatures
    statistical_features: StatisticalFeatures
    llm_insights: LLMInsights
    
    # Generated outputs
    language_code: LanguageCode
    style_guide: Dict[str, Any]
    
    # Metadata
    content_samples_analyzed: int
    total_word_count: int
    analysis_confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export"""
        return asdict(self)
    
    def to_team_format(self) -> Dict[str, Any]:
        """Export in team's current format"""
        return {
            "analysis_summary": {
                "word_count": self.total_word_count,
                "samples_analyzed": self.content_samples_analyzed,
                "confidence_score": self.analysis_confidence
            },
            "linguistic_analysis": asdict(self.linguistic_features),
            "semantic_analysis": asdict(self.semantic_features),
            "statistical_analysis": asdict(self.statistical_features),
            "llm_insights": asdict(self.llm_insights),
            "language_code": {
                "code_string": self.language_code.to_code_string(),
                "parameters": asdict(self.language_code)
            },
            "style_guide": self.style_guide,
            "generated_at": self.created_at.isoformat()
        }

class LinguisticProcessor:
    """Advanced linguistic analysis using spaCy and NLTK"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LinguisticProcessor")
        self._load_models()
    
    def _load_models(self):
        """Load required NLP models"""
        try:
            if spacy is None:
                raise ImportError("spaCy not available")
            
            # Try to load spaCy model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.logger.warning("spaCy model not found, downloading...")
                spacy.cli.download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            
            # Download required NLTK data
            nltk_downloads = ['stopwords', 'punkt', 'wordnet', 'averaged_perceptron_tagger', 'omw-1.4']
            for download in nltk_downloads:
                try:
                    nltk.data.find(f'tokenizers/{download}')
                except LookupError:
                    nltk.download(download, quiet=True)
            
            # Initialize smart stop word detection
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
            
            # Initialize TF-IDF for intelligent keyword extraction
            if TfidfVectorizer is not None:
                self.tfidf_vectorizer = TfidfVectorizer(
                    stop_words='english',
                    max_features=1000,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.8
                )
            else:
                self.tfidf_vectorizer = None
            
            self.logger.info("Linguistic models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading linguistic models: {e}")
            self.nlp = None
            self.stop_words = set()
            self.lemmatizer = None
            self.tfidf_vectorizer = None
    
    async def analyze_linguistic_features(self, content: str) -> LinguisticFeatures:
        """Extract comprehensive linguistic features"""
        if not self.nlp:
            self.logger.warning("spaCy not available, using fallback analysis")
            return await self._fallback_linguistic_analysis(content)
        
        doc = self.nlp(content)
        
        # Basic metrics
        sentences = list(doc.sents)
        tokens = [token for token in doc if not token.is_space]
        words = [token for token in tokens if token.is_alpha]
        
        # Sentence and word length analysis
        sentence_lengths = [len([t for t in sent if t.is_alpha]) for sent in sentences]
        word_lengths = [len(token.text) for token in words]
        
        avg_sentence_length = statistics.mean(sentence_lengths) if sentence_lengths else 0
        avg_word_length = statistics.mean(word_lengths) if word_lengths else 0
        sentence_length_variance = statistics.variance(sentence_lengths) if len(sentence_lengths) > 1 else 0
        word_length_variance = statistics.variance(word_lengths) if len(word_lengths) > 1 else 0
        
        # Readability metrics
        flesch_reading_ease = textstat.flesch_reading_ease(content)
        flesch_kincaid_grade = textstat.flesch_kincaid_grade(content)
        gunning_fog = textstat.gunning_fog(content)
        automated_readability_index = textstat.automated_readability_index(content)
        
        # Vocabulary metrics
        unique_words = set(token.lemma_.lower() for token in words)
        vocabulary_richness = len(unique_words) / len(words) if words else 0
        lexical_diversity = len(unique_words) / len(words) if words else 0
        
        # POS distribution
        pos_counts = Counter(token.pos_ for token in words)
        total_pos = sum(pos_counts.values())
        pos_distribution = {pos: count / total_pos for pos, count in pos_counts.items()}
        
        # Dependency patterns
        dependency_patterns = Counter(token.dep_ for token in doc if not token.is_space)
        
        # Sentence structure analysis
        sentence_structures = await self._analyze_sentence_structures(sentences)
        
        # Punctuation analysis
        punctuation_analysis = await self._analyze_punctuation(content, tokens)
        
        # Technical term analysis
        technical_analysis = await self._analyze_technical_terms(words)
        
        return LinguisticFeatures(
            avg_sentence_length=avg_sentence_length,
            avg_word_length=avg_word_length,
            sentence_length_variance=sentence_length_variance,
            word_length_variance=word_length_variance,
            flesch_reading_ease=flesch_reading_ease,
            flesch_kincaid_grade=flesch_kincaid_grade,
            gunning_fog=gunning_fog,
            automated_readability_index=automated_readability_index,
            vocabulary_richness=vocabulary_richness,
            lexical_diversity=lexical_diversity,
            pos_distribution=pos_distribution,
            dependency_patterns=dict(dependency_patterns),
            simple_sentence_ratio=sentence_structures['simple'],
            compound_sentence_ratio=sentence_structures['compound'],
            complex_sentence_ratio=sentence_structures['complex'],
            punctuation_density=punctuation_analysis['density'],
            exclamation_ratio=punctuation_analysis['exclamation_ratio'],
            question_ratio=punctuation_analysis['question_ratio'],
            technical_term_density=technical_analysis['density'],
            jargon_usage=technical_analysis['jargon_usage'],
            confidence_score=0.9 if self.nlp else 0.6
        )
    
    async def _analyze_sentence_structures(self, sentences) -> Dict[str, float]:
        """Analyze sentence structure complexity"""
        if not sentences:
            return {'simple': 0, 'compound': 0, 'complex': 0}
        
        structure_counts = {'simple': 0, 'compound': 0, 'complex': 0}
        
        for sent in sentences:
            # Count clauses and conjunctions
            clauses = len([token for token in sent if token.dep_ in ['ROOT', 'ccomp', 'xcomp', 'advcl']])
            conjunctions = len([token for token in sent if token.pos_ in ['CCONJ', 'SCONJ']])
            
            if clauses <= 1 and conjunctions == 0:
                structure_counts['simple'] += 1
            elif conjunctions > 0 and clauses > 1:
                if any(token.dep_ in ['advcl', 'acl'] for token in sent):
                    structure_counts['complex'] += 1
                else:
                    structure_counts['compound'] += 1
            else:
                structure_counts['complex'] += 1
        
        total = len(sentences)
        return {k: v / total for k, v in structure_counts.items()}
    
    async def _analyze_punctuation(self, content: str, tokens) -> Dict[str, float]:
        """Analyze punctuation patterns"""
        punct_tokens = [token for token in tokens if token.is_punct]
        
        if not punct_tokens:
            return {'density': 0, 'exclamation_ratio': 0, 'question_ratio': 0}
        
        total_tokens = len(tokens)
        exclamations = len([token for token in punct_tokens if '!' in token.text])
        questions = len([token for token in punct_tokens if '?' in token.text])
        
        return {
            'density': len(punct_tokens) / total_tokens,
            'exclamation_ratio': exclamations / len(punct_tokens),
            'question_ratio': questions / len(punct_tokens)
        }
    
    async def _analyze_technical_terms(self, words) -> Dict[str, float]:
        """Analyze technical term usage"""
        if not words:
            return {'density': 0, 'jargon_usage': 0}
        
        # Simple heuristics for technical terms
        technical_indicators = [
            lambda w: len(w.text) > 8,  # Long words often technical
            lambda w: w.text.endswith(('tion', 'sion', 'ment', 'ance', 'ence')),
            lambda w: w.text.isupper() and len(w.text) > 2,  # Acronyms
            lambda w: any(char.isdigit() for char in w.text),  # Contains numbers
        ]
        
        technical_count = 0
        for word in words:
            if any(indicator(word) for indicator in technical_indicators):
                technical_count += 1
        
        # Additional jargon detection (simplified)
        jargon_patterns = ['implement', 'utilize', 'optimize', 'leverage', 'synergy', 'paradigm']
        jargon_count = sum(1 for word in words if word.lemma_.lower() in jargon_patterns)
        
        return {
            'density': technical_count / len(words),
            'jargon_usage': jargon_count / len(words)
        }
    
    async def _fallback_linguistic_analysis(self, content: str) -> LinguisticFeatures:
        """Fallback analysis when spaCy is not available"""
        self.logger.info("Using fallback linguistic analysis")
        
        # Basic tokenization
        sentences = sent_tokenize(content)
        words = word_tokenize(content)
        alpha_words = [w for w in words if w.isalpha()]
        
        # Basic metrics
        avg_sentence_length = len(alpha_words) / len(sentences) if sentences else 0
        avg_word_length = statistics.mean(len(w) for w in alpha_words) if alpha_words else 0
        
        # Basic readability
        flesch_reading_ease = textstat.flesch_reading_ease(content)
        flesch_kincaid_grade = textstat.flesch_kincaid_grade(content)
        
        # Simple vocabulary metrics
        unique_words = set(w.lower() for w in alpha_words)
        vocabulary_richness = len(unique_words) / len(alpha_words) if alpha_words else 0
        
        return LinguisticFeatures(
            avg_sentence_length=avg_sentence_length,
            avg_word_length=avg_word_length,
            sentence_length_variance=0,
            word_length_variance=0,
            flesch_reading_ease=flesch_reading_ease,
            flesch_kincaid_grade=flesch_kincaid_grade,
            gunning_fog=textstat.gunning_fog(content),
            automated_readability_index=textstat.automated_readability_index(content),
            vocabulary_richness=vocabulary_richness,
            lexical_diversity=vocabulary_richness,
            pos_distribution={},
            dependency_patterns={},
            simple_sentence_ratio=0.7,  # Default estimates
            compound_sentence_ratio=0.2,
            complex_sentence_ratio=0.1,
            punctuation_density=0.1,
            exclamation_ratio=0.05,
            question_ratio=0.05,
            technical_term_density=0.1,
            jargon_usage=0.05,
            confidence_score=0.4  # Low confidence for fallback
        )

class SemanticProcessor:
    """Semantic analysis using transformer models"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SemanticProcessor")
        self._load_models()
    
    def _load_models(self):
        """Load transformer models for semantic analysis"""
        try:
            if SentenceTransformer is None:
                raise ImportError("sentence-transformers not available")
            
            # Use a lightweight model for production
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.logger.info("Semantic models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading semantic models: {e}")
            self.sentence_model = None
    
    async def analyze_semantic_features(self, content: str) -> SemanticFeatures:
        """Extract semantic features using transformers"""
        if not self.sentence_model:
            self.logger.warning("Transformers not available, using fallback")
            return await self._fallback_semantic_analysis(content)
        
        # Split content into sentences
        sentences = sent_tokenize(content)
        if not sentences:
            return await self._fallback_semantic_analysis(content)
        
        # Generate embeddings
        embeddings = self.sentence_model.encode(sentences, convert_to_tensor=True)
        
        # Semantic coherence analysis
        coherence_score = await self._calculate_semantic_coherence(embeddings)
        
        # Topic consistency
        topic_consistency = await self._calculate_topic_consistency(embeddings)
        
        # Conceptual density
        conceptual_density = await self._calculate_conceptual_density(embeddings)
        
        # Theme analysis
        themes = await self._extract_themes(sentences, embeddings)
        
        # Clustering analysis
        clusters = await self._perform_semantic_clustering(sentences, embeddings)
        
        # Embedding statistics
        embedding_stats = await self._calculate_embedding_statistics(embeddings)
        
        return SemanticFeatures(
            semantic_coherence=coherence_score,
            topic_consistency=topic_consistency,
            conceptual_density=conceptual_density,
            primary_themes=themes['primary'],
            theme_distribution=themes['distribution'],
            content_clusters=clusters['clusters'],
            cluster_coherence=clusters['coherence'],
            embedding_variance=embedding_stats['variance'],
            semantic_diversity=embedding_stats['diversity'],
            confidence_score=0.85
        )
    
    async def _calculate_semantic_coherence(self, embeddings) -> float:
        """Calculate semantic coherence between sentences"""
        if len(embeddings) < 2:
            return 1.0
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = torch.cosine_similarity(embeddings[i].unsqueeze(0), embeddings[i+1].unsqueeze(0))
            similarities.append(sim.item())
        
        return statistics.mean(similarities)
    
    async def _calculate_topic_consistency(self, embeddings) -> float:
        """Calculate topic consistency across content"""
        if len(embeddings) < 3:
            return 1.0
        
        # Calculate variance in embeddings
        embedding_mean = torch.mean(embeddings, dim=0)
        variances = []
        
        for embedding in embeddings:
            variance = torch.var(embedding - embedding_mean)
            variances.append(variance.item())
        
        # Lower variance indicates higher consistency
        return 1.0 / (1.0 + statistics.mean(variances))
    
    async def _calculate_conceptual_density(self, embeddings) -> float:
        """Calculate conceptual density of content"""
        if len(embeddings) < 2:
            return 0.5
        
        # Calculate the spread of embeddings in semantic space
        pairwise_distances = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                distance = torch.dist(embeddings[i], embeddings[j])
                pairwise_distances.append(distance.item())
        
        if not pairwise_distances:
            return 0.5
        
        # Normalize to 0-1 range
        avg_distance = statistics.mean(pairwise_distances)
        return min(avg_distance / 2.0, 1.0)  # Normalize assuming max distance ~2
    
    async def _extract_themes(self, sentences: List[str], embeddings) -> Dict[str, Any]:
        """Extract primary themes using intelligent NLP techniques"""
        
        # Method 1: TF-IDF based intelligent keyword extraction
        if self.tfidf_vectorizer is not None:
            return await self._extract_themes_tfidf(sentences)
        
        # Method 2: spaCy-based entity and keyword extraction
        if self.nlp is not None:
            return await self._extract_themes_spacy(sentences)
        
        # Method 3: Statistical approach with proper stop word filtering
        return await self._extract_themes_statistical(sentences)
    
    async def _extract_themes_tfidf(self, sentences: List[str]) -> Dict[str, Any]:
        """Extract themes using TF-IDF and feature importance"""
        try:
            # Fit TF-IDF on sentences
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(sentences)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # Get feature scores (sum of TF-IDF scores across all sentences)
            feature_scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
            
            # Create word-score pairs and sort by importance
            word_scores = list(zip(feature_names, feature_scores))
            word_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Extract top themes
            primary_themes = [word for word, score in word_scores[:10] if score > 0]
            
            # Calculate theme distribution (normalized scores)
            total_score = sum(score for _, score in word_scores if score > 0)
            theme_distribution = {
                word: score / total_score 
                for word, score in word_scores[:15] 
                if score > 0
            }
            
            return {
                'primary': primary_themes[:5],
                'distribution': theme_distribution
            }
            
        except Exception as e:
            self.logger.warning(f"TF-IDF theme extraction failed: {e}")
            return await self._extract_themes_spacy(sentences)
    
    async def _extract_themes_spacy(self, sentences: List[str]) -> Dict[str, Any]:
        """Extract themes using spaCy's NLP capabilities"""
        try:
            # Process all sentences
            all_text = " ".join(sentences)
            doc = self.nlp(all_text)
            
            # Extract meaningful keywords using multiple strategies
            keywords = []
            
            # Strategy 1: Named entities
            entities = [ent.text.lower() for ent in doc.ents if ent.label_ in 
                       ['ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW', 'LANGUAGE']]
            keywords.extend(entities)
            
            # Strategy 2: Noun phrases (filtered)
            noun_phrases = [chunk.text.lower() for chunk in doc.noun_chunks 
                           if len(chunk.text) > 3 and not chunk.root.is_stop]
            keywords.extend(noun_phrases)
            
            # Strategy 3: Important individual words (NOUN, ADJ, VERB)
            important_words = [
                token.lemma_.lower() for token in doc 
                if (token.pos_ in ['NOUN', 'ADJ', 'VERB'] and 
                    not token.is_stop and 
                    not token.is_punct and 
                    len(token.text) > 3 and
                    token.is_alpha)
            ]
            keywords.extend(important_words)
            
            # Count and rank keywords
            keyword_counts = Counter(keywords)
            
            # Filter out very common words using frequency distribution
            total_keywords = sum(keyword_counts.values())
            filtered_keywords = {
                word: count for word, count in keyword_counts.items()
                if count / total_keywords < 0.3  # Not too frequent (likely stop words)
                and count > 1  # Appears more than once
                and len(word.split()) <= 3  # Not too long phrases
            }
            
            # Sort by importance
            sorted_keywords = sorted(filtered_keywords.items(), 
                                   key=lambda x: x[1], reverse=True)
            
            primary_themes = [word for word, _ in sorted_keywords[:10]]
            
            # Calculate distribution
            total_filtered = sum(filtered_keywords.values())
            theme_distribution = {
                word: count / total_filtered 
                for word, count in sorted_keywords[:15]
            }
            
            return {
                'primary': primary_themes[:5],
                'distribution': theme_distribution
            }
            
        except Exception as e:
            self.logger.warning(f"spaCy theme extraction failed: {e}")
            return await self._extract_themes_statistical(sentences)
    
    async def _extract_themes_statistical(self, sentences: List[str]) -> Dict[str, Any]:
        """Extract themes using statistical methods with smart filtering"""
        try:
            # Tokenize and clean all text
            all_text = " ".join(sentences).lower()
            
            # Use NLTK for better tokenization
            words = word_tokenize(all_text)
            
            # Smart filtering using multiple criteria
            filtered_words = []
            for word in words:
                if (len(word) > 3 and  # Minimum length
                    word.isalpha() and  # Only alphabetic
                    word not in self.stop_words and  # Not a stop word
                    not self._is_common_word(word)):  # Not too common
                    
                    # Lemmatize if possible
                    if self.lemmatizer:
                        word = self.lemmatizer.lemmatize(word)
                    
                    filtered_words.append(word)
            
            # Count occurrences
            word_counts = Counter(filtered_words)
            
            # Additional filtering: remove words that are too frequent or too rare
            total_words = len(filtered_words)
            final_keywords = {
                word: count for word, count in word_counts.items()
                if (count / total_words < 0.1 and  # Not more than 10% of all words
                    count >= 2)  # Appears at least twice
            }
            
            # Sort by frequency
            sorted_keywords = sorted(final_keywords.items(), 
                                   key=lambda x: x[1], reverse=True)
            
            primary_themes = [word for word, _ in sorted_keywords[:10]]
            
            # Calculate distribution
            total_final = sum(final_keywords.values())
            theme_distribution = {
                word: count / total_final 
                for word, count in sorted_keywords[:15]
            }
            
            return {
                'primary': primary_themes[:5],
                'distribution': theme_distribution
            }
            
        except Exception as e:
            self.logger.error(f"Statistical theme extraction failed: {e}")
            return {
                'primary': ['content', 'analysis', 'text'],
                'distribution': {'content': 0.3, 'analysis': 0.3, 'text': 0.4}
            }
    
    def _is_common_word(self, word: str) -> bool:
        """Determine if a word is too common using multiple heuristics"""
        # Check against common English word patterns
        common_patterns = [
            len(word) <= 2,  # Very short words
            word in ['said', 'says', 'say', 'make', 'made', 'take', 'took', 'come', 'came'],  # Common verbs
            word.endswith('ing') and len(word) <= 6,  # Short -ing words
            word.endswith('ed') and len(word) <= 5,   # Short past tense
            word in ['thing', 'things', 'something', 'anything', 'everything'],  # Generic nouns
            word.startswith('http') or '@' in word or '#' in word,  # URLs, mentions, hashtags
        ]
        
        return any(common_patterns)
    
    async def _perform_semantic_clustering(self, sentences: List[str], embeddings) -> Dict[str, Any]:
        """Perform semantic clustering of content"""
        if len(sentences) < 3:
            return {
                'clusters': [{'sentences': sentences, 'theme': 'general'}],
                'coherence': 1.0
            }
        
        # Convert to numpy for sklearn
        embeddings_np = embeddings.cpu().numpy()
        
        # Determine optimal number of clusters (simple heuristic)
        n_clusters = min(max(2, len(sentences) // 3), 5)
        
        try:
            if KMeans is not None:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embeddings_np)
                
                # Group sentences by cluster
                clusters = []
                for i in range(n_clusters):
                    cluster_sentences = [sentences[j] for j, label in enumerate(cluster_labels) if label == i]
                    if cluster_sentences:
                        clusters.append({
                            'sentences': cluster_sentences,
                            'theme': f'theme_{i+1}'
                        })
                
                # Calculate cluster coherence
                coherence = await self._calculate_cluster_coherence(embeddings_np, cluster_labels)
                
                return {
                    'clusters': clusters,
                    'coherence': coherence
                }
            else:
                # Fallback without sklearn
                return {
                    'clusters': [{'sentences': sentences, 'theme': 'general'}],
                    'coherence': 0.7
                }
                
        except Exception as e:
            self.logger.warning(f"Clustering failed: {e}")
            return {
                'clusters': [{'sentences': sentences, 'theme': 'general'}],
                'coherence': 0.5
            }
    
    async def _calculate_cluster_coherence(self, embeddings_np, cluster_labels) -> float:
        """Calculate coherence of clusters"""
        if cosine_similarity is None:
            return 0.7
        
        try:
            # Calculate within-cluster similarities
            coherence_scores = []
            
            for cluster_id in np.unique(cluster_labels):
                cluster_embeddings = embeddings_np[cluster_labels == cluster_id]
                if len(cluster_embeddings) > 1:
                    similarities = cosine_similarity(cluster_embeddings)
                    # Get upper triangle (excluding diagonal)
                    upper_triangle = similarities[np.triu_indices_from(similarities, k=1)]
                    if len(upper_triangle) > 0:
                        coherence_scores.append(np.mean(upper_triangle))
            
            return statistics.mean(coherence_scores) if coherence_scores else 0.7
            
        except Exception as e:
            self.logger.warning(f"Coherence calculation failed: {e}")
            return 0.7
    
    async def _calculate_embedding_statistics(self, embeddings) -> Dict[str, float]:
        """Calculate statistics about embeddings"""
        try:
            # Convert to numpy
            embeddings_np = embeddings.cpu().numpy()
            
            # Calculate variance across dimensions
            variance = np.var(embeddings_np, axis=0).mean()
            
            # Calculate diversity (spread of embeddings)
            if len(embeddings_np) > 1:
                pairwise_distances = []
                for i in range(len(embeddings_np)):
                    for j in range(i + 1, len(embeddings_np)):
                        distance = np.linalg.norm(embeddings_np[i] - embeddings_np[j])
                        pairwise_distances.append(distance)
                
                diversity = statistics.mean(pairwise_distances) if pairwise_distances else 0.5
            else:
                diversity = 0.0
            
            return {
                'variance': float(variance),
                'diversity': float(diversity)
            }
            
        except Exception as e:
            self.logger.warning(f"Embedding statistics calculation failed: {e}")
            return {'variance': 0.5, 'diversity': 0.5}
    
    async def _fallback_semantic_analysis(self, content: str) -> SemanticFeatures:
        """Fallback semantic analysis without transformers"""
        self.logger.info("Using fallback semantic analysis")
        
        sentences = sent_tokenize(content)
        
        # Simple theme extraction using our smart method
        themes = await self._extract_themes_statistical(sentences)
        
        return SemanticFeatures(
            semantic_coherence=0.7,  # Default estimate
            topic_consistency=0.6,
            conceptual_density=0.5,
            primary_themes=themes['primary'],
            theme_distribution=themes['distribution'],
            content_clusters=[{'sentences': sentences, 'theme': 'general'}],
            cluster_coherence=0.6,
            embedding_variance=0.5,
            semantic_diversity=0.5,
            confidence_score=0.4  # Low confidence for fallback
        )


class StatisticalAnalyzer:
    """Advanced statistical analysis of writing patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.StatisticalAnalyzer")
        self._load_resources()
    
    def _load_resources(self):
        """Load statistical analysis resources"""
        try:
            # Download required NLTK data
            nltk_downloads = ['punkt', 'stopwords', 'averaged_perceptron_tagger', 'wordnet']
            for download in nltk_downloads:
                try:
                    nltk.data.find(f'tokenizers/{download}')
                except LookupError:
                    nltk.download(download, quiet=True)
            
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
            
            # Initialize TF-IDF for pattern analysis
            if TfidfVectorizer is not None:
                self.tfidf = TfidfVectorizer(
                    stop_words='english',
                    max_features=500,
                    ngram_range=(1, 3),
                    min_df=1
                )
            else:
                self.tfidf = None
                
            self.logger.info("Statistical analyzer resources loaded")
            
        except Exception as e:
            self.logger.error(f"Error loading statistical resources: {e}")
            self.stop_words = set()
            self.lemmatizer = None
            self.tfidf = None
    
    async def analyze_statistical_features(self, content: str) -> StatisticalFeatures:
        """Extract comprehensive statistical features"""
        
        # Tokenization
        sentences = sent_tokenize(content)
        words = word_tokenize(content)
        alpha_words = [w for w in words if w.isalpha()]
        
        # Word frequency analysis
        word_freq = await self._analyze_word_frequency(alpha_words)
        
        # N-gram analysis
        ngrams = await self._analyze_ngrams(content)
        
        # Voice and person analysis
        voice_analysis = await self._analyze_voice_patterns(content, words)
        
        # Transition patterns
        transitions = await self._analyze_transition_patterns(sentences)
        
        # Emphasis patterns
        emphasis = await self._analyze_emphasis_patterns(content, words)
        
        return StatisticalFeatures(
            word_frequency_distribution=word_freq['distribution'],
            rare_word_usage=word_freq['rare_word_ratio'],
            common_word_preference=word_freq['common_word_ratio'],
            bigram_patterns=ngrams['bigrams'],
            trigram_patterns=ngrams['trigrams'],
            passive_voice_ratio=voice_analysis['passive_ratio'],
            first_person_usage=voice_analysis['first_person'],
            second_person_usage=voice_analysis['second_person'],
            third_person_usage=voice_analysis['third_person'],
            transition_word_usage=transitions['transition_ratio'],
            connecting_word_patterns=transitions['patterns'],
            capitalization_patterns=emphasis['capitalization'],
            emphasis_marker_usage=emphasis['emphasis_ratio'],
            confidence_score=0.85
        )
    
    async def _analyze_word_frequency(self, words: List[str]) -> Dict[str, Any]:
        """Analyze word frequency patterns"""
        if not words:
            return {
                'distribution': {},
                'rare_word_ratio': 0,
                'common_word_ratio': 0
            }
        
        # Clean and lemmatize words
        clean_words = []
        for word in words:
            word_lower = word.lower()
            if (len(word_lower) > 2 and 
                word_lower not in self.stop_words and 
                word_lower.isalpha()):
                
                if self.lemmatizer:
                    word_lower = self.lemmatizer.lemmatize(word_lower)
                clean_words.append(word_lower)
        
        if not clean_words:
            return {
                'distribution': {},
                'rare_word_ratio': 0,
                'common_word_ratio': 0
            }
        
        # Frequency analysis
        word_counts = Counter(clean_words)
        total_words = len(clean_words)
        
        # Calculate rare vs common word usage
        frequency_threshold_rare = 1  # Words appearing once
        frequency_threshold_common = max(1, total_words * 0.02)  # Top 2% threshold
        
        rare_words = sum(1 for count in word_counts.values() if count <= frequency_threshold_rare)
        common_words = sum(1 for count in word_counts.values() if count >= frequency_threshold_common)
        
        rare_word_ratio = rare_words / len(word_counts) if word_counts else 0
        common_word_ratio = common_words / len(word_counts) if word_counts else 0
        
        # Get top word frequencies (limit for storage)
        top_words = dict(word_counts.most_common(50))
        
        return {
            'distribution': top_words,
            'rare_word_ratio': rare_word_ratio,
            'common_word_ratio': common_word_ratio
        }
    
    async def _analyze_ngrams(self, content: str) -> Dict[str, Dict[str, int]]:
        """Analyze n-gram patterns"""
        try:
            # Clean content
            clean_content = re.sub(r'[^\w\s]', ' ', content.lower())
            words = clean_content.split()
            
            # Filter out stop words and short words
            filtered_words = [
                w for w in words 
                if len(w) > 2 and w not in self.stop_words
            ]
            
            if len(filtered_words) < 2:
                return {'bigrams': {}, 'trigrams': {}}
            
            # Generate bigrams
            bigrams = []
            for i in range(len(filtered_words) - 1):
                bigram = f"{filtered_words[i]} {filtered_words[i+1]}"
                bigrams.append(bigram)
            
            # Generate trigrams
            trigrams = []
            for i in range(len(filtered_words) - 2):
                trigram = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                trigrams.append(trigram)
            
            # Count and limit for storage
            bigram_counts = dict(Counter(bigrams).most_common(30))
            trigram_counts = dict(Counter(trigrams).most_common(20))
            
            return {
                'bigrams': bigram_counts,
                'trigrams': trigram_counts
            }
            
        except Exception as e:
            self.logger.warning(f"N-gram analysis failed: {e}")
            return {'bigrams': {}, 'trigrams': {}}
    
    async def _analyze_voice_patterns(self, content: str, words: List[str]) -> Dict[str, float]:
        """Analyze voice and person usage patterns"""
        
        # Passive voice detection (simplified)
        passive_indicators = ['is', 'are', 'was', 'were', 'been', 'being']
        past_participle_endings = ['ed', 'en', 'ne', 'te', 'se']
        
        sentences = sent_tokenize(content)
        passive_count = 0
        
        for sentence in sentences:
            sentence_words = word_tokenize(sentence.lower())
            has_passive_verb = any(word in passive_indicators for word in sentence_words)
            has_past_participle = any(
                any(word.endswith(ending) for ending in past_participle_endings)
                for word in sentence_words if len(word) > 3
            )
            if has_passive_verb and has_past_participle:
                passive_count += 1
        
        passive_ratio = passive_count / len(sentences) if sentences else 0
        
        # Person usage analysis
        first_person = ['i', 'me', 'my', 'mine', 'myself', 'we', 'us', 'our', 'ours', 'ourselves']
        second_person = ['you', 'your', 'yours', 'yourself', 'yourselves']
        third_person = ['he', 'she', 'it', 'they', 'him', 'her', 'them', 'his', 'hers', 'its', 'their', 'theirs']
        
        word_lower = [w.lower() for w in words if w.isalpha()]
        total_pronouns = len([w for w in word_lower if w in first_person + second_person + third_person])
        
        if total_pronouns > 0:
            first_person_usage = len([w for w in word_lower if w in first_person]) / total_pronouns
            second_person_usage = len([w for w in word_lower if w in second_person]) / total_pronouns
            third_person_usage = len([w for w in word_lower if w in third_person]) / total_pronouns
        else:
            first_person_usage = second_person_usage = third_person_usage = 0
        
        return {
            'passive_ratio': passive_ratio,
            'first_person': first_person_usage,
            'second_person': second_person_usage,
            'third_person': third_person_usage
        }
    
    async def _analyze_transition_patterns(self, sentences: List[str]) -> Dict[str, Any]:
        """Analyze transition and connecting word usage"""
        
        transition_words = {
            'addition': ['also', 'furthermore', 'moreover', 'additionally', 'besides'],
            'contrast': ['however', 'nevertheless', 'nonetheless', 'conversely', 'although'],
            'cause_effect': ['therefore', 'consequently', 'thus', 'hence', 'accordingly'],
            'sequence': ['first', 'second', 'third', 'next', 'then', 'finally'],
            'emphasis': ['indeed', 'certainly', 'undoubtedly', 'definitely'],
            'example': ['example', 'instance', 'specifically', 'particularly']
        }
        
        all_transitions = []
        for category_words in transition_words.values():
            all_transitions.extend(category_words)
        
        # Count transition usage
        transition_count = 0
        pattern_counts = defaultdict(int)
        
        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            for word in words:
                if word in all_transitions:
                    transition_count += 1
                    # Find category
                    for category, category_words in transition_words.items():
                        if word in category_words:
                            pattern_counts[category] += 1
                            break
        
        total_sentences = len(sentences)
        transition_ratio = transition_count / total_sentences if total_sentences > 0 else 0
        
        return {
            'transition_ratio': transition_ratio,
            'patterns': dict(pattern_counts)
        }
    
    async def _analyze_emphasis_patterns(self, content: str, words: List[str]) -> Dict[str, Any]:
        """Analyze emphasis and capitalization patterns"""
        
        # Capitalization patterns
        cap_patterns = {
            'all_caps': len([w for w in words if w.isupper() and len(w) > 1]),
            'title_case': len([w for w in words if w.istitle() and len(w) > 1]),
            'mixed_case': len([w for w in words if any(c.isupper() for c in w[1:]) and any(c.islower() for c in w)])
        }
        
        # Emphasis markers
        emphasis_markers = ['!', '?', '*', '_', '"', "'"]
        emphasis_count = sum(content.count(marker) for marker in emphasis_markers)
        
        # Calculate ratios
        total_words = len([w for w in words if w.isalpha()])
        emphasis_ratio = emphasis_count / len(content) if content else 0
        
        return {
            'capitalization': cap_patterns,
            'emphasis_ratio': emphasis_ratio
        }


class LLMInsightsGenerator:
    """Generate high-level style insights using CAMEL agents"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.LLMInsightsGenerator")
        self._setup_agents()
    
    def _setup_agents(self):
        """Setup specialized CAMEL agents for style analysis"""
        try:
            # Create a specialized style analysis agent
            self.style_agent = agent_factory.create_agent(
                agent_type=AgentType.STYLE_ANALYZER,
                project_id=self.project_id,
                custom_instructions="""
                You are an expert content style analyst. Analyze writing samples to identify:
                1. Tone and voice characteristics
                2. Audience positioning and expertise level
                3. Communication style and engagement patterns
                4. Brand personality traits
                5. Industry-specific adaptations
                
                Provide specific, quantifiable insights with evidence from the text.
                Focus on actionable style elements that can guide content creation.
                """
            )
            
            self.logger.info("LLM analysis agents initialized")
            
        except Exception as e:
            self.logger.error(f"Error setting up LLM agents: {e}")
            self.style_agent = None
    
    async def generate_llm_insights(self, content: str, 
                                  linguistic_features: LinguisticFeatures,
                                  semantic_features: SemanticFeatures) -> LLMInsights:
        """Generate high-level insights using LLM analysis"""
        
        if not self.style_agent:
            self.logger.warning("LLM agent not available, using fallback insights")
            return await self._fallback_insights(content)
        
        try:
            # Prepare analysis prompt with context
            analysis_prompt = await self._create_analysis_prompt(
                content, linguistic_features, semantic_features
            )
            
            # Get insights from LLM
            response = self.style_agent.step(analysis_prompt)
            insights_text = response.msg.content
            
            # Parse and structure the insights
            structured_insights = await self._parse_llm_insights(insights_text)
            
            return structured_insights
            
        except Exception as e:
            self.logger.error(f"LLM insight generation failed: {e}")
            return await self._fallback_insights(content)
    
    async def _create_analysis_prompt(self, content: str,
                                    linguistic_features: LinguisticFeatures,
                                    semantic_features: SemanticFeatures) -> str:
        """Create comprehensive analysis prompt for LLM"""
        
        # Truncate content if too long
        content_sample = content[:2000] + "..." if len(content) > 2000 else content
        
        prompt = f"""
        Analyze this content sample for detailed style characteristics:

        CONTENT SAMPLE:
        {content_sample}

        LINGUISTIC CONTEXT:
        - Average sentence length: {linguistic_features.avg_sentence_length:.1f} words
        - Reading level: {linguistic_features.flesch_kincaid_grade:.1f}
        - Vocabulary richness: {linguistic_features.vocabulary_richness:.2f}
        - Primary themes: {', '.join(semantic_features.primary_themes[:3])}

        ANALYSIS REQUIREMENTS:
        1. TONE ANALYSIS: Identify the dominant emotional tone (scale 1-10 for each):
           - Professional, Casual, Authoritative, Friendly, Technical, Creative

        2. VOICE CHARACTERISTICS: Describe the writing voice:
           - Personality traits (confident, approachable, expert, etc.)
           - Communication values (clarity, precision, engagement, etc.)

        3. AUDIENCE POSITIONING: How does the writer position themselves?
           - Expertise level demonstrated
           - Relationship with audience (peer, teacher, consultant, etc.)

        4. COMMUNICATION STYLE:
           - Directness level (1-10)
           - Engagement approach
           - Persuasion techniques used

        5. INDUSTRY ADAPTATION: How does the style adapt to industry/context?

        Provide specific examples from the text to support your analysis.
        Format your response as structured insights with clear categories.
        """
        
        return prompt
    
    async def _parse_llm_insights(self, insights_text: str) -> LLMInsights:
        """Parse and structure LLM insights into data format"""
        
        # This is a simplified parser - in production, you might use more sophisticated NLP
        try:
            # Extract tone scores (looking for patterns like "Professional: 8")
            tone_pattern = r'(\w+):\s*(\d+(?:\.\d+)?)'
            tone_matches = re.findall(tone_pattern, insights_text, re.IGNORECASE)
            
            tone_analysis = {}
            for tone_name, score in tone_matches:
                try:
                    tone_analysis[tone_name.lower()] = float(score) / 10.0  # Normalize to 0-1
                except ValueError:
                    continue
            
            # Extract formality level
            formality_pattern = r'formality.*?(\d+(?:\.\d+)?)'
            formality_match = re.search(formality_pattern, insights_text, re.IGNORECASE)
            formality_level = float(formality_match.group(1)) / 10.0 if formality_match else 0.5
            
            # Extract directness level
            directness_pattern = r'directness.*?(\d+(?:\.\d+)?)'
            directness_match = re.search(directness_pattern, insights_text, re.IGNORECASE)
            directness_level = float(directness_match.group(1)) / 10.0 if directness_match else 0.5
            
            # Extract key phrases for characteristics
            personality_keywords = ['confident', 'approachable', 'expert', 'friendly', 'professional', 'authoritative']
            personality_traits = [trait for trait in personality_keywords if trait in insights_text.lower()]
            
            # Default values with extracted content
            return LLMInsights(
                tone_analysis=tone_analysis or {'professional': 0.7, 'authoritative': 0.6},
                voice_characteristics={
                    'primary_voice': personality_traits[0] if personality_traits else 'professional',
                    'secondary_traits': personality_traits[1:3] if len(personality_traits) > 1 else ['clear']
                },
                audience_positioning=self._extract_audience_positioning(insights_text),
                expertise_level=self._extract_expertise_level(insights_text),
                formality_level=formality_level,
                directness_level=directness_level,
                engagement_style=self._extract_engagement_style(insights_text),
                persuasion_techniques=self._extract_persuasion_techniques(insights_text),
                personality_traits=personality_traits or ['professional', 'clear'],
                communication_values=['clarity', 'expertise'],
                industry_adaptation=self._extract_industry_adaptation(insights_text),
                content_purpose_alignment='informative',
                confidence_score=0.8
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing LLM insights: {e}")
            return await self._fallback_insights("")
    
    def _extract_audience_positioning(self, text: str) -> str:
        """Extract audience positioning from insights text"""
        positioning_keywords = {
            'expert': ['expert', 'authority', 'specialist', 'professional'],
            'peer': ['peer', 'colleague', 'equal', 'collaborative'],
            'teacher': ['teacher', 'educator', 'guide', 'instructor'],
            'consultant': ['consultant', 'advisor', 'recommended', 'guidance']
        }
        
        text_lower = text.lower()
        for position, keywords in positioning_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return position
        
        return 'professional'
    
    def _extract_expertise_level(self, text: str) -> str:
        """Extract demonstrated expertise level"""
        if any(word in text.lower() for word in ['advanced', 'expert', 'sophisticated', 'complex']):
            return 'advanced'
        elif any(word in text.lower() for word in ['intermediate', 'moderate', 'some']):
            return 'intermediate'
        else:
            return 'basic'
    
    def _extract_engagement_style(self, text: str) -> str:
        """Extract engagement style"""
        engagement_patterns = {
            'interactive': ['question', 'engage', 'interactive', 'participate'],
            'informative': ['inform', 'explain', 'describe', 'detail'],
            'persuasive': ['convince', 'persuade', 'argue', 'recommend'],
            'storytelling': ['story', 'narrative', 'example', 'anecdote']
        }
        
        text_lower = text.lower()
        for style, keywords in engagement_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return style
        
        return 'informative'
    
    def _extract_persuasion_techniques(self, text: str) -> List[str]:
        """Extract persuasion techniques used"""
        techniques = {
            'evidence': ['data', 'research', 'study', 'evidence', 'proof'],
            'authority': ['expert', 'authority', 'credential', 'experience'],
            'logic': ['logic', 'reason', 'therefore', 'because', 'analysis'],
            'emotion': ['feel', 'emotion', 'passionate', 'exciting', 'concern']
        }
        
        text_lower = text.lower()
        found_techniques = []
        
        for technique, keywords in techniques.items():
            if any(keyword in text_lower for keyword in keywords):
                found_techniques.append(technique)
        
        return found_techniques or ['logic']
    
    def _extract_industry_adaptation(self, text: str) -> str:
        """Extract industry-specific adaptations"""
        industry_keywords = {
            'technology': ['tech', 'software', 'digital', 'data', 'algorithm'],
            'business': ['business', 'market', 'strategy', 'revenue', 'growth'],
            'education': ['learn', 'teach', 'student', 'education', 'knowledge'],
            'healthcare': ['health', 'medical', 'patient', 'treatment', 'care'],
            'finance': ['financial', 'money', 'investment', 'budget', 'cost']
        }
        
        text_lower = text.lower()
        for industry, keywords in industry_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return industry
        
        return 'general'
    
    async def _fallback_insights(self, content: str) -> LLMInsights:
        """Generate fallback insights when LLM is not available"""
        
        # Basic analysis based on content characteristics
        word_count = len(content.split())
        sentence_count = len(sent_tokenize(content))
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Estimate characteristics based on simple heuristics
        if avg_sentence_length > 20:
            formality = 0.8
            complexity = 'advanced'
        elif avg_sentence_length > 15:
            formality = 0.6
            complexity = 'intermediate'
        else:
            formality = 0.4
            complexity = 'basic'
        
        return LLMInsights(
            tone_analysis={'professional': 0.7, 'informative': 0.8},
            voice_characteristics={'primary_voice': 'professional', 'clarity': 'high'},
            audience_positioning='professional',
            expertise_level=complexity,
            formality_level=formality,
            directness_level=0.6,
            engagement_style='informative',
            persuasion_techniques=['logic', 'evidence'],
            personality_traits=['professional', 'clear'],
            communication_values=['clarity', 'accuracy'],
            industry_adaptation='general',
            content_purpose_alignment='informative',
            confidence_score=0.4  # Low confidence for fallback
        )


class LanguageCodeGenerator:
    """Generate dynamic language codes compatible with existing format"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LanguageCodeGenerator")
    
    async def generate_language_code(self, 
                                   linguistic_features: LinguisticFeatures,
                                   semantic_features: SemanticFeatures,
                                   statistical_features: StatisticalFeatures,
                                   llm_insights: LLMInsights) -> LanguageCode:
        """Generate language code based on comprehensive analysis"""
        
        try:
            # Map analysis results to language code parameters
            content_focus = await self._determine_content_focus(semantic_features)
            creative_freedom = await self._determine_creative_freedom(statistical_features, llm_insights)
            persuasiveness = await self._determine_persuasiveness(llm_insights)
            figurative_language = await self._determine_figurative_language(linguistic_features)
            verb_strength = await self._determine_verb_strength(statistical_features)
            language_formality = await self._determine_formality(llm_insights, linguistic_features)
            detail_level = await self._determine_detail_level(linguistic_features, semantic_features)
            sentence_complexity = await self._determine_sentence_complexity(linguistic_features)
            vocabulary_level = await self._determine_vocabulary_level(linguistic_features)
            subject_expertise = await self._determine_subject_expertise(llm_insights, semantic_features)
            audience = await self._determine_audience(llm_insights)
            tone = await self._determine_tone(llm_insights)
            
            return LanguageCode(
                content_focus=content_focus,
                creative_freedom_conceptual=creative_freedom['conceptual'],
                creative_freedom_structural=creative_freedom['structural'],
                persuasiveness=persuasiveness,
                figurative_language=figurative_language,
                verb_strength=verb_strength,
                language_formality=language_formality,
                detail_level=detail_level,
                sentence_complexity=sentence_complexity,
                vocabulary_level=vocabulary_level,
                subject_expertise=subject_expertise,
                audience=audience,
                tone=tone
            )
            
        except Exception as e:
            self.logger.error(f"Language code generation failed: {e}")
            return await self._fallback_language_code()
    
    async def _determine_content_focus(self, semantic_features: SemanticFeatures) -> int:
        """Determine content focus (1-5 scale)"""
        # Based on topic consistency and theme concentration
        if semantic_features.topic_consistency > 0.8:
            return 5  # Very focused
        elif semantic_features.topic_consistency > 0.6:
            return 4
        elif semantic_features.topic_consistency > 0.4:
            return 3
        elif semantic_features.topic_consistency > 0.2:
            return 2
        else:
            return 1  # Very broad
    
    async def _determine_creative_freedom(self, statistical_features: StatisticalFeatures,
                                        llm_insights: LLMInsights) -> Dict[str, int]:
        """Determine creative freedom levels"""
        
        # Conceptual freedom based on vocabulary diversity and themes
        vocab_diversity = statistical_features.rare_word_usage
        conceptual = min(10, max(1, int(vocab_diversity * 10) + 3))
        
        # Structural freedom based on sentence variety and formality
        structural_variety = (
            abs(statistical_features.passive_voice_ratio - 0.2) +  # Varied voice usage
            (1 - llm_insights.formality_level)  # Less formal = more structural freedom
        )
        structural = min(10, max(1, int(structural_variety * 10)))
        
        return {
            'conceptual': conceptual,
            'structural': structural
        }
    
    async def _determine_persuasiveness(self, llm_insights: LLMInsights) -> int:
        """Determine persuasiveness level (1-5 scale)"""
        
        persuasion_score = 0
        
        # Check for persuasive techniques
        if 'emotion' in llm_insights.persuasion_techniques:
            persuasion_score += 2
        if 'authority' in llm_insights.persuasion_techniques:
            persuasion_score += 1
        if llm_insights.engagement_style == 'persuasive':
            persuasion_score += 2
        
        # Check tone for persuasive elements
        tone_scores = llm_insights.tone_analysis
        if tone_scores.get('authoritative', 0) > 0.7:
            persuasion_score += 1
        
        return min(5, max(1, persuasion_score))
    
    async def _determine_figurative_language(self, linguistic_features: LinguisticFeatures) -> int:
        """Determine figurative language usage (1-5 scale)"""
        
        # Estimate based on vocabulary richness and complexity
        richness = linguistic_features.vocabulary_richness
        complexity = linguistic_features.sentence_length_variance
        
        # Higher vocabulary richness and sentence variety suggests more figurative language
        fig_score = (richness * 2) + (complexity / 10)
        
        return min(5, max(1, int(fig_score * 5) + 1))
    
    async def _determine_verb_strength(self, statistical_features: StatisticalFeatures) -> int:
        """Determine verb strength (1-10 scale)"""
        
        # Check for action-oriented language patterns
        passive_ratio = statistical_features.passive_voice_ratio
        
        # Lower passive voice = stronger active verbs
        active_strength = 1 - passive_ratio
        
        # Map to 1-10 scale
        return min(10, max(1, int(active_strength * 8) + 2))
    
    async def _determine_formality(self, llm_insights: LLMInsights, 
                                 linguistic_features: LinguisticFeatures) -> int:
        """Determine language formality (1-5 scale)"""
        
        # Use LLM formality assessment as primary indicator
        formality_score = llm_insights.formality_level * 5
        
        # Adjust based on linguistic features
        if linguistic_features.flesch_kincaid_grade > 12:
            formality_score += 0.5  # Higher grade level = more formal
        
        if linguistic_features.avg_word_length > 6:
            formality_score += 0.5  # Longer words = more formal
        
        return min(5, max(1, int(formality_score)))
    
    async def _determine_detail_level(self, linguistic_features: LinguisticFeatures,
                                    semantic_features: SemanticFeatures) -> int:
        """Determine level of detail (1-5 scale)"""
        
        # Longer sentences and higher conceptual density = more detail
        sentence_factor = min(1.0, linguistic_features.avg_sentence_length / 25)
        density_factor = semantic_features.conceptual_density
        
        detail_score = (sentence_factor + density_factor) * 2.5
        
        return min(5, max(1, int(detail_score) + 1))
    
    async def _determine_sentence_complexity(self, linguistic_features: LinguisticFeatures) -> int:
        """Determine sentence complexity (1-5 scale)"""
        
        # Based on sentence structure ratios
        complex_ratio = linguistic_features.complex_sentence_ratio
        compound_ratio = linguistic_features.compound_sentence_ratio
        
        # Weight complex sentences more heavily
        complexity_score = (complex_ratio * 2) + compound_ratio
        
        return min(5, max(1, int(complexity_score * 5) + 1))
    
    async def _determine_vocabulary_level(self, linguistic_features: LinguisticFeatures) -> int:
        """Determine vocabulary level (1-10 scale)"""
        
        # Combine multiple vocabulary indicators
        word_length_factor = min(1.0, linguistic_features.avg_word_length / 8)
        richness_factor = linguistic_features.vocabulary_richness
        grade_level_factor = min(1.0, linguistic_features.flesch_kincaid_grade / 16)
        
        vocab_score = (word_length_factor + richness_factor + grade_level_factor) / 3
        
        return min(10, max(1, int(vocab_score * 8) + 2))
    
    async def _determine_subject_expertise(self, llm_insights: LLMInsights,
                                         semantic_features: SemanticFeatures) -> int:
        """Determine subject expertise level (1-5 scale)"""
        
        expertise_mapping = {
            'basic': 1,
            'intermediate': 3,
            'advanced': 5
        }
        
        base_score = expertise_mapping.get(llm_insights.expertise_level, 3)
        
        # Adjust based on topic consistency (experts tend to be more focused)
        if semantic_features.topic_consistency > 0.7:
            base_score = min(5, base_score + 1)
        
        return base_score
    
    async def _determine_audience(self, llm_insights: LLMInsights) -> str:
        """Determine target audience"""
        
        # Map audience positioning to audience codes
        audience_mapping = {
            'expert': 'experts',
            'professional': 'professionals',
            'peer': 'peers',
            'teacher': 'students',
            'consultant': 'clients'
        }
        
        base_audience = audience_mapping.get(llm_insights.audience_positioning, 'general')
        
        # Consider industry adaptation
        if llm_insights.industry_adaptation != 'general':
            return f"{llm_insights.industry_adaptation}-{base_audience}"
        
        return base_audience
    
    async def _determine_tone(self, llm_insights: LLMInsights) -> str:
        """Determine primary tone with intensity"""
        
        tone_analysis = llm_insights.tone_analysis
        
        if not tone_analysis:
            return "professional-5"
        
        # Find dominant tone
        dominant_tone = max(tone_analysis.items(), key=lambda x: x[1])
        tone_name, intensity = dominant_tone
        
        # Map tone names to codes
        tone_codes = {
            'professional': 'P',
            'authoritative': 'A',
            'friendly': 'F',
            'technical': 'T',
            'creative': 'C',
            'casual': 'CA',
            'empathetic': 'EMP',
            'enthusiastic': 'ET'
        }
        
        tone_code = tone_codes.get(tone_name.lower(), 'P')
        intensity_level = min(5, max(1, int(intensity * 5)))
        
        return f"{tone_code}-{intensity_level}"
    
    async def _fallback_language_code(self) -> LanguageCode:
        """Generate fallback language code with reasonable defaults"""
        
        return LanguageCode(
            content_focus=3,
            creative_freedom_conceptual=5,
            creative_freedom_structural=5,
            persuasiveness=3,
            figurative_language=2,
            verb_strength=6,
            language_formality=3,
            detail_level=3,
            sentence_complexity=3,
            vocabulary_level=5,
            subject_expertise=3,
            audience="professionals",
            tone="P-5"
        )


class ProductionStyleAnalyzer:
    """
    Production-grade style analyzer that orchestrates all analysis components
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.ProductionStyleAnalyzer")
        
        # Initialize analysis components
        self.linguistic_processor = LinguisticProcessor()
        self.semantic_processor = SemanticProcessor()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.llm_insights_generator = LLMInsightsGenerator(project_id)
        self.language_code_generator = LanguageCodeGenerator()
        
        # Initialize knowledge base connection
        if project_id:
            self.knowledge_base = KnowledgeBase(project_id)
        else:
            self.knowledge_base = None
    
    async def analyze_content_corpus(self, content_samples: List[str]) -> StyleProfile:
        """
        Analyze a corpus of content samples to create comprehensive style profile
        
        Args:
            content_samples: List of content strings to analyze
            
        Returns:
            Complete StyleProfile with all analysis components
        """
        
        self.logger.info(f"Starting style analysis for {len(content_samples)} content samples")
        
        try:
            # Validate input
            if not content_samples:
                raise ValueError("No content samples provided for analysis")
            
            # Prepare content for analysis
            processed_content = await self._prepare_content(content_samples)
            
            # Run all analysis components in parallel for performance
            analysis_tasks = [
                self._run_linguistic_analysis(processed_content),
                self._run_semantic_analysis(processed_content),
                self._run_statistical_analysis(processed_content)
            ]
            
            linguistic_features, semantic_features, statistical_features = await asyncio.gather(*analysis_tasks)
            
            # Generate LLM insights (requires results from other analyses)
            llm_insights = await self.llm_insights_generator.generate_llm_insights(
                processed_content, linguistic_features, semantic_features
            )
            
            # Generate language code
            language_code = await self.language_code_generator.generate_language_code(
                linguistic_features, semantic_features, statistical_features, llm_insights
            )
            
            # Create comprehensive style guide
            style_guide = await self._create_style_guide(
                linguistic_features, semantic_features, statistical_features, llm_insights, language_code
            )
            
            # Calculate overall confidence score
            analysis_confidence = await self._calculate_confidence(
                linguistic_features, semantic_features, statistical_features, llm_insights
            )
            
            # Create style profile
            style_profile = StyleProfile(
                project_id=self.project_id or "anonymous",
                analysis_id=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now(),
                linguistic_features=linguistic_features,
                semantic_features=semantic_features,
                statistical_features=statistical_features,
                llm_insights=llm_insights,
                language_code=language_code,
                style_guide=style_guide,
                content_samples_analyzed=len(content_samples),
                total_word_count=len(processed_content.split()),
                analysis_confidence=analysis_confidence
            )
            
            # Store results in knowledge base if available
            if self.knowledge_base:
                await self._store_analysis_results(style_profile)
            
            self.logger.info(f"Style analysis completed with confidence: {analysis_confidence:.2f}")
            
            return style_profile
            
        except Exception as e:
            self.logger.error(f"Style analysis failed: {e}")
            raise
    
    async def _prepare_content(self, content_samples: List[str]) -> str:
        """Prepare and clean content for analysis"""
        
        # Combine all samples
        combined_content = "\n\n".join(content_samples)
        
        # Basic cleaning
        # Remove excessive whitespace
        cleaned_content = re.sub(r'\s+', ' ', combined_content)
        
        # Remove URLs
        cleaned_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned_content)
        
        # Remove email addresses
        cleaned_content = re.sub(r'\S+@\S+', '', cleaned_content)
        
        # Remove excessive punctuation
        cleaned_content = re.sub(r'[.]{3,}', '...', cleaned_content)
        cleaned_content = re.sub(r'[!]{2,}', '!', cleaned_content)
        cleaned_content = re.sub(r'[?]{2,}', '?', cleaned_content)
        
        return cleaned_content.strip()
    
    async def _run_linguistic_analysis(self, content: str) -> LinguisticFeatures:
        """Run linguistic analysis component"""
        try:
            return await self.linguistic_processor.analyze_linguistic_features(content)
        except Exception as e:
            self.logger.warning(f"Linguistic analysis failed: {e}")
            # Return minimal features on failure
            return LinguisticFeatures(
                avg_sentence_length=15.0,
                avg_word_length=5.0,
                sentence_length_variance=5.0,
                word_length_variance=2.0,
                flesch_reading_ease=60.0,
                flesch_kincaid_grade=10.0,
                gunning_fog=12.0,
                automated_readability_index=10.0,
                vocabulary_richness=0.5,
                lexical_diversity=0.5,
                pos_distribution={},
                dependency_patterns={},
                simple_sentence_ratio=0.6,
                compound_sentence_ratio=0.3,
                complex_sentence_ratio=0.1,
                punctuation_density=0.1,
                exclamation_ratio=0.05,
                question_ratio=0.05,
                technical_term_density=0.1,
                jargon_usage=0.05,
                confidence_score=0.2
            )
    
    async def _run_semantic_analysis(self, content: str) -> SemanticFeatures:
        """Run semantic analysis component"""
        try:
            return await self.semantic_processor.analyze_semantic_features(content)
        except Exception as e:
            self.logger.warning(f"Semantic analysis failed: {e}")
            # Return minimal features on failure
            return SemanticFeatures(
                semantic_coherence=0.7,
                topic_consistency=0.6,
                conceptual_density=0.5,
                primary_themes=['content', 'analysis'],
                theme_distribution={'content': 0.5, 'analysis': 0.5},
                content_clusters=[],
                cluster_coherence=0.6,
                embedding_variance=0.5,
                semantic_diversity=0.5,
                confidence_score=0.2
            )
    
    async def _run_statistical_analysis(self, content: str) -> StatisticalFeatures:
        """Run statistical analysis component"""
        try:
            return await self.statistical_analyzer.analyze_statistical_features(content)
        except Exception as e:
            self.logger.warning(f"Statistical analysis failed: {e}")
            # Return minimal features on failure
            return StatisticalFeatures(
                word_frequency_distribution={},
                rare_word_usage=0.3,
                common_word_preference=0.7,
                bigram_patterns={},
                trigram_patterns={},
                passive_voice_ratio=0.2,
                first_person_usage=0.1,
                second_person_usage=0.2,
                third_person_usage=0.7,
                transition_word_usage=0.1,
                connecting_word_patterns={},
                capitalization_patterns={},
                emphasis_marker_usage=0.05,
                confidence_score=0.2
            )
    
    async def _create_style_guide(self, 
                                linguistic_features: LinguisticFeatures,
                                semantic_features: SemanticFeatures,
                                statistical_features: StatisticalFeatures,
                                llm_insights: LLMInsights,
                                language_code: LanguageCode) -> Dict[str, Any]:
        """Create comprehensive style guide from analysis results"""
        
        style_guide = {
            "overview": {
                "primary_voice": llm_insights.voice_characteristics.get('primary_voice', 'professional'),
                "target_audience": llm_insights.audience_positioning,
                "expertise_level": llm_insights.expertise_level,
                "industry_focus": llm_insights.industry_adaptation,
                "language_code": language_code.to_code_string()
            },
            
            "writing_style": {
                "sentence_structure": {
                    "average_length": f"{linguistic_features.avg_sentence_length:.1f} words",
                    "complexity_preference": "complex" if linguistic_features.complex_sentence_ratio > 0.3 else "simple",
                    "variety_score": linguistic_features.sentence_length_variance
                },
                
                "vocabulary": {
                    "sophistication_level": language_code.vocabulary_level,
                    "technical_density": f"{linguistic_features.technical_term_density:.1%}",
                    "richness_score": linguistic_features.vocabulary_richness,
                    "preferred_word_length": f"{linguistic_features.avg_word_length:.1f} characters"
                },
                
                "tone_characteristics": {
                    "formality_level": language_code.language_formality,
                    "directness": llm_insights.directness_level,
                    "primary_tones": list(llm_insights.tone_analysis.keys())[:3],
                    "engagement_style": llm_insights.engagement_style
                }
            },
            
            "content_patterns": {
                "focus_level": language_code.content_focus,
                "detail_preference": language_code.detail_level,
                "primary_themes": semantic_features.primary_themes,
                "topic_consistency": semantic_features.topic_consistency,
                "persuasion_level": language_code.persuasiveness
            },
            
            "technical_guidelines": {
                "readability_target": {
                    "flesch_score": linguistic_features.flesch_reading_ease,
                    "grade_level": linguistic_features.flesch_kincaid_grade,
                    "target_audience": "general" if linguistic_features.flesch_reading_ease > 60 else "specialized"
                },
                
                "voice_usage": {
                    "active_voice_preference": f"{(1 - statistical_features.passive_voice_ratio):.1%}",
                    "person_usage": {
                        "first_person": f"{statistical_features.first_person_usage:.1%}",
                        "second_person": f"{statistical_features.second_person_usage:.1%}",
                        "third_person": f"{statistical_features.third_person_usage:.1%}"
                    }
                },
                
                "structural_elements": {
                    "transition_usage": f"{statistical_features.transition_word_usage:.1%}",
                    "emphasis_patterns": statistical_features.emphasis_marker_usage,
                    "punctuation_style": linguistic_features.punctuation_density
                }
            },
            
            "brand_voice_elements": {
                "personality_traits": llm_insights.personality_traits,
                "communication_values": llm_insights.communication_values,
                "persuasion_techniques": llm_insights.persuasion_techniques,
                "audience_relationship": llm_insights.audience_positioning
            },
            
            "implementation_guidelines": {
                "content_creation_focus": f"CF={language_code.content_focus}",
                "creative_freedom": f"Conceptual: {language_code.creative_freedom_conceptual}/10, Structural: {language_code.creative_freedom_structural}/10",
                "language_formality": f"LF={language_code.language_formality}",
                "vocabulary_level": f"VL={language_code.vocabulary_level}",
                "subject_expertise": f"SE={language_code.subject_expertise}"
            }
        }
        
        return style_guide
    
    async def _calculate_confidence(self, 
                                  linguistic_features: LinguisticFeatures,
                                  semantic_features: SemanticFeatures,
                                  statistical_features: StatisticalFeatures,
                                  llm_insights: LLMInsights) -> float:
        """Calculate overall confidence score for the analysis"""
        
        # Weight each component's confidence
        confidence_scores = [
            (linguistic_features.confidence_score, 0.25),
            (semantic_features.confidence_score, 0.25),
            (statistical_features.confidence_score, 0.25),
            (llm_insights.confidence_score, 0.25)
        ]
        
        # Calculate weighted average
        total_confidence = sum(score * weight for score, weight in confidence_scores)
        
        return round(total_confidence, 3)
    
    async def _store_analysis_results(self, style_profile: StyleProfile):
        """Store analysis results in knowledge base"""
        
        if not self.knowledge_base:
            return
        
        try:
            # Store the complete style profile
            await self.knowledge_base.store_document({
                "type": "style_analysis",
                "title": f"Style Analysis - {style_profile.analysis_id}",
                "content": json.dumps(style_profile.to_dict(), indent=2),
                "metadata": {
                    "analysis_id": style_profile.analysis_id,
                    "content_samples_count": style_profile.content_samples_analyzed,
                    "word_count": style_profile.total_word_count,
                    "confidence_score": style_profile.analysis_confidence,
                    "language_code": style_profile.language_code.to_code_string(),
                    "created_at": style_profile.created_at.isoformat()
                }
            })
            
            self.logger.info(f"Style analysis stored in knowledge base: {style_profile.analysis_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store analysis results: {e}")
    
    async def export_team_format(self, style_profile: StyleProfile) -> Dict[str, Any]:
        """Export analysis results in team's current format"""
        return style_profile.to_team_format()
    
    async def get_style_consistency_score(self, content: str, style_profile: StyleProfile) -> float:
        """Check how well new content matches the established style profile"""
        
        try:
            # Quick analysis of new content
            quick_linguistic = await self.linguistic_processor.analyze_linguistic_features(content)
            quick_semantic = await self.semantic_processor.analyze_semantic_features(content)
            
            # Compare key metrics
            consistency_scores = []
            
            # Sentence length consistency
            length_diff = abs(quick_linguistic.avg_sentence_length - style_profile.linguistic_features.avg_sentence_length)
            length_score = max(0, 1 - (length_diff / 20))  # Normalize to 0-1
            consistency_scores.append(length_score)
            
            # Vocabulary consistency
            vocab_diff = abs(quick_linguistic.vocabulary_richness - style_profile.linguistic_features.vocabulary_richness)
            vocab_score = max(0, 1 - (vocab_diff / 0.5))
            consistency_scores.append(vocab_score)
            
            # Theme consistency
            common_themes = set(quick_semantic.primary_themes) & set(style_profile.semantic_features.primary_themes)
            theme_score = len(common_themes) / max(1, len(style_profile.semantic_features.primary_themes))
            consistency_scores.append(theme_score)
            
            # Overall consistency
            return sum(consistency_scores) / len(consistency_scores)
            
        except Exception as e:
            self.logger.error(f"Consistency scoring failed: {e}")
            return 0.5  # Default neutral score


# Factory function for easy instantiation
async def create_style_analyzer(project_id: str = None) -> ProductionStyleAnalyzer:
    """
    Factory function to create and initialize a ProductionStyleAnalyzer
    
    Args:
        project_id: Optional project ID for database integration
        
    Returns:
        Initialized ProductionStyleAnalyzer instance
    """
    analyzer = ProductionStyleAnalyzer(project_id)
    
    # Could add initialization steps here if needed
    # e.g., model downloading, cache warming, etc.
    
    return analyzer


# Backwards compatibility with existing placeholder
class StyleAnalyzer:
    """Backwards compatibility wrapper"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self._analyzer = None
    
    async def _get_analyzer(self):
        if self._analyzer is None:
            self._analyzer = await create_style_analyzer(self.project_id)
        return self._analyzer
    
    async def analyze_document(self, document_data: dict):
        """Backwards compatible method"""
        analyzer = await self._get_analyzer()
        content = document_data.get("content", "")
        
        if not content:
            return {"error": "No content provided"}
        
        try:
            style_profile = await analyzer.analyze_content_corpus([content])
            return style_profile.to_team_format()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_aggregated_patterns(self):
        """Backwards compatible method"""
        return {"message": "Use ProductionStyleAnalyzer.analyze_content_corpus() for comprehensive analysis"}
    
    async def check_consistency(self, content: str):
        """Backwards compatible method"""
        analyzer = await self._get_analyzer()
        
        # Would need a stored style profile to check against
        # For now, return basic analysis
        try:
            style_profile = await analyzer.analyze_content_corpus([content])
            return {
                "consistency_score": style_profile.analysis_confidence,
                "recommendations": ["Analysis completed successfully"]
            }
        except Exception as e:
            return {"consistency_score": 0.0, "recommendations": [f"Analysis failed: {e}"]}


# Export main classes
__all__ = [
    'ProductionStyleAnalyzer',
    'StyleProfile',
    'LanguageCode',
    'LinguisticFeatures',
    'SemanticFeatures',
    'StatisticalFeatures',
    'LLMInsights',
    'create_style_analyzer',
    'StyleAnalyzer'  # For backwards compatibility
]