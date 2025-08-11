"""
Custom Metrics Collector for vLLM Local Swarm
Collects and exposes application-specific metrics
"""

import asyncio
import time
import httpx
import psutil
from typing import Dict, Any, Optional
from fastapi import FastAPI, Response
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, push_to_gateway
)
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="vLLM Swarm Metrics Collector")

# Create custom registry
registry = CollectorRegistry()

# Define metrics
# Service metrics
service_health = Gauge(
    'vllm_service_health',
    'Health status of services (1=healthy, 0=unhealthy)',
    ['service'],
    registry=registry
)

service_response_time = Histogram(
    'vllm_service_response_time_seconds',
    'Response time of service endpoints',
    ['service', 'endpoint'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

# Model metrics
model_requests_total = Counter(
    'vllm_model_requests_total',
    'Total number of model requests',
    ['model', 'status'],
    registry=registry
)

model_tokens_processed = Counter(
    'vllm_model_tokens_processed_total',
    'Total tokens processed by models',
    ['model', 'type'],
    registry=registry
)

model_queue_size = Gauge(
    'vllm_model_queue_size',
    'Current model request queue size',
    ['model'],
    registry=registry
)

# Memory system metrics
memory_entries_total = Gauge(
    'vllm_memory_entries_total',
    'Total memory entries stored',
    ['type'],
    registry=registry
)

memory_operations = Counter(
    'vllm_memory_operations_total',
    'Memory operations performed',
    ['operation', 'status'],
    registry=registry
)

# Agent metrics
agent_tasks_total = Counter(
    'vllm_agent_tasks_total',
    'Total tasks processed by agents',
    ['agent_type', 'status'],
    registry=registry
)

agent_active_tasks = Gauge(
    'vllm_agent_active_tasks',
    'Currently active agent tasks',
    ['agent_type'],
    registry=registry
)

# Authentication metrics
auth_requests = Counter(
    'vllm_auth_requests_total',
    'Authentication requests',
    ['type', 'status'],
    registry=registry
)

active_sessions = Gauge(
    'vllm_active_sessions',
    'Number of active user sessions',
    registry=registry
)

# System resource metrics
gpu_memory_usage = Gauge(
    'vllm_gpu_memory_usage_bytes',
    'GPU memory usage in bytes',
    ['gpu_id'],
    registry=registry
)

gpu_utilization = Gauge(
    'vllm_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id'],
    registry=registry
)

# Business metrics
workflow_duration = Summary(
    'vllm_workflow_duration_seconds',
    'Duration of complete workflows',
    ['workflow_type'],
    registry=registry
)

workflow_success_rate = Gauge(
    'vllm_workflow_success_rate',
    'Success rate of workflows',
    ['workflow_type'],
    registry=registry
)

class MetricsCollector:
    """Collects metrics from various services"""
    
    def __init__(self):
        self.services = {
            'auth': os.getenv('AUTH_SERVICE_URL', 'http://auth-service:8005'),
            'memory': os.getenv('MEMORY_API_URL', 'http://memory-api:8003'),
            'orchestrator': os.getenv('ORCHESTRATOR_URL', 'http://orchestrator:8004'),
            'vllm': os.getenv('VLLM_URL', 'http://vllm-phi:8000'),
            'qdrant': os.getenv('QDRANT_URL', 'http://qdrant:6333'),
        }
        self.client = httpx.AsyncClient(timeout=5.0)
        
    async def collect_service_health(self):
        """Check health of all services"""
        for service_name, url in self.services.items():
            try:
                start_time = time.time()
                response = await self.client.get(f"{url}/health")
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    service_health.labels(service=service_name).set(1)
                    service_response_time.labels(
                        service=service_name,
                        endpoint='health'
                    ).observe(duration)
                else:
                    service_health.labels(service=service_name).set(0)
                    
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                service_health.labels(service=service_name).set(0)
    
    async def collect_model_metrics(self):
        """Collect vLLM model server metrics"""
        try:
            # Get model stats
            response = await self.client.get(f"{self.services['vllm']}/v1/models")
            if response.status_code == 200:
                models = response.json().get('data', [])
                for model in models:
                    model_queue_size.labels(model=model['id']).set(0)  # Placeholder
            
            # Try to get metrics endpoint if available
            try:
                metrics_response = await self.client.get(f"{self.services['vllm']}/metrics")
                if metrics_response.status_code == 200:
                    # Parse vLLM metrics if available
                    pass
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to collect model metrics: {e}")
    
    async def collect_memory_metrics(self):
        """Collect memory system metrics"""
        try:
            response = await self.client.get(f"{self.services['memory']}/stats")
            if response.status_code == 200:
                stats = response.json()
                
                # Update memory metrics
                for entry_type, count in stats.get('entries_by_type', {}).items():
                    memory_entries_total.labels(type=entry_type).set(count)
                    
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")
    
    async def collect_auth_metrics(self):
        """Collect authentication metrics"""
        try:
            response = await self.client.get(f"{self.services['auth']}/metrics")
            if response.status_code == 200:
                metrics = response.json()
                
                # Update auth metrics
                active_sessions.set(metrics.get('active_sessions', 0))
                
        except Exception as e:
            logger.error(f"Failed to collect auth metrics: {e}")
    
    async def collect_gpu_metrics(self):
        """Collect GPU metrics if available"""
        try:
            import pynvml
            pynvml.nvmlInit()
            
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_memory_usage.labels(gpu_id=str(i)).set(mem_info.used)
                
                # Utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_utilization.labels(gpu_id=str(i)).set(util.gpu)
                
        except ImportError:
            logger.debug("pynvml not available, skipping GPU metrics")
        except Exception as e:
            logger.error(f"Failed to collect GPU metrics: {e}")
    
    async def collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            mem = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # These would normally be exposed as Prometheus metrics
            # For now, we'll log them
            logger.debug(f"System metrics - CPU: {cpu_percent}%, "
                        f"Memory: {mem.percent}%, Disk: {disk.percent}%")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def run_collection_loop(self):
        """Main collection loop"""
        while True:
            try:
                # Collect all metrics
                await asyncio.gather(
                    self.collect_service_health(),
                    self.collect_model_metrics(),
                    self.collect_memory_metrics(),
                    self.collect_auth_metrics(),
                    self.collect_gpu_metrics(),
                    self.collect_system_metrics(),
                    return_exceptions=True
                )
                
                # Push to Pushgateway if configured
                pushgateway_url = os.getenv('PROMETHEUS_PUSHGATEWAY')
                if pushgateway_url:
                    try:
                        push_to_gateway(
                            pushgateway_url,
                            job='metrics_collector',
                            registry=registry
                        )
                    except Exception as e:
                        logger.error(f"Failed to push metrics: {e}")
                
            except Exception as e:
                logger.error(f"Collection loop error: {e}")
            
            # Wait before next collection
            await asyncio.sleep(15)

# Global collector instance
collector = MetricsCollector()

@app.on_event("startup")
async def startup_event():
    """Start metrics collection on startup"""
    asyncio.create_task(collector.run_collection_loop())
    logger.info("Metrics collector started")

@app.get("/metrics")
async def metrics():
    """Expose metrics for Prometheus scraping"""
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/record")
async def record_metric(metric_data: Dict[str, Any]):
    """Record custom metrics via API"""
    try:
        metric_type = metric_data.get('type')
        metric_name = metric_data.get('name')
        value = metric_data.get('value')
        labels = metric_data.get('labels', {})
        
        # Record based on type
        if metric_type == 'workflow_complete':
            workflow_duration.labels(
                workflow_type=labels.get('workflow_type', 'unknown')
            ).observe(value)
            
        elif metric_type == 'task_complete':
            agent_tasks_total.labels(
                agent_type=labels.get('agent_type', 'unknown'),
                status=labels.get('status', 'success')
            ).inc()
            
        elif metric_type == 'model_request':
            model_requests_total.labels(
                model=labels.get('model', 'unknown'),
                status=labels.get('status', 'success')
            ).inc()
            
            if 'tokens' in metric_data:
                model_tokens_processed.labels(
                    model=labels.get('model', 'unknown'),
                    type=labels.get('token_type', 'total')
                ).inc(metric_data['tokens'])
        
        return {"status": "recorded", "metric": metric_name}
        
    except Exception as e:
        logger.error(f"Failed to record metric: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)