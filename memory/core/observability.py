"""
Observability Manager - Langfuse and ClickHouse integration

Handles comprehensive observability, trace logging, and analytics for the
multi-agent system using Langfuse and ClickHouse.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict

try:
    from langfuse import Langfuse
    from langfuse.model import CreateTrace, CreateSpan, CreateGeneration
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    clickhouse_connect = None

from .config import LangfuseConfig, ClickHouseConfig
from .memory_manager import MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """
    Comprehensive observability system using Langfuse and ClickHouse.
    
    Features:
    - LLM trace logging with Langfuse
    - Agent performance monitoring
    - Long-term analytics with ClickHouse
    - Custom metrics and dashboards
    - Self-improvement feedback loops
    """
    
    def __init__(self, langfuse_config: LangfuseConfig, clickhouse_config: ClickHouseConfig):
        """Initialize observability manager."""
        self.langfuse_config = langfuse_config
        self.clickhouse_config = clickhouse_config
        self.logger = logging.getLogger(f"{__name__}.ObservabilityManager")
        
        # Components
        self.langfuse: Optional[Langfuse] = None
        self.clickhouse = None
        
        # Internal state
        self._trace_buffer = []
        self._flush_task = None
        self._buffer_lock = asyncio.Lock()
        
        # Check dependencies
        if not LANGFUSE_AVAILABLE:
            self.logger.warning("Langfuse not available. Install with: pip install langfuse")
        
        if not CLICKHOUSE_AVAILABLE:
            self.logger.warning("ClickHouse client not available. Install with: pip install clickhouse-connect")
    
    async def initialize(self) -> None:
        """Initialize Langfuse and ClickHouse connections."""
        try:
            self.logger.info("Initializing observability system...")
            
            # Initialize Langfuse if enabled and available
            if self.langfuse_config.enabled and LANGFUSE_AVAILABLE:
                await self._initialize_langfuse()
            
            # Initialize ClickHouse if available
            if CLICKHOUSE_AVAILABLE:
                await self._initialize_clickhouse()
            
            # Start flush task for buffered traces
            if self.langfuse:
                self._flush_task = asyncio.create_task(self._flush_loop())
            
            self.logger.info("Observability system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize observability system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown observability system."""
        self.logger.info("Shutting down observability system...")
        
        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining traces
        await self._flush_traces()
        
        # Shutdown Langfuse
        if self.langfuse:
            self.langfuse.flush()
        
        # Close ClickHouse connection
        if self.clickhouse:
            self.clickhouse.close()
        
        self.logger.info("Observability system shutdown complete")
    
    async def log_trace(self, entry: MemoryEntry) -> str:
        """
        Log a trace entry to observability systems.
        
        Args:
            entry: Memory entry to log as trace
            
        Returns:
            str: Trace ID
        """
        try:
            trace_id = entry.id or str(uuid.uuid4())
            
            # Add to buffer for Langfuse
            if self.langfuse:
                async with self._buffer_lock:
                    self._trace_buffer.append(entry)
            
            # Log to ClickHouse immediately for analytics
            if self.clickhouse:
                await self._log_to_clickhouse(entry)
            
            # Log to local file as backup
            await self._log_to_file(entry)
            
            self.logger.debug(f"Logged trace: {trace_id}")
            return trace_id
            
        except Exception as e:
            self.logger.error(f"Failed to log trace: {e}")
            raise
    
    async def start_trace(self, name: str, session_id: Optional[str] = None, 
                         agent_id: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        """
        Start a new trace for a complex operation.
        
        Args:
            name: Trace name
            session_id: Optional session ID
            agent_id: Optional agent ID  
            metadata: Optional metadata
            
        Returns:
            str: Trace ID
        """
        trace_entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=MemoryType.TRACE,
            content={
                "trace_type": "start",
                "name": name,
                "status": "started"
            },
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            session_id=session_id,
            tags=["trace", "start"]
        )
        
        return await self.log_trace(trace_entry)
    
    async def end_trace(self, trace_id: str, status: str = "completed", 
                       output: Optional[Any] = None, metrics: Optional[Dict] = None) -> None:
        """
        End a trace with results.
        
        Args:
            trace_id: Trace ID to end
            status: Completion status
            output: Optional output data
            metrics: Optional performance metrics
        """
        trace_entry = MemoryEntry(
            id=f"{trace_id}_end",
            type=MemoryType.TRACE,
            content={
                "trace_type": "end",
                "trace_id": trace_id,
                "status": status,
                "output": output
            },
            metadata=metrics or {},
            timestamp=datetime.utcnow(),
            tags=["trace", "end"]
        )
        
        await self.log_trace(trace_entry)
    
    async def log_agent_action(self, agent_id: str, action: str, input_data: Any,
                              output_data: Any, duration_ms: float, 
                              session_id: Optional[str] = None) -> str:
        """
        Log an agent action with performance metrics.
        
        Args:
            agent_id: Agent performing the action
            action: Action being performed
            input_data: Input to the action
            output_data: Output from the action
            duration_ms: Duration in milliseconds
            session_id: Optional session ID
            
        Returns:
            str: Log entry ID
        """
        action_entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=MemoryType.TRACE,
            content={
                "action": action,
                "input": input_data,
                "output": output_data,
                "duration_ms": duration_ms
            },
            metadata={
                "agent_action": True,
                "performance": {
                    "duration_ms": duration_ms,
                    "input_size": len(str(input_data)) if input_data else 0,
                    "output_size": len(str(output_data)) if output_data else 0
                }
            },
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            session_id=session_id,
            tags=["agent_action", action]
        )
        
        return await self.log_trace(action_entry)
    
    async def log_llm_call(self, agent_id: str, model: str, prompt: str,
                          response: str, tokens_used: int, duration_ms: float,
                          session_id: Optional[str] = None) -> str:
        """
        Log an LLM API call with metrics.
        
        Args:
            agent_id: Agent making the call
            model: Model used
            prompt: Input prompt
            response: Model response
            tokens_used: Number of tokens consumed
            duration_ms: Duration in milliseconds
            session_id: Optional session ID
            
        Returns:
            str: Log entry ID
        """
        llm_entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=MemoryType.TRACE,
            content={
                "model": model,
                "prompt": prompt,
                "response": response,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms
            },
            metadata={
                "llm_call": True,
                "performance": {
                    "tokens_used": tokens_used,
                    "duration_ms": duration_ms,
                    "tokens_per_second": tokens_used / (duration_ms / 1000) if duration_ms > 0 else 0
                },
                "model_info": {
                    "model": model,
                    "prompt_length": len(prompt),
                    "response_length": len(response)
                }
            },
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            session_id=session_id,
            tags=["llm_call", model]
        )
        
        return await self.log_trace(llm_entry)
    
    async def log_error(self, agent_id: str, error: Exception, context: Dict[str, Any],
                       session_id: Optional[str] = None) -> str:
        """
        Log an error with context.
        
        Args:
            agent_id: Agent that encountered the error
            error: Exception object
            context: Additional context about the error
            session_id: Optional session ID
            
        Returns:
            str: Log entry ID
        """
        error_entry = MemoryEntry(
            id=str(uuid.uuid4()),
            type=MemoryType.TRACE,
            content={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            },
            metadata={
                "error": True,
                "severity": "error"
            },
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            session_id=session_id,
            tags=["error", type(error).__name__]
        )
        
        return await self.log_trace(error_entry)
    
    async def get_agent_metrics(self, agent_id: str, 
                               time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.
        
        Args:
            agent_id: Agent ID
            time_range: Optional time range tuple (start, end)
            
        Returns:
            Dict containing agent metrics
        """
        if not self.clickhouse:
            return {"error": "ClickHouse not available"}
        
        try:
            # Default to last 24 hours if no time range specified
            if not time_range:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)
                time_range = (start_time, end_time)
            
            start_time, end_time = time_range
            
            # Query ClickHouse for agent metrics
            query = """
            SELECT 
                COUNT(*) as total_actions,
                AVG(JSONExtractFloat(metadata, 'performance.duration_ms')) as avg_duration_ms,
                SUM(JSONExtractInt(metadata, 'performance.tokens_used')) as total_tokens,
                COUNT(DISTINCT session_id) as unique_sessions,
                groupArray(DISTINCT JSONExtractString(content, 'action')) as actions_performed
            FROM agent_traces 
            WHERE agent_id = %(agent_id)s 
              AND timestamp >= %(start_time)s 
              AND timestamp <= %(end_time)s
              AND JSONHas(metadata, 'agent_action')
            """
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.query(
                    query,
                    {
                        'agent_id': agent_id,
                        'start_time': start_time,
                        'end_time': end_time
                    }
                ).first_row
            )
            
            if result:
                return {
                    "agent_id": agent_id,
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "total_actions": result[0],
                    "avg_duration_ms": result[1],
                    "total_tokens": result[2],
                    "unique_sessions": result[3],
                    "actions_performed": result[4]
                }
            else:
                return {
                    "agent_id": agent_id,
                    "total_actions": 0,
                    "message": "No data found for the specified time range"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get agent metrics: {e}")
            return {"error": str(e)}
    
    async def get_system_metrics(self, 
                                time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Get overall system performance metrics.
        
        Args:
            time_range: Optional time range tuple (start, end)
            
        Returns:
            Dict containing system metrics
        """
        if not self.clickhouse:
            return {"error": "ClickHouse not available"}
        
        try:
            # Default to last 24 hours if no time range specified
            if not time_range:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)
                time_range = (start_time, end_time)
            
            start_time, end_time = time_range
            
            # Query for system-wide metrics
            query = """
            SELECT 
                COUNT(*) as total_traces,
                COUNT(DISTINCT agent_id) as active_agents,
                COUNT(DISTINCT session_id) as total_sessions,
                AVG(JSONExtractFloat(metadata, 'performance.duration_ms')) as avg_duration_ms,
                SUM(JSONExtractInt(metadata, 'performance.tokens_used')) as total_tokens,
                COUNT(*) FILTER(WHERE JSONHas(metadata, 'error')) as error_count
            FROM agent_traces 
            WHERE timestamp >= %(start_time)s 
              AND timestamp <= %(end_time)s
            """
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.query(
                    query,
                    {
                        'start_time': start_time,
                        'end_time': end_time
                    }
                ).first_row
            )
            
            if result:
                return {
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "total_traces": result[0],
                    "active_agents": result[1],
                    "total_sessions": result[2],
                    "avg_duration_ms": result[3],
                    "total_tokens": result[4],
                    "error_count": result[5],
                    "error_rate": result[5] / result[0] if result[0] > 0 else 0
                }
            else:
                return {"message": "No data found for the specified time range"}
                
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    async def get_improvement_insights(self) -> List[Dict[str, Any]]:
        """
        Analyze traces to identify improvement opportunities.
        
        Returns:
            List of improvement insights
        """
        insights = []
        
        try:
            # Analyze common error patterns
            error_insights = await self._analyze_error_patterns()
            insights.extend(error_insights)
            
            # Analyze performance bottlenecks
            performance_insights = await self._analyze_performance_bottlenecks()
            insights.extend(performance_insights)
            
            # Analyze agent coordination patterns
            coordination_insights = await self._analyze_coordination_patterns()
            insights.extend(coordination_insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get improvement insights: {e}")
            return [{"type": "error", "message": str(e)}]
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get observability system statistics.
        
        Returns:
            Dict containing statistics
        """
        stats = {
            "langfuse_enabled": self.langfuse is not None,
            "clickhouse_enabled": self.clickhouse is not None,
            "buffer_size": len(self._trace_buffer)
        }
        
        if self.clickhouse:
            try:
                # Get table stats from ClickHouse
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.clickhouse.query("SELECT COUNT(*) FROM agent_traces").first_row
                )
                stats["total_traces_stored"] = result[0] if result else 0
            except Exception as e:
                stats["clickhouse_error"] = str(e)
        
        return stats
    
    async def _initialize_langfuse(self) -> None:
        """Initialize Langfuse client."""
        try:
            # Create Langfuse client
            host_url = f"http://{self.langfuse_config.host}:{self.langfuse_config.port}"
            
            self.langfuse = Langfuse(
                public_key=self.langfuse_config.public_key,
                secret_key=self.langfuse_config.secret_key,
                host=host_url,
                flush_interval=self.langfuse_config.flush_interval
            )
            
            self.logger.info("Langfuse client initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Langfuse: {e}")
            raise
    
    async def _initialize_clickhouse(self) -> None:
        """Initialize ClickHouse client and setup tables."""
        try:
            # Create ClickHouse client
            self.clickhouse = clickhouse_connect.get_client(
                host=self.clickhouse_config.host,
                port=self.clickhouse_config.port,
                database=self.clickhouse_config.database,
                username=self.clickhouse_config.username,
                password=self.clickhouse_config.password,
                secure=self.clickhouse_config.secure
            )
            
            # Setup tables
            await self._setup_clickhouse_tables()
            
            self.logger.info("ClickHouse client initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ClickHouse: {e}")
            # Don't raise here - ClickHouse is optional
            self.clickhouse = None
    
    async def _setup_clickhouse_tables(self) -> None:
        """Setup ClickHouse tables for storing traces."""
        try:
            # Create agent_traces table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS agent_traces (
                id String,
                type String,
                content String,
                metadata String,
                timestamp DateTime64(3),
                agent_id Nullable(String),
                session_id Nullable(String),
                tags Array(String),
                created_at DateTime64(3) DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (timestamp, agent_id, session_id)
            PARTITION BY toYYYYMM(timestamp)
            """
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.command(create_table_query)
            )
            
            self.logger.info("ClickHouse tables setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup ClickHouse tables: {e}")
            raise
    
    async def _log_to_clickhouse(self, entry: MemoryEntry) -> None:
        """Log entry to ClickHouse."""
        if not self.clickhouse:
            return
        
        try:
            data = {
                'id': entry.id,
                'type': entry.type.value,
                'content': json.dumps(entry.content),
                'metadata': json.dumps(entry.metadata),
                'timestamp': entry.timestamp,
                'agent_id': entry.agent_id,
                'session_id': entry.session_id,
                'tags': entry.tags
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.insert('agent_traces', [data])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log to ClickHouse: {e}")
    
    async def _log_to_file(self, entry: MemoryEntry) -> None:
        """Log entry to local file as backup."""
        try:
            log_data = {
                "id": entry.id,
                "type": entry.type.value,
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp.isoformat(),
                "agent_id": entry.agent_id,
                "session_id": entry.session_id,
                "tags": entry.tags
            }
            
            # Write to daily log file
            log_file = f"logs/traces_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
            
            # Ensure logs directory exists
            import os
            os.makedirs("logs", exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(json.dumps(log_data) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log to file: {e}")
    
    async def _flush_loop(self) -> None:
        """Background task to flush traces to Langfuse."""
        while True:
            try:
                await asyncio.sleep(self.langfuse_config.flush_interval)
                await self._flush_traces()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in flush loop: {e}")
    
    async def _flush_traces(self) -> None:
        """Flush buffered traces to Langfuse."""
        if not self.langfuse or not self._trace_buffer:
            return
        
        try:
            async with self._buffer_lock:
                traces_to_flush = self._trace_buffer.copy()
                self._trace_buffer.clear()
            
            # Send traces to Langfuse
            for entry in traces_to_flush:
                await self._send_to_langfuse(entry)
            
            # Flush Langfuse buffer
            self.langfuse.flush()
            
        except Exception as e:
            self.logger.error(f"Failed to flush traces: {e}")
    
    async def _send_to_langfuse(self, entry: MemoryEntry) -> None:
        """Send trace entry to Langfuse."""
        try:
            # Convert memory entry to Langfuse trace
            trace_data = {
                "id": entry.id,
                "name": entry.metadata.get("operation", "agent_operation"),
                "metadata": entry.metadata,
                "tags": entry.tags,
                "timestamp": entry.timestamp,
                "session_id": entry.session_id,
                "user_id": entry.agent_id
            }
            
            if "llm_call" in entry.tags:
                # Log as generation
                self.langfuse.generation(
                    id=entry.id,
                    name=f"llm_call_{entry.content.get('model', 'unknown')}",
                    model=entry.content.get('model'),
                    input=entry.content.get('prompt'),
                    output=entry.content.get('response'),
                    usage={
                        "input_tokens": entry.metadata.get('performance', {}).get('tokens_used', 0),
                        "output_tokens": 0  # Would need to calculate separately
                    },
                    metadata=entry.metadata,
                    trace_id=entry.session_id
                )
            else:
                # Log as span
                self.langfuse.span(
                    id=entry.id,
                    name=entry.metadata.get("operation", "agent_operation"),
                    input=entry.content,
                    output=entry.metadata.get("output"),
                    metadata=entry.metadata,
                    trace_id=entry.session_id
                )
                
        except Exception as e:
            self.logger.error(f"Failed to send to Langfuse: {e}")
    
    async def _analyze_error_patterns(self) -> List[Dict[str, Any]]:
        """Analyze error patterns for insights."""
        insights = []
        
        if not self.clickhouse:
            return insights
        
        try:
            # Query for common errors
            query = """
            SELECT 
                JSONExtractString(content, 'error_type') as error_type,
                COUNT(*) as count,
                agent_id,
                groupArray(JSONExtractString(content, 'error_message')) as messages
            FROM agent_traces 
            WHERE JSONHas(metadata, 'error') 
              AND timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY error_type, agent_id
            ORDER BY count DESC
            LIMIT 10
            """
            
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.query(query).result_rows
            )
            
            for result in results:
                error_type, count, agent_id, messages = result
                insights.append({
                    "type": "error_pattern",
                    "priority": "high" if count > 10 else "medium",
                    "description": f"Agent {agent_id} has {count} {error_type} errors",
                    "suggestion": f"Review {error_type} handling in agent {agent_id}",
                    "data": {
                        "error_type": error_type,
                        "count": count,
                        "agent_id": agent_id,
                        "sample_messages": messages[:3]
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {e}")
        
        return insights
    
    async def _analyze_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze performance bottlenecks."""
        insights = []
        
        if not self.clickhouse:
            return insights
        
        try:
            # Query for slow operations
            query = """
            SELECT 
                agent_id,
                JSONExtractString(content, 'action') as action,
                AVG(JSONExtractFloat(metadata, 'performance.duration_ms')) as avg_duration,
                COUNT(*) as count
            FROM agent_traces 
            WHERE JSONHas(metadata, 'agent_action') 
              AND timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY agent_id, action
            HAVING avg_duration > 5000  -- More than 5 seconds
            ORDER BY avg_duration DESC
            LIMIT 10
            """
            
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.query(query).result_rows
            )
            
            for result in results:
                agent_id, action, avg_duration, count = result
                insights.append({
                    "type": "performance_bottleneck",
                    "priority": "high" if avg_duration > 10000 else "medium",
                    "description": f"Agent {agent_id} action '{action}' is slow (avg: {avg_duration:.0f}ms)",
                    "suggestion": f"Optimize {action} performance in agent {agent_id}",
                    "data": {
                        "agent_id": agent_id,
                        "action": action,
                        "avg_duration_ms": avg_duration,
                        "count": count
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Failed to analyze performance bottlenecks: {e}")
        
        return insights
    
    async def _analyze_coordination_patterns(self) -> List[Dict[str, Any]]:
        """Analyze agent coordination patterns."""
        insights = []
        
        if not self.clickhouse:
            return insights
        
        try:
            # Query for coordination issues
            query = """
            SELECT 
                session_id,
                COUNT(DISTINCT agent_id) as agent_count,
                COUNT(*) FILTER(WHERE has(tags, 'handoff')) as handoff_count,
                COUNT(*) FILTER(WHERE JSONHas(metadata, 'error')) as error_count
            FROM agent_traces 
            WHERE timestamp >= now() - INTERVAL 24 HOUR
              AND session_id IS NOT NULL
            GROUP BY session_id
            HAVING agent_count > 1 AND error_count > 0
            ORDER BY error_count DESC
            LIMIT 5
            """
            
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.clickhouse.query(query).result_rows
            )
            
            for result in results:
                session_id, agent_count, handoff_count, error_count = result
                insights.append({
                    "type": "coordination_issue", 
                    "priority": "medium",
                    "description": f"Session {session_id} with {agent_count} agents had {error_count} errors",
                    "suggestion": f"Review coordination patterns in session {session_id}",
                    "data": {
                        "session_id": session_id,
                        "agent_count": agent_count,
                        "handoff_count": handoff_count,
                        "error_count": error_count
                    }
                })
                
        except Exception as e:
            self.logger.error(f"Failed to analyze coordination patterns: {e}")
        
        return insights