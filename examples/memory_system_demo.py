#!/usr/bin/env python3
"""
Memory System Demonstration

Shows how to use the complete memory and observability system with agents.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

from memory.core import MemoryManager, MemoryConfig, MemoryEntry, MemoryType
from memory.tools import MemoryTool, CoordinationTool, AnalyticsTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemoAgent:
    """Demo agent that uses the memory system."""
    
    def __init__(self, agent_id: str, memory_manager: MemoryManager):
        self.agent_id = agent_id
        self.memory_tool = MemoryTool(memory_manager, agent_id)
        self.coordination_tool = CoordinationTool(memory_manager, agent_id)
        self.session_id = None
    
    def set_session(self, session_id: str):
        """Set session for this agent."""
        self.session_id = session_id
        self.memory_tool.set_session(session_id)
        self.coordination_tool.set_session(session_id)
    
    async def perform_task(self, task_description: str) -> Dict[str, Any]:
        """Perform a task and store the results in memory."""
        logger.info(f"Agent {self.agent_id} starting task: {task_description}")
        
        # Store task in context
        await self.memory_tool.store_context(
            {
                "task": task_description,
                "status": "started",
                "start_time": datetime.utcnow().isoformat()
            },
            "task_state"
        )
        
        # Simulate some work
        await asyncio.sleep(1)
        
        # Generate results
        result = {
            "task": task_description,
            "result": f"Completed by {self.agent_id}",
            "success": True,
            "completion_time": datetime.utcnow().isoformat()
        }
        
        # Store results in semantic memory for future reference
        await self.memory_tool.store_knowledge(
            result,
            f"Task completion: {task_description}",
            tags=["task_completion", "success"]
        )
        
        # Update task context
        await self.memory_tool.store_context(
            {
                "task": task_description,
                "status": "completed",
                "result": result,
                "end_time": datetime.utcnow().isoformat()
            },
            "task_state"
        )
        
        # Learn from the interaction
        await self.memory_tool.learn_from_interaction(
            {"task": task_description, "agent": self.agent_id},
            "successful_completion",
            0.9  # High effectiveness score
        )
        
        logger.info(f"Agent {self.agent_id} completed task: {task_description}")
        return result
    
    async def collaborate_with_agent(self, target_agent_id: str, task_data: Dict[str, Any]):
        """Collaborate with another agent via handoff."""
        logger.info(f"Agent {self.agent_id} handing off to {target_agent_id}")
        
        # Create handoff
        handoff_id = await self.coordination_tool.handoff_to_agent(
            target_agent_id,
            task_data,
            "task_delegation",
            "normal"
        )
        
        # Broadcast status
        await self.coordination_tool.broadcast_status(
            "delegating",
            {"handoff_id": handoff_id, "target_agent": target_agent_id}
        )
        
        return handoff_id
    
    async def handle_handoffs(self):
        """Check for and handle pending handoffs."""
        pending = await self.coordination_tool.get_pending_handoffs()
        
        for handoff in pending:
            logger.info(f"Agent {self.agent_id} accepting handoff {handoff['handoff_id']}")
            
            # Accept the handoff
            await self.coordination_tool.accept_handoff(
                handoff["handoff_id"],
                f"Accepted by {self.agent_id}"
            )
            
            # Process the task
            task_data = handoff["task_data"]
            result = await self.perform_task(task_data.get("description", "Delegated task"))
            
            # Complete the handoff
            await self.coordination_tool.complete_handoff(
                handoff["handoff_id"],
                result,
                f"Completed by {self.agent_id}"
            )
    
    async def share_knowledge(self, knowledge_key: str, knowledge_data: Any):
        """Share knowledge with other agents."""
        await self.coordination_tool.share_context(
            knowledge_key,
            knowledge_data,
            "session"
        )
        
        logger.info(f"Agent {self.agent_id} shared knowledge: {knowledge_key}")
    
    async def get_relevant_knowledge(self, query: str):
        """Get relevant knowledge from memory."""
        knowledge = await self.memory_tool.retrieve_knowledge(query, limit=3)
        
        if knowledge:
            logger.info(f"Agent {self.agent_id} found {len(knowledge)} relevant knowledge entries")
            for entry in knowledge:
                logger.info(f"  - {entry['description']} (similarity: {entry['similarity_score']:.2f})")
        
        return knowledge


async def demonstrate_memory_system():
    """Demonstrate the complete memory system functionality."""
    logger.info("Starting Memory System Demonstration")
    
    try:
        # Initialize memory system
        config = MemoryConfig.from_env()
        memory_manager = MemoryManager(config)
        await memory_manager.initialize()
        
        # Create demo agents
        agent1 = DemoAgent("researcher", memory_manager)
        agent2 = DemoAgent("analyst", memory_manager)
        agent3 = DemoAgent("coordinator", memory_manager)
        
        # Set up session
        session_id = f"demo_session_{int(datetime.utcnow().timestamp())}"
        for agent in [agent1, agent2, agent3]:
            agent.set_session(session_id)
        
        logger.info(f"Demo session: {session_id}")
        
        # --- Phase 1: Basic Memory Operations ---
        logger.info("\n=== Phase 1: Basic Memory Operations ===")
        
        # Agent 1 performs tasks and stores knowledge
        await agent1.perform_task("Research market trends for Q4")
        await agent1.perform_task("Analyze competitor strategies")
        
        # Agent 1 shares knowledge
        await agent1.share_knowledge(
            "market_insights",
            {
                "trend": "upward",
                "key_factors": ["innovation", "customer_demand"],
                "confidence": 0.85
            }
        )
        
        # Agent 2 retrieves relevant knowledge
        knowledge = await agent2.get_relevant_knowledge("market trends analysis")
        
        # --- Phase 2: Agent Coordination ---
        logger.info("\n=== Phase 2: Agent Coordination ===")
        
        # Agent 1 delegates task to Agent 2
        handoff_id = await agent1.collaborate_with_agent(
            "analyst",
            {
                "description": "Create detailed analysis report",
                "context": "Based on research findings",
                "priority": "high"
            }
        )
        
        # Agent 2 handles the handoff
        await agent2.handle_handoffs()
        
        # Agent 3 coordinates between agents
        await agent3.perform_task("Review coordination between research and analysis teams")
        
        # Get shared context
        shared_contexts = await agent3.coordination_tool.get_shared_context()
        logger.info(f"Found {len(shared_contexts)} shared contexts")
        
        # --- Phase 3: Analytics and Insights ---
        logger.info("\n=== Phase 3: Analytics and Insights ===")
        
        analytics_tool = AnalyticsTool(memory_manager)
        
        # Analyze each agent's performance
        for agent in [agent1, agent2, agent3]:
            analysis = await analytics_tool.analyze_agent_performance(agent.agent_id)
            logger.info(f"\nAgent {agent.agent_id} Performance:")
            logger.info(f"  Total Activities: {analysis['total_activities']}")
            logger.info(f"  Memory Usage: {analysis['memory_usage']}")
            logger.info(f"  Coordination: {analysis['coordination_metrics']}")
        
        # Analyze coordination patterns
        coordination_analysis = await analytics_tool.analyze_coordination_patterns(session_id)
        logger.info(f"\nCoordination Analysis:")
        logger.info(f"  Total Events: {coordination_analysis['total_coordination_events']}")
        logger.info(f"  Handoffs: {coordination_analysis['handoff_analysis']}")
        
        # Analyze memory usage
        memory_analysis = await analytics_tool.analyze_memory_usage()
        logger.info(f"\nMemory Usage Analysis:")
        logger.info(f"  Distribution: {memory_analysis['memory_type_distribution']}")
        logger.info(f"  Popular Tags: {list(memory_analysis['popular_tags'].keys())[:5]}")
        
        # Analyze learning effectiveness
        learning_analysis = await analytics_tool.analyze_learning_effectiveness()
        logger.info(f"\nLearning Analysis:")
        logger.info(f"  Total Learning Events: {learning_analysis['total_learning_events']}")
        logger.info(f"  Avg Effectiveness: {learning_analysis['effectiveness_metrics']['avg_effectiveness']:.2f}")
        
        # Generate system health report
        health_report = await analytics_tool.generate_system_health_report()
        logger.info(f"\nSystem Health: {health_report['summary']['overall_health']}")
        logger.info(f"  Issues: {health_report['summary']['critical_issues']} critical, {health_report['summary']['warnings']} warnings")
        logger.info(f"  Recommendations: {health_report['summary']['recommendations']}")
        
        # --- Phase 4: Advanced Features ---
        logger.info("\n=== Phase 4: Advanced Features ===")
        
        # Demonstrate learning and knowledge reuse
        await agent1.perform_task("Research market trends for Q1 next year")
        relevant_learnings = await agent1.memory_tool.get_relevant_learnings(
            "market trends research",
            min_effectiveness=0.7
        )
        
        logger.info(f"Found {len(relevant_learnings)} relevant past learnings")
        
        # Demonstrate memory search across types
        search_results = await agent2.memory_tool.search_memory(
            "market analysis",
            tags=["task_completion"],
            limit=5
        )
        
        logger.info(f"Found {len(search_results)} entries matching 'market analysis'")
        
        # Demonstrate agent state persistence
        await agent3.memory_tool.store_agent_state(
            {
                "current_focus": "coordination",
                "active_tasks": ["monitoring", "reporting"],
                "preferences": {"communication_style": "detailed"}
            },
            "current"
        )
        
        # Retrieve agent state
        state = await agent3.memory_tool.retrieve_agent_state("current")
        logger.info(f"Agent 3 state: {state}")
        
        # Get memory summaries
        for agent in [agent1, agent2, agent3]:
            summary = await agent.memory_tool.get_my_memory_summary()
            logger.info(f"\nAgent {agent.agent_id} Memory Summary:")
            logger.info(f"  Session Entries: {len(summary['session_entries'])}")
            logger.info(f"  Semantic Entries: {len(summary['semantic_entries'])}")
            logger.info(f"  Knowledge Count: {summary['knowledge_count']}")
        
        logger.info("\n=== Memory System Demonstration Complete ===")
        
        # Final system stats
        final_stats = await memory_manager.get_system_stats()
        logger.info(f"Final System Stats: {json.dumps(final_stats, indent=2, default=str)}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        # Cleanup
        if 'memory_manager' in locals():
            await memory_manager.shutdown()


async def demonstrate_observability():
    """Demonstrate observability features."""
    logger.info("\n=== Observability Demonstration ===")
    
    config = MemoryConfig.from_env()
    memory_manager = MemoryManager(config)
    await memory_manager.initialize()
    
    try:
        # Get observability manager
        obs = memory_manager.observability
        
        if obs:
            # Log various trace types
            trace_id = await obs.start_trace("demo_workflow", agent_id="demo_agent")
            
            await obs.log_agent_action(
                "demo_agent",
                "process_data",
                {"input": "sample data"},
                {"output": "processed result"},
                1500.0,  # 1.5 seconds
                session_id="demo_session"
            )
            
            await obs.log_llm_call(
                "demo_agent",
                "gpt-4",
                "Analyze this data",
                "Here's the analysis...",
                150,  # tokens
                2300.0,  # 2.3 seconds
                session_id="demo_session"
            )
            
            await obs.end_trace(trace_id, "completed", {"success": True})
            
            # Get metrics
            agent_metrics = await obs.get_agent_metrics("demo_agent")
            logger.info(f"Agent Metrics: {agent_metrics}")
            
            system_metrics = await obs.get_system_metrics()
            logger.info(f"System Metrics: {system_metrics}")
            
            # Get improvement insights
            insights = await obs.get_improvement_insights()
            logger.info(f"Improvement Insights: {len(insights)} found")
            for insight in insights[:3]:  # Show first 3
                logger.info(f"  - {insight['type']}: {insight['description']}")
        
    finally:
        await memory_manager.shutdown()


if __name__ == "__main__":
    # Run the demonstrations
    asyncio.run(demonstrate_memory_system())
    asyncio.run(demonstrate_observability())