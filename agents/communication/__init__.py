"""
Real-Time Agent Communication System
===================================

This module provides WebSocket-based real-time communication capabilities
for the vLLM Local Swarm agent coordination system.

Components:
- RealtimeHub: Central WebSocket server for agent communication
- AgentClient: Client library for agents to connect to the hub
- Message types and data structures for coordination

Features:
- Real-time messaging between agents
- Channel-based broadcasting
- Task coordination and progress tracking
- Agent presence management
- Performance metrics and monitoring
"""

from .realtime_hub import (
    RealtimeHub,
    MessageType,
    AgentRole,
    Message,
    AgentConnection
)

from .agent_client import (
    AgentClient,
    ConnectionConfig,
    ConnectionState
)

__all__ = [
    'RealtimeHub',
    'AgentClient',
    'MessageType',
    'AgentRole', 
    'Message',
    'AgentConnection',
    'ConnectionConfig',
    'ConnectionState'
]

__version__ = '1.0.0'