#!/usr/bin/env python3
"""
Complete test showing FULL agent outputs without truncation
Save as: test_full_output.py
"""

import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))

print("\n" + "="*80)
print("FULL AGENT OUTPUT TEST - NO TRUNCATION")
print("="*80)

from spinscribe.workforce.enhanced_builder import EnhancedWorkforceBuilder
from camel.messages import BaseMessage

# Create builder
builder = EnhancedWorkforceBuilder(
    project_id="test-project",
    token_limit=10000,  # Higher limit for more content
    websocket_interceptor=None
)

# Build workforce
workforce = builder.build_enhanced_workforce()
print(f"\nBuilt workforce with {len(builder.agents)} agents\n")

# Test each agent with detailed prompts to get full outputs
test_scenarios = {
    'enhanced_style_analysis': {
        'prompt': """Analyze the writing style needed for a comprehensive article about 'The Future of AI in Healthcare'. 
        Please provide:
        1. Target audience analysis
        2. Tone and voice recommendations
        3. Technical level guidelines
        4. Key stylistic elements to include
        5. Things to avoid
        6. Example opening sentence
        Provide detailed analysis for each point.""",
        'name': 'STYLE ANALYSIS AGENT'
    },
    
    'enhanced_content_planning': {
        'prompt': """Create a detailed outline for a 2000-word article titled 'The Future of AI in Healthcare'.
        Include:
        1. Introduction (with hook and thesis)
        2. At least 5 main sections with subsections
        3. Key points for each section
        4. Transition strategies between sections
        5. Conclusion structure
        6. Call-to-action ideas
        Provide complete detail for each section.""",
        'name': 'CONTENT PLANNING AGENT'
    },
    
    'enhanced_content_generation': {
        'prompt': """Write the complete introduction and first two sections for an article about 'The Future of AI in Healthcare'.
        Requirements:
        - Introduction: 200 words with compelling hook
        - Section 1: Current State of AI in Healthcare (300 words)
        - Section 2: Breakthrough Technologies on the Horizon (300 words)
        Include specific examples, statistics (you can use placeholder data), and expert perspectives.
        Write the full content without any truncation.""",
        'name': 'CONTENT GENERATION AGENT'
    },
    
    'enhanced_qa': {
        'prompt': """Review and provide detailed feedback on this content:
        
        'Artificial intelligence is transforming healthcare at an unprecedented pace. From diagnostic imaging to drug discovery, 
        AI systems are augmenting human capabilities and opening new frontiers in patient care. Machine learning algorithms 
        can now detect certain cancers earlier than human radiologists, predict patient deterioration hours before it occurs, 
        and personalize treatment plans based on individual genetic profiles.'
        
        Please provide:
        1. Grammar and style corrections
        2. Suggestions for improving clarity
        3. Fact-checking notes
        4. Recommendations for stronger impact
        5. Alternative phrasings for key sentences
        6. Overall assessment with specific improvements""",
        'name': 'QUALITY ASSURANCE AGENT'
    },
    
    'enhanced_coordinator': {
        'prompt': """As the coordinator, create a comprehensive workflow plan for producing a high-quality article about 
        'The Future of AI in Healthcare'. Include:
        1. Complete task breakdown with dependencies
        2. Agent assignment strategy
        3. Quality checkpoints
        4. Timeline estimates
        5. Risk mitigation strategies
        6. Success metrics
        Provide full details for each component.""",
        'name': 'COORDINATOR AGENT'
    }
}

print("="*80)
print("TESTING EACH AGENT WITH FULL OUTPUT")
print("="*80)

for agent_name, scenario in test_scenarios.items():
    if agent_name in builder.agents:
        print(f"\n{'='*80}")
        print(f"TESTING: {scenario['name']}")
        print(f"Agent ID: {agent_name}")
        print("-"*80)
        print(f"PROMPT:\n{scenario['prompt']}")
        print("-"*80)
        
        agent = builder.agents[agent_name]
        
        try:
            # Create message
            msg = BaseMessage.make_user_message(
                role_name="User",
                content=scenario['prompt']
            )
            
            # Get response
            response = agent.step(msg)
            
            if response and hasattr(response, 'msgs') and response.msgs:
                content = response.msgs[0].content
                print(f"FULL RESPONSE ({len(content)} characters):")
                print("-"*80)
                print(content)  # Print FULL content without truncation
                print("-"*80)
                print(f"END OF {scenario['name']} RESPONSE\n")
            else:
                print("No response received")
                
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"\nAgent {agent_name} not found")

