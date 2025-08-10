#!/usr/bin/env python3
"""
Distributed Task Queue System
============================

High-performance distributed task queuing system for the vLLM Local Swarm with:
- Redis-based task persistence and distribution
- Priority-based task scheduling
- Dead letter queues and retry mechanisms
- Task result caching and retrieval
- Real-time monitoring and metrics
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
import hashlib

try:
    import redis.asyncio as redis
except ImportError:
    print("Installing redis...")
    import subprocess
    subprocess.run(["pip", "install", "redis"], check=True)
    import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    QUEUED = "queued" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 10
    HIGH = 8
    NORMAL = 5
    LOW = 2
    BACKGROUND = 1


@dataclass
class TaskDefinition:
    """Task definition structure"""
    id: str
    name: str
    handler: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 300  # seconds
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    agent_requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: float = 0.0
    retry_count: int = 0
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DistributedTaskQueue:
    """
    High-performance distributed task queue with Redis backend
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 queue_prefix: str = "vllm_task_queue"):
        self.redis_url = redis_url
        self.queue_prefix = queue_prefix
        self.redis_pool = None
        
        # Queue names
        self.queues = {
            TaskPriority.CRITICAL: f"{queue_prefix}:critical",
            TaskPriority.HIGH: f"{queue_prefix}:high", 
            TaskPriority.NORMAL: f"{queue_prefix}:normal",
            TaskPriority.LOW: f"{queue_prefix}:low",
            TaskPriority.BACKGROUND: f"{queue_prefix}:background"
        }
        
        # Redis keys
        self.keys = {
            'tasks': f"{queue_prefix}:tasks",  # Hash of task definitions
            'results': f"{queue_prefix}:results",  # Hash of task results
            'processing': f"{queue_prefix}:processing",  # Set of processing tasks
            'scheduled': f"{queue_prefix}:scheduled",  # Sorted set of scheduled tasks
            'dead_letter': f"{queue_prefix}:dead_letter",  # Failed tasks
            'metrics': f"{queue_prefix}:metrics",  # Queue metrics
            'locks': f"{queue_prefix}:locks"  # Task processing locks
        }
        
        # Task handlers registry
        self.handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self._running = False
        self._scheduler_task = None
        self._cleanup_task = None
        self._metrics_task = None
        
        # Performance metrics
        self.metrics = {
            'tasks_enqueued': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'queue_sizes': {priority.name: 0 for priority in TaskPriority}
        }
        
    async def initialize(self):
        """Initialize the task queue system"""
        logger.info("🚀 Initializing Distributed Task Queue...")
        
        try:
            # Create Redis connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Test connection
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            await redis_client.ping()
            await redis_client.close()
            
            logger.info("✅ Distributed Task Queue initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize task queue: {e}")
            raise
            
    async def start(self):
        """Start the task queue background services"""
        if self._running:
            return
            
        self._running = True
        
        # Start background tasks
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._metrics_task = asyncio.create_task(self._metrics_loop())
        
        logger.info("✅ Task queue background services started")
        
    async def stop(self):
        """Stop the task queue system"""
        self._running = False
        
        # Cancel background tasks
        for task in [self._scheduler_task, self._cleanup_task, self._metrics_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Close Redis connection pool
        if self.redis_pool:
            await self.redis_pool.disconnect()
            
        logger.info("🛑 Task queue system stopped")
        
    def register_handler(self, name: str, handler: Callable):
        """Register a task handler"""
        self.handlers[name] = handler
        logger.info(f"📝 Registered task handler: {name}")
        
    async def enqueue(self, task: TaskDefinition) -> str:
        """Enqueue a task for processing"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            # Generate task ID if not provided
            if not task.id:
                task.id = f"task_{uuid.uuid4().hex[:8]}_{int(time.time())}"
                
            # Store task definition
            task_data = json.dumps(asdict(task), default=str)
            await redis_client.hset(self.keys['tasks'], task.id, task_data)
            
            # Handle scheduled tasks
            if task.scheduled_at and task.scheduled_at > datetime.now():
                # Add to scheduled set
                timestamp = task.scheduled_at.timestamp()
                await redis_client.zadd(self.keys['scheduled'], {task.id: timestamp})
                logger.info(f"📅 Task {task.id} scheduled for {task.scheduled_at}")
            else:
                # Add to appropriate priority queue
                queue_name = self.queues[task.priority]
                await redis_client.lpush(queue_name, task.id)
                logger.info(f"📥 Task {task.id} enqueued to {task.priority.name} queue")
                
            # Update metrics
            self.metrics['tasks_enqueued'] += 1
            
            # Store initial result record
            initial_result = TaskResult(
                task_id=task.id,
                status=TaskStatus.QUEUED if not task.scheduled_at else TaskStatus.PENDING
            )
            
            result_data = json.dumps(asdict(initial_result), default=str)
            await redis_client.hset(self.keys['results'], task.id, result_data)
            
            return task.id
            
        finally:
            await redis_client.close()
            
    async def dequeue(self, priorities: List[TaskPriority] = None, 
                     timeout: int = 5) -> Optional[TaskDefinition]:
        """Dequeue a task for processing"""
        if priorities is None:
            priorities = list(TaskPriority)
            
        # Sort by priority (highest first)
        priorities.sort(key=lambda p: p.value, reverse=True)
        
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            # Try to get task from priority queues
            queue_names = [self.queues[p] for p in priorities]
            
            # Blocking pop with timeout
            result = await redis_client.brpop(queue_names, timeout=timeout)
            
            if not result:
                return None
                
            queue_name, task_id = result
            task_id = task_id.decode('utf-8')
            
            # Get task definition
            task_data = await redis_client.hget(self.keys['tasks'], task_id)
            
            if not task_data:
                logger.warning(f"⚠️ Task {task_id} not found in definitions")
                return None
                
            # Parse task definition
            task_dict = json.loads(task_data.decode('utf-8'))
            
            # Convert string dates back to datetime
            if task_dict.get('created_at'):
                task_dict['created_at'] = datetime.fromisoformat(task_dict['created_at'])
            if task_dict.get('scheduled_at'):
                task_dict['scheduled_at'] = datetime.fromisoformat(task_dict['scheduled_at'])
            if task_dict.get('expires_at'):
                task_dict['expires_at'] = datetime.fromisoformat(task_dict['expires_at'])
                
            # Convert priority back to enum
            task_dict['priority'] = TaskPriority(task_dict['priority'])
            
            task = TaskDefinition(**task_dict)
            
            # Check if task has expired
            if task.expires_at and datetime.now() > task.expires_at:
                await self._mark_task_expired(task_id)
                return None
                
            # Mark task as processing
            await redis_client.sadd(self.keys['processing'], task_id)
            
            # Update task status
            await self._update_task_status(task_id, TaskStatus.PROCESSING)
            
            logger.info(f"📤 Dequeued task {task_id} from {queue_name.decode('utf-8')}")
            return task
            
        finally:
            await redis_client.close()
            
    async def complete_task(self, task_id: str, result: Any = None, 
                          agent_id: str = None, metadata: Dict[str, Any] = None):
        """Mark task as completed with result"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            # Get current result
            current_result = await self._get_task_result(task_id)
            if not current_result:
                logger.warning(f"⚠️ Task result not found for {task_id}")
                return
                
            # Update result
            current_result.status = TaskStatus.COMPLETED
            current_result.result = result
            current_result.completed_at = datetime.now()
            current_result.agent_id = agent_id
            
            if current_result.started_at:
                current_result.processing_time = (
                    current_result.completed_at - current_result.started_at
                ).total_seconds()
                
            if metadata:
                current_result.metadata.update(metadata)
                
            # Store updated result
            result_data = json.dumps(asdict(current_result), default=str)
            await redis_client.hset(self.keys['results'], task_id, result_data)
            
            # Remove from processing set
            await redis_client.srem(self.keys['processing'], task_id)
            
            # Update metrics
            self.metrics['tasks_completed'] += 1
            self.metrics['total_processing_time'] += current_result.processing_time
            
            if self.metrics['tasks_completed'] > 0:
                self.metrics['avg_processing_time'] = (
                    self.metrics['total_processing_time'] / 
                    self.metrics['tasks_completed']
                )
                
            logger.info(f"✅ Task {task_id} completed successfully")
            
        finally:
            await redis_client.close()
            
    async def fail_task(self, task_id: str, error: str, agent_id: str = None,
                       retry: bool = True):
        """Mark task as failed and optionally retry"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            # Get current result and task definition
            current_result = await self._get_task_result(task_id)
            task_data = await redis_client.hget(self.keys['tasks'], task_id)
            
            if not current_result or not task_data:
                logger.warning(f"⚠️ Task or result not found for {task_id}")
                return
                
            # Parse task definition to get retry settings
            task_dict = json.loads(task_data.decode('utf-8'))
            max_retries = task_dict.get('max_retries', 3)
            retry_delay = task_dict.get('retry_delay', 60)
            
            # Update result
            current_result.status = TaskStatus.FAILED
            current_result.error = error
            current_result.completed_at = datetime.now()
            current_result.agent_id = agent_id
            current_result.retry_count += 1
            
            if current_result.started_at:
                current_result.processing_time = (
                    current_result.completed_at - current_result.started_at
                ).total_seconds()
                
            # Determine if task should be retried
            should_retry = (
                retry and 
                current_result.retry_count <= max_retries and
                max_retries > 0
            )
            
            if should_retry:
                # Schedule retry
                retry_time = datetime.now() + timedelta(seconds=retry_delay)
                await redis_client.zadd(
                    self.keys['scheduled'], 
                    {task_id: retry_time.timestamp()}
                )
                
                current_result.status = TaskStatus.RETRY
                logger.info(f"🔄 Task {task_id} scheduled for retry at {retry_time}")
            else:
                # Move to dead letter queue
                await redis_client.lpush(self.keys['dead_letter'], task_id)
                logger.warning(f"💀 Task {task_id} moved to dead letter queue")
                
            # Store updated result
            result_data = json.dumps(asdict(current_result), default=str)
            await redis_client.hset(self.keys['results'], task_id, result_data)
            
            # Remove from processing set
            await redis_client.srem(self.keys['processing'], task_id)
            
            # Update metrics
            self.metrics['tasks_failed'] += 1
            
        finally:
            await redis_client.close()
            
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or queued task"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            # Check if task is currently processing
            is_processing = await redis_client.sismember(self.keys['processing'], task_id)
            if is_processing:
                logger.warning(f"⚠️ Cannot cancel task {task_id} - currently processing")
                return False
                
            # Remove from all queues
            removed = False
            for queue_name in self.queues.values():
                count = await redis_client.lrem(queue_name, 0, task_id)
                if count > 0:
                    removed = True
                    
            # Remove from scheduled set
            scheduled_removed = await redis_client.zrem(self.keys['scheduled'], task_id)
            if scheduled_removed > 0:
                removed = True
                
            if removed:
                # Update task status
                await self._update_task_status(task_id, TaskStatus.CANCELLED)
                logger.info(f"🚫 Task {task_id} cancelled")
                return True
            else:
                logger.warning(f"⚠️ Task {task_id} not found in queues")
                return False
                
        finally:
            await redis_client.close()
            
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task execution result"""
        return await self._get_task_result(task_id)
        
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            stats = {}
            
            # Get queue sizes
            for priority, queue_name in self.queues.items():
                size = await redis_client.llen(queue_name)
                stats[f"{priority.name.lower()}_queue_size"] = size
                
            # Get processing count
            stats['processing_count'] = await redis_client.scard(self.keys['processing'])
            
            # Get scheduled count
            stats['scheduled_count'] = await redis_client.zcard(self.keys['scheduled'])
            
            # Get dead letter count
            stats['dead_letter_count'] = await redis_client.llen(self.keys['dead_letter'])
            
            # Get total task counts
            stats['total_tasks'] = await redis_client.hlen(self.keys['tasks'])
            stats['total_results'] = await redis_client.hlen(self.keys['results'])
            
            # Add performance metrics
            stats.update(self.metrics)
            
            return stats
            
        finally:
            await redis_client.close()
            
    async def process_task(self, task: TaskDefinition) -> TaskResult:
        """Process a single task"""
        task_id = task.id
        
        try:
            # Update start time
            await self._update_task_start_time(task_id)
            
            # Get handler
            if task.handler not in self.handlers:
                raise ValueError(f"Handler {task.handler} not registered")
                
            handler = self.handlers[task.handler]
            
            # Execute task with timeout
            try:
                result = await asyncio.wait_for(
                    handler(task.payload),
                    timeout=task.timeout
                )
                
                # Mark as completed
                await self.complete_task(task_id, result)
                
                return await self._get_task_result(task_id)
                
            except asyncio.TimeoutError:
                await self.fail_task(task_id, f"Task timeout after {task.timeout}s")
                return await self._get_task_result(task_id)
                
        except Exception as e:
            await self.fail_task(task_id, str(e))
            return await self._get_task_result(task_id)
            
    # Private methods
    async def _get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result from Redis"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            result_data = await redis_client.hget(self.keys['results'], task_id)
            if not result_data:
                return None
                
            result_dict = json.loads(result_data.decode('utf-8'))
            
            # Convert string dates back to datetime
            for field in ['started_at', 'completed_at']:
                if result_dict.get(field):
                    result_dict[field] = datetime.fromisoformat(result_dict[field])
                    
            # Convert status back to enum
            result_dict['status'] = TaskStatus(result_dict['status'])
            
            return TaskResult(**result_dict)
            
        finally:
            await redis_client.close()
            
    async def _update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            current_result = await self._get_task_result(task_id)
            if current_result:
                current_result.status = status
                result_data = json.dumps(asdict(current_result), default=str)
                await redis_client.hset(self.keys['results'], task_id, result_data)
                
        finally:
            await redis_client.close()
            
    async def _update_task_start_time(self, task_id: str):
        """Update task start time"""
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        try:
            current_result = await self._get_task_result(task_id)
            if current_result:
                current_result.started_at = datetime.now()
                result_data = json.dumps(asdict(current_result), default=str)
                await redis_client.hset(self.keys['results'], task_id, result_data)
                
        finally:
            await redis_client.close()
            
    async def _mark_task_expired(self, task_id: str):
        """Mark task as expired"""
        await self._update_task_status(task_id, TaskStatus.EXPIRED)
        logger.warning(f"⏰ Task {task_id} expired")
        
    async def _scheduler_loop(self):
        """Background task scheduler"""
        while self._running:
            try:
                redis_client = redis.Redis(connection_pool=self.redis_pool)
                
                try:
                    # Get tasks ready for scheduling
                    now = time.time()
                    ready_tasks = await redis_client.zrangebyscore(
                        self.keys['scheduled'], 
                        '-inf', 
                        now,
                        withscores=True
                    )
                    
                    for task_id_bytes, score in ready_tasks:
                        task_id = task_id_bytes.decode('utf-8')
                        
                        # Get task definition to determine priority
                        task_data = await redis_client.hget(self.keys['tasks'], task_id)
                        if task_data:
                            task_dict = json.loads(task_data.decode('utf-8'))
                            priority = TaskPriority(task_dict['priority'])
                            
                            # Move to appropriate queue
                            queue_name = self.queues[priority]
                            await redis_client.lpush(queue_name, task_id)
                            
                            # Remove from scheduled set
                            await redis_client.zrem(self.keys['scheduled'], task_id)
                            
                            # Update status
                            await self._update_task_status(task_id, TaskStatus.QUEUED)
                            
                            logger.info(f"⏰ Scheduled task {task_id} moved to {priority.name} queue")
                            
                finally:
                    await redis_client.close()
                    
                # Sleep before next check
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                await asyncio.sleep(10)
                
    async def _cleanup_loop(self):
        """Background cleanup of completed tasks and metrics"""
        while self._running:
            try:
                redis_client = redis.Redis(connection_pool=self.redis_pool)
                
                try:
                    # Clean up old completed tasks (older than 1 hour)
                    cutoff_time = datetime.now() - timedelta(hours=1)
                    
                    # Get all results
                    all_results = await redis_client.hgetall(self.keys['results'])
                    
                    for task_id_bytes, result_data in all_results.items():
                        task_id = task_id_bytes.decode('utf-8')
                        result_dict = json.loads(result_data.decode('utf-8'))
                        
                        # Check if task is old and completed
                        if result_dict.get('completed_at'):
                            completed_at = datetime.fromisoformat(result_dict['completed_at'])
                            status = TaskStatus(result_dict['status'])
                            
                            if (completed_at < cutoff_time and 
                                status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.EXPIRED]):
                                
                                # Remove task definition and result
                                await redis_client.hdel(self.keys['tasks'], task_id)
                                await redis_client.hdel(self.keys['results'], task_id)
                                
                                logger.debug(f"🧹 Cleaned up old task {task_id}")
                                
                finally:
                    await redis_client.close()
                    
                # Sleep for 1 hour between cleanups
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in cleanup loop: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
                
    async def _metrics_loop(self):
        """Background metrics collection"""
        while self._running:
            try:
                # Update queue size metrics
                redis_client = redis.Redis(connection_pool=self.redis_pool)
                
                try:
                    for priority, queue_name in self.queues.items():
                        size = await redis_client.llen(queue_name)
                        self.metrics['queue_sizes'][priority.name] = size
                        
                finally:
                    await redis_client.close()
                    
                # Sleep for 30 seconds between metrics updates
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in metrics loop: {e}")
                await asyncio.sleep(60)


