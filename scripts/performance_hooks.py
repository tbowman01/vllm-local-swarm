#!/usr/bin/env python3
"""
vLLM Local Swarm Performance Monitoring Hooks
============================================

Real-time performance monitoring hooks that integrate with the swarm operation:
- Pre-operation performance baseline capture
- Post-operation performance analysis and comparison
- Automatic bottleneck detection during operations
- Performance regression detection and alerting
- Integration with Claude Flow hook system
"""

import asyncio
import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
    import psutil
    import aiohttp
    from contextlib import asynccontextmanager
except ImportError:
    print("Installing performance hooks dependencies...")
    import subprocess
    subprocess.run([
        "pip", "install", 
        "redis", "psutil", "aiohttp"
    ], check=True)
    import redis.asyncio as redis
    import psutil
    import aiohttp
    from contextlib import asynccontextmanager

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from scripts.bottleneck_detector import BottleneckDetector, BottleneckSeverity

logger = logging.getLogger(__name__)


class HookPhase(Enum):
    """Performance hook execution phases"""
    PRE_OPERATION = "pre_operation"
    POST_OPERATION = "post_operation"
    DURING_OPERATION = "during_operation"
    ON_ERROR = "on_error"


class PerformanceThreshold(Enum):
    """Performance threshold levels"""
    EXCELLENT = 0.95
    GOOD = 0.80
    ACCEPTABLE = 0.65
    POOR = 0.50
    CRITICAL = 0.30


