# app/knowledge/retrievers/semantic_retriever.py
"""
Production Semantic Retriever for SpinScribe
Provides intelligent knowledge retrieval using semantic search and contextual filtering.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from app.knowledge.storage.vector_storage import VectorStorage, VectorSearchResult
from app.knowledge.processors.document_processor import DocumentProcessor, ProcessedDocument
from app.services.knowledge_service import get_knowledge_service
from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem

logger = logging.getLogger(__name__)

@dataclass
class RetrievalContext:
    """Context for knowledge retrieval"""
    query: str
    knowledge_types: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    content_length_preference: Optional[str] = None  # "short", "medium", "long"
    language: str = "en"
    priority_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None

@dataclass
class EnrichedSearchResult:
    """Search result enriched with additional context"""
    content: str
    title: str
    knowledge_type: str
    similarity_score: float
    metadata: Dict[str, Any]
    source_document: Dict[str, Any]
    relevance_factors: Dict[str, float]
    chunk_context: Optional[str] = None
    related_chunks: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "title": self.title,
            "knowledge_type": self.knowledge_type,
            "similarity_score": self.similarity_score,
            "metadata": self.metadata,
            "source_document": self.source_document,
            "relevance_factors": self.relevance_factors,
            "chunk_context": self.chunk_context,
            "related_chunks": self.related_chunks
        }

@dataclass
class RetrievalResult:
    """Complete retrieval result with analytics"""
    query: str
    results: List[EnrichedSearchResult]
    total_found: int
    search_time: float
    retrieval_strategy: str
    quality_score: float
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "total_found": self.total_found,
            "search_time": self.search_time,
            "retrieval_strategy": self.retrieval_strategy,
            "quality_score": self.quality_score,
            "suggestions": self.suggestions
        }

class SemanticRetriever:
    """
    Production-grade semantic retriever that provides intelligent knowledge retrieval
    with contextual understanding and quality optimization.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}.{project_id}")
        
        # Initialize components
        self.vector_storage = VectorStorage(project_id)
        self.knowledge_service = get_knowledge_service()
        
        # Retrieval configuration
        self.default_limit = 10
        self.min_similarity_threshold = 0.3
        self.quality_threshold = 0.7
        
        # Context window for chunk expansion
        self.context_window_size = 500  # Characters before/after chunk
        
        # Performance tracking
        self.metrics = {
            "total_queries": 0,
            "average_response_time": 0.0,
            "cache_hits": 0,
            "quality_scores": []
        }
        
        # Simple cache for frequent queries
        self.query_cache: Dict[str, Tuple[RetrievalResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=15)
        
        self.logger.info(f"Semantic retriever initialized for project: {project_id}")
    
    async def retrieve_knowledge(self,
                                context: RetrievalContext,
                                limit: Optional[int] = None,
                                include_context: bool = True) -> RetrievalResult:
        """
        Retrieve knowledge using semantic search with contextual filtering
        
        Args:
            context: Retrieval context with query and filters
            limit: Maximum number of results
            include_context: Whether to include chunk context
            
        Returns:
            Complete retrieval result with enriched information
        """
        start_time = datetime.utcnow()
        limit = limit or self.default_limit
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(context, limit)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.metrics["cache_hits"] += 1
                return cached_result
            
            # Determine retrieval strategy
            strategy = self._determine_strategy(context)
            
            # Perform semantic search
            search_results = await self._perform_semantic_search(context, limit * 2)  # Get more for filtering
            
            # Enrich results with additional context
            enriched_results = await self._enrich_search_results(
                search_results, context, include_context
            )
            
            # Apply intelligent filtering and ranking
            filtered_results = self._apply_intelligent_filtering(enriched_results, context)
            
            # Limit final results
            final_results = filtered_results[:limit]
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(final_results, context)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(final_results, context)
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create result
            result = RetrievalResult(
                query=context.query,
                results=final_results,
                total_found=len(search_results),
                search_time=response_time,
                retrieval_strategy=strategy,
                quality_score=quality_score,
                suggestions=suggestions
            )
            
            # Update metrics
            self._update_metrics(response_time, quality_score)
            
            # Cache result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Retrieved {len(final_results)} results for query: {context.query[:50]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"Knowledge retrieval failed: {e}")
            raise
    
    async def retrieve_by_type(self,
                              knowledge_type: str,
                              limit: int = 10,
                              recent_first: bool = True) -> List[EnrichedSearchResult]:
        """Retrieve knowledge items by type"""
        try:
            # Get from database first for type filtering
            with self.knowledge_service.get_db_session() as db:
                items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id,
                    KnowledgeItem.knowledge_type == knowledge_type
                ).limit(limit * 2).all()
            
            if not items:
                return []
            
            # Convert to enriched results
            enriched_results = []
            for item in items:
                enriched_result = EnrichedSearchResult(
                    content=item.content or "",
                    title=item.title,
                    knowledge_type=item.knowledge_type,
                    similarity_score=1.0,  # Perfect match for type
                    metadata=item.metadata or {},
                    relevance_factors={"type_match": 1.0, "recency": 0.8}
                )
                enriched_results.append(enriched_result)
            
            # Sort by recency if requested
            if recent_first:
                enriched_results.sort(key=lambda x: x.source_document.get("updated_at", ""), reverse=True)
            
            return enriched_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Type-based retrieval failed: {e}")
            return []
    
    async def find_similar_content(self,
                                 reference_content: str,
                                 limit: int = 5,
                                 exclude_self: bool = True) -> List[EnrichedSearchResult]:
        """Find content similar to reference content"""
        context = RetrievalContext(query=reference_content[:1000])  # Limit query size
        
        result = await self.retrieve_knowledge(context, limit)
        return result.results
    
    # Private methods
    
    async def _perform_semantic_search(self,
                                     context: RetrievalContext,
                                     limit: int) -> List[VectorSearchResult]:
        """Perform the core semantic search"""
        # Prepare metadata filters
        metadata_filters = {}
        
        if context.knowledge_types:
            metadata_filters["knowledge_type"] = context.knowledge_types
        
        # Perform search
        results = await self.vector_storage.semantic_search(
            query=context.query,
            limit=limit,
            score_threshold=self.min_similarity_threshold,
            metadata_filters=metadata_filters
        )
        
        return results
    
    async def _enrich_search_results(self,
                                   search_results: List[VectorSearchResult],
                                   context: RetrievalContext,
                                   include_context: bool) -> List[EnrichedSearchResult]:
        """Enrich search results with additional information"""
        enriched_results = []
        
        # Get source documents from database
        knowledge_items = await self._get_source_documents([r.document_id for r in search_results])
        
        for result in search_results:
            # Find corresponding knowledge item
            knowledge_item = knowledge_items.get(result.document_id)
            
            if not knowledge_item:
                continue
            
            # Get chunk context if requested
            chunk_context = None
            if include_context:
                chunk_context = await self._get_chunk_context(result)
            
            # Calculate relevance factors
            relevance_factors = self._calculate_relevance_factors(result, context)
            
            enriched_result = EnrichedSearchResult(
                content=result.content,
                title=knowledge_item.get("title", "Untitled"),
                knowledge_type=knowledge_item.get("knowledge_type", "unknown"),
                similarity_score=result.similarity_score,
                metadata=result.metadata,
                source_document=knowledge_item,
                relevance_factors=relevance_factors,
                chunk_context=chunk_context
            )
            
            enriched_results.append(enriched_result)
        
        return enriched_results
    
    async def _get_source_documents(self, document_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get source knowledge items from database"""
        documents = {}
        
        try:
            with self.knowledge_service.get_db_session() as db:
                # Note: document_id in vector storage corresponds to file_hash or knowledge_id
                items = db.query(KnowledgeItem).filter(
                    KnowledgeItem.project_id == self.project_id
                ).all()
                
                for item in items:
                    # Create lookup by both knowledge_id and potential file_hash
                    doc_data = {
                        "knowledge_id": item.knowledge_id,
                        "title": item.title,
                        "knowledge_type": item.knowledge_type,
                        "created_at": item.created_at.isoformat(),
                        "updated_at": item.updated_at.isoformat(),
                        "metadata": item.metadata or {}
                    }
                    
                    documents[item.knowledge_id] = doc_data
                    # Also add by file_hash if it exists in metadata
                    if item.metadata and "file_hash" in item.metadata:
                        documents[item.metadata["file_hash"]] = doc_data
        
        except Exception as e:
            self.logger.error(f"Failed to get source documents: {e}")
        
        return documents
    
    async def _get_chunk_context(self, result: VectorSearchResult) -> Optional[str]:
        """Get expanded context around a chunk"""
        try:
            # This would require storing chunk relationships in metadata
            # For now, return the chunk content as context
            return result.content
        except Exception as e:
            self.logger.warning(f"Failed to get chunk context: {e}")
            return None
    
    def _calculate_relevance_factors(self,
                                   result: VectorSearchResult,
                                   context: RetrievalContext) -> Dict[str, float]:
        """Calculate various relevance factors"""
        factors = {
            "semantic_similarity": result.similarity_score,
            "query_length_match": 1.0,
            "keyword_density": 1.0,
            "recency": 1.0,
            "content_quality": 1.0
        }
        
        # Keyword matching
        if context.priority_keywords:
            content_lower = result.content.lower()
            keyword_matches = sum(1 for kw in context.priority_keywords if kw.lower() in content_lower)
            factors["keyword_density"] = keyword_matches / len(context.priority_keywords)
        
        # Content length preference
        if context.content_length_preference:
            content_length = len(result.content)
            if context.content_length_preference == "short" and content_length < 500:
                factors["length_preference"] = 1.0
            elif context.content_length_preference == "medium" and 500 <= content_length <= 2000:
                factors["length_preference"] = 1.0
            elif context.content_length_preference == "long" and content_length > 2000:
                factors["length_preference"] = 1.0
            else:
                factors["length_preference"] = 0.7
        
        return factors
    
    def _apply_intelligent_filtering(self,
                                   results: List[EnrichedSearchResult],
                                   context: RetrievalContext) -> List[EnrichedSearchResult]:
        """Apply intelligent filtering and reranking"""
        filtered_results = results.copy()
        
        # Remove excluded keywords
        if context.exclude_keywords:
            filtered_results = [
                r for r in filtered_results
                if not any(kw.lower() in r.content.lower() for kw in context.exclude_keywords)
            ]
        
        # Sort by combined relevance score
        def combined_score(result: EnrichedSearchResult) -> float:
            base_score = result.similarity_score
            
            # Weight by relevance factors
            factor_weights = {
                "semantic_similarity": 0.4,
                "keyword_density": 0.3,
                "recency": 0.2,
                "content_quality": 0.1
            }
            
            weighted_score = base_score
            for factor, weight in factor_weights.items():
                if factor in result.relevance_factors:
                    weighted_score += result.relevance_factors[factor] * weight
            
            return weighted_score
        
        filtered_results.sort(key=combined_score, reverse=True)
        
        return filtered_results
    
    def _determine_strategy(self, context: RetrievalContext) -> str:
        """Determine the best retrieval strategy"""
        if context.knowledge_types:
            return "filtered_semantic"
        elif context.priority_keywords:
            return "keyword_enhanced_semantic"
        else:
            return "pure_semantic"
    
    def _calculate_quality_score(self,
                               results: List[EnrichedSearchResult],
                               context: RetrievalContext) -> float:
        """Calculate overall quality score for results"""
        if not results:
            return 0.0
        
        # Average similarity score
        avg_similarity = sum(r.similarity_score for r in results) / len(results)
        
        # Coverage score (how well we covered the query)
        coverage_score = min(1.0, len(results) / 5)  # Prefer at least 5 results
        
        # Diversity score (avoid too similar results)
        diversity_score = 1.0  # Simplified for now
        
        return (avg_similarity * 0.5 + coverage_score * 0.3 + diversity_score * 0.2)
    
    def _generate_suggestions(self,
                            results: List[EnrichedSearchResult],
                            context: RetrievalContext) -> List[str]:
        """Generate search suggestions"""
        suggestions = []
        
        if not results:
            suggestions.append("Try broader keywords")
            suggestions.append("Check spelling and try synonyms")
        elif len(results) < 3:
            suggestions.append("Try more general terms")
            suggestions.append("Consider related topics")
        
        # Extract common themes from results
        if results:
            common_types = set(r.knowledge_type for r in results)
            if len(common_types) == 1:
                suggestions.append(f"More results available in {common_types.pop()}")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _generate_cache_key(self, context: RetrievalContext, limit: int) -> str:
        """Generate cache key for query"""
        key_parts = [
            context.query,
            str(sorted(context.knowledge_types or [])),
            str(limit),
            str(context.priority_keywords or [])
        ]
        return "|".join(key_parts)
    
    def _get_cached_result(self, cache_key: str) -> Optional[RetrievalResult]:
        """Get cached result if still valid"""
        if cache_key in self.query_cache:
            result, timestamp = self.query_cache[cache_key]
            if datetime.utcnow() - timestamp < self.cache_ttl:
                return result
            else:
                del self.query_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: RetrievalResult):
        """Cache result with timestamp"""
        self.query_cache[cache_key] = (result, datetime.utcnow())
        
        # Simple cache cleanup (keep last 100 entries)
        if len(self.query_cache) > 100:
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k][1])
            del self.query_cache[oldest_key]
    
    def _update_metrics(self, response_time: float, quality_score: float):
        """Update performance metrics"""
        self.metrics["total_queries"] += 1
        
        # Update average response time
        prev_avg = self.metrics["average_response_time"]
        count = self.metrics["total_queries"]
        self.metrics["average_response_time"] = ((prev_avg * (count - 1)) + response_time) / count
        
        # Track quality scores
        self.metrics["quality_scores"].append(quality_score)
        if len(self.metrics["quality_scores"]) > 100:
            self.metrics["quality_scores"] = self.metrics["quality_scores"][-100:]
    
    async def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval performance statistics"""
        avg_quality = (sum(self.metrics["quality_scores"]) / len(self.metrics["quality_scores"]) 
                      if self.metrics["quality_scores"] else 0.0)
        
        return {
            **self.metrics,
            "average_quality_score": avg_quality,
            "cache_size": len(self.query_cache),
            "cache_hit_rate": (self.metrics["cache_hits"] / max(1, self.metrics["total_queries"]))
        }

# Factory function
def create_semantic_retriever(project_id: str) -> SemanticRetriever:
    """
    Factory function to create a SemanticRetriever instance
    
    Args:
        project_id: Project ID for retriever
        
    Returns:
        Initialized SemanticRetriever
    """
    return SemanticRetriever(project_id)

# Export main classes
__all__ = [
    'SemanticRetriever',
    'RetrievalContext',
    'EnrichedSearchResult', 
    'RetrievalResult',
    'create_semantic_retriever'
]