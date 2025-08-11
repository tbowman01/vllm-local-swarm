#!/usr/bin/env python3
"""
🔄 Auto-Scaling System for vLLM Local Swarm
Monitors metrics and automatically scales services based on load
"""

import asyncio
import docker
import httpx
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScalingMetrics:
    """Container for scaling decision metrics"""
    cpu_percent: float
    memory_percent: float
    response_time: float
    request_rate: float
    error_rate: float
    timestamp: datetime

@dataclass
class ServiceConfig:
    """Configuration for a scalable service"""
    name: str
    min_replicas: int
    max_replicas: int
    target_cpu: float
    target_memory: float
    target_response_time: float
    cooldown_seconds: int
    
class AutoScaler:
    """Intelligent auto-scaling system"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        # Load configuration
        self.services = {
            'memory-api': ServiceConfig(
                name='memory-api',
                min_replicas=1,
                max_replicas=3,
                target_cpu=70.0,
                target_memory=80.0,
                target_response_time=0.5,
                cooldown_seconds=300
            ),
            'orchestrator': ServiceConfig(
                name='orchestrator',
                min_replicas=1,
                max_replicas=5,
                target_cpu=60.0,
                target_memory=75.0,
                target_response_time=1.0,
                cooldown_seconds=180
            ),
            'auth-service': ServiceConfig(
                name='auth-service',
                min_replicas=1,
                max_replicas=2,
                target_cpu=50.0,
                target_memory=60.0,
                target_response_time=0.2,
                cooldown_seconds=600
            )
        }
        
        # Scaling history
        self.last_scaling_action: Dict[str, datetime] = {}
        self.metrics_history: Dict[str, List[ScalingMetrics]] = {}
        
        # Prometheus URL
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        
        logger.info("Auto-scaler initialized with services: %s", list(self.services.keys()))
    
    async def get_prometheus_metric(self, query: str) -> Optional[float]:
        """Query Prometheus for a metric"""
        try:
            response = await self.http_client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    return float(data['data']['result'][0]['value'][1])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to query Prometheus: {e}")
            return None
    
    async def collect_service_metrics(self, service_name: str) -> Optional[ScalingMetrics]:
        """Collect current metrics for a service"""
        try:
            # CPU usage
            cpu_query = f'rate(container_cpu_usage_seconds_total{{name=~".*{service_name}.*"}}[5m]) * 100'
            cpu_percent = await self.get_prometheus_metric(cpu_query) or 0.0
            
            # Memory usage
            memory_query = f'(container_memory_usage_bytes{{name=~".*{service_name}.*"}} / container_spec_memory_limit_bytes{{name=~".*{service_name}.*"}}) * 100'
            memory_percent = await self.get_prometheus_metric(memory_query) or 0.0
            
            # Response time (95th percentile)
            response_query = f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m]))'
            response_time = await self.get_prometheus_metric(response_query) or 0.0
            
            # Request rate
            request_query = f'rate(http_requests_total{{service="{service_name}"}}[5m])'
            request_rate = await self.get_prometheus_metric(request_query) or 0.0
            
            # Error rate
            error_query = f'rate(http_requests_total{{service="{service_name}", status=~"5.."}}[5m]) / rate(http_requests_total{{service="{service_name}"}}[5m])'
            error_rate = await self.get_prometheus_metric(error_query) or 0.0
            
            return ScalingMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                response_time=response_time,
                request_rate=request_rate,
                error_rate=error_rate,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for {service_name}: {e}")
            return None
    
    def get_current_replicas(self, service_name: str) -> int:
        """Get current number of replicas for a service"""
        try:
            containers = self.docker_client.containers.list(
                filters={'name': service_name}
            )
            return len(containers)
        except Exception as e:
            logger.error(f"Failed to get replica count for {service_name}: {e}")
            return 1
    
    def calculate_desired_replicas(self, service: ServiceConfig, metrics: ScalingMetrics) -> int:
        """Calculate desired number of replicas based on metrics"""
        current_replicas = self.get_current_replicas(service.name)
        
        # Calculate scaling factors for different metrics
        factors = []
        
        # CPU-based scaling
        if metrics.cpu_percent > 0:
            cpu_factor = metrics.cpu_percent / service.target_cpu
            factors.append(cpu_factor)
        
        # Memory-based scaling
        if metrics.memory_percent > 0:
            memory_factor = metrics.memory_percent / service.target_memory
            factors.append(memory_factor)
        
        # Response time-based scaling
        if metrics.response_time > 0 and service.target_response_time > 0:
            response_factor = metrics.response_time / service.target_response_time
            factors.append(response_factor)
        
        # Use the maximum factor (most stressed metric)
        if factors:
            max_factor = max(factors)
            desired_replicas = int(current_replicas * max_factor)
        else:
            desired_replicas = current_replicas
        
        # Apply constraints
        desired_replicas = max(service.min_replicas, min(service.max_replicas, desired_replicas))
        
        # Avoid frequent scaling (hysteresis)
        if abs(desired_replicas - current_replicas) <= 1:
            return current_replicas
        
        return desired_replicas
    
    def can_scale(self, service_name: str) -> bool:
        """Check if service can be scaled (cooldown check)"""
        last_action = self.last_scaling_action.get(service_name)
        if last_action is None:
            return True
        
        service = self.services[service_name]
        cooldown = timedelta(seconds=service.cooldown_seconds)
        return datetime.utcnow() - last_action > cooldown
    
    async def scale_service(self, service_name: str, desired_replicas: int) -> bool:
        """Scale a service to the desired number of replicas"""
        try:
            current_replicas = self.get_current_replicas(service_name)
            
            if desired_replicas == current_replicas:
                return True
            
            if desired_replicas > current_replicas:
                # Scale up
                action = "scale_up"
                for i in range(desired_replicas - current_replicas):
                    await self._create_replica(service_name, i + current_replicas)
            else:
                # Scale down
                action = "scale_down"
                containers = self.docker_client.containers.list(
                    filters={'name': service_name}
                )
                
                # Remove excess containers
                for i in range(current_replicas - desired_replicas):
                    if i < len(containers):
                        containers[i].stop()
                        containers[i].remove()
            
            # Record scaling action
            self.last_scaling_action[service_name] = datetime.utcnow()
            
            logger.info(
                f"Scaled {service_name}: {current_replicas} -> {desired_replicas} ({action})"
            )
            
            # Send notification (webhook, Slack, etc.)
            await self._send_scaling_notification(service_name, action, current_replicas, desired_replicas)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale {service_name}: {e}")
            return False
    
    async def _create_replica(self, service_name: str, replica_id: int):
        """Create a new replica of a service"""
        try:
            # Get the original container for reference
            original_containers = self.docker_client.containers.list(
                filters={'name': service_name},
                limit=1
            )
            
            if not original_containers:
                logger.error(f"No existing container found for {service_name}")
                return
            
            original = original_containers[0]
            
            # Create new container with same configuration
            new_container = self.docker_client.containers.run(
                image=original.image.id,
                name=f"{service_name}-replica-{replica_id}",
                environment=original.attrs['Config']['Env'],
                ports=None,  # Don't bind ports for replicas
                network=original.attrs['HostConfig']['NetworkMode'],
                restart_policy={"Name": "unless-stopped"},
                detach=True
            )
            
            logger.info(f"Created replica {new_container.name}")
            
        except Exception as e:
            logger.error(f"Failed to create replica for {service_name}: {e}")
    
    async def _send_scaling_notification(self, service_name: str, action: str, old_count: int, new_count: int):
        """Send notification about scaling action"""
        webhook_url = os.getenv('SCALING_WEBHOOK_URL')
        if not webhook_url:
            return
        
        try:
            message = {
                "service": service_name,
                "action": action,
                "old_replicas": old_count,
                "new_replicas": new_count,
                "timestamp": datetime.utcnow().isoformat(),
                "environment": os.getenv('ENVIRONMENT', 'production')
            }
            
            await self.http_client.post(webhook_url, json=message)
            
        except Exception as e:
            logger.error(f"Failed to send scaling notification: {e}")
    
    async def evaluate_scaling_decisions(self):
        """Evaluate and execute scaling decisions for all services"""
        for service_name, service_config in self.services.items():
            try:
                # Check if service can be scaled
                if not self.can_scale(service_name):
                    continue
                
                # Collect metrics
                metrics = await self.collect_service_metrics(service_name)
                if not metrics:
                    continue
                
                # Store metrics history
                if service_name not in self.metrics_history:
                    self.metrics_history[service_name] = []
                
                self.metrics_history[service_name].append(metrics)
                
                # Keep only recent metrics (last hour)
                cutoff = datetime.utcnow() - timedelta(hours=1)
                self.metrics_history[service_name] = [
                    m for m in self.metrics_history[service_name]
                    if m.timestamp > cutoff
                ]
                
                # Calculate desired replicas
                desired_replicas = self.calculate_desired_replicas(service_config, metrics)
                current_replicas = self.get_current_replicas(service_name)
                
                # Log decision
                logger.info(
                    f"{service_name}: CPU={metrics.cpu_percent:.1f}%, "
                    f"Mem={metrics.memory_percent:.1f}%, "
                    f"RT={metrics.response_time:.3f}s, "
                    f"Replicas={current_replicas}->{desired_replicas}"
                )
                
                # Execute scaling if needed
                if desired_replicas != current_replicas:
                    await self.scale_service(service_name, desired_replicas)
                
            except Exception as e:
                logger.error(f"Error evaluating scaling for {service_name}: {e}")
    
    async def run_scaling_loop(self):
        """Main scaling loop"""
        logger.info("Starting auto-scaling loop")
        
        while True:
            try:
                await self.evaluate_scaling_decisions()
                
                # Wait before next evaluation
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scaling loop error: {e}")
                await asyncio.sleep(30)  # Shorter wait on error
    
    async def get_scaling_status(self) -> Dict:
        """Get current scaling status for all services"""
        status = {}
        
        for service_name in self.services:
            current_replicas = self.get_current_replicas(service_name)
            last_action = self.last_scaling_action.get(service_name)
            recent_metrics = self.metrics_history.get(service_name, [])
            
            status[service_name] = {
                "current_replicas": current_replicas,
                "min_replicas": self.services[service_name].min_replicas,
                "max_replicas": self.services[service_name].max_replicas,
                "last_scaling_action": last_action.isoformat() if last_action else None,
                "can_scale": self.can_scale(service_name),
                "metrics_count": len(recent_metrics),
                "latest_metrics": recent_metrics[-1].__dict__ if recent_metrics else None
            }
        
        return status

async def main():
    """Main function"""
    scaler = AutoScaler()
    
    # Run scaling loop
    await scaler.run_scaling_loop()

if __name__ == "__main__":
    asyncio.run(main())