#!/usr/bin/env python3
"""
Research & Analysis Pipeline Workflow
=====================================

Demonstrates a sophisticated multi-agent research workflow with:
- Intelligent task routing and agent specialization
- Real-time coordination and progress tracking
- Memory-persistent learning and context sharing
- Automated report generation and quality control

Workflow Steps:
1. Research Coordinator receives research request
2. Research tasks distributed to specialist agents
3. Data analysis performed in parallel
4. Results synthesized and quality-checked
5. Final report generated and delivered

Agents Involved:
- Research Coordinator: Orchestrates the entire workflow
- Research Specialist: Conducts specific research tasks
- Data Analyst: Processes and analyzes collected data  
- Quality Controller: Validates research quality
- Report Writer: Creates final comprehensive reports
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from agents.communication import (
    RealtimeHub, AgentClient, ConnectionConfig, 
    AgentRole, MessageType
)
from agents.coordination.task_router import (
    TaskRouter, Task, TaskRequirements, TaskPriority, 
    AgentCapability, AgentProfile
)
from agents.communication.integration import SmartAgentClient

logger = logging.getLogger(__name__)


class ResearchCoordinator(SmartAgentClient):
    """
    Coordinates the entire research pipeline workflow
    """
    
    def __init__(self):
        config = ConnectionConfig(
            agent_id="research_coordinator",
            role=AgentRole.COORDINATOR,
            capabilities=["coordination", "planning", "quality_control"],
            metadata={
                "type": "coordinator",
                "workflow": "research_pipeline",
                "version": "1.0.0"
            }
        )
        super().__init__(config, auto_accept_tasks=False)
        
        self.active_research_projects: Dict[str, Dict[str, Any]] = {}
        self.research_progress: Dict[str, Dict[str, Any]] = {}
        
    async def start_research_project(self, project_config: Dict[str, Any]) -> str:
        """Start a new research project"""
        project_id = f"research_project_{int(datetime.now().timestamp())}"
        
        self.active_research_projects[project_id] = {
            "config": project_config,
            "started_at": datetime.now().isoformat(),
            "status": "planning",
            "tasks": [],
            "results": {}
        }
        
        logger.info(f"🚀 Starting research project: {project_config.get('title', project_id)}")
        
        # Create research plan
        research_plan = await self._create_research_plan(project_config)
        
        # Distribute tasks to agents
        await self._distribute_research_tasks(project_id, research_plan)
        
        return project_id
        
    async def _create_research_plan(self, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed research plan from project configuration"""
        
        topic = project_config.get("topic", "Unknown")
        scope = project_config.get("scope", "general")
        depth = project_config.get("depth", "medium")  # shallow, medium, deep
        
        # Define research tasks based on configuration
        research_tasks = []
        
        if depth in ["medium", "deep"]:
            research_tasks.extend([
                {
                    "task_type": "literature_review",
                    "description": f"Conduct comprehensive literature review on {topic}",
                    "priority": "high",
                    "estimated_time": 30,
                    "required_capabilities": ["research", "analysis"]
                },
                {
                    "task_type": "data_collection", 
                    "description": f"Collect relevant data and statistics for {topic}",
                    "priority": "high",
                    "estimated_time": 25,
                    "required_capabilities": ["research", "data_analysis"]
                }
            ])
            
        if depth == "deep":
            research_tasks.extend([
                {
                    "task_type": "expert_analysis",
                    "description": f"Analyze expert opinions and case studies on {topic}",
                    "priority": "medium",
                    "estimated_time": 20,
                    "required_capabilities": ["analysis", "reasoning"]
                },
                {
                    "task_type": "trend_analysis",
                    "description": f"Identify trends and patterns related to {topic}",
                    "priority": "medium", 
                    "estimated_time": 15,
                    "required_capabilities": ["analysis", "math"]
                }
            ])
            
        # Always include synthesis and report generation
        research_tasks.extend([
            {
                "task_type": "synthesis",
                "description": f"Synthesize research findings on {topic}",
                "priority": "high",
                "estimated_time": 20,
                "required_capabilities": ["analysis", "reasoning", "writing"],
                "depends_on": ["literature_review", "data_collection"]
            },
            {
                "task_type": "report_generation",
                "description": f"Generate comprehensive research report on {topic}",
                "priority": "critical",
                "estimated_time": 30,
                "required_capabilities": ["writing", "analysis"],
                "depends_on": ["synthesis"]
            }
        ])
        
        return {
            "topic": topic,
            "scope": scope,
            "depth": depth,
            "total_tasks": len(research_tasks),
            "estimated_duration": sum(task["estimated_time"] for task in research_tasks),
            "tasks": research_tasks
        }
        
    async def _distribute_research_tasks(self, project_id: str, research_plan: Dict[str, Any]):
        """Distribute research tasks to appropriate agents"""
        
        project = self.active_research_projects[project_id]
        project["status"] = "active"
        
        # Send research coordination message
        await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {
                "event": "research_project_started",
                "project_id": project_id,
                "plan": research_plan,
                "coordinator": self.config.agent_id
            },
            channel="research_coordination"
        )
        
        # Create individual task assignments
        for task_config in research_plan["tasks"]:
            task_id = f"{project_id}_{task_config['task_type']}"
            
            # Convert to task assignment message
            task_data = {
                "task_id": task_id,
                "project_id": project_id,
                "task_type": task_config["task_type"],
                "description": task_config["description"],
                "priority": task_config["priority"],
                "estimated_time": task_config["estimated_time"],
                "required_capabilities": task_config["required_capabilities"],
                "depends_on": task_config.get("depends_on", []),
                "deadline": None,  # Could calculate based on estimated_time
                "context": {
                    "topic": research_plan["topic"],
                    "scope": research_plan["scope"]
                }
            }
            
            # Send task assignment
            await self.send_message(
                MessageType.TASK_ASSIGNMENT,
                task_data,
                channel="task_updates"
            )
            
            project["tasks"].append(task_id)
            
        logger.info(f"📋 Distributed {len(research_plan['tasks'])} tasks for project {project_id}")
        
    async def handle_task_completion(self, message_data: Dict[str, Any]):
        """Handle completion of research tasks"""
        data = message_data.get("data", {})
        task_id = data.get("task_id")
        project_id = data.get("project_id")
        result = data.get("result", {})
        
        if project_id not in self.active_research_projects:
            return
            
        project = self.active_research_projects[project_id]
        project["results"][task_id] = result
        
        logger.info(f"✅ Task {task_id} completed for project {project_id}")
        
        # Check if all tasks are complete
        completed_tasks = len(project["results"])
        total_tasks = len(project["tasks"])
        
        if completed_tasks == total_tasks:
            await self._finalize_research_project(project_id)
            
    async def _finalize_research_project(self, project_id: str):
        """Finalize completed research project"""
        project = self.active_research_projects[project_id]
        project["status"] = "completed"
        project["completed_at"] = datetime.now().isoformat()
        
        # Generate final summary
        summary = {
            "project_id": project_id,
            "title": project["config"].get("title", "Research Project"),
            "duration": "calculated_duration",
            "tasks_completed": len(project["results"]),
            "results_summary": "Comprehensive research completed successfully"
        }
        
        # Broadcast completion
        await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {
                "event": "research_project_completed", 
                "project_id": project_id,
                "summary": summary
            },
            channel="research_coordination"
        )
        
        logger.info(f"🎉 Research project {project_id} completed successfully!")


