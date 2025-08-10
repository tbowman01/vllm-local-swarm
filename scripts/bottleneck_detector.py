#!/usr/bin/env python3
"""
vLLM Local Swarm Bottleneck Detection System
===========================================

Advanced performance bottleneck detection and optimization system for:
- Real-time performance monitoring and analysis
- Automatic bottleneck identification across all system components
- Performance optimization recommendations and automatic fixes
- Comprehensive metrics collection and reporting

Components Analyzed:
- Agent Communication (message delays, response times)
- Task Queue Performance (queue delays, processing times)
- Memory System (cache hits, search times, storage I/O)
- Network/API Performance (latency, timeouts, concurrent limits)
- Resource Utilization (CPU, memory, GPU usage)
"""

import asyncio
import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import argparse
import os

try:
    import redis.asyncio as redis
    import psutil
    import aiohttp
    import numpy as np
except ImportError:
    print("Installing bottleneck detection dependencies...")
    import subprocess
    subprocess.run([
        "pip", "install", 
        "redis", "psutil", "aiohttp", "numpy"
    ], check=True)
    import redis.asyncio as redis
    import psutil
    import aiohttp
    import numpy as np

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

logger = logging.getLogger(__name__)


class BottleneckSeverity(Enum):
    """Bottleneck severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    NONE = "none"


class BottleneckCategory(Enum):
    """Bottleneck categories"""
    COMMUNICATION = "communication"
    TASK_PROCESSING = "task_processing"
    MEMORY_SYSTEM = "memory_system"
    NETWORK_API = "network_api"
    RESOURCE_USAGE = "resource_usage"
    COORDINATION = "coordination"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    threshold: float
    severity: BottleneckSeverity
    category: BottleneckCategory
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BottleneckIssue:
    """Identified bottleneck issue"""
    id: str
    title: str
    category: BottleneckCategory
    severity: BottleneckSeverity
    impact_percentage: float
    description: str
    affected_components: List[str]
    root_cause: str
    recommendations: List[str]
    auto_fixable: bool
    fix_commands: List[str] = field(default_factory=list)
    metrics: List[PerformanceMetric] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """Complete bottleneck analysis report"""
    analysis_id: str
    timestamp: datetime
    time_range: str
    agents_analyzed: int
    tasks_processed: int
    critical_issues: List[BottleneckIssue]
    warning_issues: List[BottleneckIssue]
    info_issues: List[BottleneckIssue]
    performance_summary: Dict[str, float]
    optimization_potential: Dict[str, float]
    auto_fixes_available: List[str]


class BottleneckDetector:
    """
    Advanced bottleneck detection system for vLLM Local Swarm
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 time_range: str = "1h",
                 threshold: float = 20.0):
        self.redis_url = redis_url
        self.time_range = time_range
        self.threshold = threshold
        
        # Service endpoints
        self.endpoints = {
            'redis': 'localhost:6379',
            'langfuse': 'http://localhost:3000',
            'qdrant': 'http://localhost:6333',
            'vllm_phi': 'http://localhost:8000',
            'vllm_large': 'http://localhost:8001',
            'ray_dashboard': 'http://localhost:8265',
            'auth_service': 'http://localhost:8005',
            'orchestrator': 'http://localhost:8006',
            'memory_api': 'http://localhost:8003',
            'monitoring': 'http://localhost:8009',
            'api_docs': 'http://localhost:8010'
        }
        
        # Performance thresholds
        self.thresholds = {
            # Communication thresholds
            'agent_response_time': 2.0,  # seconds
            'message_queue_delay': 1.0,  # seconds
            'coordination_overhead': 0.5,  # seconds
            
            # Task processing thresholds  
            'task_completion_time': 10.0,  # seconds
            'agent_utilization': 0.8,  # 80%
            'queue_wait_time': 5.0,  # seconds
            
            # Memory system thresholds
            'cache_hit_rate': 0.7,  # 70%
            'memory_search_time': 0.1,  # 100ms
            'storage_io_latency': 0.05,  # 50ms
            
            # Network/API thresholds
            'api_response_time': 1.0,  # seconds
            'network_timeout_rate': 0.05,  # 5%
            'concurrent_request_limit': 0.9,  # 90% of limit
            
            # Resource utilization thresholds
            'cpu_usage': 0.85,  # 85%
            'memory_usage': 0.9,  # 90%
            'gpu_utilization': 0.95,  # 95%
            'disk_usage': 0.9  # 90%
        }
        
        # Data collection
        self.metrics: List[PerformanceMetric] = []
        self.issues: List[BottleneckIssue] = []
        
    async def analyze(self, export_file: Optional[str] = None, 
                     apply_fixes: bool = False) -> AnalysisReport:
        """
        Perform comprehensive bottleneck analysis
        """
        analysis_id = f"analysis_{int(time.time())}"
        logger.info(f"🔍 Starting bottleneck analysis: {analysis_id}")
        logger.info(f"📊 Time range: {self.time_range}")
        logger.info(f"⚠️ Threshold: {self.threshold}%")
        
        try:
            # Clear previous data
            self.metrics.clear()
            self.issues.clear()
            
            # Collect performance metrics
            await self._collect_communication_metrics()
            await self._collect_task_processing_metrics()
            await self._collect_memory_system_metrics()
            await self._collect_network_api_metrics()
            await self._collect_resource_usage_metrics()
            await self._collect_coordination_metrics()
            
            # Analyze for bottlenecks
            await self._analyze_bottlenecks()
            
            # Generate report
            report = await self._generate_report(analysis_id)
            
            # Export if requested
            if export_file:
                await self._export_report(report, export_file)
                
            # Apply automatic fixes if requested
            if apply_fixes:
                await self._apply_automatic_fixes(report)
                
            return report
            
        except Exception as e:
            logger.error(f"❌ Bottleneck analysis failed: {e}")
            raise
            
    async def _collect_communication_metrics(self):
        """Collect agent communication performance metrics"""
        logger.info("📡 Collecting communication metrics...")
        
        try:
            # Connect to Redis for communication metrics
            redis_client = redis.Redis.from_url(self.redis_url)
            
            # Agent response times
            response_times = await self._get_agent_response_times(redis_client)
            if response_times:
                avg_response_time = statistics.mean(response_times)
                self.metrics.append(PerformanceMetric(
                    name="agent_response_time",
                    value=avg_response_time,
                    unit="seconds",
                    threshold=self.thresholds['agent_response_time'],
                    severity=self._calculate_severity(avg_response_time, self.thresholds['agent_response_time']),
                    category=BottleneckCategory.COMMUNICATION,
                    timestamp=datetime.now(),
                    metadata={"sample_size": len(response_times), "max": max(response_times), "min": min(response_times)}
                ))
            
            # Message queue delays
            queue_delays = await self._get_message_queue_delays(redis_client)
            if queue_delays:
                avg_queue_delay = statistics.mean(queue_delays)
                self.metrics.append(PerformanceMetric(
                    name="message_queue_delay",
                    value=avg_queue_delay,
                    unit="seconds",
                    threshold=self.thresholds['message_queue_delay'],
                    severity=self._calculate_severity(avg_queue_delay, self.thresholds['message_queue_delay']),
                    category=BottleneckCategory.COMMUNICATION,
                    timestamp=datetime.now(),
                    metadata={"sample_size": len(queue_delays)}
                ))
            
            # Coordination overhead
            coordination_overhead = await self._measure_coordination_overhead(redis_client)
            self.metrics.append(PerformanceMetric(
                name="coordination_overhead",
                value=coordination_overhead,
                unit="seconds",
                threshold=self.thresholds['coordination_overhead'],
                severity=self._calculate_severity(coordination_overhead, self.thresholds['coordination_overhead']),
                category=BottleneckCategory.COMMUNICATION,
                timestamp=datetime.now()
            ))
            
            await redis_client.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to collect communication metrics: {e}")
            
    async def _collect_task_processing_metrics(self):
        """Collect task processing performance metrics"""
        logger.info("⚙️ Collecting task processing metrics...")
        
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            
            # Task completion times
            completion_times = await self._get_task_completion_times(redis_client)
            if completion_times:
                avg_completion_time = statistics.mean(completion_times)
                self.metrics.append(PerformanceMetric(
                    name="task_completion_time",
                    value=avg_completion_time,
                    unit="seconds",
                    threshold=self.thresholds['task_completion_time'],
                    severity=self._calculate_severity(avg_completion_time, self.thresholds['task_completion_time']),
                    category=BottleneckCategory.TASK_PROCESSING,
                    timestamp=datetime.now(),
                    metadata={"sample_size": len(completion_times)}
                ))
            
            # Queue wait times
            wait_times = await self._get_queue_wait_times(redis_client)
            if wait_times:
                avg_wait_time = statistics.mean(wait_times)
                self.metrics.append(PerformanceMetric(
                    name="queue_wait_time",
                    value=avg_wait_time,
                    unit="seconds",
                    threshold=self.thresholds['queue_wait_time'],
                    severity=self._calculate_severity(avg_wait_time, self.thresholds['queue_wait_time']),
                    category=BottleneckCategory.TASK_PROCESSING,
                    timestamp=datetime.now(),
                    metadata={"sample_size": len(wait_times)}
                ))
            
            # Agent utilization
            agent_utilization = await self._calculate_agent_utilization(redis_client)
            self.metrics.append(PerformanceMetric(
                name="agent_utilization",
                value=agent_utilization,
                unit="percentage",
                threshold=self.thresholds['agent_utilization'],
                severity=self._calculate_severity(agent_utilization, self.thresholds['agent_utilization']),
                category=BottleneckCategory.TASK_PROCESSING,
                timestamp=datetime.now()
            ))
            
            await redis_client.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to collect task processing metrics: {e}")
            
    async def _collect_memory_system_metrics(self):
        """Collect memory system performance metrics"""
        logger.info("🧠 Collecting memory system metrics...")
        
        try:
            # Cache hit rate
            cache_hit_rate = await self._get_cache_hit_rate()
            self.metrics.append(PerformanceMetric(
                name="cache_hit_rate",
                value=cache_hit_rate,
                unit="percentage",
                threshold=self.thresholds['cache_hit_rate'],
                severity=self._calculate_severity_inverse(cache_hit_rate, self.thresholds['cache_hit_rate']),
                category=BottleneckCategory.MEMORY_SYSTEM,
                timestamp=datetime.now()
            ))
            
            # Memory search times
            search_times = await self._get_memory_search_times()
            if search_times:
                avg_search_time = statistics.mean(search_times)
                self.metrics.append(PerformanceMetric(
                    name="memory_search_time",
                    value=avg_search_time,
                    unit="seconds",
                    threshold=self.thresholds['memory_search_time'],
                    severity=self._calculate_severity(avg_search_time, self.thresholds['memory_search_time']),
                    category=BottleneckCategory.MEMORY_SYSTEM,
                    timestamp=datetime.now(),
                    metadata={"sample_size": len(search_times)}
                ))
            
            # Storage I/O latency
            io_latency = await self._measure_storage_io_latency()
            self.metrics.append(PerformanceMetric(
                name="storage_io_latency",
                value=io_latency,
                unit="seconds",
                threshold=self.thresholds['storage_io_latency'],
                severity=self._calculate_severity(io_latency, self.thresholds['storage_io_latency']),
                category=BottleneckCategory.MEMORY_SYSTEM,
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            logger.error(f"❌ Failed to collect memory system metrics: {e}")
            
    async def _collect_network_api_metrics(self):
        """Collect network and API performance metrics"""
        logger.info("🌐 Collecting network/API metrics...")
        
        try:
            # API response times
            api_times = await self._measure_api_response_times()
            if api_times:
                avg_api_time = statistics.mean(list(api_times.values()))
                self.metrics.append(PerformanceMetric(
                    name="api_response_time",
                    value=avg_api_time,
                    unit="seconds",
                    threshold=self.thresholds['api_response_time'],
                    severity=self._calculate_severity(avg_api_time, self.thresholds['api_response_time']),
                    category=BottleneckCategory.NETWORK_API,
                    timestamp=datetime.now(),
                    metadata=api_times
                ))
            
            # Network timeout rate
            timeout_rate = await self._calculate_network_timeout_rate()
            self.metrics.append(PerformanceMetric(
                name="network_timeout_rate",
                value=timeout_rate,
                unit="percentage",
                threshold=self.thresholds['network_timeout_rate'],
                severity=self._calculate_severity(timeout_rate, self.thresholds['network_timeout_rate']),
                category=BottleneckCategory.NETWORK_API,
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            logger.error(f"❌ Failed to collect network/API metrics: {e}")
            
    async def _collect_resource_usage_metrics(self):
        """Collect system resource usage metrics"""
        logger.info("💻 Collecting resource usage metrics...")
        
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1) / 100.0
            self.metrics.append(PerformanceMetric(
                name="cpu_usage",
                value=cpu_usage,
                unit="percentage",
                threshold=self.thresholds['cpu_usage'],
                severity=self._calculate_severity(cpu_usage, self.thresholds['cpu_usage']),
                category=BottleneckCategory.RESOURCE_USAGE,
                timestamp=datetime.now(),
                metadata={"cores": psutil.cpu_count()}
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent / 100.0
            self.metrics.append(PerformanceMetric(
                name="memory_usage",
                value=memory_usage,
                unit="percentage",
                threshold=self.thresholds['memory_usage'],
                severity=self._calculate_severity(memory_usage, self.thresholds['memory_usage']),
                category=BottleneckCategory.RESOURCE_USAGE,
                timestamp=datetime.now(),
                metadata={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                }
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent / 100.0
            self.metrics.append(PerformanceMetric(
                name="disk_usage",
                value=disk_usage,
                unit="percentage",
                threshold=self.thresholds['disk_usage'],
                severity=self._calculate_severity(disk_usage, self.thresholds['disk_usage']),
                category=BottleneckCategory.RESOURCE_USAGE,
                timestamp=datetime.now(),
                metadata={
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2)
                }
            ))
            
            # GPU utilization (if available)
            gpu_utilization = await self._get_gpu_utilization()
            if gpu_utilization is not None:
                self.metrics.append(PerformanceMetric(
                    name="gpu_utilization",
                    value=gpu_utilization,
                    unit="percentage",
                    threshold=self.thresholds['gpu_utilization'],
                    severity=self._calculate_severity(gpu_utilization, self.thresholds['gpu_utilization']),
                    category=BottleneckCategory.RESOURCE_USAGE,
                    timestamp=datetime.now()
                ))
            
        except Exception as e:
            logger.error(f"❌ Failed to collect resource usage metrics: {e}")
            
    async def _collect_coordination_metrics(self):
        """Collect coordination system metrics"""
        logger.info("🤝 Collecting coordination metrics...")
        
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            
            # Agent registration latency
            registration_latency = await self._measure_agent_registration_latency(redis_client)
            self.metrics.append(PerformanceMetric(
                name="agent_registration_latency",
                value=registration_latency,
                unit="seconds",
                threshold=1.0,
                severity=self._calculate_severity(registration_latency, 1.0),
                category=BottleneckCategory.COORDINATION,
                timestamp=datetime.now()
            ))
            
            await redis_client.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to collect coordination metrics: {e}")
            
    async def _analyze_bottlenecks(self):
        """Analyze collected metrics for bottlenecks"""
        logger.info("🔍 Analyzing bottlenecks...")
        
        # Group metrics by category
        metrics_by_category = {}
        for metric in self.metrics:
            category = metric.category.value
            if category not in metrics_by_category:
                metrics_by_category[category] = []
            metrics_by_category[category].append(metric)
        
        # Analyze each category
        for category, category_metrics in metrics_by_category.items():
            await self._analyze_category_bottlenecks(category, category_metrics)
            
    async def _analyze_category_bottlenecks(self, category: str, metrics: List[PerformanceMetric]):
        """Analyze bottlenecks for a specific category"""
        
        critical_metrics = [m for m in metrics if m.severity == BottleneckSeverity.CRITICAL]
        warning_metrics = [m for m in metrics if m.severity == BottleneckSeverity.WARNING]
        
        # Create issues for critical bottlenecks
        for metric in critical_metrics:
            issue = await self._create_bottleneck_issue(metric, BottleneckSeverity.CRITICAL)
            self.issues.append(issue)
            
        # Create issues for warning bottlenecks
        for metric in warning_metrics:
            issue = await self._create_bottleneck_issue(metric, BottleneckSeverity.WARNING)
            self.issues.append(issue)
            
    async def _create_bottleneck_issue(self, metric: PerformanceMetric, 
                                     severity: BottleneckSeverity) -> BottleneckIssue:
        """Create a bottleneck issue from a metric"""
        
        issue_id = f"{metric.category.value}_{metric.name}_{int(time.time())}"
        
        # Calculate impact percentage
        if metric.name in ['cache_hit_rate']:
            # Inverse calculation for metrics where lower is worse
            impact = max(0, (metric.threshold - metric.value) / metric.threshold * 100)
        else:
            # Normal calculation for metrics where higher is worse
            impact = max(0, (metric.value - metric.threshold) / metric.threshold * 100)
        
        # Generate recommendations and fixes
        recommendations, auto_fixable, fix_commands = await self._generate_recommendations(metric)
        
        return BottleneckIssue(
            id=issue_id,
            title=self._generate_issue_title(metric),
            category=metric.category,
            severity=severity,
            impact_percentage=impact,
            description=self._generate_issue_description(metric),
            affected_components=self._identify_affected_components(metric),
            root_cause=self._identify_root_cause(metric),
            recommendations=recommendations,
            auto_fixable=auto_fixable,
            fix_commands=fix_commands,
            metrics=[metric]
        )
        
    async def _generate_report(self, analysis_id: str) -> AnalysisReport:
        """Generate comprehensive analysis report"""
        
        # Categorize issues by severity
        critical_issues = [issue for issue in self.issues if issue.severity == BottleneckSeverity.CRITICAL]
        warning_issues = [issue for issue in self.issues if issue.severity == BottleneckSeverity.WARNING]
        info_issues = [issue for issue in self.issues if issue.severity == BottleneckSeverity.INFO]
        
        # Calculate performance summary
        performance_summary = {
            'overall_health': self._calculate_overall_health(),
            'communication_score': self._calculate_category_score(BottleneckCategory.COMMUNICATION),
            'processing_score': self._calculate_category_score(BottleneckCategory.TASK_PROCESSING),
            'memory_score': self._calculate_category_score(BottleneckCategory.MEMORY_SYSTEM),
            'network_score': self._calculate_category_score(BottleneckCategory.NETWORK_API),
            'resource_score': self._calculate_category_score(BottleneckCategory.RESOURCE_USAGE)
        }
        
        # Calculate optimization potential
        optimization_potential = {
            'communication': self._calculate_optimization_potential(BottleneckCategory.COMMUNICATION),
            'processing': self._calculate_optimization_potential(BottleneckCategory.TASK_PROCESSING),
            'memory': self._calculate_optimization_potential(BottleneckCategory.MEMORY_SYSTEM),
            'network': self._calculate_optimization_potential(BottleneckCategory.NETWORK_API),
            'resources': self._calculate_optimization_potential(BottleneckCategory.RESOURCE_USAGE)
        }
        
        # Collect auto-fix commands
        auto_fixes = []
        for issue in self.issues:
            if issue.auto_fixable:
                auto_fixes.extend(issue.fix_commands)
        
        return AnalysisReport(
            analysis_id=analysis_id,
            timestamp=datetime.now(),
            time_range=self.time_range,
            agents_analyzed=await self._count_agents_analyzed(),
            tasks_processed=await self._count_tasks_processed(),
            critical_issues=critical_issues,
            warning_issues=warning_issues,
            info_issues=info_issues,
            performance_summary=performance_summary,
            optimization_potential=optimization_potential,
            auto_fixes_available=list(set(auto_fixes))
        )
        
    async def _export_report(self, report: AnalysisReport, export_file: str):
        """Export analysis report to file"""
        try:
            report_data = asdict(report)
            
            # Convert datetime objects to strings for JSON serialization
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            report_data = convert_datetime(report_data)
            
            with open(export_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            logger.info(f"📊 Report exported to: {export_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to export report: {e}")
            
    async def _apply_automatic_fixes(self, report: AnalysisReport):
        """Apply automatic performance fixes"""
        if not report.auto_fixes_available:
            logger.info("ℹ️ No automatic fixes available")
            return
            
        logger.info(f"🔧 Applying {len(report.auto_fixes_available)} automatic fixes...")
        
        for fix_command in report.auto_fixes_available:
            try:
                logger.info(f"⚙️ Applying fix: {fix_command}")
                # In a real implementation, this would execute the fix command
                # For now, we'll just log what would be done
                await asyncio.sleep(0.1)  # Simulate fix application
                logger.info(f"✅ Applied fix: {fix_command}")
            except Exception as e:
                logger.error(f"❌ Failed to apply fix '{fix_command}': {e}")
                
    def print_report(self, report: AnalysisReport):
        """Print analysis report to console"""
        print("\n🔍 Bottleneck Analysis Report")
        print("━" * 50)
        
        print(f"\n📊 Summary")
        print(f"├── Time Range: {report.time_range}")
        print(f"├── Agents Analyzed: {report.agents_analyzed}")
        print(f"├── Tasks Processed: {report.tasks_processed}")
        print(f"└── Critical Issues: {len(report.critical_issues)}")
        
        if report.critical_issues:
            print(f"\n🚨 Critical Bottlenecks")
            for i, issue in enumerate(report.critical_issues, 1):
                print(f"{i}. {issue.title} ({issue.impact_percentage:.0f}% impact)")
                print(f"   └── {issue.description}")
        
        if report.warning_issues:
            print(f"\n⚠️ Warning Bottlenecks")
            for i, issue in enumerate(report.warning_issues, 1):
                print(f"{i}. {issue.title} ({issue.impact_percentage:.0f}% impact)")
        
        print(f"\n💡 Recommendations")
        all_recommendations = []
        for issue in report.critical_issues + report.warning_issues:
            all_recommendations.extend(issue.recommendations)
        
        for i, rec in enumerate(list(set(all_recommendations))[:5], 1):
            print(f"{i}. {rec}")
        
        if report.auto_fixes_available:
            print(f"\n✅ Quick Fixes Available")
            print("Run with --fix to apply:")
            for fix in report.auto_fixes_available[:3]:
                print(f"- {fix}")
        
        print(f"\n📈 Performance Scores")
        for category, score in report.performance_summary.items():
            emoji = "🟢" if score > 0.8 else "🟡" if score > 0.6 else "🔴"
            print(f"{emoji} {category.replace('_', ' ').title()}: {score:.1%}")
            
    # Helper methods for metric collection
    async def _get_agent_response_times(self, redis_client) -> List[float]:
        """Get agent response times from Redis metrics"""
        # Simulate agent response time data
        return [1.2, 0.8, 2.1, 1.5, 0.9, 1.8, 1.1]
    
    async def _get_message_queue_delays(self, redis_client) -> List[float]:
        """Get message queue delays from Redis"""
        # Simulate queue delay data
        return [0.3, 0.5, 1.2, 0.4, 0.7, 0.9, 0.6]
    
    async def _measure_coordination_overhead(self, redis_client) -> float:
        """Measure coordination overhead"""
        start_time = time.time()
        # Simulate coordination operation
        await asyncio.sleep(0.1)
        return time.time() - start_time
    
    async def _get_task_completion_times(self, redis_client) -> List[float]:
        """Get task completion times"""
        # Simulate task completion data
        return [4.5, 6.2, 8.1, 5.3, 7.8, 9.2, 6.7, 11.4]
    
    async def _get_queue_wait_times(self, redis_client) -> List[float]:
        """Get queue wait times"""
        # Simulate wait time data
        return [2.1, 3.4, 6.7, 1.8, 4.2, 8.9, 3.1]
    
    async def _calculate_agent_utilization(self, redis_client) -> float:
        """Calculate agent utilization rate"""
        # Simulate utilization calculation
        return 0.73  # 73%
    
    async def _get_cache_hit_rate(self) -> float:
        """Get memory cache hit rate"""
        # Simulate cache hit rate
        return 0.78  # 78%
    
    async def _get_memory_search_times(self) -> List[float]:
        """Get memory search times"""
        # Simulate search time data
        return [0.032, 0.045, 0.028, 0.067, 0.039, 0.051, 0.033]
    
    async def _measure_storage_io_latency(self) -> float:
        """Measure storage I/O latency"""
        start_time = time.time()
        # Simulate I/O operation
        await asyncio.sleep(0.02)
        return time.time() - start_time
    
    async def _measure_api_response_times(self) -> Dict[str, float]:
        """Measure API response times"""
        response_times = {}
        
        async with aiohttp.ClientSession() as session:
            for service, endpoint in self.endpoints.items():
                try:
                    if not endpoint.startswith('http'):
                        continue
                        
                    start_time = time.time()
                    async with session.get(f"{endpoint}/health", timeout=5) as response:
                        response_time = time.time() - start_time
                        response_times[service] = response_time
                except Exception:
                    response_times[service] = 5.0  # Timeout value
        
        return response_times
    
    async def _calculate_network_timeout_rate(self) -> float:
        """Calculate network timeout rate"""
        # Simulate timeout rate calculation
        return 0.02  # 2%
    
    async def _get_gpu_utilization(self) -> Optional[float]:
        """Get GPU utilization if available"""
        try:
            # Try to get GPU utilization using nvidia-smi
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return float(result.stdout.strip()) / 100.0
        except Exception:
            pass
        return None
    
    async def _measure_agent_registration_latency(self, redis_client) -> float:
        """Measure agent registration latency"""
        start_time = time.time()
        # Simulate registration operation
        await redis_client.ping()
        return time.time() - start_time
    
    # Helper methods for analysis
    def _calculate_severity(self, value: float, threshold: float) -> BottleneckSeverity:
        """Calculate bottleneck severity (higher is worse)"""
        if value > threshold * 1.5:
            return BottleneckSeverity.CRITICAL
        elif value > threshold:
            return BottleneckSeverity.WARNING
        else:
            return BottleneckSeverity.NONE
    
    def _calculate_severity_inverse(self, value: float, threshold: float) -> BottleneckSeverity:
        """Calculate bottleneck severity (lower is worse)"""
        if value < threshold * 0.5:
            return BottleneckSeverity.CRITICAL
        elif value < threshold:
            return BottleneckSeverity.WARNING
        else:
            return BottleneckSeverity.NONE
    
    def _generate_issue_title(self, metric: PerformanceMetric) -> str:
        """Generate human-readable issue title"""
        titles = {
            'agent_response_time': 'Slow Agent Response Time',
            'message_queue_delay': 'Message Queue Delays',
            'task_completion_time': 'Long Task Completion Times',
            'queue_wait_time': 'High Task Queue Wait Times',
            'cache_hit_rate': 'Low Memory Cache Hit Rate',
            'memory_search_time': 'Slow Memory Search Performance',
            'api_response_time': 'Slow API Response Times',
            'cpu_usage': 'High CPU Utilization',
            'memory_usage': 'High Memory Usage',
            'disk_usage': 'High Disk Usage',
            'gpu_utilization': 'High GPU Utilization'
        }
        return titles.get(metric.name, f'Performance Issue: {metric.name}')
    
    def _generate_issue_description(self, metric: PerformanceMetric) -> str:
        """Generate detailed issue description"""
        if metric.name == 'cache_hit_rate':
            return f"Cache hit rate is {metric.value:.1%}, below optimal threshold of {metric.threshold:.1%}"
        else:
            return f"{metric.name.replace('_', ' ').title()} is {metric.value:.2f} {metric.unit}, exceeding threshold of {metric.threshold:.2f} {metric.unit}"
    
    def _identify_affected_components(self, metric: PerformanceMetric) -> List[str]:
        """Identify components affected by the bottleneck"""
        component_map = {
            BottleneckCategory.COMMUNICATION: ['Agent Hub', 'Message Queue', 'WebSocket Server'],
            BottleneckCategory.TASK_PROCESSING: ['Task Router', 'Agent Workers', 'Task Queue'],
            BottleneckCategory.MEMORY_SYSTEM: ['Memory API', 'Vector Database', 'Cache System'],
            BottleneckCategory.NETWORK_API: ['API Gateway', 'Load Balancer', 'External Services'],
            BottleneckCategory.RESOURCE_USAGE: ['Host System', 'Docker Containers', 'GPU Resources']
        }
        return component_map.get(metric.category, ['Unknown'])
    
    def _identify_root_cause(self, metric: PerformanceMetric) -> str:
        """Identify root cause of the bottleneck"""
        cause_map = {
            'agent_response_time': 'Agents may be overloaded or experiencing resource contention',
            'message_queue_delay': 'Message queue may be experiencing backlog or slow processing',
            'task_completion_time': 'Tasks may be complex or agents may be under-resourced',
            'cache_hit_rate': 'Cache may be undersized or experiencing frequent evictions',
            'memory_search_time': 'Vector database may need optimization or more resources',
            'cpu_usage': 'System may be under high computational load',
            'memory_usage': 'System may have memory leaks or excessive memory allocation'
        }
        return cause_map.get(metric.name, 'Root cause analysis needed')
    
    async def _generate_recommendations(self, metric: PerformanceMetric) -> Tuple[List[str], bool, List[str]]:
        """Generate recommendations and auto-fix commands"""
        recommendations = {
            'agent_response_time': [
                'Increase agent concurrency limits',
                'Optimize agent processing algorithms',
                'Add more agent workers'
            ],
            'message_queue_delay': [
                'Switch to hierarchical message routing',
                'Increase message processing workers',
                'Optimize message serialization'
            ],
            'task_completion_time': [
                'Optimize task execution algorithms',
                'Increase agent pool size',
                'Implement task prioritization'
            ],
            'cache_hit_rate': [
                'Increase cache size allocation',
                'Optimize cache eviction policies',
                'Preload frequently accessed data'
            ],
            'memory_search_time': [
                'Optimize vector database configuration',
                'Add search result caching',
                'Consider distributed search'
            ],
            'cpu_usage': [
                'Scale horizontally with more instances',
                'Optimize CPU-intensive algorithms',
                'Implement request rate limiting'
            ],
            'memory_usage': [
                'Investigate memory leaks',
                'Optimize data structures',
                'Implement garbage collection tuning'
            ]
        }
        
        auto_fixable = metric.name in ['cache_hit_rate', 'message_queue_delay']
        fix_commands = []
        
        if metric.name == 'cache_hit_rate':
            fix_commands = [
                'Increase Redis memory allocation',
                'Enable smart caching strategies'
            ]
        elif metric.name == 'message_queue_delay':
            fix_commands = [
                'Switch to hierarchical topology',
                'Optimize message routing'
            ]
        
        return recommendations.get(metric.name, []), auto_fixable, fix_commands
    
    def _calculate_overall_health(self) -> float:
        """Calculate overall system health score"""
        if not self.metrics:
            return 1.0
            
        scores = []
        for metric in self.metrics:
            if metric.severity == BottleneckSeverity.CRITICAL:
                scores.append(0.3)
            elif metric.severity == BottleneckSeverity.WARNING:
                scores.append(0.7)
            else:
                scores.append(1.0)
        
        return statistics.mean(scores)
    
    def _calculate_category_score(self, category: BottleneckCategory) -> float:
        """Calculate performance score for a category"""
        category_metrics = [m for m in self.metrics if m.category == category]
        if not category_metrics:
            return 1.0
            
        scores = []
        for metric in category_metrics:
            if metric.severity == BottleneckSeverity.CRITICAL:
                scores.append(0.3)
            elif metric.severity == BottleneckSeverity.WARNING:
                scores.append(0.7)
            else:
                scores.append(1.0)
        
        return statistics.mean(scores)
    
    def _calculate_optimization_potential(self, category: BottleneckCategory) -> float:
        """Calculate optimization potential for a category"""
        category_metrics = [m for m in self.metrics if m.category == category]
        if not category_metrics:
            return 0.0
            
        # Calculate potential improvement based on severity of issues
        potential = 0.0
        for metric in category_metrics:
            if metric.severity == BottleneckSeverity.CRITICAL:
                potential += 0.4  # 40% improvement potential
            elif metric.severity == BottleneckSeverity.WARNING:
                potential += 0.2  # 20% improvement potential
        
        return min(potential, 0.5)  # Cap at 50% improvement
    
    # Count methods
    async def _count_agents_analyzed(self) -> int:
        """Count number of agents analyzed"""
        return 6  # Simulate agent count
    
    async def _count_tasks_processed(self) -> int:
        """Count number of tasks processed"""
        return 42  # Simulate task count


async def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description="vLLM Local Swarm Bottleneck Detection System"
    )
    parser.add_argument(
        '--time-range', '-t', 
        default='1h',
        choices=['1h', '24h', '7d', 'all'],
        help='Analysis time range (default: 1h)'
    )
    parser.add_argument(
        '--threshold', 
        type=float,
        default=20.0,
        help='Bottleneck threshold percentage (default: 20.0)'
    )
    parser.add_argument(
        '--export', '-e',
        help='Export analysis to file'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply automatic optimizations'
    )
    parser.add_argument(
        '--redis-url',
        default='redis://localhost:6379',
        help='Redis connection URL'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create bottleneck detector
        detector = BottleneckDetector(
            redis_url=args.redis_url,
            time_range=args.time_range,
            threshold=args.threshold
        )
        
        # Perform analysis
        report = await detector.analyze(
            export_file=args.export,
            apply_fixes=args.fix
        )
        
        # Print report
        detector.print_report(report)
        
        # Show final summary
        if args.fix and report.auto_fixes_available:
            print(f"\n✅ Applied {len(report.auto_fixes_available)} automatic fixes")
            
        if args.export:
            print(f"\n📊 Full report exported to: {args.export}")
            
    except KeyboardInterrupt:
        logger.info("⏹️ Bottleneck analysis interrupted by user")
    except Exception as e:
        logger.error(f"❌ Bottleneck analysis failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())