# Example task handlers
async def example_data_processing_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Example data processing task"""
    data = payload.get('data', [])
    operation = payload.get('operation', 'sum')
    
    # Simulate processing time
    await asyncio.sleep(2)
    
    if operation == 'sum':
        result = sum(data)
    elif operation == 'average':
        result = sum(data) / len(data) if data else 0
    elif operation == 'count':
        result = len(data)
    else:
        raise ValueError(f"Unknown operation: {operation}")
        
    return {
        'operation': operation,
        'input_size': len(data),
        'result': result,
        'processed_at': datetime.now().isoformat()
    }


async def example_ai_inference_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Example AI inference task"""
    prompt = payload.get('prompt', '')
    model = payload.get('model', 'default')
    
    # Simulate AI inference
    await asyncio.sleep(5)
    
    return {
        'prompt': prompt,
        'model': model,
        'response': f"AI response to: {prompt}",
        'tokens_used': len(prompt.split()) * 2,
        'inference_time': 5.0
    }


# Example usage and testing
async def test_distributed_task_queue():
    """Test the distributed task queue"""
    
    # Initialize queue
    task_queue = DistributedTaskQueue()
    await task_queue.initialize()
    await task_queue.start()
    
    # Register handlers
    task_queue.register_handler('data_processing', example_data_processing_task)
    task_queue.register_handler('ai_inference', example_ai_inference_task)
    
    try:
        # Create test tasks
        tasks = [
            TaskDefinition(
                id="",
                name="Sum calculation",
                handler="data_processing",
                payload={'data': [1, 2, 3, 4, 5], 'operation': 'sum'},
                priority=TaskPriority.HIGH
            ),
            TaskDefinition(
                id="",
                name="AI inference",
                handler="ai_inference", 
                payload={'prompt': 'What is the meaning of life?', 'model': 'gpt-3.5'},
                priority=TaskPriority.NORMAL
            ),
            TaskDefinition(
                id="",
                name="Average calculation",
                handler="data_processing",
                payload={'data': [10, 20, 30], 'operation': 'average'},
                priority=TaskPriority.LOW,
                scheduled_at=datetime.now() + timedelta(seconds=10)
            )
        ]
        
        # Enqueue tasks
        task_ids = []
        for task in tasks:
            task_id = await task_queue.enqueue(task)
            task_ids.append(task_id)
            print(f"📥 Enqueued task: {task_id}")
            
        # Process tasks
        print("\n🔄 Processing tasks...")
        
        for i in range(5):  # Try to process multiple times
            task = await task_queue.dequeue(timeout=2)
            
            if task:
                print(f"📤 Dequeued task: {task.id} ({task.name})")
                result = await task_queue.process_task(task)
                print(f"✅ Task {task.id} completed with status: {result.status.value}")
                
                if result.result:
                    print(f"   Result: {result.result}")
                    
            else:
                print("⏰ No tasks available")
                
        # Check final statistics
        stats = await task_queue.get_queue_stats()
        print(f"\n📊 Queue Statistics:")
        print(f"   Tasks completed: {stats['tasks_completed']}")
        print(f"   Tasks failed: {stats['tasks_failed']}")
        print(f"   Average processing time: {stats['avg_processing_time']:.2f}s")
        print(f"   Processing queue: {stats['processing_count']}")
        
        # Get task results
        print(f"\n📋 Task Results:")
        for task_id in task_ids:
            result = await task_queue.get_task_result(task_id)
            if result:
                print(f"   {task_id}: {result.status.value}")
                
    finally:
        await task_queue.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_distributed_task_queue())