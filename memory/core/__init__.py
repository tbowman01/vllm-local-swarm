"""
Core Memory System for vLLM Local Swarm

This module provides the foundational memory management components for the
multi-agent system, supporting session memory, semantic memory, and observability.
"""

from .memory_manager import MemoryManager
from .session_memory import SessionMemory
# from .semantic_memory import SemanticMemory  # Disabled due to dependency issues
from .observability import ObservabilityManager
from .config import MemoryConfig
from .models import MemoryEntry, MemoryQuery, MemoryType, MemoryStats

__all__ = [
    'MemoryManager',
    'MemoryEntry',
    'MemoryQuery',
    'MemoryType', 
    'MemoryStats',
    'SessionMemory',
    # 'SemanticMemory',  # Disabled
    'ObservabilityManager',
    'MemoryConfig'
]

__version__ = "1.0.0"