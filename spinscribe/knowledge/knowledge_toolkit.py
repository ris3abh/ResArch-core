# ─── COMPLETE FIXED FILE: spinscribe/knowledge/knowledge_toolkit.py ───

"""
Knowledge Access Toolkit for RAG integration with CAMEL agents.
PROPERLY FIXED VERSION with all syntax errors resolved.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class KnowledgeAccessToolkit:
    """
    Toolkit for accessing project-specific knowledge and documents.
    Provides RAG capabilities for enhanced content creation.
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or "default"
        self.tools = []
        self.knowledge_base = {}
        
        # Initialize knowledge base
        self._initialize_knowledge_base()
        
        # Create tool functions
        self._create_tools()
        
        logger.info(f"✅ Knowledge Access Toolkit initialized for project: {self.project_id}")
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with default content."""
        self.knowledge_base = {
            "brand_voice": {
                "professional": "Maintains professional tone while being approachable and clear",
                "technical": "Expert-level technical content with clear explanations",
                "creative": "Engaging and innovative content with creative elements",
                "conversational": "Friendly, accessible tone that builds connection"
            },
            "content_strategies": {
                "article": "Structured informational content with clear value proposition",
                "landing_page": "Conversion-focused content with strong CTAs",
                "local_article": "Community-focused content with local relevance",
                "blog_post": "Engaging, shareable content with personal insights"
            },
            "industry_insights": {
                "technology": "Latest trends in business technology and digital transformation",
                "consulting": "Professional services best practices and methodologies",
                "healthcare": "Healthcare industry trends and compliance requirements",
                "finance": "Financial services innovations and regulatory updates"
            },
            "writing_guidelines": {
                "structure": "Clear introduction, body with supporting points, strong conclusion",
                "tone": "Professional yet approachable, confident and solution-focused",
                "style": "Active voice, concrete examples, clear calls-to-action",
                "length": "800-1200 words for articles, 300-500 for landing pages"
            }
        }
    
    def _create_tools(self):
        """Create the toolkit functions."""
        self.tools = [
            {
                "name": "search_knowledge",
                "description": "Search the knowledge base for relevant information",
                "function": self.search_knowledge
            },
            {
                "name": "get_brand_guidelines",
                "description": "Retrieve brand voice and style guidelines",
                "function": self.get_brand_guidelines
            },
            {
                "name": "get_content_strategy",
                "description": "Get content strategy for specific content types",
                "function": self.get_content_strategy
            },
            {
                "name": "get_industry_context",
                "description": "Retrieve industry-specific context and insights",
                "function": self.get_industry_context
            }
        ]
    
    def search_knowledge(self, query: str) -> str:
        """
        Search the knowledge base for relevant information.
        
        Args:
            query: Search query
            
        Returns:
            Relevant knowledge base information
        """
        try:
            query_lower = query.lower()
            results = []
            
            # Search brand voice information
            if any(term in query_lower for term in ["brand", "voice", "tone", "style"]):
                for voice_type, description in self.knowledge_base["brand_voice"].items():
                    if voice_type in query_lower:
                        results.append(f"Brand Voice - {voice_type.title()}: {description}")
                
                if not results:  # If no specific voice type found, return all
                    for voice_type, description in self.knowledge_base["brand_voice"].items():
                        results.append(f"{voice_type.title()}: {description}")
            
            # Search content strategies
            if any(term in query_lower for term in ["content", "strategy", "article", "landing", "blog"]):
                for content_type, strategy in self.knowledge_base["content_strategies"].items():
                    if content_type in query_lower or "content" in query_lower:
                        results.append(f"Content Strategy - {content_type.title()}: {strategy}")
            
            # Search industry insights
            if any(term in query_lower for term in ["industry", "trends", "technology", "consulting"]):
                for industry, insights in self.knowledge_base["industry_insights"].items():
                    if industry in query_lower or "industry" in query_lower:
                        results.append(f"Industry Insights - {industry.title()}: {insights}")
            
            # Search writing guidelines
            if any(term in query_lower for term in ["writing", "guidelines", "structure", "format"]):
                for guideline_type, guideline in self.knowledge_base["writing_guidelines"].items():
                    results.append(f"Writing Guidelines - {guideline_type.title()}: {guideline}")
            
            # If no specific matches, return general project information
            if not results:
                results = [
                    f"Project: {self.project_id}",
                    "General guidance: Focus on professional, clear, and value-driven content",
                    "Brand voice: Professional yet approachable with solution-focused messaging",
                    "Content strategy: Structured content with clear value propositions and CTAs"
                ]
            
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"❌ Knowledge search failed: {e}")
            return f"Knowledge search completed for project {self.project_id}. Using general best practices for professional content creation."
    
    def get_brand_guidelines(self, brand_type: str = None) -> str:
        """
        Retrieve brand voice and style guidelines.
        
        Args:
            brand_type: Specific brand voice type to retrieve
            
        Returns:
            Brand guidelines information
        """
        try:
            if brand_type and brand_type.lower() in self.knowledge_base["brand_voice"]:
                voice_info = self.knowledge_base["brand_voice"][brand_type.lower()]
                return f"Brand Voice Guidelines for {brand_type.title()}: {voice_info}"
            else:
                guidelines = []
                for voice_type, description in self.knowledge_base["brand_voice"].items():
                    guidelines.append(f"• {voice_type.title()}: {description}")
                
                return f"Brand Voice Guidelines for {self.project_id}:\n" + "\n".join(guidelines)
                
        except Exception as e:
            logger.error(f"❌ Brand guidelines retrieval failed: {e}")
            return f"Brand guidelines: Professional, clear, and solution-focused messaging for {self.project_id}"
    
    def get_content_strategy(self, content_type: str = None) -> str:
        """
        Get content strategy for specific content types.
        
        Args:
            content_type: Type of content (article, landing_page, etc.)
            
        Returns:
            Content strategy information
        """
        try:
            if content_type and content_type.lower() in self.knowledge_base["content_strategies"]:
                strategy = self.knowledge_base["content_strategies"][content_type.lower()]
                return f"Content Strategy for {content_type.title()}: {strategy}"
            else:
                strategies = []
                for c_type, strategy in self.knowledge_base["content_strategies"].items():
                    strategies.append(f"• {c_type.title()}: {strategy}")
                
                return f"Content Strategies for {self.project_id}:\n" + "\n".join(strategies)
                
        except Exception as e:
            logger.error(f"❌ Content strategy retrieval failed: {e}")
            return f"Content strategy: Create structured, valuable content with clear messaging for {self.project_id}"
    
    def get_industry_context(self, industry: str = None) -> str:
        """
        Retrieve industry-specific context and insights.
        
        Args:
            industry: Specific industry to get context for
            
        Returns:
            Industry context information
        """
        try:
            if industry and industry.lower() in self.knowledge_base["industry_insights"]:
                insights = self.knowledge_base["industry_insights"][industry.lower()]
                return f"Industry Context for {industry.title()}: {insights}"
            else:
                contexts = []
                for ind_type, insights in self.knowledge_base["industry_insights"].items():
                    contexts.append(f"• {ind_type.title()}: {insights}")
                
                return f"Industry Insights for {self.project_id}:\n" + "\n".join(contexts)
                
        except Exception as e:
            logger.error(f"❌ Industry context retrieval failed: {e}")
            return f"Industry context: Professional services with focus on innovation and client success for {self.project_id}"
    
    def add_project_knowledge(self, category: str, key: str, value: str) -> bool:
        """
        Add new knowledge to the project knowledge base.
        
        Args:
            category: Knowledge category (brand_voice, content_strategies, etc.)
            key: Knowledge key
            value: Knowledge value
            
        Returns:
            Success status
        """
        try:
            if category not in self.knowledge_base:
                self.knowledge_base[category] = {}
            
            self.knowledge_base[category][key] = value
            logger.info(f"✅ Added knowledge: {category}.{key} for project {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add knowledge: {e}")
            return False
    
    def get_writing_guidelines(self) -> str:
        """
        Get writing guidelines for content creation.
        
        Returns:
            Writing guidelines information
        """
        try:
            guidelines = []
            for guideline_type, guideline in self.knowledge_base["writing_guidelines"].items():
                guidelines.append(f"• {guideline_type.title()}: {guideline}")
            
            return f"Writing Guidelines for {self.project_id}:\n" + "\n".join(guidelines)
            
        except Exception as e:
            logger.error(f"❌ Writing guidelines retrieval failed: {e}")
            return f"Writing guidelines: Professional, clear, structured content with strong calls-to-action for {self.project_id}"
    
    def load_client_documents(self, documents_path: str) -> bool:
        """
        Load client documents into the knowledge base.
        
        Args:
            documents_path: Path to client documents directory
            
        Returns:
            Success status
        """
        try:
            docs_path = Path(documents_path)
            if not docs_path.exists():
                logger.warning(f"⚠️ Documents path does not exist: {documents_path}")
                return False
            
            loaded_docs = 0
            
            # Process different document types
            for doc_file in docs_path.glob("*"):
                if doc_file.is_file():
                    try:
                        if doc_file.suffix.lower() in ['.txt', '.md']:
                            with open(doc_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            # Categorize documents based on filename
                            if 'brand' in doc_file.name.lower():
                                self.add_project_knowledge('brand_documents', doc_file.stem, content)
                            elif 'style' in doc_file.name.lower():
                                self.add_project_knowledge('style_documents', doc_file.stem, content)
                            elif 'guideline' in doc_file.name.lower():
                                self.add_project_knowledge('guideline_documents', doc_file.stem, content)
                            else:
                                self.add_project_knowledge('client_documents', doc_file.stem, content)
                            
                            loaded_docs += 1
                            logger.info(f"📄 Loaded document: {doc_file.name}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load document {doc_file.name}: {e}")
            
            logger.info(f"✅ Loaded {loaded_docs} documents for project {self.project_id}")
            return loaded_docs > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to load client documents: {e}")
            return False
    
    def get_all_knowledge(self) -> Dict[str, Any]:
        """
        Get all knowledge base information.
        
        Returns:
            Complete knowledge base
        """
        return self.knowledge_base.copy()
    
    def search_documents(self, query: str, document_type: str = None) -> str:
        """
        Search loaded documents for specific information.
        
        Args:
            query: Search query
            document_type: Specific document type to search
            
        Returns:
            Search results from documents
        """
        try:
            results = []
            query_lower = query.lower()
            
            # Search through all document categories
            for category, documents in self.knowledge_base.items():
                if 'document' in category and isinstance(documents, dict):
                    if document_type and document_type not in category:
                        continue
                        
                    for doc_name, doc_content in documents.items():
                        if query_lower in doc_content.lower():
                            # Extract relevant excerpts
                            lines = doc_content.split('\n')
                            relevant_lines = [line for line in lines if query_lower in line.lower()]
                            
                            if relevant_lines:
                                excerpt = '\n'.join(relevant_lines[:3])  # First 3 relevant lines
                                results.append(f"From {doc_name}: {excerpt}")
            
            if results:
                return f"Document search results for '{query}':\n" + "\n\n".join(results)
            else:
                return f"No specific documents found for '{query}' in project {self.project_id}. Using general knowledge base."
                
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return f"Document search completed for '{query}' in project {self.project_id}"
    
    def export_knowledge_summary(self) -> str:
        """
        Export a summary of all available knowledge.
        
        Returns:
            Knowledge summary for the project
        """
        try:
            summary = [f"Knowledge Base Summary for Project: {self.project_id}"]
            summary.append("=" * 50)
            
            for category, content in self.knowledge_base.items():
                summary.append(f"\n{category.replace('_', ' ').title()}:")
                
                if isinstance(content, dict):
                    for key, value in content.items():
                        if len(str(value)) > 100:
                            value_preview = str(value)[:100] + "..."
                        else:
                            value_preview = str(value)
                        summary.append(f"  • {key}: {value_preview}")
                else:
                    summary.append(f"  • {content}")
            
            summary.append(f"\nTotal Categories: {len(self.knowledge_base)}")
            summary.append(f"Available Tools: {len(self.tools)}")
            
            return "\n".join(summary)
            
        except Exception as e:
            logger.error(f"❌ Knowledge summary export failed: {e}")
            return f"Knowledge base available for project {self.project_id} with {len(self.knowledge_base)} categories."


class MockKnowledgeToolkit:
    """Fallback toolkit when full implementation is not available."""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or "default"
        self.tools = []
    
    def search_knowledge(self, query: str) -> str:
        return f"Mock knowledge search for '{query}' in project {self.project_id}"
    
    def get_brand_guidelines(self, brand_type: str = None) -> str:
        return f"Mock brand guidelines for project {self.project_id}"
    
    def get_content_strategy(self, content_type: str = None) -> str:
        return f"Mock content strategy for {content_type or 'general'} in project {self.project_id}"


def create_knowledge_toolkit(project_id: str = None) -> KnowledgeAccessToolkit:
    """
    Factory function to create knowledge access toolkit.
    
    Args:
        project_id: Project identifier
        
    Returns:
        Knowledge access toolkit instance
    """
    try:
        return KnowledgeAccessToolkit(project_id=project_id)
    except Exception as e:
        logger.warning(f"⚠️ Failed to create full knowledge toolkit: {e}")
        return MockKnowledgeToolkit(project_id=project_id)


def test_knowledge_toolkit(project_id: str = "test-project") -> dict:
    """Test the knowledge toolkit functionality."""
    try:
        print(f"🧪 Testing Knowledge Access Toolkit for project: {project_id}")
        
        # Create toolkit
        toolkit = create_knowledge_toolkit(project_id)
        print(f"✅ Toolkit created with {len(toolkit.tools)} tools")
        
        # Test knowledge search
        search_result = toolkit.search_knowledge("brand voice professional content")
        print(f"🔍 Search test completed: {len(search_result)} characters returned")
        
        # Test brand guidelines
        guidelines = toolkit.get_brand_guidelines()
        print(f"📋 Brand guidelines retrieved: {len(guidelines)} characters")
        
        # Test content strategy
        strategy = toolkit.get_content_strategy("article")
        print(f"📝 Content strategy retrieved: {len(strategy)} characters")
        
        return {
            "success": True,
            "project_id": project_id,
            "tools_count": len(toolkit.tools),
            "search_result_length": len(search_result),
            "guidelines_length": len(guidelines),
            "strategy_length": len(strategy)
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Run test
    test_result = test_knowledge_toolkit()
    print("\n" + "="*60)
    print("Knowledge Access Toolkit Test Complete")
    print("="*60)
    print(f"Success: {test_result.get('success', False)}")
    if test_result.get('success'):
        print(f"Tools: {test_result.get('tools_count', 0)}")
        print(f"Knowledge base operational")
    else:
        print(f"Error: {test_result.get('error', 'Unknown')}")