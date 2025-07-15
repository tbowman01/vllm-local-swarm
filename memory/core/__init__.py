"""
Core Memory System for vLLM Local Swarm

This module provides the foundational memory management components for the
multi-agent system, supporting session memory, semantic memory, and observability.
"""

from .memory_manager import MemoryManager, MemoryType
from .session_memory import SessionMemory
from .semantic_memory import SemanticMemory
from .observability import ObservabilityManager
from .config import MemoryConfig

__all__ = [
    'MemoryManager',
    'MemoryType', 
    'SessionMemory',
    'SemanticMemory',
    'ObservabilityManager',
    'MemoryConfig'
]

__version__ = "1.0.0"