# Now run a complete workflow simulation
print("\n" + "="*80)
print("COMPLETE WORKFLOW SIMULATION WITH FULL OUTPUTS")
print("="*80)

async def run_full_workflow():
    """Run complete workflow showing all content"""
    
    article_context = {
        'topic': 'The Future of AI in Healthcare',
        'target_words': 2000,
        'audience': 'Healthcare professionals and technology leaders'
    }
    
    print(f"\n📋 Article Requirements:")
    print(f"   Topic: {article_context['topic']}")
    print(f"   Length: {article_context['target_words']} words")
    print(f"   Audience: {article_context['audience']}\n")
    
    # Phase 1: Style Analysis
    print("="*80)
    print("PHASE 1: STYLE ANALYSIS")
    print("="*80)
    
    style_agent = builder.agents['enhanced_style_analysis']
    msg = BaseMessage.make_user_message(
        role_name="User",
        content=f"Provide complete style guide for article: '{article_context['topic']}' targeting {article_context['audience']}"
    )
    style_response = style_agent.step(msg)
    
    style_guide = ""
    if style_response and style_response.msgs:
        style_guide = style_response.msgs[0].content
        print("COMPLETE STYLE GUIDE:")
        print("-"*80)
        print(style_guide)
        print("-"*80)
    
    # Checkpoint simulation
    print("\n🔴 CHECKPOINT: STRATEGY APPROVAL")
    await asyncio.sleep(1)
    print("✅ Checkpoint approved - continuing...\n")
    
    # Phase 2: Content Planning
    print("="*80)
    print("PHASE 2: CONTENT PLANNING")
    print("="*80)
    
    planning_agent = builder.agents['enhanced_content_planning']
    msg = BaseMessage.make_user_message(
        role_name="User",
        content=f"Create complete outline for {article_context['target_words']}-word article on '{article_context['topic']}' following this style guide: {style_guide[:500]}"
    )
    planning_response = planning_agent.step(msg)
    
    outline = ""
    if planning_response and planning_response.msgs:
        outline = planning_response.msgs[0].content
        print("COMPLETE ARTICLE OUTLINE:")
        print("-"*80)
        print(outline)
        print("-"*80)
    
    # Phase 3: Content Generation
    print("="*80)
    print("PHASE 3: CONTENT GENERATION")
    print("="*80)
    
    generation_agent = builder.agents['enhanced_content_generation']
    msg = BaseMessage.make_user_message(
        role_name="User",
        content=f"Write the complete article based on this outline: {outline[:1000]}. Write at least 1000 words."
    )
    generation_response = generation_agent.step(msg)
    
    draft = ""
    if generation_response and generation_response.msgs:
        draft = generation_response.msgs[0].content
        print("COMPLETE GENERATED ARTICLE:")
        print("-"*80)
        print(draft)
        print("-"*80)
    
    # Checkpoint 2
    print("\n🔴 CHECKPOINT: CONTENT REVIEW")
    await asyncio.sleep(1)
    print("✅ Content approved with minor revision requests\n")
    
    # Phase 4: Quality Assurance
    print("="*80)
    print("PHASE 4: QUALITY ASSURANCE")
    print("="*80)
    
    qa_agent = builder.agents['enhanced_qa']
    msg = BaseMessage.make_user_message(
        role_name="User",
        content=f"Provide complete QA review and improved version of this article: {draft}"
    )
    qa_response = qa_agent.step(msg)
    
    if qa_response and qa_response.msgs:
        final_version = qa_response.msgs[0].content
        print("COMPLETE QA FEEDBACK AND FINAL VERSION:")
        print("-"*80)
        print(final_version)
        print("-"*80)
    
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE - ALL CONTENT GENERATED")
    print("="*80)

# Run the workflow
print("\nStarting workflow simulation...")
asyncio.run(run_full_workflow())

print("\n✅ TEST COMPLETE - Full agent outputs displayed above")