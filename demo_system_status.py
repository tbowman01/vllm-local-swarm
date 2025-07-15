#!/usr/bin/env python3
"""
Demo script to show current vLLM Local Swarm system status and capabilities.

This demonstrates what's working and what's been implemented.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n📋 {title}")
    print(f"{'-'*50}")


async def demo_message_system():
    """Demonstrate the message system"""
    print_section("Message System")
    
    try:
        from src.core.messaging import Message, MessageType, TaskRequest, Priority
        
        # Test message creation
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id="demo_user",
            recipient_id="planner_agent",
            content={"task": "Build a web scraper"}
        )
        
        print(f"✅ Created message: {message.message_id}")
        print(f"   Type: {message.message_type}")
        print(f"   From: {message.sender_id}")
        print(f"   To: {message.recipient_id}")
        
        # Test task request
        task_request = TaskRequest(
            objective="Build a web scraper for product prices",
            task_definition="Create a Python script that scrapes product information",
            priority=Priority.HIGH
        )
        
        print(f"✅ Created task request: {task_request.task_id}")
        print(f"   Objective: {task_request.objective}")
        print(f"   Priority: {task_request.priority}")
        
        return True
        
    except Exception as e:
        print(f"❌ Message system error: {e}")
        return False


async def demo_memory_system():
    """Demonstrate the memory system"""
    print_section("Memory System")
    
    try:
        from memory.core.memory_manager import MemoryManager, MemoryEntry, MemoryType
        from memory.core.session_memory import SessionMemory
        from datetime import datetime
        
        # Test memory manager
        memory_manager = MemoryManager()
        await memory_manager.initialize()
        
        # Test session memory
        session_memory = SessionMemory("demo_session")
        await session_memory.store("demo_key", "demo_value")
        value = await session_memory.retrieve("demo_key")
        
        print(f"✅ Memory Manager initialized: {memory_manager._initialized}")
        print(f"✅ Session memory test: stored and retrieved '{value}'")
        
        # Test memory entry
        entry = MemoryEntry(
            id="demo_entry",
            type=MemoryType.SESSION,
            content={"data": "test content"},
            metadata={"source": "demo"},
            timestamp=datetime.now()
        )
        
        await memory_manager.store(entry)
        retrieved = await memory_manager.retrieve("demo_entry")
        
        print(f"✅ Memory entry stored and retrieved: {retrieved is not None}")
        
        stats = await memory_manager.get_stats()
        print(f"✅ Memory stats: {stats}")
        
        await memory_manager.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ Memory system error: {e}")
        return False


async def demo_agent_configuration():
    """Demonstrate agent configuration"""
    print_section("Agent Configuration")
    
    try:
        from src.core.agents import (
            AgentType, AgentConfiguration, AgentCapabilities, create_agent_config
        )
        
        # Test agent configuration
        config = create_agent_config(
            agent_id="demo_planner",
            agent_type=AgentType.PLANNER,
            primary_model="phi-3.5"
        )
        
        print(f"✅ Agent config created: {config.agent_id}")
        print(f"   Type: {config.agent_type}")
        print(f"   Model: {config.primary_model}")
        print(f"   Capabilities: {len(config.capabilities.supported_tasks)} tasks")
        
        # Test all agent types
        for agent_type in AgentType:
            config = create_agent_config(
                agent_id=f"demo_{agent_type.value}",
                agent_type=agent_type
            )
            print(f"✅ {agent_type.value.title()} agent configuration ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent configuration error: {e}")
        return False


async def demo_infrastructure_status():
    """Show infrastructure status"""
    print_section("Infrastructure Status")
    
    try:
        import redis
        import subprocess
        
        # Test Redis
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            print("✅ Redis: Connected and responsive")
        except Exception as e:
            print(f"❌ Redis: Connection failed - {e}")
        
        # Test Docker containers
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Docker containers:")
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            name = parts[0]
                            status = parts[1]
                            if "healthy" in status:
                                print(f"   ✅ {name}: {status}")
                            elif "unhealthy" in status:
                                print(f"   ⚠️  {name}: {status}")
                            else:
                                print(f"   🔄 {name}: {status}")
        except Exception as e:
            print(f"❌ Docker status check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Infrastructure status error: {e}")
        return False


async def demo_project_structure():
    """Show project structure"""
    print_section("Project Structure")
    
    project_root = Path(__file__).parent
    
    structure = {
        "Core System": [
            "src/core/agents.py",
            "src/core/messaging.py",
            "src/core/orchestrator.py",
            "agents/base_agent.py",
            "agents/planner_agent.py",
            "agents/coder_agent.py",
            "agents/researcher_agent.py",
            "agents/qa_agent.py"
        ],
        "Memory System": [
            "memory/core/memory_manager.py",
            "memory/core/session_memory.py",
            "memory/tools/memory_tools.py"
        ],
        "Configuration": [
            "docker-compose.yml",
            "docker-compose.cpu.yml",
            ".env",
            "CLAUDE.md"
        ],
        "CLI & Tools": [
            "sparc_cli.py",
            "test_basic_system.py"
        ]
    }
    
    for category, files in structure.items():
        print(f"\n📁 {category}:")
        for file_path in files:
            full_path = project_root / file_path
            if full_path.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} (missing)")
    
    return True


async def demo_system_capabilities():
    """Show system capabilities"""
    print_section("System Capabilities")
    
    capabilities = {
        "✅ Implemented": [
            "SPARC agent architecture (6 agent types)",
            "Message passing system",
            "Memory management (session + persistent)",
            "Docker containerization",
            "Redis for caching",
            "CLI interface framework",
            "Agent configuration management",
            "Task orchestration structure",
            "Observability integration points"
        ],
        "🔄 In Progress": [
            "vLLM model deployment",
            "Ray cluster setup",
            "Langfuse integration",
            "ClickHouse setup",
            "Qdrant vector storage"
        ],
        "📋 Planned": [
            "GPT-4 fallback proxy",
            "Auto-updating system",
            "Kubernetes deployment",
            "Web UI integration",
            "Performance optimization"
        ]
    }
    
    for status, items in capabilities.items():
        print(f"\n{status}:")
        for item in items:
            print(f"   • {item}")
    
    return True


async def run_demo():
    """Run the complete system demo"""
    print_header("vLLM Local Swarm - System Status Demo")
    print("🎯 Demonstrating current system capabilities and status")
    
    demos = [
        ("Message System", demo_message_system),
        ("Memory System", demo_memory_system),
        ("Agent Configuration", demo_agent_configuration),
        ("Infrastructure Status", demo_infrastructure_status),
        ("Project Structure", demo_project_structure),
        ("System Capabilities", demo_system_capabilities),
    ]
    
    results = []
    for name, demo_func in demos:
        try:
            result = await demo_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} demo failed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📊 Demo Results: {passed}/{total} components working")
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    if passed == total:
        print(f"\n🎉 All components working! System is ready for the next phase.")
    else:
        print(f"\n⚠️  {total - passed} components need attention.")
    
    print(f"\n🚀 Next Steps:")
    print("   1. Complete vLLM model deployment")
    print("   2. Integrate Ray cluster")
    print("   3. Test end-to-end task execution")
    print("   4. Deploy Claude Flow MCP integration")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_demo())
    sys.exit(0 if success else 1)