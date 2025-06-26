# app/services/knowledge_service.py
"""
Knowledge Service - Core business logic for knowledge management in SpinScribe.
Handles document processing, storage, retrieval, and analysis.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import hashlib
import mimetypes
from pathlib import Path
import json
import re
from dataclasses import dataclass

from app.services.base_service import BaseService, ServiceRegistry
from app.services.project_service import get_project_service
from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.project import Project
from app.core.exceptions import (
    ValidationError, 
    NotFoundError, 
    DocumentProcessingError,
    ServiceError
)

# Data schemas for type safety
@dataclass
class KnowledgeCreateData:
    """Data structure for creating knowledge items."""
    project_id: str
    knowledge_type: str
    title: str
    content: Optional[str] = None
    source_file_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class KnowledgeUpdateData:
    """Data structure for updating knowledge items."""
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class DocumentUploadData:
    """Data structure for document uploads."""
    file_content: bytes
    file_name: str
    content_type: str
    project_id: str
    knowledge_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class KnowledgeSearchQuery:
    """Data structure for knowledge search."""
    project_id: str
    query: str
    knowledge_types: Optional[List[str]] = None
    limit: int = 10

class KnowledgeService(BaseService[KnowledgeItem]):
    """
    Service class for managing knowledge items in SpinScribe.
    
    Handles:
    - Document upload and processing
    - Knowledge item CRUD operations
    - Content analysis and extraction
    - Search and retrieval operations
    - Brand voice analysis
    """
    
    def __init__(self):
        super().__init__(KnowledgeItem)
        self.supported_file_types = {
            'text/plain': 'text',
            'text/markdown': 'markdown',
            'application/json': 'json',
            'text/html': 'html'
        }
        
        self.knowledge_types = {
            'brand_guide', 'style_guide', 'content_sample', 
            'brand_voice', 'competitor_analysis', 'target_audience',
            'seo_keywords', 'content_template', 'reference_material'
        }
        
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.max_content_length = 500000  # 500K characters
    
    def upload_document(self, upload_data: DocumentUploadData) -> KnowledgeItem:
        """
        Upload and process a document into the knowledge base.
        
        Args:
            upload_data: Document upload data
            
        Returns:
            Created knowledge item
        """
        # Validate upload
        self._validate_document_upload(upload_data)
        
        with self.get_db_session() as db:
            # Verify project exists
            project_service = get_project_service()
            project = project_service.get_by_id_or_raise(upload_data.project_id, db)
            
            # Process document content
            processed_content = self._process_document_content(
                upload_data.file_content, 
                upload_data.content_type
            )
            
            # Determine knowledge type
            knowledge_type = upload_data.knowledge_type or self._infer_knowledge_type(
                upload_data.file_name, 
                processed_content
            )
            
            # Create metadata
            metadata = self._create_document_metadata(upload_data, processed_content)
            
            # Create knowledge item
            knowledge_data = KnowledgeCreateData(
                project_id=upload_data.project_id,
                knowledge_type=knowledge_type,
                title=self._generate_title_from_filename(upload_data.file_name),
                content=processed_content,
                source_file_name=upload_data.file_name,
                metadata=metadata
            )
            
            knowledge_item = self.create(knowledge_data, db)
            
            # Update project activity
            project.last_activity_at = datetime.utcnow()
            db.commit()
            
            self.log_operation(
                "upload_document", 
                knowledge_item.knowledge_id,
                file_name=upload_data.file_name,
                knowledge_type=knowledge_type
            )
            
            return knowledge_item
    
    def analyze_brand_voice(self, project_id: str, content_samples: Optional[List[str]] = None) -> KnowledgeItem:
        """
        Analyze brand voice from project content samples.
        
        Args:
            project_id: Project ID
            content_samples: Optional specific content samples to analyze
            
        Returns:
            Brand voice analysis knowledge item
        """
        with self.get_db_session() as db:
            # Get project and validate
            project_service = get_project_service()
            project = project_service.get_by_id_or_raise(project_id, db)
            
            # Gather content samples if not provided
            if not content_samples:
                content_samples = self._gather_content_samples(project_id, db)
            
            if not content_samples:
                raise ValidationError("No content samples available for brand voice analysis")
            
            # Perform brand voice analysis
            analysis_results = self._perform_brand_voice_analysis(content_samples)
            
            # Create or update brand voice knowledge item
            existing_brand_voice = self._get_brand_voice_item(project_id, db)
            
            if existing_brand_voice:
                # Update existing analysis
                update_data = KnowledgeUpdateData(
                    content=json.dumps(analysis_results, indent=2),
                    metadata=self._create_brand_voice_metadata(analysis_results)
                )
                knowledge_item = self.update(existing_brand_voice.knowledge_id, update_data, db)
            else:
                # Create new analysis
                knowledge_data = KnowledgeCreateData(
                    project_id=project_id,
                    knowledge_type='brand_voice',
                    title=f"Brand Voice Analysis - {project.client_name}",
                    content=json.dumps(analysis_results, indent=2),
                    metadata=self._create_brand_voice_metadata(analysis_results)
                )
                knowledge_item = self.create(knowledge_data, db)
            
            self.log_operation(
                "analyze_brand_voice", 
                knowledge_item.knowledge_id,
                sample_count=len(content_samples)
            )
            
            return knowledge_item
    
    def search_knowledge(self, search_query: KnowledgeSearchQuery) -> List[Dict[str, Any]]:
        """
        Search knowledge items using text matching.
        
        Args:
            search_query: Search parameters
            
        Returns:
            List of matching knowledge items with relevance scores
        """
        with self.get_db_session() as db:
            # Build base query
            query = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == search_query.project_id
            )
            
            # Filter by knowledge types if specified
            if search_query.knowledge_types:
                query = query.filter(
                    KnowledgeItem.knowledge_type.in_(search_query.knowledge_types)
                )
            
            # Get all potential matches
            all_items = query.all()
            
            # Perform text-based scoring
            scored_results = []
            for item in all_items:
                score = self._calculate_relevance_score(item, search_query.query)
                if score > 0:
                    result = {
                        'knowledge_item': item,
                        'relevance_score': score,
                        'matches': self._find_text_matches(item, search_query.query)
                    }
                    scored_results.append(result)
            
            # Sort by relevance and limit results
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return scored_results[:search_query.limit]
    
    def get_knowledge_by_type(self, project_id: str, knowledge_type: str) -> List[KnowledgeItem]:
        """Get all knowledge items of a specific type for a project."""
        with self.get_db_session() as db:
            return db.query(KnowledgeItem).filter(
                and_(
                    KnowledgeItem.project_id == project_id,
                    KnowledgeItem.knowledge_type == knowledge_type
                )
            ).order_by(KnowledgeItem.updated_at.desc()).all()
    
    def get_project_knowledge_summary(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of project's knowledge base."""
        with self.get_db_session() as db:
            items = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == project_id
            ).all()
            
            # Calculate statistics
            stats = self._calculate_knowledge_statistics(items)
            
            # Check completeness
            completeness = self._assess_knowledge_completeness(items)
            
            return {
                'total_items': len(items),
                'by_type': stats['by_type'],
                'total_content_size': stats['total_size'],
                'completeness': completeness,
                'last_update': max((item.updated_at for item in items), default=None),
                'recommendations': self._generate_knowledge_recommendations(stats, completeness)
            }
    
    def extract_content_insights(self, knowledge_id: str) -> Dict[str, Any]:
        """Extract insights from a knowledge item's content."""
        with self.get_db_session() as db:
            item = self.get_by_id_or_raise(knowledge_id, db)
            
            if not item.content:
                return {'error': 'No content available for analysis'}
            
            insights = {
                'word_count': len(item.content.split()),
                'character_count': len(item.content),
                'paragraph_count': len([p for p in item.content.split('\n\n') if p.strip()]),
                'keywords': self._extract_keywords(item.content),
                'tone_indicators': self._analyze_tone_indicators(item.content)
            }
            
            return insights
    
    # BaseService implementation methods
    
    def _validate_create_data(self, data: KnowledgeCreateData, db: Session) -> None:
        """Validate knowledge item creation data."""
        # Required fields
        self.validate_required_fields(
            data.__dict__, 
            ['project_id', 'knowledge_type', 'title']
        )
        
        # Project existence
        project_service = get_project_service()
        project_service.get_by_id_or_raise(data.project_id, db)
        
        # Knowledge type validation
        if data.knowledge_type not in self.knowledge_types:
            raise ValidationError(
                f"Invalid knowledge_type. Must be one of: {', '.join(self.knowledge_types)}"
            )
        
        # Title validation
        title = self.sanitize_string_field(data.title, max_length=500)
        if not title:
            raise ValidationError("Title cannot be empty")
        
        # Content length validation
        if data.content and len(data.content) > self.max_content_length:
            raise ValidationError(f"Content exceeds maximum length of {self.max_content_length} characters")
    
    def _validate_update_data(self, entity: KnowledgeItem, data: KnowledgeUpdateData, db: Session) -> None:
        """Validate knowledge item update data."""
        # Title validation if provided
        if data.title is not None:
            title = self.sanitize_string_field(data.title, max_length=500)
            if not title:
                raise ValidationError("Title cannot be empty")
        
        # Content length validation
        if data.content and len(data.content) > self.max_content_length:
            raise ValidationError(f"Content exceeds maximum length of {self.max_content_length} characters")
    
    def _create_entity(self, data: KnowledgeCreateData, db: Session) -> KnowledgeItem:
        """Create knowledge item entity from data."""
        # Use appropriate factory method based on knowledge type
        if data.knowledge_type == 'brand_guide':
            return KnowledgeItem.create_brand_guide(
                project_id=data.project_id,
                title=data.title,
                content=data.content or "",
                metadata=data.metadata or {}
            )
        elif data.knowledge_type == 'style_guide':
            return KnowledgeItem.create_style_guide(
                project_id=data.project_id,
                title=data.title,
                content=data.content or "",
                metadata=data.metadata or {}
            )
        elif data.knowledge_type == 'content_sample':
            category = (data.metadata or {}).get('category', 'general')
            return KnowledgeItem.create_content_sample(
                project_id=data.project_id,
                title=data.title,
                content=data.content or "",
                category=category,
                metadata=data.metadata or {}
            )
        elif data.knowledge_type == 'brand_voice':
            return KnowledgeItem.create_brand_voice(
                project_id=data.project_id,
                title=data.title,
                content=data.content or "",
                metadata=data.metadata or {}
            )
        else:
            # Generic knowledge item
            return KnowledgeItem(
                project_id=data.project_id,
                knowledge_type=data.knowledge_type,
                title=data.title,
                content=data.content,
                source_file_name=data.source_file_name,
                metadata=data.metadata or {}
            )
    
    def _apply_updates(self, entity: KnowledgeItem, data: KnowledgeUpdateData, db: Session) -> KnowledgeItem:
        """Apply updates to knowledge item entity."""
        if data.title is not None:
            entity.title = data.title.strip()
        
        if data.content is not None:
            entity.content = data.content
        
        if data.metadata is not None:
            entity.metadata = data.metadata
        
        # Update timestamps
        entity.updated_at = datetime.utcnow()
        
        return entity
    
    # Helper methods
    
    def _validate_document_upload(self, upload_data: DocumentUploadData) -> None:
        """Validate document upload data."""
        # File size validation
        if len(upload_data.file_content) > self.max_file_size:
            raise ValidationError(f"File size exceeds maximum of {self.max_file_size} bytes")
        
        # Content type validation
        if upload_data.content_type not in self.supported_file_types:
            raise ValidationError(
                f"Unsupported file type: {upload_data.content_type}. "
                f"Supported types: {', '.join(self.supported_file_types.keys())}"
            )
        
        # File name validation
        if not upload_data.file_name or not upload_data.file_name.strip():
            raise ValidationError("File name is required")
    
    def _process_document_content(self, file_content: bytes, content_type: str) -> str:
        """Process document content based on file type."""
        try:
            if content_type in ['text/plain', 'text/markdown', 'text/html']:
                return file_content.decode('utf-8', errors='replace')
            elif content_type == 'application/json':
                json_data = json.loads(file_content.decode('utf-8'))
                return json.dumps(json_data, indent=2)
            else:
                raise DocumentProcessingError(
                    f"No processor available for content type: {content_type}",
                    document_type=content_type
                )
        except UnicodeDecodeError as e:
            raise DocumentProcessingError(
                f"Failed to decode file content: {str(e)}",
                document_type=content_type
            )
        except json.JSONDecodeError as e:
            raise DocumentProcessingError(
                f"Invalid JSON format: {str(e)}",
                document_type=content_type
            )
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to process document: {str(e)}",
                document_type=content_type
            )
    
    def _infer_knowledge_type(self, file_name: str, content: str) -> str:
        """Infer knowledge type from filename and content."""
        file_name_lower = file_name.lower()
        content_lower = content.lower()
        
        # Check filename patterns
        if any(term in file_name_lower for term in ['brand', 'guide', 'guideline']):
            return 'brand_guide'
        elif any(term in file_name_lower for term in ['style', 'voice', 'tone']):
            return 'style_guide'
        elif any(term in file_name_lower for term in ['sample', 'example']):
            return 'content_sample'
        elif any(term in file_name_lower for term in ['competitor']):
            return 'competitor_analysis'
        elif any(term in file_name_lower for term in ['audience', 'persona']):
            return 'target_audience'
        
        # Check content patterns
        if any(phrase in content_lower for phrase in ['brand voice', 'tone of voice']):
            return 'style_guide'
        elif any(phrase in content_lower for phrase in ['brand guidelines']):
            return 'brand_guide'
        elif any(phrase in content_lower for phrase in ['target audience']):
            return 'target_audience'
        
        return 'reference_material'
    
    def _create_document_metadata(self, upload_data: DocumentUploadData, content: str) -> Dict[str, Any]:
        """Create metadata for uploaded document."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        return {
            'source_file': {
                'name': upload_data.file_name,
                'content_type': upload_data.content_type,
                'size_bytes': len(upload_data.file_content),
                'upload_timestamp': datetime.utcnow().isoformat()
            },
            'content_analysis': {
                'hash': content_hash,
                'word_count': len(content.split()),
                'character_count': len(content)
            },
            'processing': {
                'processed_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0'
            }
        }
    
    def _generate_title_from_filename(self, file_name: str) -> str:
        """Generate a clean title from filename."""
        name_without_ext = Path(file_name).stem
        title = name_without_ext.replace('_', ' ').replace('-', ' ')
        title = ' '.join(word.capitalize() for word in title.split())
        
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    def _gather_content_samples(self, project_id: str, db: Session) -> List[str]:
        """Gather content samples for brand voice analysis."""
        content_samples = db.query(KnowledgeItem).filter(
            and_(
                KnowledgeItem.project_id == project_id,
                KnowledgeItem.knowledge_type == 'content_sample',
                KnowledgeItem.content.isnot(None)
            )
        ).all()
        
        samples = []
        for item in content_samples:
            if item.content and len(item.content.strip()) > 100:
                samples.append(item.content)
        
        return samples
    
    def _perform_brand_voice_analysis(self, content_samples: List[str]) -> Dict[str, Any]:
        """Perform brand voice analysis on content samples."""
        all_text = ' '.join(content_samples)
        words = all_text.split()
        
        # Basic statistics
        total_words = len(words)
        unique_words = len(set(word.lower() for word in words))
        avg_word_length = sum(len(word) for word in words) / total_words if total_words > 0 else 0
        
        # Sentence analysis
        sentences = [s.strip() for s in all_text.split('.') if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Tone indicators
        formal_indicators = ['therefore', 'furthermore', 'consequently', 'moreover', 'however']
        casual_indicators = ['really', 'pretty', 'totally', 'awesome', 'cool']
        technical_indicators = ['implement', 'configure', 'optimize', 'integrate', 'process']
        
        formal_count = sum(all_text.lower().count(word) for word in formal_indicators)
        casual_count = sum(all_text.lower().count(word) for word in casual_indicators)
        technical_count = sum(all_text.lower().count(word) for word in technical_indicators)
        
        # Determine primary tone
        tone_scores = {
            'formal': formal_count,
            'casual': casual_count,
            'technical': technical_count
        }
        primary_tone = max(tone_scores.keys(), key=lambda k: tone_scores[k]) if any(tone_scores.values()) else 'balanced'
        
        # Formality analysis
        contractions = len(re.findall(r'\b\w+\'[a-z]+\b', all_text.lower()))
        formality_score = (formal_count - casual_count - contractions) / max(total_words / 100, 1)
        formality_score = max(0, min(1, (formality_score + 5) / 10))
        
        return {
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'sample_count': len(content_samples),
            'statistics': {
                'total_words': total_words,
                'unique_words': unique_words,
                'vocabulary_diversity': unique_words / total_words if total_words > 0 else 0,
                'average_word_length': round(avg_word_length, 2),
                'average_sentence_length': round(avg_sentence_length, 2)
            },
            'tone_analysis': {
                'primary_tone': primary_tone,
                'tone_scores': tone_scores,
                'formality_score': round(formality_score, 2)
            },
            'language_patterns': {
                'uses_contractions': contractions > total_words * 0.01,
                'prefers_short_sentences': avg_sentence_length < 15,
                'technical_vocabulary': technical_count > total_words * 0.01
            }
        }
    
    def _create_brand_voice_metadata(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for brand voice analysis."""
        return {
            'analysis_type': 'brand_voice',
            'primary_tone': analysis_results.get('tone_analysis', {}).get('primary_tone', 'unknown'),
            'sample_count': analysis_results.get('sample_count', 0),
            'last_analysis': analysis_results.get('analysis_timestamp'),
            'auto_generated': True
        }
    
    def _get_brand_voice_item(self, project_id: str, db: Session) -> Optional[KnowledgeItem]:
        """Get existing brand voice analysis item."""
        return db.query(KnowledgeItem).filter(
            and_(
                KnowledgeItem.project_id == project_id,
                KnowledgeItem.knowledge_type == 'brand_voice'
            )
        ).first()
    
    def _calculate_relevance_score(self, item: KnowledgeItem, query: str) -> float:
        """Calculate relevance score for search query."""
        if not item.content:
            return 0.0
        
        query_terms = query.lower().split()
        content_lower = item.content.lower()
        title_lower = item.title.lower()
        
        score = 0.0
        
        # Title matches (higher weight)
        for term in query_terms:
            if term in title_lower:
                score += 2.0
        
        # Content matches
        for term in query_terms:
            if term in content_lower:
                score += 1.0
        
        # Exact phrase matches (bonus)
        if query.lower() in content_lower:
            score += 3.0
        
        return score
    
    def _find_text_matches(self, item: KnowledgeItem, query: str) -> List[Dict[str, Any]]:
        """Find specific text matches for highlighting."""
        matches = []
        
        if not item.content:
            return matches
        
        query_lower = query.lower()
        content_lower = item.content.lower()
        
        # Find all occurrences
        start = 0
        while True:
            pos = content_lower.find(query_lower, start)
            if pos == -1:
                break
            
            # Extract context around match
            context_start = max(0, pos - 50)
            context_end = min(len(item.content), pos + len(query) + 50)
            context = item.content[context_start:context_end]
            
            matches.append({
                'position': pos,
                'context': context,
                'match_text': item.content[pos:pos + len(query)]
            })
            
            start = pos + 1
            
            if len(matches) >= 5:
                break
        
        return matches
    
    def _calculate_knowledge_statistics(self, items: List[KnowledgeItem]) -> Dict[str, Any]:
        """Calculate statistics for knowledge items."""
        if not items:
            return {'by_type': {}, 'total_size': 0}
        
        by_type = {}
        total_size = 0
        
        for item in items:
            item_type = item.knowledge_type
            by_type[item_type] = by_type.get(item_type, 0) + 1
            
            content_size = len(item.content) if item.content else 0
            total_size += content_size
        
        return {
            'by_type': by_type,
            'total_size': total_size
        }
    
    def _assess_knowledge_completeness(self, items: List[KnowledgeItem]) -> Dict[str, Any]:
        """Assess completeness of knowledge base."""
        by_type = {}
        for item in items:
            by_type[item.knowledge_type] = by_type.get(item.knowledge_type, 0) + 1
        
        required_types = {'brand_guide', 'style_guide', 'content_sample'}
        optional_types = {'brand_voice', 'target_audience'}
        
        required_score = sum(1 for kt in required_types if kt in by_type) / len(required_types)
        optional_score = sum(1 for kt in optional_types if kt in by_type) / len(optional_types)
        
        overall_score = (required_score * 0.7) + (optional_score * 0.3)
        
        return {
            'overall_score': round(overall_score, 2),
            'missing_required': [kt for kt in required_types if kt not in by_type],
            'missing_optional': [kt for kt in optional_types if kt not in by_type],
            'status': 'complete' if overall_score >= 0.8 else 'partial' if overall_score >= 0.4 else 'incomplete'
        }
    
    def _generate_knowledge_recommendations(self, stats: Dict[str, Any], completeness: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving knowledge base."""
        recommendations = []
        
        if 'brand_guide' not in stats['by_type']:
            recommendations.append("Add brand guidelines to establish clear brand standards")
        
        if 'style_guide' not in stats['by_type']:
            recommendations.append("Create style guide for consistent voice and tone")
        
        if stats['by_type'].get('content_sample', 0) < 3:
            recommendations.append("Add more content samples for better brand voice analysis")
        
        if 'brand_voice' not in stats['by_type']:
            recommendations.append("Run brand voice analysis to understand writing patterns")
        
        return recommendations
    
    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from content."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        
        # Filter common words
        stop_words = {
            'that', 'this', 'with', 'from', 'they', 'been', 'have', 'were',
            'each', 'which', 'their', 'time', 'will', 'about', 'would', 'there'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Count frequency
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def _analyze_tone_indicators(self, content: str) -> Dict[str, int]:
        """Analyze tone indicators in content."""
        content_lower = content.lower()
        
        indicators = {
            'professional': ['therefore', 'furthermore', 'analysis', 'strategy'],
            'casual': ['really', 'pretty', 'awesome', 'cool'],
            'technical': ['implement', 'configure', 'optimize', 'integrate'],
            'friendly': ['welcome', 'thanks', 'please', 'help']
        }
        
        tone_counts = {}
        for tone, words in indicators.items():
            count = sum(content_lower.count(word) for word in words)
            tone_counts[tone] = count
        
        return tone_counts


# Service instance factory
def get_knowledge_service() -> KnowledgeService:
    """Get KnowledgeService instance from registry."""
    return ServiceRegistry.get_service(KnowledgeService)


# Utility functions for knowledge management

def bulk_upload_documents(project_id: str, file_paths: List[str]) -> List[KnowledgeItem]:
    """
    Bulk upload multiple documents to a project.
    
    Args:
        project_id: Project ID
        file_paths: List of file paths to upload
        
    Returns:
        List of created knowledge items
    """
    service = get_knowledge_service()
    results = []
    
    for file_path in file_paths:
        try:
            path = Path(file_path)
            if not path.exists():
                service.logger.warning(f"File not found: {file_path}")
                continue
            
            # Read file content
            with open(path, 'rb') as f:
                file_content = f.read()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(path))
            if not content_type:
                content_type = 'text/plain'
            
            # Create upload data
            upload_data = DocumentUploadData(
                file_content=file_content,
                file_name=path.name,
                content_type=content_type,
                project_id=project_id
            )
            
            # Upload document
            knowledge_item = service.upload_document(upload_data)
            results.append(knowledge_item)
            
        except Exception as e:
            service.logger.error(f"Failed to upload {file_path}: {e}")
            continue
    
    return results


def export_project_knowledge(project_id: str, export_format: str = 'json') -> Dict[str, Any]:
    """
    Export all knowledge items for a project.
    
    Args:
        project_id: Project ID
        export_format: Export format ('json', 'text')
        
    Returns:
        Exported knowledge data
    """
    service = get_knowledge_service()
    
    with service.get_db_session() as db:
        items = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == project_id
        ).all()
    
    if export_format == 'json':
        return {
            'project_id': project_id,
            'export_timestamp': datetime.utcnow().isoformat(),
            'total_items': len(items),
            'knowledge_items': [
                {
                    'knowledge_id': item.knowledge_id,
                    'knowledge_type': item.knowledge_type,
                    'title': item.title,
                    'content': item.content,
                    'metadata': item.metadata,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat()
                }
                for item in items
            ]
        }
    elif export_format == 'text':
        text_content = f"Knowledge Export for Project: {project_id}\n"
        text_content += f"Export Date: {datetime.utcnow().isoformat()}\n"
        text_content += f"Total Items: {len(items)}\n\n"
        
        for item in items:
            text_content += f"{'='*50}\n"
            text_content += f"Title: {item.title}\n"
            text_content += f"Type: {item.knowledge_type}\n"
            text_content += f"Created: {item.created_at}\n\n"
            text_content += f"{item.content}\n\n"
        
        return {'content': text_content}
    else:
        raise ValidationError(f"Unsupported export format: {export_format}")


def create_knowledge_from_text(project_id: str, title: str, content: str, knowledge_type: str = 'reference_material') -> KnowledgeItem:
    """
    Create knowledge item directly from text content.
    
    Args:
        project_id: Project ID
        title: Knowledge item title
        content: Text content
        knowledge_type: Type of knowledge item
        
    Returns:
        Created knowledge item
    """
    service = get_knowledge_service()
    
    knowledge_data = KnowledgeCreateData(
        project_id=project_id,
        knowledge_type=knowledge_type,
        title=title,
        content=content,
        metadata={
            'created_via': 'direct_text_input',
            'word_count': len(content.split()),
            'character_count': len(content)
        }
    )
    
    return service.create(knowledge_data)


def analyze_project_content_gaps(project_id: str) -> Dict[str, Any]:
    """
    Analyze what content is missing from a project's knowledge base.
    
    Args:
        project_id: Project ID
        
    Returns:
        Analysis of content gaps and recommendations
    """
    service = get_knowledge_service()
    summary = service.get_project_knowledge_summary(project_id)
    
    # Required content types for a complete knowledge base
    required_content = {
        'brand_guide': 'Brand guidelines and standards',
        'style_guide': 'Writing style and voice guidelines',
        'content_sample': 'Examples of existing content (need 3+)',
        'target_audience': 'Target audience definitions'
    }
    
    # Optional but valuable content
    optional_content = {
        'brand_voice': 'AI-generated brand voice analysis',
        'competitor_analysis': 'Competitor content analysis',
        'seo_keywords': 'SEO keyword strategies',
        'content_template': 'Content templates and frameworks'
    }
    
    existing_types = set(summary['by_type'].keys())
    
    gaps = {
        'critical_missing': [],
        'optional_missing': [],
        'content_volume_issues': [],
        'recommendations': []
    }
    
    # Check for critical missing content
    for content_type, description in required_content.items():
        if content_type not in existing_types:
            gaps['critical_missing'].append({
                'type': content_type,
                'description': description,
                'priority': 'high'
            })
    
    # Check for optional missing content
    for content_type, description in optional_content.items():
        if content_type not in existing_types:
            gaps['optional_missing'].append({
                'type': content_type,
                'description': description,
                'priority': 'medium'
            })
    
    # Check content volume issues
    content_sample_count = summary['by_type'].get('content_sample', 0)
    if content_sample_count < 3:
        gaps['content_volume_issues'].append({
            'issue': 'insufficient_content_samples',
            'current': content_sample_count,
            'recommended': 3,
            'description': 'Need at least 3 content samples for reliable brand voice analysis'
        })
    
    # Generate specific recommendations
    if gaps['critical_missing']:
        gaps['recommendations'].append('Address critical missing content types first')
    
    if content_sample_count == 0:
        gaps['recommendations'].append('Upload existing content samples to enable brand voice analysis')
    elif content_sample_count < 3:
        gaps['recommendations'].append('Add more content samples for better brand voice analysis')
    
    if 'brand_voice' not in existing_types and content_sample_count >= 2:
        gaps['recommendations'].append('Run brand voice analysis on existing content samples')
    
    if len(gaps['critical_missing']) == 0 and len(gaps['optional_missing']) > 0:
        gaps['recommendations'].append('Consider adding optional content types to enhance AI capabilities')
    
    gaps['completeness_score'] = summary['completeness']['overall_score']
    gaps['total_items'] = summary['total_items']
    
    return gaps


def migrate_knowledge_between_projects(source_project_id: str, target_project_id: str, knowledge_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Migrate knowledge items from one project to another.
    
    Args:
        source_project_id: Source project ID
        target_project_id: Target project ID
        knowledge_types: Optional list of knowledge types to migrate (migrates all if None)
        
    Returns:
        Migration results
    """
    service = get_knowledge_service()
    
    with service.get_db_session() as db:
        # Verify both projects exist
        project_service = get_project_service()
        source_project = project_service.get_by_id_or_raise(source_project_id, db)
        target_project = project_service.get_by_id_or_raise(target_project_id, db)
        
        # Get source knowledge items
        query = db.query(KnowledgeItem).filter(
            KnowledgeItem.project_id == source_project_id
        )
        
        if knowledge_types:
            query = query.filter(KnowledgeItem.knowledge_type.in_(knowledge_types))
        
        source_items = query.all()
        
        migrated_items = []
        failed_migrations = []
        
        for item in source_items:
            try:
                # Create new knowledge item in target project
                new_metadata = item.metadata.copy() if item.metadata else {}
                new_metadata['migrated_from'] = {
                    'source_project_id': source_project_id,
                    'source_item_id': item.knowledge_id,
                    'migration_timestamp': datetime.utcnow().isoformat()
                }
                
                knowledge_data = KnowledgeCreateData(
                    project_id=target_project_id,
                    knowledge_type=item.knowledge_type,
                    title=f"{item.title} (Migrated)",
                    content=item.content,
                    source_file_name=item.source_file_name,
                    metadata=new_metadata
                )
                
                new_item = service.create(knowledge_data, db)
                migrated_items.append({
                    'source_id': item.knowledge_id,
                    'target_id': new_item.knowledge_id,
                    'title': item.title,
                    'type': item.knowledge_type
                })
                
            except Exception as e:
                failed_migrations.append({
                    'source_id': item.knowledge_id,
                    'title': item.title,
                    'error': str(e)
                })
        
        db.commit()
    
    return {
        'source_project': source_project.client_name,
        'target_project': target_project.client_name,
        'total_items_processed': len(source_items),
        'successful_migrations': len(migrated_items),
        'failed_migrations': len(failed_migrations),
        'migrated_items': migrated_items,
        'failed_items': failed_migrations
    }


def validate_knowledge_content(knowledge_id: str) -> Dict[str, Any]:
    """
    Validate knowledge item content for quality and completeness.
    
    Args:
        knowledge_id: Knowledge item ID
        
    Returns:
        Validation results with recommendations
    """
    service = get_knowledge_service()
    
    with service.get_db_session() as db:
        item = service.get_by_id_or_raise(knowledge_id, db)
    
    validation_results = {
        'knowledge_id': knowledge_id,
        'title': item.title,
        'knowledge_type': item.knowledge_type,
        'validation_timestamp': datetime.utcnow().isoformat(),
        'issues': [],
        'warnings': [],
        'recommendations': [],
        'overall_score': 1.0
    }
    
    score_deductions = 0
    
    # Content presence validation
    if not item.content or len(item.content.strip()) == 0:
        validation_results['issues'].append('No content provided')
        score_deductions += 0.5
    elif len(item.content.strip()) < 50:
        validation_results['warnings'].append('Content is very short (less than 50 characters)')
        score_deductions += 0.1
    
    # Title validation
    if not item.title or len(item.title.strip()) == 0:
        validation_results['issues'].append('No title provided')
        score_deductions += 0.2
    elif len(item.title) > 200:
        validation_results['warnings'].append('Title is very long')
        score_deductions += 0.05
    
    # Content-specific validations
    if item.content:
        word_count = len(item.content.split())
        
        if item.knowledge_type == 'content_sample' and word_count < 100:
            validation_results['warnings'].append('Content sample is quite short for effective analysis')
            score_deductions += 0.1
        
        if item.knowledge_type == 'brand_guide' and word_count < 200:
            validation_results['warnings'].append('Brand guide seems incomplete (very short)')
            score_deductions += 0.1
        
        # Check for common formatting issues
        if item.content.count('\n') == 0 and word_count > 100:
            validation_results['warnings'].append('Content lacks paragraph breaks (poor formatting)')
            score_deductions += 0.05
        
        # Check for placeholder text
        placeholder_indicators = ['lorem ipsum', 'placeholder', 'todo', 'tbd', 'fill in']
        if any(indicator in item.content.lower() for indicator in placeholder_indicators):
            validation_results['issues'].append('Content contains placeholder text')
            score_deductions += 0.3
    
    # Generate recommendations
    if validation_results['issues']:
        validation_results['recommendations'].append('Address critical issues before using this content')
    
    if item.knowledge_type == 'content_sample' and item.content and len(item.content.split()) < 200:
        validation_results['recommendations'].append('Consider adding more substantial content samples for better analysis')
    
    if not item.metadata or len(item.metadata) < 2:
        validation_results['recommendations'].append('Add metadata to improve content organization and searchability')
    
    # Calculate final score
    validation_results['overall_score'] = max(0.0, 1.0 - score_deductions)
    
    # Determine validation status
    if validation_results['overall_score'] >= 0.8:
        validation_results['status'] = 'excellent'
    elif validation_results['overall_score'] >= 0.6:
        validation_results['status'] = 'good'
    elif validation_results['overall_score'] >= 0.4:
        validation_results['status'] = 'needs_improvement'
    else:
        validation_results['status'] = 'poor'
    
    return validation_results


def generate_knowledge_report(project_id: str) -> str:
    """
    Generate a comprehensive knowledge base report for a project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Formatted report as string
    """
    service = get_knowledge_service()
    
    # Get project info
    project_service = get_project_service()
    with service.get_db_session() as db:
        project = project_service.get_by_id_or_raise(project_id, db)
    
    # Get knowledge summary
    summary = service.get_project_knowledge_summary(project_id)
    
    # Get content gaps analysis
    gaps = analyze_project_content_gaps(project_id)
    
    # Generate report
    report = f"""
        KNOWLEDGE BASE REPORT
        =====================

        Project: {project.client_name}
        Project ID: {project_id}
        Report Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

        OVERVIEW
        --------
        Total Knowledge Items: {summary['total_items']}
        Total Content Size: {summary['total_content_size']:,} characters
        Completeness Score: {summary['completeness']['overall_score']:.1%}
        Status: {summary['completeness']['status'].title()}

        KNOWLEDGE BREAKDOWN
        ------------------
        """
    
    for knowledge_type, count in summary['by_type'].items():
        report += f"• {knowledge_type.replace('_', ' ').title()}: {count} items\n"
    
    if gaps['critical_missing']:
        report += f"\nCRITICAL GAPS\n"
        report += f"-------------\n"
        for gap in gaps['critical_missing']:
            report += f"❌ Missing: {gap['type'].replace('_', ' ').title()}\n"
            report += f"   {gap['description']}\n"
    
    if gaps['optional_missing']:
        report += f"\nOPTIONAL IMPROVEMENTS\n"
        report += f"--------------------\n"
        for gap in gaps['optional_missing']:
            report += f"⚠️  Consider adding: {gap['type'].replace('_', ' ').title()}\n"
            report += f"   {gap['description']}\n"
    
    if gaps['content_volume_issues']:
        report += f"\nCONTENT VOLUME ISSUES\n"
        report += f"--------------------\n"
        for issue in gaps['content_volume_issues']:
            report += f"📊 {issue['description']}\n"
            report += f"   Current: {issue['current']}, Recommended: {issue['recommended']}\n"
    
    if summary['recommendations']:
        report += f"\nRECOMMENDATIONS\n"
        report += f"---------------\n"
        for i, rec in enumerate(summary['recommendations'], 1):
            report += f"{i}. {rec}\n"
    
    report += f"\nLAST ACTIVITY\n"
    report += f"-------------\n"
    if summary['last_update']:
        report += f"Last Update: {summary['last_update'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        report += f"No recent activity\n"
    
    return report


# Export main classes and functions
__all__ = [
    'KnowledgeService',
    'KnowledgeCreateData',
    'KnowledgeUpdateData', 
    'DocumentUploadData',
    'KnowledgeSearchQuery',
    'get_knowledge_service',
    'bulk_upload_documents',
    'export_project_knowledge',
    'create_knowledge_from_text',
    'analyze_project_content_gaps',
    'migrate_knowledge_between_projects',
    'validate_knowledge_content',
    'generate_knowledge_report'
]