class ResearchSpecialist(SmartAgentClient):
    """
    Specialized agent for conducting research tasks
    """
    
    def __init__(self, agent_id: str = "research_specialist"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["research", "analysis", "data_collection"],
            metadata={
                "type": "research_specialist",
                "specialization": "academic_research",
                "expertise_areas": ["literature_review", "data_collection", "source_analysis"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process research-specific tasks"""
        logger.info(f"🔍 Research Specialist processing: {description}")
        
        task_type = requirements.get("task_type", "general_research")
        topic = requirements.get("context", {}).get("topic", "unknown")
        
        # Simulate different types of research
        if task_type == "literature_review":
            result = await self._conduct_literature_review(topic)
        elif task_type == "data_collection":
            result = await self._collect_data(topic)
        else:
            result = await self._general_research(topic, description)
            
        await self.report_task_completion(task_id, result)
        
    async def _conduct_literature_review(self, topic: str) -> Dict[str, Any]:
        """Simulate literature review process"""
        await asyncio.sleep(5)  # Simulate research time
        
        return {
            "type": "literature_review",
            "topic": topic,
            "sources_reviewed": 25,
            "key_findings": [
                f"Recent advances in {topic} show significant promise",
                f"Current research gaps identified in {topic} methodology",
                f"Emerging trends suggest new directions for {topic} applications"
            ],
            "recommendations": [
                f"Further investigation needed in {topic} implementation",
                f"Collaborative research opportunities in {topic} domain"
            ],
            "confidence_score": 0.85
        }
        
    async def _collect_data(self, topic: str) -> Dict[str, Any]:
        """Simulate data collection process"""
        await asyncio.sleep(4)  # Simulate data gathering time
        
        return {
            "type": "data_collection",
            "topic": topic,
            "data_points": 150,
            "sources": ["academic_papers", "industry_reports", "case_studies"],
            "data_quality": "high",
            "coverage": "comprehensive",
            "insights": [
                f"Market size for {topic} estimated at $X billion",
                f"Growth rate of {topic} industry at Y% annually",
                f"Key players in {topic} space identified"
            ],
            "confidence_score": 0.90
        }
        
    async def _general_research(self, topic: str, description: str) -> Dict[str, Any]:
        """General research processing"""
        await asyncio.sleep(3)
        
        return {
            "type": "general_research",
            "topic": topic,
            "description": description,
            "findings": f"Research completed for {topic}",
            "methodology": "comprehensive_analysis",
            "confidence_score": 0.80
        }


class DataAnalyst(SmartAgentClient):
    """
    Specialized agent for data analysis tasks
    """
    
    def __init__(self, agent_id: str = "data_analyst"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["analysis", "data_analysis", "math", "reasoning"],
            metadata={
                "type": "data_analyst",
                "specialization": "quantitative_analysis",
                "tools": ["statistical_analysis", "trend_detection", "pattern_recognition"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process data analysis tasks"""
        logger.info(f"📊 Data Analyst processing: {description}")
        
        task_type = requirements.get("task_type", "general_analysis")
        
        if task_type == "trend_analysis":
            result = await self._analyze_trends(requirements)
        elif task_type == "expert_analysis":
            result = await self._analyze_expert_opinions(requirements)
        else:
            result = await self._general_analysis(requirements)
            
        await self.report_task_completion(task_id, result)
        
    async def _analyze_trends(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends and patterns"""
        await asyncio.sleep(3)
        
        topic = requirements.get("context", {}).get("topic", "unknown")
        
        return {
            "type": "trend_analysis", 
            "topic": topic,
            "trends_identified": [
                f"Increasing adoption of {topic} technology",
                f"Shift towards {topic}-based solutions",
                f"Growing investment in {topic} research"
            ],
            "patterns": [
                "Seasonal fluctuations observed",
                "Geographic concentration in developed markets",
                "Technology maturity curve progression"
            ],
            "predictions": [
                f"{topic} market expected to double in 3 years",
                "Breakthrough innovations likely within 18 months"
            ],
            "confidence_score": 0.88
        }
        
    async def _analyze_expert_opinions(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze expert opinions and case studies"""
        await asyncio.sleep(4)
        
        return {
            "type": "expert_analysis",
            "experts_consulted": 15,
            "case_studies_analyzed": 8,
            "consensus_points": [
                "Technology shows significant promise",
                "Implementation challenges are surmountable",
                "Market timing appears favorable"
            ],
            "dissenting_opinions": [
                "Regulatory concerns need addressing",
                "Scalability questions remain"
            ],
            "confidence_score": 0.82
        }
        
    async def _general_analysis(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """General data analysis"""
        await asyncio.sleep(2)
        
        return {
            "type": "general_analysis",
            "methodology": "comprehensive_statistical_analysis",
            "key_metrics": {
                "sample_size": 1000,
                "confidence_interval": "95%",
                "p_value": 0.01
            },
            "findings": "Statistically significant results obtained",
            "confidence_score": 0.87
        }


class ReportWriter(SmartAgentClient):
    """
    Specialized agent for report writing and synthesis
    """
    
    def __init__(self, agent_id: str = "report_writer"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["writing", "analysis", "reasoning", "synthesis"],
            metadata={
                "type": "report_writer",
                "specialization": "research_reports",
                "formats": ["executive_summary", "technical_report", "presentation"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process report writing tasks"""
        logger.info(f"📝 Report Writer processing: {description}")
        
        task_type = requirements.get("task_type", "general_writing")
        
        if task_type == "synthesis":
            result = await self._synthesize_findings(requirements)
        elif task_type == "report_generation":
            result = await self._generate_report(requirements)
        else:
            result = await self._general_writing(requirements)
            
        await self.report_task_completion(task_id, result)
        
    async def _synthesize_findings(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize research findings from multiple sources"""
        await asyncio.sleep(4)
        
        topic = requirements.get("context", {}).get("topic", "research topic")
        
        return {
            "type": "synthesis",
            "topic": topic,
            "sources_integrated": 4,
            "key_insights": [
                f"Convergent evidence supports {topic} viability",
                f"Multiple methodologies confirm {topic} effectiveness",
                f"Cross-domain applications of {topic} identified"
            ],
            "synthesis_summary": f"Comprehensive analysis of {topic} reveals strong potential with manageable risks",
            "recommendations": [
                "Proceed with pilot implementation",
                "Monitor key performance indicators",
                "Establish feedback mechanisms"
            ],
            "confidence_score": 0.91
        }
        
    async def _generate_report(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive research report"""
        await asyncio.sleep(6)
        
        topic = requirements.get("context", {}).get("topic", "research topic")
        
        return {
            "type": "comprehensive_report",
            "title": f"Research Analysis Report: {topic}",
            "sections": [
                "Executive Summary",
                "Literature Review",
                "Data Analysis",
                "Findings & Insights", 
                "Recommendations",
                "Conclusion"
            ],
            "page_count": 25,
            "format": "professional_report",
            "quality_score": 0.93,
            "readability": "executive_level",
            "deliverables": [
                "Full report document",
                "Executive summary",
                "Key findings presentation"
            ]
        }
        
    async def _general_writing(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """General writing tasks"""
        await asyncio.sleep(3)
        
        return {
            "type": "general_writing",
            "content_created": "Professional documentation",
            "word_count": 2500,
            "quality_score": 0.85
        }


async def run_research_pipeline_demo():
    """
    Demonstrate the research pipeline workflow
    """
    logger.info("🚀 Starting Research Pipeline Demo")
    
    # Start infrastructure (in production, this would already be running)
    realtime_hub = RealtimeHub()
    
    # Start hub in background
    hub_task = asyncio.create_task(realtime_hub.start())
    await asyncio.sleep(2)  # Give hub time to start
    
    # Create and connect agents
    coordinator = ResearchCoordinator()
    research_specialist = ResearchSpecialist()
    data_analyst = DataAnalyst()
    report_writer = ReportWriter()
    
    agents = [coordinator, research_specialist, data_analyst, report_writer]
    
    try:
        # Connect all agents
        for agent in agents:
            await agent.connect()
            await agent.subscribe_to_channel("research_coordination")
            await agent.subscribe_to_channel("task_updates")
            
        logger.info("✅ All agents connected and subscribed")
        
        # Register task completion handler for coordinator
        coordinator.register_message_handler(
            MessageType.TASK_COMPLETION,
            coordinator.handle_task_completion
        )
        
        # Wait for connections to stabilize
        await asyncio.sleep(3)
        
        # Start a research project
        project_config = {
            "title": "Artificial Intelligence in Healthcare",
            "topic": "AI medical diagnostics",
            "scope": "comprehensive",
            "depth": "deep",
            "deadline": "2024-02-15",
            "stakeholders": ["medical_professionals", "ai_researchers", "healthcare_administrators"]
        }
        
        project_id = await coordinator.start_research_project(project_config)
        
        # Monitor workflow progress
        logger.info("📊 Monitoring research pipeline progress...")
        
        # Let the workflow run
        await asyncio.sleep(30)  # Give time for tasks to complete
        
        # Check project status
        if project_id in coordinator.active_research_projects:
            project = coordinator.active_research_projects[project_id]
            logger.info(f"📈 Project Status: {project['status']}")
            logger.info(f"📋 Tasks Completed: {len(project['results'])}/{len(project['tasks'])}")
            
            # Display some results
            for task_id, result in project["results"].items():
                logger.info(f"✅ {task_id}: {result.get('type', 'unknown')} - Confidence: {result.get('confidence_score', 'N/A')}")
                
        logger.info("🎉 Research Pipeline Demo completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in research pipeline demo: {e}")
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
        asyncio.run(run_research_pipeline_demo())
    except KeyboardInterrupt:
        logger.info("⏹️ Research pipeline demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Research pipeline demo failed: {e}")
        raise