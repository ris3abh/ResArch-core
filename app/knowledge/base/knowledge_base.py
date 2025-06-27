# app/knowledge/base/knowledge_base.py
"""
Core Knowledge Base for SpinScribe
Manages project-specific knowledge storage, retrieval, and processing.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import logging
import json
import uuid

from app.database.models.knowledge_item import KnowledgeItem
from app.database.models.project import Project
from app.database.connection import SessionLocal
from app.knowledge.retrievers.semantic_retriever import (
    SemanticRetriever,
    SearchResult,
    SearchQuery
)
from app.core.exceptions import KnowledgeError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeStats:
    """Statistics about project knowledge"""
    total_items: int
    content_samples: int
    style_guides: int
    marketing_materials: int
    recent_additions: int
    last_updated: Optional[datetime] = None

@dataclass
class BrandVoiceProfile:
    """Brand voice analysis profile"""
    primary_tone: str
    secondary_tones: List[str]
    vocabulary_patterns: List[str]
    writing_style: str
    target_audience: str
    key_characteristics: List[str]
    confidence_score: float

class KnowledgeBase:
    """
    Central knowledge management system for a SpinScribe project.
    Handles storage, retrieval, and analysis of project-specific knowledge.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.retriever = SemanticRetriever(project_id)
        self._cache: Dict[str, Any] = {}
        self._brand_voice_cache: Optional[BrandVoiceProfile] = None
        
        logger.info(f"KnowledgeBase initialized for project {project_id}")
    
    # Core Knowledge Management
    
    async def add_knowledge_item(
        self, 
        title: str, 
        content: Dict[str, Any],
        item_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeItem:
        """Add a new knowledge item to the project"""
        try:
            # Validate inputs
            if not title or not content:
                raise ValidationError("Title and content are required")
            
            # Create knowledge item
            knowledge_item = KnowledgeItem(
                item_id=f"kb_{uuid.uuid4().hex[:12]}",
                project_id=self.project_id,
                title=title,
                item_type=item_type,
                content=content,
                metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            
            # Store in database
            with SessionLocal() as db:
                db.add(knowledge_item)
                db.commit()
                db.refresh(knowledge_item)
            
            # Add to semantic retriever
            await self.retriever.add_knowledge_item(knowledge_item)
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Added knowledge item: {title}")
            return knowledge_item
            
        except Exception as e:
            logger.error(f"Failed to add knowledge item: {e}")
            raise KnowledgeError(f"Failed to add knowledge item: {e}")
    
    async def search_knowledge(
        self, 
        query: str, 
        limit: int = 10,
        content_types: Optional[List[str]] = None,
        min_score: float = 0.3
    ) -> List[SearchResult]:
        """Search knowledge using semantic retrieval"""
        try:
            search_query = SearchQuery(
                query=query,
                project_id=self.project_id,
                limit=limit,
                content_types=content_types,
                min_score=min_score
            )
            
            results = await self.retriever.search(search_query)
            
            logger.info(f"Knowledge search '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            raise KnowledgeError(f"Search failed: {e}")
    
    async def get_related_knowledge(
        self, 
        knowledge_item_id: str, 
        limit: int = 5
    ) -> List[SearchResult]:
        """Get knowledge items related to a specific item"""
        try:
            results = await self.retriever.get_related_content(knowledge_item_id, limit)
            
            logger.info(f"Found {len(results)} related items for {knowledge_item_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get related knowledge: {e}")
            raise KnowledgeError(f"Failed to get related knowledge: {e}")
    
    async def update_knowledge_item(
        self, 
        item_id: str, 
        updates: Dict[str, Any]
    ) -> KnowledgeItem:
        """Update an existing knowledge item"""
        try:
            with SessionLocal() as db:
                # Get existing item
                knowledge_item = db.query(KnowledgeItem).filter(
                    KnowledgeItem.item_id == item_id,
                    KnowledgeItem.project_id == self.project_id
                ).first()
                
                if not knowledge_item:
                    raise NotFoundError(f"Knowledge item {item_id} not found")
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(knowledge_item, key):
                        setattr(knowledge_item, key, value)
                
                knowledge_item.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(knowledge_item)
            
            # Update in semantic retriever
            await self.retriever.update_knowledge_item(knowledge_item)
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Updated knowledge item: {item_id}")
            return knowledge_item
            
        except Exception as e:
            logger.error(f"Failed to update knowledge item: {e}")
            raise KnowledgeError(f"Failed to update knowledge item: {e}")
    
    async def remove_knowledge_item(self, item_id: str) -> bool:
        """Remove a knowledge item"""
        try:
            with SessionLocal() as db:
                # Remove from database
                result = db.query(KnowledgeItem).filter(
                    KnowledgeItem.item_id == item_id,
                    KnowledgeItem.project_id == self.project_id
                ).delete()
                
                if result == 0:
                    raise NotFoundError(f"Knowledge item {item_id} not found")
                
                db.commit()
            
            # Remove from semantic retriever
            await self.retriever.remove_knowledge_item(item_id)
            
            # Clear caches
            self._clear_caches()
            
            logger.info(f"Removed knowledge item: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove knowledge item: {e}")
            raise KnowledgeError(f"Failed to remove knowledge item: {e}")
    
    # Knowledge Analysis
    
    async def analyze_brand_voice(self, force_refresh: bool = False) -> BrandVoiceProfile:
        """Analyze brand voice from content samples"""
        if self._brand_voice_cache and not force_refresh:
            return self._brand_voice_cache
        
        try:
            # Get content samples
            content_samples = await self.get_knowledge_by_type("content_sample")
            
            if not content_samples:
                # Return default profile
                profile = BrandVoiceProfile(
                    primary_tone="professional",
                    secondary_tones=["informative"],
                    vocabulary_patterns=["clear", "concise"],
                    writing_style="formal",
                    target_audience="general",
                    key_characteristics=["professional", "clear"],
                    confidence_score=0.5
                )
            else:
                # Analyze samples (simplified analysis)
                profile = await self._analyze_content_samples(content_samples)
            
            # Cache the result
            self._brand_voice_cache = profile
            
            logger.info(f"Brand voice analysis completed with {profile.confidence_score:.2f} confidence")
            return profile
            
        except Exception as e:
            logger.error(f"Brand voice analysis failed: {e}")
            raise KnowledgeError(f"Brand voice analysis failed: {e}")
    
    async def get_style_guidelines(self) -> Dict[str, Any]:
        """Get compiled style guidelines for the project"""
        try:
            # Get style guide items
            style_guides = await self.get_knowledge_by_type("style_guide")
            
            # Get brand voice analysis
            brand_voice = await self.analyze_brand_voice()
            
            # Compile guidelines
            guidelines = {
                "brand_voice": {
                    "primary_tone": brand_voice.primary_tone,
                    "secondary_tones": brand_voice.secondary_tones,
                    "writing_style": brand_voice.writing_style,
                    "target_audience": brand_voice.target_audience,
                    "key_characteristics": brand_voice.key_characteristics
                },
                "style_rules": [],
                "vocabulary_preferences": brand_voice.vocabulary_patterns,
                "content_structure": "standard",
                "quality_standards": "high"
            }
            
            # Add explicit style rules from style guides
            for guide in style_guides:
                if isinstance(guide.content, dict):
                    if "rules" in guide.content:
                        guidelines["style_rules"].extend(guide.content["rules"])
                    if "vocabulary" in guide.content:
                        guidelines["vocabulary_preferences"].extend(guide.content["vocabulary"])
            
            logger.info("Compiled style guidelines")
            return guidelines
            
        except Exception as e:
            logger.error(f"Failed to compile style guidelines: {e}")
            raise KnowledgeError(f"Failed to compile style guidelines: {e}")
    
    # Knowledge Retrieval
    
    async def get_knowledge_by_type(self, item_type: str) -> List[KnowledgeItem]:
        """Get all knowledge items of a specific type"""
        try:
            with SessionLocal() as db:
                items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.item_type == item_type
                ).order_by(KnowledgeItem.created_at.desc()).all()
            
            logger.info(f"Retrieved {len(items)} items of type {item_type}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get knowledge by type: {e}")
            raise KnowledgeError(f"Failed to get knowledge by type: {e}")
    
    async def get_all_knowledge(self, limit: Optional[int] = None) -> List[KnowledgeItem]:
        """Get all knowledge items for the project"""
        try:
            with SessionLocal() as db:
                query = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).order_by(KnowledgeItem.created_at.desc())
                
                if limit:
                    query = query.limit(limit)
                
                items = query.all()
            
            logger.info(f"Retrieved {len(items)} total knowledge items")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get all knowledge: {e}")
            raise KnowledgeError(f"Failed to get all knowledge: {e}")
    
    async def get_knowledge_stats(self) -> KnowledgeStats:
        """Get statistics about project knowledge"""
        try:
            with SessionLocal() as db:
                # Get counts by type
                total_items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).count()
                
                content_samples = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.item_type == "content_sample"
                ).count()
                
                style_guides = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.item_type == "style_guide"
                ).count()
                
                marketing_materials = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.item_type == "marketing_material"
                ).count()
                
                # Get recent additions (last 7 days)
                week_ago = datetime.utcnow().replace(day=datetime.utcnow().day - 7)
                recent_additions = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.created_at >= week_ago
                ).count()
                
                # Get last updated
                latest_item = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).order_by(KnowledgeItem.updated_at.desc()).first()
                
                last_updated = latest_item.updated_at if latest_item else None
            
            stats = KnowledgeStats(
                total_items=total_items,
                content_samples=content_samples,
                style_guides=style_guides,
                marketing_materials=marketing_materials,
                recent_additions=recent_additions,
                last_updated=last_updated
            )
            
            logger.info(f"Generated knowledge stats: {total_items} total items")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get knowledge stats: {e}")
            raise KnowledgeError(f"Failed to get knowledge stats: {e}")
    
    # Utility Methods
    
    async def _analyze_content_samples(self, samples: List[KnowledgeItem]) -> BrandVoiceProfile:
        """Analyze content samples to extract brand voice (simplified implementation)"""
        # This is a simplified analysis - in production this would use NLP
        
        # Aggregate content
        all_content = []
        for sample in samples:
            if isinstance(sample.content, dict) and "text" in sample.content:
                all_content.append(sample.content["text"])
            elif isinstance(sample.content, str):
                all_content.append(sample.content)
        
        combined_text = " ".join(all_content).lower()
        
        # Simple keyword-based analysis
        tone_indicators = {
            "professional": ["professional", "business", "corporate", "formal"],
            "casual": ["casual", "friendly", "relaxed", "informal"],
            "technical": ["technical", "detailed", "precise", "specific"],
            "creative": ["creative", "innovative", "unique", "original"]
        }
        
        tone_scores = {}
        for tone, keywords in tone_indicators.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            tone_scores[tone] = score
        
        # Determine primary tone
        primary_tone = max(tone_scores, key=tone_scores.get) if tone_scores else "professional"
        
        # Get secondary tones
        sorted_tones = sorted(tone_scores.items(), key=lambda x: x[1], reverse=True)
        secondary_tones = [tone for tone, score in sorted_tones[1:3] if score > 0]
        
        return BrandVoiceProfile(
            primary_tone=primary_tone,
            secondary_tones=secondary_tones,
            vocabulary_patterns=["clear", "engaging", "professional"],
            writing_style="balanced",
            target_audience="business professionals",
            key_characteristics=[primary_tone, "well-structured"],
            confidence_score=0.8 if len(samples) >= 3 else 0.6
        )
    
    def _clear_caches(self):
        """Clear internal caches"""
        self._cache.clear()
        self._brand_voice_cache = None
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the knowledge collection"""
        try:
            stats = await self.get_knowledge_stats()
            retriever_stats = await self.retriever.get_collection_stats()
            
            return {
                "project_id": self.project_id,
                "knowledge_stats": stats,
                "retriever_stats": retriever_stats,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "project_id": self.project_id,
                "status": "error",
                "error": str(e)
            }

# Export main classes
__all__ = [
    'KnowledgeBase',
    'KnowledgeStats',
    'BrandVoiceProfile'
]