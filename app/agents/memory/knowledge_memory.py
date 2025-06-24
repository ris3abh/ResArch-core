# app/agents/memory/knowledge_memory.py
"""
Knowledge Memory for SpinScribe Agents
Manages agent access to project knowledge and learning from interactions
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from camel.memories import VectorDBMemory, VectorDBBlock
from app.database.connection import SessionLocal
from app.database.models.knowledge_item import KnowledgeItem
from app.knowledge.base.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class KnowledgeMemory:
    """
    Manages knowledge-based memory for agents
    Provides access to project knowledge and learns from agent interactions
    """
    
    def __init__(self, 
                 project_id: str,
                 agent_type: str):
        self.project_id = project_id
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{agent_type}.{project_id}")
        
        # Initialize knowledge base
        self.knowledge_base = KnowledgeBase(project_id) if project_id else None
        
        # Initialize vector memory for semantic search
        self.vector_memory = VectorDBMemory(
            vector_db_block=VectorDBBlock(),
            retrieve_limit=5
        )
        
        # Cache for frequently accessed knowledge
        self.knowledge_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = datetime.now()
    
    async def get_relevant_knowledge(self, 
                                   query: str,
                                   knowledge_types: Optional[List[str]] = None,
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant knowledge items for a query
        
        Args:
            query: Search query
            knowledge_types: Optional filter by knowledge types
            limit: Maximum number of results
            
        Returns:
            List of relevant knowledge items
        """
        
        try:
            if not self.knowledge_base:
                return []
            
            # Check cache first
            cache_key = f"{query}_{knowledge_types}_{limit}"
            if cache_key in self.knowledge_cache:
                cache_entry = self.knowledge_cache[cache_key]
                if (datetime.now() - cache_entry["timestamp"]).seconds < self.cache_ttl:
                    return cache_entry["data"]
            
            # Search knowledge base
            db = SessionLocal()
            
            query_filter = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id
            )
            
            # Apply knowledge type filter
            if knowledge_types:
                query_filter = query_filter.filter(
                    KnowledgeItem.knowledge_type.in_(knowledge_types)
                )
            
            # Simple text search (in production, use vector search)
            items = query_filter.filter(
                KnowledgeItem.content.ilike(f"%{query}%")
            ).limit(limit).all()
            
            # Convert to response format
            knowledge_items = []
            for item in items:
                knowledge_items.append({
                    "knowledge_id": item.knowledge_id,
                    "title": item.title,
                    "content": item.content,
                    "knowledge_type": item.knowledge_type,
                    "relevance_score": 0.8,  # Placeholder relevance
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "metadata": item.meta_data or {}
                })
            
            # Cache results
            self.knowledge_cache[cache_key] = {
                "data": knowledge_items,
                "timestamp": datetime.now()
            }
            
            db.close()
            self.logger.debug(f"Retrieved {len(knowledge_items)} knowledge items for query: {query}")
            
            return knowledge_items
            
        except Exception as e:
            self.logger.error(f"Failed to get relevant knowledge: {e}")
            if 'db' in locals():
                db.close()
            return []
    
    async def get_style_guidelines(self) -> Dict[str, Any]:
        """Get style guidelines specific to this project"""
        
        try:
            style_knowledge = await self.get_relevant_knowledge(
                query="style guide brand voice",
                knowledge_types=["style_guide", "brand_voice", "style_analysis"],
                limit=3
            )
            
            # Combine style information
            guidelines = {
                "brand_voice": "professional",
                "tone": "helpful",
                "formality_level": 3,
                "vocabulary_level": 5,
                "style_elements": []
            }
            
            for item in style_knowledge:
                if item["knowledge_type"] == "style_analysis":
                    try:
                        # Extract style data from content
                        content = json.loads(item["content"]) if isinstance(item["content"], str) else item["content"]
                        if "brand_voice_elements" in content:
                            guidelines.update(content["brand_voice_elements"])
                    except:
                        pass
                
                guidelines["style_elements"].append({
                    "source": item["title"],
                    "type": item["knowledge_type"],
                    "relevance": item["relevance_score"]
                })
            
            return guidelines
            
        except Exception as e:
            self.logger.error(f"Failed to get style guidelines: {e}")
            return {}
    
    async def get_content_examples(self, 
                                 content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get content examples for reference"""
        
        try:
            query = f"content example {content_type}" if content_type else "content example"
            
            examples = await self.get_relevant_knowledge(
                query=query,
                knowledge_types=["content_sample", "generated_content", "content_plan"],
                limit=5
            )
            
            return examples
            
        except Exception as e:
            self.logger.error(f"Failed to get content examples: {e}")
            return []
    
    async def learn_from_interaction(self, 
                                   interaction_data: Dict[str, Any],
                                   quality_score: Optional[float] = None):
        """
        Learn from agent interactions to improve future responses
        
        Args:
            interaction_data: Data about the interaction
            quality_score: Optional quality score for the interaction
        """
        
        try:
            if not self.knowledge_base:
                return
            
            # Create learning record
            learning_record = {
                "title": f"Learning Record: {self.agent_type} - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "learning_record",
                "content": json.dumps({
                    "agent_type": self.agent_type,
                    "interaction": interaction_data,
                    "quality_score": quality_score,
                    "timestamp": datetime.now().isoformat(),
                    "learning_insights": self._extract_learning_insights(interaction_data, quality_score)
                }),
                "metadata": {
                    "agent_type": self.agent_type,
                    "quality_score": quality_score,
                    "learning_type": "interaction_feedback"
                }
            }
            
            # Store learning record
            await self.knowledge_base.store_document(learning_record)
            
            # Clear cache to ensure fresh data
            self._clear_cache()
            
            self.logger.debug(f"Stored learning record for {self.agent_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to learn from interaction: {e}")
    
    def _extract_learning_insights(self, 
                                 interaction_data: Dict[str, Any],
                                 quality_score: Optional[float] = None) -> List[str]:
        """Extract learning insights from interaction data"""
        
        insights = []
        
        # Analyze quality score
        if quality_score is not None:
            if quality_score >= 0.9:
                insights.append("High quality interaction - patterns should be reinforced")
            elif quality_score >= 0.7:
                insights.append("Good quality interaction with room for improvement")
            else:
                insights.append("Low quality interaction - review and improve patterns")
        
        # Analyze interaction patterns
        if "user_input" in interaction_data and "agent_response" in interaction_data:
            user_input = interaction_data["user_input"]
            agent_response = interaction_data["agent_response"]
            
            # Simple pattern analysis
            if len(agent_response) < 50:
                insights.append("Response was very brief - consider more detailed responses")
            elif len(agent_response) > 1000:
                insights.append("Response was very long - consider more concise communication")
            
            if "?" in user_input and "?" not in agent_response:
                insights.append("User asked questions - ensure comprehensive answers")
        
        return insights
    
    async def get_learning_insights(self) -> List[Dict[str, Any]]:
        """Get accumulated learning insights for this agent"""
        
        try:
            learning_records = await self.get_relevant_knowledge(
                query=f"learning record {self.agent_type}",
                knowledge_types=["learning_record"],
                limit=10
            )
            
            insights = []
            for record in learning_records:
                try:
                    content = json.loads(record["content"]) if isinstance(record["content"], str) else record["content"]
                    if "learning_insights" in content:
                        insights.extend(content["learning_insights"])
                except:
                    pass
            
            # Remove duplicates and return unique insights
            unique_insights = []
            for insight in insights:
                if isinstance(insight, str) and insight not in unique_insights:
                    unique_insights.append(insight)
            
            return [{"insight": insight, "frequency": insights.count(insight)} for insight in unique_insights]
            
        except Exception as e:
            self.logger.error(f"Failed to get learning insights: {e}")
            return []
    
    async def get_project_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of project knowledge"""
        
        try:
            if not self.knowledge_base:
                return {}
            
            db = SessionLocal()
            
            # Get knowledge statistics
            total_items = db.query(KnowledgeItem).filter(
                KnowledgeItem.project_id == self.project_id
            ).count()
            
            # Get knowledge by type
            knowledge_types = db.query(KnowledgeItem.knowledge_type)\
                               .filter(KnowledgeItem.project_id == self.project_id)\
                               .distinct().all()
            
            type_counts = {}
            for (knowledge_type,) in knowledge_types:
                count = db.query(KnowledgeItem)\
                         .filter(KnowledgeItem.project_id == self.project_id)\
                         .filter(KnowledgeItem.knowledge_type == knowledge_type)\
                         .count()
                type_counts[knowledge_type] = count
            
            summary = {
                "project_id": self.project_id,
                "total_knowledge_items": total_items,
                "knowledge_types": type_counts,
                "agent_type": self.agent_type,
                "cache_size": len(self.knowledge_cache),
                "last_accessed": datetime.now().isoformat()
            }
            
            db.close()
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge summary: {e}")
            if 'db' in locals():
                db.close()
            return {"error": str(e)}
    
    def _clear_cache(self):
        """Clear knowledge cache"""
        self.knowledge_cache.clear()
        self.last_cache_update = datetime.now()
        self.logger.debug("Cleared knowledge cache")
    
    async def preload_agent_knowledge(self):
        """Preload commonly needed knowledge for this agent type"""
        
        try:
            # Agent-specific knowledge preloading
            if self.agent_type == "style_analyzer":
                await self.get_relevant_knowledge("style guide brand voice", limit=3)
                await self.get_content_examples()
                
            elif self.agent_type == "content_planner":
                await self.get_style_guidelines()
                await self.get_content_examples("blog_post")
                await self.get_content_examples("landing_page")
                
            elif self.agent_type == "content_generator":
                await self.get_style_guidelines()
                await self.get_relevant_knowledge("content plan outline", limit=3)
                
            elif self.agent_type == "editor_qa":
                await self.get_style_guidelines()
                await self.get_relevant_knowledge("quality guidelines", limit=3)
                
            elif self.agent_type == "coordinator":
                await self.get_project_knowledge_summary()
                await self.get_relevant_knowledge("workflow project", limit=5)
            
            self.logger.info(f"Preloaded knowledge for {self.agent_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to preload knowledge: {e}")


# Knowledge memory registry
_knowledge_memories: Dict[str, Dict[str, KnowledgeMemory]] = {}

def get_knowledge_memory(project_id: str, agent_type: str) -> KnowledgeMemory:
    """
    Get or create knowledge memory for agent
    
    Args:
        project_id: Project identifier
        agent_type: Type of agent
        
    Returns:
        KnowledgeMemory instance
    """
    if project_id not in _knowledge_memories:
        _knowledge_memories[project_id] = {}
    
    if agent_type not in _knowledge_memories[project_id]:
        _knowledge_memories[project_id][agent_type] = KnowledgeMemory(project_id, agent_type)
    
    return _knowledge_memories[project_id][agent_type]

def clear_knowledge_memory(project_id: str, agent_type: Optional[str] = None):
    """
    Clear knowledge memory
    
    Args:
        project_id: Project identifier
        agent_type: Optional specific agent type to clear
    """
    if project_id in _knowledge_memories:
        if agent_type:
            if agent_type in _knowledge_memories[project_id]:
                _knowledge_memories[project_id][agent_type]._clear_cache()
                del _knowledge_memories[project_id][agent_type]
        else:
            # Clear all agent memories for project
            for agent_mem in _knowledge_memories[project_id].values():
                agent_mem._clear_cache()
            del _knowledge_memories[project_id]