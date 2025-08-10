# 🤖 Agent Workflow Examples

This directory contains example workflows demonstrating the capabilities of the vLLM Local Swarm agent coordination system.

## 🌟 Featured Workflows

### 1. Research & Analysis Pipeline
- **File**: `research_pipeline.py`
- **Description**: Demonstrates multi-agent research coordination with task routing
- **Agents**: Research Specialist, Data Analyst, Report Writer
- **Use Case**: Comprehensive research with automated report generation

### 2. Code Review & Testing Workflow  
- **File**: `code_review_workflow.py`
- **Description**: Automated code review process with security scanning
- **Agents**: Code Reviewer, Security Analyst, Test Generator
- **Use Case**: Pull request analysis and test automation

### 3. Content Creation Pipeline
- **File**: `content_creation.py` 
- **Description**: Multi-stage content creation with editing and optimization
- **Agents**: Content Creator, Editor, SEO Optimizer
- **Use Case**: Blog post and marketing content generation

### 4. Data Processing Swarm
- **File**: `data_processing_swarm.py`
- **Description**: Parallel data processing with real-time coordination
- **Agents**: Data Ingester, Processor, Quality Controller
- **Use Case**: Large dataset analysis and transformation

### 5. Customer Support Bot Network
- **File**: `support_bot_network.py`
- **Description**: Multi-specialist customer support system
- **Agents**: Triage Bot, Technical Support, Escalation Handler  
- **Use Case**: Automated customer support with human handoff

## 🚀 Quick Start

1. **Start the infrastructure**:
   ```bash
   make ghcr-up  # or make dev-up for local builds
   ```

2. **Run an example workflow**:
   ```bash
   cd examples/agent_workflows
   python research_pipeline.py
   ```

3. **Monitor agent activity**:
   - Real-time Hub: ws://localhost:8008
   - Orchestrator API: http://localhost:8006
   - Memory API: http://localhost:8003

## 📊 Workflow Features

Each workflow demonstrates:

- ✅ **Task Routing**: Intelligent agent selection based on capabilities
- ✅ **Real-time Communication**: WebSocket-based agent coordination  
- ✅ **Memory Persistence**: Shared context and learning between tasks
- ✅ **Progress Tracking**: Live status updates and metrics
- ✅ **Error Handling**: Graceful failure recovery and task reassignment
- ✅ **Performance Monitoring**: Comprehensive metrics and observability

## 🏗️ Workflow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Task Router   │◄──►│  Realtime Hub    │◄──►│  Memory API     │
│                 │    │                  │    │                 │
│ • Agent Selection│    │ • WebSocket Comm│    │ • Persistent    │
│ • Load Balancing│    │ • Event Broadcasting │ • Context Sharing│
│ • Anti-collision│    │ • Progress Tracking  │ • Learning      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Swarm                                 │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Specialist  │  │   Worker    │  │ Coordinator │             │
│  │   Agent     │  │   Agent     │  │    Agent    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Customization

### Creating Custom Workflows

1. **Extend SmartAgentClient**:
   ```python
   class CustomAgent(SmartAgentClient):
       async def _process_task(self, task_id, description, requirements):
           # Custom task processing logic
           pass
   ```

2. **Configure Agent Capabilities**:
   ```python
   config = ConnectionConfig(
       agent_id="custom_agent",
       role=AgentRole.SPECIALIST,
       capabilities=["custom_skill_1", "custom_skill_2"]
   )
   ```

3. **Implement Coordination Logic**:
   ```python
   async def coordinate_workflow():
       # Task creation and routing
       # Agent communication
       # Progress monitoring
       pass
   ```

## 📈 Performance Optimization

- **Parallel Processing**: Multiple agents work simultaneously
- **Smart Routing**: Tasks assigned to most suitable agents
- **Memory Efficiency**: Shared context prevents redundant processing
- **Adaptive Learning**: Agents improve through persistent memory
- **Resource Monitoring**: Real-time performance tracking

## 🔍 Debugging & Monitoring

### View Real-time Agent Activity
```bash
# WebSocket connection to hub
wscat -c ws://localhost:8008

# Agent status via API
curl http://localhost:8006/agents/status

# Memory utilization
curl http://localhost:8003/memory/stats
```

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Testing Workflows

Each workflow includes:
- Unit tests for individual agents
- Integration tests for coordination
- Performance benchmarks
- Error simulation and recovery testing

Run tests:
```bash
pytest examples/agent_workflows/tests/
```

## 📚 Advanced Features

- **Dynamic Agent Spawning**: Create agents on-demand
- **Cross-Workflow Communication**: Agents share insights between workflows  
- **Checkpoint & Resume**: Save and restore workflow state
- **A/B Testing**: Compare different coordination strategies
- **Resource Scaling**: Auto-scale agent count based on load

## 🤝 Contributing

To add new workflows:

1. Create workflow file in this directory
2. Follow the naming convention: `{use_case}_workflow.py`
3. Include comprehensive documentation and examples
4. Add tests in `tests/` subdirectory
5. Update this README with workflow description

---

💡 **Tip**: Start with the research pipeline example to understand the coordination patterns, then build custom workflows for your specific use cases.