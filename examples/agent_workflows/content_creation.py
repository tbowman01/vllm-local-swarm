#!/usr/bin/env python3
"""
Content Creation Pipeline Workflow
=================================

Advanced multi-stage content creation workflow with:
- AI-powered content generation and optimization
- Real-time collaboration between specialist agents
- SEO optimization and quality assurance
- Multi-format output generation

Workflow Steps:
1. Content Strategy & Planning
2. Research & Data Gathering
3. Draft Content Creation
4. Editorial Review & Enhancement
5. SEO Optimization & Formatting
6. Quality Assurance & Publishing

Agents Involved:
- Content Strategist: Plans content strategy and topics
- Research Agent: Gathers relevant data and insights
- Content Creator: Generates initial draft content
- Editor: Reviews and enhances content quality
- SEO Specialist: Optimizes for search engines
- Quality Controller: Final review and publishing
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from agents.communication import (
    RealtimeHub, AgentClient, ConnectionConfig, 
    AgentRole, MessageType
)
from agents.communication.integration import SmartAgentClient

logger = logging.getLogger(__name__)


class ContentStrategist(SmartAgentClient):
    """
    Content strategy and planning coordinator
    """
    
    def __init__(self):
        config = ConnectionConfig(
            agent_id="content_strategist",
            role=AgentRole.COORDINATOR,
            capabilities=["strategy", "planning", "content_analysis", "market_research"],
            metadata={
                "type": "strategist",
                "specialization": "content_strategy",
                "expertise": ["topic_research", "audience_analysis", "content_planning"]
            }
        )
        super().__init__(config, auto_accept_tasks=False)
        
        self.active_campaigns: Dict[str, Dict[str, Any]] = {}
        self.content_templates = {
            "blog_post": {
                "structure": ["introduction", "main_points", "conclusion"],
                "target_length": 1500,
                "seo_requirements": ["title_tag", "meta_description", "keywords"]
            },
            "article": {
                "structure": ["headline", "lead", "body", "conclusion"],
                "target_length": 2000,
                "seo_requirements": ["h1_tag", "internal_links", "alt_text"]
            },
            "social_media": {
                "structure": ["hook", "content", "call_to_action"],
                "target_length": 280,
                "seo_requirements": ["hashtags", "mentions"]
            }
        }
        
    async def start_content_campaign(self, campaign_config: Dict[str, Any]) -> str:
        """Start a new content creation campaign"""
        campaign_id = f"campaign_{int(datetime.now().timestamp())}"
        
        self.active_campaigns[campaign_id] = {
            "config": campaign_config,
            "started_at": datetime.now().isoformat(),
            "status": "planning",
            "content_pieces": [],
            "results": {}
        }
        
        logger.info(f"📝 Starting content campaign: {campaign_config.get('title', campaign_id)}")
        
        # Create content strategy
        strategy = await self._develop_content_strategy(campaign_config)
        
        # Plan content pieces
        await self._plan_content_pieces(campaign_id, strategy)
        
        return campaign_id
        
    async def _develop_content_strategy(self, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Develop comprehensive content strategy"""
        
        topic = campaign_config.get("topic", "General")
        target_audience = campaign_config.get("target_audience", "general")
        content_types = campaign_config.get("content_types", ["blog_post"])
        timeline = campaign_config.get("timeline_days", 7)
        
        # Analyze topic and audience
        strategy = {
            "topic": topic,
            "target_audience": target_audience,
            "content_types": content_types,
            "timeline_days": timeline,
            "key_themes": await self._identify_key_themes(topic),
            "audience_interests": await self._analyze_audience_interests(target_audience),
            "content_calendar": await self._create_content_calendar(content_types, timeline),
            "seo_strategy": await self._develop_seo_strategy(topic),
            "distribution_channels": await self._select_distribution_channels(target_audience)
        }
        
        return strategy
        
    async def _identify_key_themes(self, topic: str) -> List[str]:
        """Identify key themes related to the topic"""
        await asyncio.sleep(2)  # Simulate research
        
        # Simulated theme analysis
        theme_map = {
            "ai": ["machine_learning", "automation", "future_of_work", "ethics"],
            "technology": ["innovation", "digital_transformation", "cybersecurity", "trends"],
            "business": ["strategy", "leadership", "growth", "market_analysis"],
            "health": ["wellness", "prevention", "treatment", "lifestyle"],
            "education": ["learning", "skills", "career", "development"]
        }
        
        topic_lower = topic.lower()
        for key, themes in theme_map.items():
            if key in topic_lower:
                return themes
                
        return ["overview", "benefits", "challenges", "future_trends"]
        
    async def _analyze_audience_interests(self, audience: str) -> Dict[str, Any]:
        """Analyze target audience interests and preferences"""
        await asyncio.sleep(1)
        
        audience_profiles = {
            "professionals": {
                "interests": ["career_growth", "industry_trends", "skill_development"],
                "content_preferences": ["in_depth_analysis", "case_studies", "expert_interviews"],
                "reading_time": "10-15 minutes",
                "preferred_format": "long_form"
            },
            "general": {
                "interests": ["practical_tips", "beginner_guides", "trending_topics"],
                "content_preferences": ["easy_to_understand", "visual_elements", "actionable_advice"],
                "reading_time": "5-8 minutes", 
                "preferred_format": "mixed"
            },
            "technical": {
                "interests": ["implementation_details", "best_practices", "tools_and_frameworks"],
                "content_preferences": ["technical_depth", "code_examples", "performance_metrics"],
                "reading_time": "15-20 minutes",
                "preferred_format": "technical_documentation"
            }
        }
        
        return audience_profiles.get(audience, audience_profiles["general"])
        
    async def _create_content_calendar(self, content_types: List[str], timeline_days: int) -> List[Dict[str, Any]]:
        """Create content publishing calendar"""
        calendar = []
        
        for i, content_type in enumerate(content_types):
            publish_date = datetime.now() + timedelta(days=i * (timeline_days // len(content_types)))
            
            calendar.append({
                "content_type": content_type,
                "planned_date": publish_date.isoformat(),
                "status": "planned",
                "priority": "high" if content_type == "blog_post" else "normal"
            })
            
        return calendar
        
    async def _develop_seo_strategy(self, topic: str) -> Dict[str, Any]:
        """Develop SEO strategy for content"""
        await asyncio.sleep(1)
        
        return {
            "primary_keywords": [topic.lower(), f"{topic} guide", f"best {topic}"],
            "secondary_keywords": [f"{topic} tips", f"{topic} benefits", f"how to {topic}"],
            "target_ranking": "top_10",
            "content_optimization": {
                "title_optimization": True,
                "meta_description": True,
                "internal_linking": True,
                "schema_markup": True
            }
        }
        
    async def _select_distribution_channels(self, audience: str) -> List[str]:
        """Select appropriate distribution channels"""
        channel_map = {
            "professionals": ["linkedin", "industry_blogs", "newsletters"],
            "general": ["social_media", "blog", "email_marketing"],
            "technical": ["github", "technical_forums", "developer_communities"]
        }
        
        return channel_map.get(audience, ["blog", "social_media"])
        
    async def _plan_content_pieces(self, campaign_id: str, strategy: Dict[str, Any]):
        """Plan individual content pieces based on strategy"""
        
        campaign = self.active_campaigns[campaign_id]
        campaign["status"] = "content_planning"
        
        # Send strategy to all agents
        await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {
                "event": "content_campaign_started",
                "campaign_id": campaign_id,
                "strategy": strategy,
                "coordinator": self.config.agent_id
            },
            channel="content_coordination"
        )
        
        # Create content tasks for each piece in calendar
        for content_item in strategy["content_calendar"]:
            content_id = f"{campaign_id}_{content_item['content_type']}"
            
            # Research task
            research_task = {
                "task_id": f"{content_id}_research",
                "campaign_id": campaign_id,
                "content_id": content_id,
                "task_type": "content_research",
                "description": f"Research content for {content_item['content_type']} about {strategy['topic']}",
                "priority": content_item["priority"],
                "requirements": {
                    "topic": strategy["topic"],
                    "audience": strategy["target_audience"],
                    "themes": strategy["key_themes"],
                    "keywords": strategy["seo_strategy"]["primary_keywords"]
                }
            }
            
            # Content creation task
            creation_task = {
                "task_id": f"{content_id}_creation",
                "campaign_id": campaign_id,
                "content_id": content_id,
                "task_type": "content_creation",
                "description": f"Create {content_item['content_type']} content",
                "priority": content_item["priority"],
                "depends_on": [f"{content_id}_research"],
                "requirements": {
                    "content_type": content_item["content_type"],
                    "template": self.content_templates.get(content_item["content_type"], {}),
                    "seo_strategy": strategy["seo_strategy"]
                }
            }
            
            # Send task assignments
            await self.send_message(
                MessageType.TASK_ASSIGNMENT,
                research_task,
                channel="task_updates"
            )
            
            await self.send_message(
                MessageType.TASK_ASSIGNMENT,
                creation_task,
                channel="task_updates"
            )
            
            campaign["content_pieces"].extend([content_id])
            
        logger.info(f"📋 Planned {len(strategy['content_calendar'])} content pieces for campaign {campaign_id}")


class ResearchAgent(SmartAgentClient):
    """
    Specialized content research agent
    """
    
    def __init__(self, agent_id: str = "research_agent"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["research", "data_gathering", "trend_analysis", "fact_checking"],
            metadata={
                "type": "research_specialist",
                "data_sources": ["web_search", "industry_reports", "academic_papers"],
                "expertise": ["market_research", "competitive_analysis", "trend_identification"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process content research tasks"""
        logger.info(f"🔍 Research Agent processing: {description}")
        
        topic = requirements.get("topic", "unknown")
        themes = requirements.get("themes", [])
        keywords = requirements.get("keywords", [])
        
        result = await self._conduct_content_research(topic, themes, keywords)
        await self.report_task_completion(task_id, result)
        
    async def _conduct_content_research(self, topic: str, themes: List[str], keywords: List[str]) -> Dict[str, Any]:
        """Conduct comprehensive content research"""
        await asyncio.sleep(4)  # Simulate research time
        
        research_data = {
            "topic": topic,
            "key_statistics": await self._gather_statistics(topic),
            "trending_subtopics": await self._identify_trending_subtopics(topic),
            "competitor_analysis": await self._analyze_competitors(topic),
            "expert_quotes": await self._find_expert_quotes(topic),
            "case_studies": await self._find_case_studies(topic),
            "current_trends": await self._analyze_current_trends(topic),
            "data_sources": self._get_data_sources(),
            "research_confidence": 0.87,
            "last_updated": datetime.now().isoformat()
        }
        
        return {
            "type": "content_research",
            "topic": topic,
            "research_data": research_data,
            "actionable_insights": self._generate_insights(research_data),
            "content_angles": self._suggest_content_angles(topic, themes),
            "supporting_data": self._organize_supporting_data(research_data)
        }
        
    async def _gather_statistics(self, topic: str) -> List[Dict[str, Any]]:
        """Gather relevant statistics"""
        stats_templates = {
            "ai": [
                {"stat": "AI market size expected to reach $1.8T by 2030", "source": "McKinsey"},
                {"stat": "70% of companies will adopt AI by 2025", "source": "Gartner"},
                {"stat": "AI productivity gains of 40% possible", "source": "PwC"}
            ],
            "technology": [
                {"stat": "Digital transformation spending to reach $2.8T by 2025", "source": "IDC"},
                {"stat": "95% of businesses use cloud technology", "source": "Flexera"},
                {"stat": "Cybersecurity spending up 15% year-over-year", "source": "Cybersecurity Ventures"}
            ]
        }
        
        topic_lower = topic.lower()
        for key, stats in stats_templates.items():
            if key in topic_lower:
                return stats
                
        return [{"stat": f"{topic} adoption growing rapidly", "source": "Industry Research"}]
        
    async def _identify_trending_subtopics(self, topic: str) -> List[str]:
        """Identify trending subtopics"""
        return [
            f"{topic} automation",
            f"{topic} best practices", 
            f"future of {topic}",
            f"{topic} case studies",
            f"{topic} implementation"
        ]
        
    async def _analyze_competitors(self, topic: str) -> Dict[str, Any]:
        """Analyze competitor content"""
        return {
            "top_competitors": ["Industry Leader A", "Market Player B", "Innovation Co C"],
            "content_gaps": [f"Lack of beginner guides for {topic}", f"Limited case studies"],
            "opportunities": [f"In-depth {topic} tutorials", f"Practical implementation guides"]
        }
        
    async def _find_expert_quotes(self, topic: str) -> List[Dict[str, str]]:
        """Find relevant expert quotes"""
        return [
            {
                "quote": f"The future of {topic} lies in its practical application",
                "expert": "Dr. Jane Smith",
                "title": f"{topic} Research Director"
            }
        ]
        
    async def _find_case_studies(self, topic: str) -> List[Dict[str, Any]]:
        """Find relevant case studies"""
        return [
            {
                "title": f"Company X's successful {topic} implementation",
                "industry": "Technology",
                "results": f"300% improvement in {topic} metrics",
                "key_lessons": [f"{topic} requires careful planning", "User training is crucial"]
            }
        ]
        
    async def _analyze_current_trends(self, topic: str) -> List[str]:
        """Analyze current trends"""
        return [
            f"Increased focus on {topic} accessibility",
            f"{topic} integration with existing systems",
            f"Growing demand for {topic} expertise"
        ]
        
    def _get_data_sources(self) -> List[str]:
        """Get list of data sources used"""
        return ["Industry Reports", "Academic Research", "Market Analysis", "Expert Interviews"]
        
    def _generate_insights(self, research_data: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from research"""
        return [
            "Market shows strong growth potential",
            "Content should focus on practical implementation",
            "Audience seeks beginner-friendly explanations",
            "Case studies highly valued by readers"
        ]
        
    def _suggest_content_angles(self, topic: str, themes: List[str]) -> List[str]:
        """Suggest content angles based on research"""
        angles = [f"How to get started with {topic}"]
        
        for theme in themes:
            angles.append(f"{topic} and {theme}: A comprehensive guide")
            
        return angles
        
    def _organize_supporting_data(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Organize supporting data for content creation"""
        return {
            "key_points": research_data.get("trending_subtopics", []),
            "supporting_stats": research_data.get("key_statistics", []),
            "expert_validation": research_data.get("expert_quotes", []),
            "real_world_examples": research_data.get("case_studies", [])
        }


class ContentCreator(SmartAgentClient):
    """
    AI-powered content creation specialist
    """
    
    def __init__(self, agent_id: str = "content_creator"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["writing", "content_creation", "storytelling", "copywriting"],
            metadata={
                "type": "content_creator",
                "writing_styles": ["informative", "conversational", "technical", "persuasive"],
                "content_formats": ["blog_post", "article", "social_media", "email"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process content creation tasks"""
        logger.info(f"✍️ Content Creator processing: {description}")
        
        content_type = requirements.get("content_type", "blog_post")
        template = requirements.get("template", {})
        
        result = await self._create_content(content_type, template, requirements)
        await self.report_task_completion(task_id, result)
        
    async def _create_content(self, content_type: str, template: Dict[str, Any], 
                            requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create content based on requirements"""
        await asyncio.sleep(6)  # Simulate content creation time
        
        if content_type == "blog_post":
            content = await self._create_blog_post(template, requirements)
        elif content_type == "article":
            content = await self._create_article(template, requirements)
        elif content_type == "social_media":
            content = await self._create_social_media_post(template, requirements)
        else:
            content = await self._create_generic_content(template, requirements)
            
        return {
            "type": "content_creation",
            "content_type": content_type,
            "content": content,
            "word_count": content.get("word_count", 0),
            "readability_score": 8.5,
            "seo_elements": content.get("seo_elements", {}),
            "created_at": datetime.now().isoformat()
        }
        
    async def _create_blog_post(self, template: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create blog post content"""
        seo_strategy = requirements.get("seo_strategy", {})
        primary_keywords = seo_strategy.get("primary_keywords", [])
        
        # Simulate AI-generated content
        title = f"The Ultimate Guide to {primary_keywords[0].title() if primary_keywords else 'Your Topic'}"
        
        content_sections = {
            "title": title,
            "meta_description": f"Discover everything you need to know about {primary_keywords[0] if primary_keywords else 'this topic'}. Complete guide with examples and best practices.",
            "introduction": f"In today's rapidly evolving landscape, {primary_keywords[0] if primary_keywords else 'this topic'} has become increasingly important. This comprehensive guide will walk you through everything you need to know.",
            "main_content": [
                {
                    "heading": "Understanding the Basics",
                    "content": "Before diving into advanced concepts, it's crucial to understand the fundamental principles..."
                },
                {
                    "heading": "Best Practices and Implementation",
                    "content": "Based on industry research and expert recommendations, here are the key strategies..."
                },
                {
                    "heading": "Common Challenges and Solutions",
                    "content": "Many organizations face similar obstacles when implementing these concepts..."
                }
            ],
            "conclusion": "By following these guidelines and best practices, you'll be well-equipped to succeed in your implementation journey.",
            "call_to_action": "Ready to get started? Contact our experts for personalized guidance."
        }
        
        # Calculate word count
        word_count = sum(len(section.split()) for section in [
            content_sections["introduction"],
            content_sections["conclusion"],
            content_sections["call_to_action"]
        ])
        
        for section in content_sections["main_content"]:
            word_count += len(section["content"].split())
            
        content_sections["word_count"] = word_count
        content_sections["seo_elements"] = {
            "title_tag": title,
            "meta_description": content_sections["meta_description"],
            "keywords_used": primary_keywords,
            "internal_links": 3,
            "external_links": 2
        }
        
        return content_sections
        
    async def _create_article(self, template: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create article content"""
        return await self._create_blog_post(template, requirements)  # Similar process
        
    async def _create_social_media_post(self, template: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create social media content"""
        seo_strategy = requirements.get("seo_strategy", {})
        keywords = seo_strategy.get("primary_keywords", ["topic"])
        
        post_text = f"🚀 Unlock the power of {keywords[0]}! Did you know that companies using {keywords[0]} see 40% better results? Here's how to get started: [link] #business #growth #{keywords[0].replace(' ', '')}"
        
        return {
            "post_text": post_text,
            "word_count": len(post_text.split()),
            "character_count": len(post_text),
            "hashtags": [f"#{keyword.replace(' ', '')}" for keyword in keywords],
            "call_to_action": "Learn more",
            "seo_elements": {
                "hashtags": [f"#{keyword.replace(' ', '')}" for keyword in keywords],
                "mentions": [],
                "links": 1
            }
        }
        
    async def _create_generic_content(self, template: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create generic content"""
        return {
            "content": "High-quality content created based on your requirements.",
            "word_count": 200,
            "format": "generic"
        }


class ContentEditor(SmartAgentClient):
    """
    Editorial review and content enhancement specialist
    """
    
    def __init__(self, agent_id: str = "content_editor"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["editing", "proofreading", "content_enhancement", "style_guide"],
            metadata={
                "type": "editor",
                "editing_focus": ["grammar", "clarity", "engagement", "structure"],
                "style_expertise": ["AP", "Chicago", "MLA", "company_style"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process editorial review tasks"""
        logger.info(f"📝 Content Editor processing: {description}")
        
        # Simulate editorial process
        await asyncio.sleep(4)
        
        result = {
            "type": "editorial_review",
            "changes_made": [
                "Improved readability and flow",
                "Enhanced engaging headlines",
                "Strengthened call-to-action",
                "Corrected grammar and style issues"
            ],
            "quality_improvements": {
                "readability_score": 9.2,
                "engagement_score": 8.8,
                "grammar_score": 9.5,
                "seo_optimization": 8.7
            },
            "editor_notes": [
                "Content flows well and maintains reader interest",
                "SEO elements properly integrated",
                "Tone appropriate for target audience"
            ],
            "approval_status": "approved_with_minor_revisions"
        }
        
        await self.report_task_completion(task_id, result)


class SEOSpecialist(SmartAgentClient):
    """
    SEO optimization and search performance specialist
    """
    
    def __init__(self, agent_id: str = "seo_specialist"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["seo", "keyword_research", "search_optimization", "analytics"],
            metadata={
                "type": "seo_specialist",
                "seo_focus": ["on_page", "technical", "content", "performance"],
                "tools": ["google_analytics", "search_console", "keyword_tools"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process SEO optimization tasks"""
        logger.info(f"🔍 SEO Specialist processing: {description}")
        
        await asyncio.sleep(3)
        
        result = {
            "type": "seo_optimization",
            "optimizations_applied": [
                "Keyword density optimization",
                "Meta description enhancement", 
                "Internal linking structure",
                "Schema markup implementation",
                "Image alt-text optimization"
            ],
            "seo_scores": {
                "keyword_optimization": 92,
                "technical_seo": 89,
                "content_quality": 94,
                "user_experience": 87
            },
            "ranking_predictions": {
                "primary_keyword": "Expected top 10 ranking",
                "secondary_keywords": "Expected top 20 ranking",
                "long_tail_keywords": "Expected top 5 ranking"
            },
            "recommendations": [
                "Monitor ranking progress weekly",
                "Build quality backlinks",
                "Create supporting pillar content"
            ]
        }
        
        await self.report_task_completion(task_id, result)


async def run_content_creation_demo():
    """
    Demonstrate the content creation workflow
    """
    logger.info("🚀 Starting Content Creation Pipeline Demo")
    
    # Start infrastructure
    realtime_hub = RealtimeHub()
    
    # Start hub in background
    hub_task = asyncio.create_task(realtime_hub.start())
    await asyncio.sleep(2)  # Give hub time to start
    
    # Create and connect agents
    strategist = ContentStrategist()
    researcher = ResearchAgent()
    creator = ContentCreator()
    editor = ContentEditor()
    seo_specialist = SEOSpecialist()
    
    agents = [strategist, researcher, creator, editor, seo_specialist]
    
    try:
        # Connect all agents
        for agent in agents:
            await agent.connect()
            await agent.subscribe_to_channel("content_coordination")
            await agent.subscribe_to_channel("task_updates")
            
        logger.info("✅ All content agents connected and subscribed")
        
        # Wait for connections to stabilize
        await asyncio.sleep(3)
        
        # Start a content campaign
        campaign_config = {
            "title": "AI in Business Transformation",
            "topic": "artificial intelligence business applications",
            "target_audience": "professionals",
            "content_types": ["blog_post", "article"],
            "timeline_days": 14,
            "goals": {
                "target_traffic": 10000,
                "engagement_rate": 0.15,
                "conversion_rate": 0.05
            },
            "distribution_channels": ["blog", "linkedin", "newsletter"]
        }
        
        campaign_id = await strategist.start_content_campaign(campaign_config)
        
        # Monitor campaign progress
        logger.info("📊 Monitoring content creation progress...")
        
        # Let the workflow run
        await asyncio.sleep(25)  # Give time for tasks to complete
        
        # Check campaign status
        if campaign_id in strategist.active_campaigns:
            campaign = strategist.active_campaigns[campaign_id]
            logger.info(f"📈 Campaign Status: {campaign['status']}")
            logger.info(f"📋 Content Pieces: {len(campaign['content_pieces'])}")
            logger.info(f"✅ Completed Tasks: {len(campaign['results'])}")
            
        logger.info("🎉 Content Creation Pipeline Demo completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in content creation demo: {e}")
        raise
    finally:
        # Cleanup
        for agent in agents:
            await agent.disconnect()
        
        # Stop hub
        hub_task.cancel()
        try:
            await hub_task
        except asyncio.CancelledError:
            pass
            
        await realtime_hub.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(run_content_creation_demo())
    except KeyboardInterrupt:
        logger.info("⏹️ Content creation demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Content creation demo failed: {e}")
        raise