@dataclass
class PerformanceBaseline:
    """Performance baseline measurement"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    response_times: Dict[str, float]
    queue_sizes: Dict[str, int]
    cache_hit_rate: float
    active_agents: int
    processing_tasks: int
    system_health: str


@dataclass
class PerformanceComparison:
    """Comparison between baseline and current performance"""
    baseline: PerformanceBaseline
    current: PerformanceBaseline
    performance_delta: Dict[str, float]
    regression_detected: bool
    improvement_detected: bool
    threshold_violations: List[str]
    recommendations: List[str]


@dataclass
class HookResult:
    """Result of a performance hook execution"""
    hook_name: str
    phase: HookPhase
    success: bool
    execution_time: float
    performance_data: Dict[str, Any]
    alerts: List[str]
    recommendations: List[str]
    should_abort: bool = False


class PerformanceHookManager:
    """
    Performance monitoring hooks manager for vLLM Local Swarm operations
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 alert_thresholds: Dict[str, float] = None):
        self.redis_url = redis_url
        self.alert_thresholds = alert_thresholds or {
            'cpu_usage': 0.90,
            'memory_usage': 0.85,
            'response_time_increase': 2.0,  # 2x slower
            'cache_hit_rate_decrease': 0.20,  # 20% decrease
            'queue_size_increase': 3.0  # 3x larger
        }
        
        # Performance monitoring
        self.baseline: Optional[PerformanceBaseline] = None
        self.bottleneck_detector = BottleneckDetector(redis_url=redis_url)
        
        # Hook registry
        self.hooks: Dict[HookPhase, List[Callable]] = {
            HookPhase.PRE_OPERATION: [],
            HookPhase.POST_OPERATION: [],
            HookPhase.DURING_OPERATION: [],
            HookPhase.ON_ERROR: []
        }
        
        # Service endpoints for health checking
        self.service_endpoints = {
            'auth_service': 'http://localhost:8005/health',
            'orchestrator': 'http://localhost:8006/health',
            'memory_api': 'http://localhost:8003/health',
            'monitoring': 'http://localhost:8009/health',
            'langfuse': 'http://localhost:3000/api/public/health',
            'qdrant': 'http://localhost:6333/health'
        }
        
        # Performance history
        self.performance_history: List[PerformanceBaseline] = []
        self.max_history_size = 100
        
    def register_hook(self, phase: HookPhase, hook_func: Callable):
        """Register a performance hook for a specific phase"""
        self.hooks[phase].append(hook_func)
        logger.info(f"📎 Registered {hook_func.__name__} hook for {phase.value}")
    
    async def execute_pre_operation_hooks(self, operation_name: str, context: Dict[str, Any] = None) -> List[HookResult]:
        """Execute pre-operation performance hooks"""
        logger.info(f"🔄 Executing pre-operation hooks for: {operation_name}")
        
        context = context or {}
        results = []
        
        try:
            # Capture performance baseline
            self.baseline = await self._capture_performance_baseline()
            logger.info("📊 Captured performance baseline")
            
            # Execute registered pre-operation hooks
            for hook in self.hooks[HookPhase.PRE_OPERATION]:
                start_time = time.time()
                try:
                    hook_result = await hook(operation_name, context, self.baseline)
                    hook_result.execution_time = time.time() - start_time
                    results.append(hook_result)
                    
                    if hook_result.should_abort:
                        logger.warning(f"⚠️ Hook {hook.__name__} requested operation abort")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Pre-operation hook {hook.__name__} failed: {e}")
                    results.append(HookResult(
                        hook_name=hook.__name__,
                        phase=HookPhase.PRE_OPERATION,
                        success=False,
                        execution_time=time.time() - start_time,
                        performance_data={},
                        alerts=[f"Hook execution failed: {e}"],
                        recommendations=[]
                    ))
            
            # Built-in performance check
            builtin_result = await self._builtin_pre_operation_check(operation_name, context)
            results.append(builtin_result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to execute pre-operation hooks: {e}")
            return [HookResult(
                hook_name="pre_operation_manager",
                phase=HookPhase.PRE_OPERATION,
                success=False,
                execution_time=0.0,
                performance_data={},
                alerts=[f"Hook manager failed: {e}"],
                recommendations=[]
            )]
    
    async def execute_post_operation_hooks(self, operation_name: str, context: Dict[str, Any] = None,
                                         operation_result: Any = None) -> List[HookResult]:
        """Execute post-operation performance hooks"""
        logger.info(f"🔄 Executing post-operation hooks for: {operation_name}")
        
        context = context or {}
        results = []
        
        try:
            # Capture current performance
            current_performance = await self._capture_performance_baseline()
            
            # Compare with baseline
            comparison = None
            if self.baseline:
                comparison = await self._compare_performance(self.baseline, current_performance)
                logger.info(f"📈 Performance comparison completed")
            
            # Execute registered post-operation hooks
            for hook in self.hooks[HookPhase.POST_OPERATION]:
                start_time = time.time()
                try:
                    hook_result = await hook(operation_name, context, current_performance, 
                                           comparison, operation_result)
                    hook_result.execution_time = time.time() - start_time
                    results.append(hook_result)
                    
                except Exception as e:
                    logger.error(f"❌ Post-operation hook {hook.__name__} failed: {e}")
                    results.append(HookResult(
                        hook_name=hook.__name__,
                        phase=HookPhase.POST_OPERATION,
                        success=False,
                        execution_time=time.time() - start_time,
                        performance_data={},
                        alerts=[f"Hook execution failed: {e}"],
                        recommendations=[]
                    ))
            
            # Built-in performance analysis
            builtin_result = await self._builtin_post_operation_analysis(
                operation_name, current_performance, comparison
            )
            results.append(builtin_result)
            
            # Store current performance in history
            self._add_to_history(current_performance)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to execute post-operation hooks: {e}")
            return [HookResult(
                hook_name="post_operation_manager",
                phase=HookPhase.POST_OPERATION,
                success=False,
                execution_time=0.0,
                performance_data={},
                alerts=[f"Hook manager failed: {e}"],
                recommendations=[]
            )]
    
    async def execute_during_operation_hooks(self, operation_name: str, 
                                           progress: float = 0.0,
                                           context: Dict[str, Any] = None) -> List[HookResult]:
        """Execute during-operation performance monitoring hooks"""
        
        context = context or {}
        results = []
        
        try:
            # Capture current performance
            current_performance = await self._capture_performance_baseline()
            
            # Execute registered during-operation hooks
            for hook in self.hooks[HookPhase.DURING_OPERATION]:
                start_time = time.time()
                try:
                    hook_result = await hook(operation_name, progress, context, current_performance)
                    hook_result.execution_time = time.time() - start_time
                    results.append(hook_result)
                    
                except Exception as e:
                    logger.error(f"❌ During-operation hook {hook.__name__} failed: {e}")
                    results.append(HookResult(
                        hook_name=hook.__name__,
                        phase=HookPhase.DURING_OPERATION,
                        success=False,
                        execution_time=time.time() - start_time,
                        performance_data={},
                        alerts=[f"Hook execution failed: {e}"],
                        recommendations=[]
                    ))
            
            # Built-in monitoring
            builtin_result = await self._builtin_during_operation_monitoring(
                operation_name, progress, current_performance
            )
            results.append(builtin_result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to execute during-operation hooks: {e}")
            return []
    
    async def execute_error_hooks(self, operation_name: str, error: Exception,
                                context: Dict[str, Any] = None) -> List[HookResult]:
        """Execute error handling performance hooks"""
        logger.warning(f"🚨 Executing error hooks for: {operation_name}")
        
        context = context or {}
        results = []
        
        try:
            # Capture performance at error time
            error_performance = await self._capture_performance_baseline()
            
            # Execute registered error hooks
            for hook in self.hooks[HookPhase.ON_ERROR]:
                start_time = time.time()
                try:
                    hook_result = await hook(operation_name, error, context, error_performance)
                    hook_result.execution_time = time.time() - start_time
                    results.append(hook_result)
                    
                except Exception as hook_error:
                    logger.error(f"❌ Error hook {hook.__name__} failed: {hook_error}")
                    results.append(HookResult(
                        hook_name=hook.__name__,
                        phase=HookPhase.ON_ERROR,
                        success=False,
                        execution_time=time.time() - start_time,
                        performance_data={},
                        alerts=[f"Hook execution failed: {hook_error}"],
                        recommendations=[]
                    ))
            
            # Built-in error analysis
            builtin_result = await self._builtin_error_analysis(operation_name, error, error_performance)
            results.append(builtin_result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to execute error hooks: {e}")
            return []
    
    @asynccontextmanager
    async def performance_monitoring(self, operation_name: str, context: Dict[str, Any] = None):
        """
        Context manager for automatic performance monitoring around operations
        """
        pre_results = []
        post_results = []
        error_results = []
        
        try:
            # Execute pre-operation hooks
            pre_results = await self.execute_pre_operation_hooks(operation_name, context)
            
            # Check if any pre-operation hook requested abort
            if any(result.should_abort for result in pre_results):
                abort_reasons = [result.alerts for result in pre_results if result.should_abort]
                raise RuntimeError(f"Operation aborted by pre-hooks: {abort_reasons}")
            
            yield {
                'pre_results': pre_results,
                'during_hook': self._create_during_hook_callback(operation_name, context)
            }
            
        except Exception as e:
            # Execute error hooks
            error_results = await self.execute_error_hooks(operation_name, e, context)
            raise
            
        finally:
            # Always execute post-operation hooks
            try:
                post_results = await self.execute_post_operation_hooks(
                    operation_name, context, getattr(e, 'operation_result', None) if 'e' in locals() else None
                )
            except Exception as post_error:
                logger.error(f"❌ Post-operation hooks failed: {post_error}")
    
    def _create_during_hook_callback(self, operation_name: str, context: Dict[str, Any]):
        """Create callback for during-operation monitoring"""
        async def during_callback(progress: float = 0.0, update_context: Dict[str, Any] = None):
            updated_context = {**(context or {}), **(update_context or {})}
            return await self.execute_during_operation_hooks(operation_name, progress, updated_context)
        
        return during_callback
    
    async def _capture_performance_baseline(self) -> PerformanceBaseline:
        """Capture current system performance baseline"""
        
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1) / 100.0
        memory = psutil.virtual_memory()
        memory_usage = memory.percent / 100.0
        
        # Service response times
        response_times = await self._measure_service_response_times()
        
        # Queue sizes (from Redis)
        queue_sizes = await self._get_queue_sizes()
        
        # Cache hit rate
        cache_hit_rate = await self._get_cache_hit_rate()
        
        # Agent and task counts
        active_agents, processing_tasks = await self._get_agent_task_counts()
        
        # System health
        system_health = await self._assess_system_health()
        
        return PerformanceBaseline(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            response_times=response_times,
            queue_sizes=queue_sizes,
            cache_hit_rate=cache_hit_rate,
            active_agents=active_agents,
            processing_tasks=processing_tasks,
            system_health=system_health
        )
    
    async def _measure_service_response_times(self) -> Dict[str, float]:
        """Measure response times for all services"""
        response_times = {}
        
        async with aiohttp.ClientSession() as session:
            for service, endpoint in self.service_endpoints.items():
                try:
                    start_time = time.time()
                    async with session.get(endpoint, timeout=5) as response:
                        response_time = time.time() - start_time
                        response_times[service] = response_time
                except Exception:
                    response_times[service] = 5.0  # Timeout value
        
        return response_times
    
    async def _get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes from Redis"""
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            
            queues = {
                'critical': await redis_client.llen('vllm_task_queue:critical'),
                'high': await redis_client.llen('vllm_task_queue:high'),
                'normal': await redis_client.llen('vllm_task_queue:normal'),
                'low': await redis_client.llen('vllm_task_queue:low'),
                'background': await redis_client.llen('vllm_task_queue:background')
            }
            
            await redis_client.close()
            return queues
            
        except Exception:
            return {'critical': 0, 'high': 0, 'normal': 0, 'low': 0, 'background': 0}
    
    async def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate from Redis"""
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            info = await redis_client.info('stats')
            
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            
            if hits + misses > 0:
                hit_rate = hits / (hits + misses)
            else:
                hit_rate = 0.0
            
            await redis_client.close()
            return hit_rate
            
        except Exception:
            return 0.0
    
    async def _get_agent_task_counts(self) -> Tuple[int, int]:
        """Get active agent and processing task counts"""
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            
            # Count active agents (simplified)
            active_agents = await redis_client.scard('active_agents')
            
            # Count processing tasks
            processing_tasks = await redis_client.scard('vllm_task_queue:processing')
            
            await redis_client.close()
            return active_agents, processing_tasks
            
        except Exception:
            return 0, 0
    
    async def _assess_system_health(self) -> str:
        """Assess overall system health"""
        try:
            # Check if critical services are responding
            critical_services = ['auth_service', 'orchestrator', 'memory_api']
            healthy_services = 0
            
            for service in critical_services:
                endpoint = self.service_endpoints.get(service)
                if endpoint:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(endpoint, timeout=2) as response:
                                if response.status == 200:
                                    healthy_services += 1
                    except Exception:
                        pass
            
            if healthy_services == len(critical_services):
                return "healthy"
            elif healthy_services > len(critical_services) / 2:
                return "degraded"
            else:
                return "unhealthy"
                
        except Exception:
            return "unknown"
    
    async def _compare_performance(self, baseline: PerformanceBaseline, 
                                 current: PerformanceBaseline) -> PerformanceComparison:
        """Compare current performance with baseline"""
        
        # Calculate performance deltas
        performance_delta = {
            'cpu_usage': current.cpu_usage - baseline.cpu_usage,
            'memory_usage': current.memory_usage - baseline.memory_usage,
            'cache_hit_rate': current.cache_hit_rate - baseline.cache_hit_rate,
            'active_agents': current.active_agents - baseline.active_agents,
            'processing_tasks': current.processing_tasks - baseline.processing_tasks
        }
        
        # Calculate average response time change
        baseline_avg_response = statistics.mean(baseline.response_times.values()) if baseline.response_times else 0
        current_avg_response = statistics.mean(current.response_times.values()) if current.response_times else 0
        performance_delta['avg_response_time'] = current_avg_response - baseline_avg_response
        
        # Detect regressions and improvements
        regression_detected = (
            performance_delta['cpu_usage'] > 0.1 or
            performance_delta['memory_usage'] > 0.1 or
            performance_delta['avg_response_time'] > 1.0 or
            performance_delta['cache_hit_rate'] < -0.2
        )
        
        improvement_detected = (
            performance_delta['cpu_usage'] < -0.05 and
            performance_delta['memory_usage'] < -0.05 and
            performance_delta['avg_response_time'] < -0.2 and
            performance_delta['cache_hit_rate'] > 0.1
        )
        
        # Check threshold violations
        threshold_violations = []
        if current.cpu_usage > self.alert_thresholds['cpu_usage']:
            threshold_violations.append(f"CPU usage: {current.cpu_usage:.1%}")
        if current.memory_usage > self.alert_thresholds['memory_usage']:
            threshold_violations.append(f"Memory usage: {current.memory_usage:.1%}")
        
        # Generate recommendations
        recommendations = []
        if performance_delta['cpu_usage'] > 0.2:
            recommendations.append("Consider scaling CPU resources or optimizing CPU-intensive operations")
        if performance_delta['memory_usage'] > 0.2:
            recommendations.append("Consider increasing memory allocation or investigating memory leaks")
        if performance_delta['cache_hit_rate'] < -0.3:
            recommendations.append("Consider increasing cache size or optimizing cache strategies")
        
        return PerformanceComparison(
            baseline=baseline,
            current=current,
            performance_delta=performance_delta,
            regression_detected=regression_detected,
            improvement_detected=improvement_detected,
            threshold_violations=threshold_violations,
            recommendations=recommendations
        )
    
    def _add_to_history(self, performance: PerformanceBaseline):
        """Add performance data to history"""
        self.performance_history.append(performance)
        
        # Maintain history size limit
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size:]
    
    # Built-in hook implementations
    async def _builtin_pre_operation_check(self, operation_name: str, 
                                         context: Dict[str, Any]) -> HookResult:
        """Built-in pre-operation performance check"""
        alerts = []
        recommendations = []
        should_abort = False
        
        if not self.baseline:
            return HookResult(
                hook_name="builtin_pre_check",
                phase=HookPhase.PRE_OPERATION,
                success=False,
                execution_time=0.0,
                performance_data={},
                alerts=["Failed to capture baseline"],
                recommendations=[],
                should_abort=True
            )
        
        # Check system resources
        if self.baseline.cpu_usage > 0.9:
            alerts.append(f"High CPU usage detected: {self.baseline.cpu_usage:.1%}")
            should_abort = True
        
        if self.baseline.memory_usage > 0.9:
            alerts.append(f"High memory usage detected: {self.baseline.memory_usage:.1%}")
            should_abort = True
        
        if self.baseline.system_health == "unhealthy":
            alerts.append("System health check failed")
            should_abort = True
        
        # Check service response times
        slow_services = [service for service, time_val in self.baseline.response_times.items() 
                        if time_val > 3.0]
        if slow_services:
            alerts.append(f"Slow services detected: {', '.join(slow_services)}")
            recommendations.append("Consider restarting slow services or investigating bottlenecks")
        
        return HookResult(
            hook_name="builtin_pre_check",
            phase=HookPhase.PRE_OPERATION,
            success=len(alerts) == 0,
            execution_time=0.1,
            performance_data=asdict(self.baseline),
            alerts=alerts,
            recommendations=recommendations,
            should_abort=should_abort
        )
    
    async def _builtin_post_operation_analysis(self, operation_name: str,
                                             current: PerformanceBaseline,
                                             comparison: Optional[PerformanceComparison]) -> HookResult:
        """Built-in post-operation performance analysis"""
        alerts = []
        recommendations = []
        
        if not comparison:
            return HookResult(
                hook_name="builtin_post_analysis",
                phase=HookPhase.POST_OPERATION,
                success=False,
                execution_time=0.0,
                performance_data={},
                alerts=["No baseline available for comparison"],
                recommendations=[]
            )
        
        # Check for performance regressions
        if comparison.regression_detected:
            alerts.append("Performance regression detected")
            recommendations.extend(comparison.recommendations)
        
        # Check for improvements
        if comparison.improvement_detected:
            logger.info("✅ Performance improvement detected")
        
        # Check threshold violations
        if comparison.threshold_violations:
            alerts.extend(comparison.threshold_violations)
        
        return HookResult(
            hook_name="builtin_post_analysis",
            phase=HookPhase.POST_OPERATION,
            success=not comparison.regression_detected,
            execution_time=0.1,
            performance_data={
                'comparison': asdict(comparison),
                'current_performance': asdict(current)
            },
            alerts=alerts,
            recommendations=recommendations
        )
    
    async def _builtin_during_operation_monitoring(self, operation_name: str,
                                                 progress: float,
                                                 current: PerformanceBaseline) -> HookResult:
        """Built-in during-operation monitoring"""
        alerts = []
        recommendations = []
        
        # Check for resource spikes
        if current.cpu_usage > 0.95:
            alerts.append(f"Critical CPU usage: {current.cpu_usage:.1%}")
        
        if current.memory_usage > 0.95:
            alerts.append(f"Critical memory usage: {current.memory_usage:.1%}")
        
        # Check service health
        if current.system_health == "unhealthy":
            alerts.append("System health degraded during operation")
        
        return HookResult(
            hook_name="builtin_during_monitoring",
            phase=HookPhase.DURING_OPERATION,
            success=len(alerts) == 0,
            execution_time=0.1,
            performance_data=asdict(current),
            alerts=alerts,
            recommendations=recommendations
        )
    
    async def _builtin_error_analysis(self, operation_name: str,
                                    error: Exception,
                                    error_performance: PerformanceBaseline) -> HookResult:
        """Built-in error analysis"""
        alerts = [f"Operation failed: {str(error)}"]
        recommendations = []
        
        # Analyze performance at error time
        if error_performance.cpu_usage > 0.9:
            recommendations.append("High CPU usage may have contributed to the error")
        
        if error_performance.memory_usage > 0.9:
            recommendations.append("High memory usage may have contributed to the error")
        
        if error_performance.system_health != "healthy":
            recommendations.append("System health issues may have contributed to the error")
        
        return HookResult(
            hook_name="builtin_error_analysis",
            phase=HookPhase.ON_ERROR,
            success=False,
            execution_time=0.1,
            performance_data=asdict(error_performance),
            alerts=alerts,
            recommendations=recommendations
        )


# Example custom hook implementations
async def gpu_monitoring_hook(operation_name: str, context: Dict[str, Any],
                            baseline: PerformanceBaseline) -> HookResult:
    """Custom hook for GPU monitoring"""
    alerts = []
    recommendations = []
    
    try:
        # Check GPU utilization
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu', 
                               '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                utilization, temperature = map(int, line.split(', '))
                
                if utilization > 95:
                    alerts.append(f"GPU {i} utilization critical: {utilization}%")
                
                if temperature > 80:
                    alerts.append(f"GPU {i} temperature high: {temperature}°C")
                    recommendations.append("Consider improving GPU cooling")
        
        return HookResult(
            hook_name="gpu_monitoring_hook",
            phase=HookPhase.PRE_OPERATION,
            success=len(alerts) == 0,
            execution_time=0.2,
            performance_data={'gpu_check': True},
            alerts=alerts,
            recommendations=recommendations
        )
        
    except Exception as e:
        return HookResult(
            hook_name="gpu_monitoring_hook",
            phase=HookPhase.PRE_OPERATION,
            success=False,
            execution_time=0.1,
            performance_data={},
            alerts=[f"GPU monitoring failed: {e}"],
            recommendations=[]
        )


async def bottleneck_detection_hook(operation_name: str, context: Dict[str, Any],
                                  current_performance: PerformanceBaseline,
                                  comparison: Optional[PerformanceComparison] = None,
                                  operation_result: Any = None) -> HookResult:
    """Custom hook that runs bottleneck detection after operations"""
    alerts = []
    recommendations = []
    
    try:
        # Run bottleneck detection
        detector = BottleneckDetector(time_range="5m", threshold=15.0)
        
        # Create sample issues from performance data
        sample_issues = []
        if current_performance.cpu_usage > 0.8:
            sample_issues.append({
                'category': 'resource_usage',
                'severity': 'warning' if current_performance.cpu_usage < 0.9 else 'critical',
                'title': 'High CPU Usage',
                'impact_percentage': (current_performance.cpu_usage - 0.5) * 100
            })
        
        if current_performance.cache_hit_rate < 0.7:
            sample_issues.append({
                'category': 'memory_system',
                'severity': 'warning',
                'title': 'Low Cache Hit Rate',
                'impact_percentage': (0.8 - current_performance.cache_hit_rate) * 100
            })
        
        # Generate quick analysis
        if sample_issues:
            critical_issues = [i for i in sample_issues if i['severity'] == 'critical']
            warning_issues = [i for i in sample_issues if i['severity'] == 'warning']
            
            if critical_issues:
                alerts.extend([issue['title'] for issue in critical_issues])
                recommendations.append("Run full bottleneck analysis with: python scripts/bottleneck_detector.py")
            
            if warning_issues:
                recommendations.extend([f"Monitor {issue['title']}" for issue in warning_issues])
        
        return HookResult(
            hook_name="bottleneck_detection_hook",
            phase=HookPhase.POST_OPERATION,
            success=len(alerts) == 0,
            execution_time=1.0,
            performance_data={'bottleneck_issues': sample_issues},
            alerts=alerts,
            recommendations=recommendations
        )
        
    except Exception as e:
        return HookResult(
            hook_name="bottleneck_detection_hook", 
            phase=HookPhase.POST_OPERATION,
            success=False,
            execution_time=0.1,
            performance_data={},
            alerts=[f"Bottleneck detection failed: {e}"],
            recommendations=[]
        )


# Example usage
async def example_operation_with_hooks():
    """Example of using performance hooks around an operation"""
    
    # Create hook manager
    hook_manager = PerformanceHookManager()
    
    # Register custom hooks
    hook_manager.register_hook(HookPhase.PRE_OPERATION, gpu_monitoring_hook)
    hook_manager.register_hook(HookPhase.POST_OPERATION, bottleneck_detection_hook)
    
    operation_name = "example_ai_workflow"
    context = {
        'workflow_type': 'content_creation',
        'expected_duration': 30,
        'resource_intensive': True
    }
    
    try:
        async with hook_manager.performance_monitoring(operation_name, context) as monitoring:
            logger.info("🔄 Starting example operation...")
            
            # Simulate operation with progress callbacks
            for progress in [0.0, 0.25, 0.5, 0.75, 1.0]:
                await asyncio.sleep(2)  # Simulate work
                
                # Call during-operation monitoring
                during_results = await monitoring['during_hook'](progress)
                
                # Check for critical alerts
                critical_alerts = [r for r in during_results 
                                 if any('Critical' in alert for alert in r.alerts)]
                if critical_alerts:
                    logger.warning("⚠️ Critical alerts during operation")
                
                logger.info(f"📊 Operation progress: {progress:.0%}")
            
            logger.info("✅ Example operation completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Example operation failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_operation_with_hooks())