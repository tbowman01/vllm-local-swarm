#!/usr/bin/env python3
"""
vLLM Local Swarm Performance Optimizer
====================================

Automated performance optimization system that implements fixes for detected bottlenecks:
- Automatic configuration tuning and optimization
- Resource allocation adjustments
- Cache and memory optimization
- Network and communication improvements
- Real-time performance monitoring and adjustment
"""

import asyncio
import json
import logging
import os
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
    import aiofiles
    import docker
    import psutil
except ImportError:
    print("Installing performance optimizer dependencies...")
    import subprocess
    subprocess.run([
        "pip", "install", 
        "redis", "aiofiles", "docker", "psutil"
    ], check=True)
    import redis.asyncio as redis
    import aiofiles
    import docker
    import psutil

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization aggressiveness levels"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate" 
    AGGRESSIVE = "aggressive"


class OptimizationType(Enum):
    """Types of optimizations"""
    CACHE_TUNING = "cache_tuning"
    RESOURCE_SCALING = "resource_scaling"
    NETWORK_OPTIMIZATION = "network_optimization"
    COORDINATION_IMPROVEMENT = "coordination_improvement"
    MEMORY_OPTIMIZATION = "memory_optimization"
    TASK_SCHEDULING = "task_scheduling"


@dataclass
class OptimizationAction:
    """Single optimization action"""
    id: str
    type: OptimizationType
    title: str
    description: str
    target_improvement: float  # Expected improvement percentage
    risk_level: str  # low, medium, high
    requires_restart: bool
    config_changes: Dict[str, Any]
    commands: List[str]
    rollback_commands: List[str]
    validation_checks: List[str]


class PerformanceOptimizer:
    """
    Automated performance optimization system for vLLM Local Swarm
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 optimization_level: OptimizationLevel = OptimizationLevel.MODERATE):
        self.redis_url = redis_url
        self.optimization_level = optimization_level
        
        # Docker client for container management
        self.docker_client = docker.from_env()
        
        # Configuration paths
        self.config_paths = {
            'docker_compose': '/mnt/c/Users/bowma/Projects/vllm-local-swarm/docker-compose.yml',
            'redis_config': '/mnt/c/Users/bowma/Projects/vllm-local-swarm/configs/redis.conf',
            'nginx_config': '/mnt/c/Users/bowma/Projects/vllm-local-swarm/configs/nginx.conf',
            'env_file': '/mnt/c/Users/bowma/Projects/vllm-local-swarm/.env'
        }
        
        # Current system configuration
        self.current_config = {}
        
        # Available optimizations
        self.optimizations = self._define_optimizations()
        
    async def optimize_system(self, bottleneck_issues: List[Dict[str, Any]], 
                            dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply optimizations based on detected bottleneck issues
        """
        logger.info(f"🚀 Starting performance optimization (level: {self.optimization_level.value})")
        
        try:
            # Load current configuration
            await self._load_current_configuration()
            
            # Determine optimal optimizations based on issues
            selected_optimizations = await self._select_optimizations(bottleneck_issues)
            
            if not selected_optimizations:
                logger.info("ℹ️ No optimizations needed or available")
                return {"status": "no_optimizations", "message": "System is already optimized"}
            
            logger.info(f"📋 Selected {len(selected_optimizations)} optimizations")
            
            # Apply optimizations
            results = []
            for optimization in selected_optimizations:
                if dry_run:
                    logger.info(f"🔍 [DRY RUN] Would apply: {optimization.title}")
                    results.append({
                        "optimization": optimization.title,
                        "status": "dry_run",
                        "expected_improvement": f"{optimization.target_improvement}%"
                    })
                else:
                    result = await self._apply_optimization(optimization)
                    results.append(result)
            
            return {
                "status": "success",
                "optimizations_applied": len([r for r in results if r.get("status") == "success"]),
                "total_expected_improvement": sum(opt.target_improvement for opt in selected_optimizations),
                "results": results,
                "requires_restart": any(opt.requires_restart for opt in selected_optimizations)
            }
            
        except Exception as e:
            logger.error(f"❌ Performance optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _load_current_configuration(self):
        """Load current system configuration"""
        logger.info("📖 Loading current system configuration...")
        
        try:
            # Load Docker Compose configuration
            if os.path.exists(self.config_paths['docker_compose']):
                async with aiofiles.open(self.config_paths['docker_compose'], 'r') as f:
                    content = await f.read()
                    self.current_config['docker_compose'] = yaml.safe_load(content)
            
            # Load environment variables
            if os.path.exists(self.config_paths['env_file']):
                async with aiofiles.open(self.config_paths['env_file'], 'r') as f:
                    content = await f.read()
                    env_vars = {}
                    for line in content.split('\n'):
                        if line.strip() and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                    self.current_config['env_vars'] = env_vars
            
            # Get system resource information
            self.current_config['system'] = {
                'cpu_count': psutil.cpu_count(),
                'memory_gb': round(psutil.virtual_memory().total / (1024**3)),
                'available_memory_gb': round(psutil.virtual_memory().available / (1024**3))
            }
            
            # Get Docker container information
            containers = self.docker_client.containers.list()
            self.current_config['containers'] = {
                container.name: {
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown'
                } for container in containers if 'vllm' in container.name
            }
            
            logger.info(f"✅ Loaded configuration for {len(self.current_config)} components")
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            self.current_config = {}
    
    async def _select_optimizations(self, bottleneck_issues: List[Dict[str, Any]]) -> List[OptimizationAction]:
        """Select appropriate optimizations based on bottleneck issues"""
        logger.info("🎯 Selecting optimizations based on detected issues...")
        
        selected = []
        issue_categories = set()
        
        # Extract categories from issues
        for issue in bottleneck_issues:
            category = issue.get('category', '')
            if category:
                issue_categories.add(category)
        
        # Select optimizations based on categories and severity
        for optimization in self.optimizations:
            should_apply = False
            
            # Check if optimization addresses detected issues
            if optimization.type == OptimizationType.CACHE_TUNING and 'memory_system' in issue_categories:
                should_apply = True
            elif optimization.type == OptimizationType.RESOURCE_SCALING and 'resource_usage' in issue_categories:
                should_apply = True
            elif optimization.type == OptimizationType.NETWORK_OPTIMIZATION and 'network_api' in issue_categories:
                should_apply = True
            elif optimization.type == OptimizationType.COORDINATION_IMPROVEMENT and 'communication' in issue_categories:
                should_apply = True
            elif optimization.type == OptimizationType.TASK_SCHEDULING and 'task_processing' in issue_categories:
                should_apply = True
            
            # Apply optimization level filtering
            if should_apply:
                if (self.optimization_level == OptimizationLevel.CONSERVATIVE and 
                    optimization.risk_level == 'high'):
                    continue
                elif (self.optimization_level == OptimizationLevel.MODERATE and 
                      optimization.risk_level == 'high' and 
                      optimization.target_improvement < 25):
                    continue
                
                selected.append(optimization)
        
        # Sort by expected improvement (highest first)
        selected.sort(key=lambda x: x.target_improvement, reverse=True)
        
        # Limit number of optimizations based on level
        max_optimizations = {
            OptimizationLevel.CONSERVATIVE: 3,
            OptimizationLevel.MODERATE: 5,
            OptimizationLevel.AGGRESSIVE: 10
        }
        
        selected = selected[:max_optimizations[self.optimization_level]]
        
        logger.info(f"🎯 Selected {len(selected)} optimizations")
        return selected
    
    async def _apply_optimization(self, optimization: OptimizationAction) -> Dict[str, Any]:
        """Apply a single optimization"""
        logger.info(f"⚙️ Applying optimization: {optimization.title}")
        
        try:
            # Create backup of current configuration
            backup_id = await self._create_configuration_backup()
            
            # Apply configuration changes
            if optimization.config_changes:
                await self._apply_config_changes(optimization.config_changes)
            
            # Execute commands
            command_results = []
            for command in optimization.commands:
                result = await self._execute_optimization_command(command)
                command_results.append(result)
                
                if not result.get('success', False):
                    logger.warning(f"⚠️ Command failed: {command}")
                    # Attempt rollback
                    await self._rollback_optimization(optimization, backup_id)
                    return {
                        "optimization": optimization.title,
                        "status": "failed",
                        "error": result.get('error', 'Command execution failed'),
                        "backup_id": backup_id
                    }
            
            # Validate optimization
            validation_results = []
            for check in optimization.validation_checks:
                result = await self._validate_optimization(check)
                validation_results.append(result)
            
            success = all(result.get('success', False) for result in validation_results)
            
            if success:
                logger.info(f"✅ Successfully applied: {optimization.title}")
                return {
                    "optimization": optimization.title,
                    "status": "success",
                    "expected_improvement": f"{optimization.target_improvement}%",
                    "backup_id": backup_id,
                    "requires_restart": optimization.requires_restart
                }
            else:
                logger.warning(f"⚠️ Optimization validation failed: {optimization.title}")
                await self._rollback_optimization(optimization, backup_id)
                return {
                    "optimization": optimization.title,
                    "status": "validation_failed",
                    "validation_results": validation_results,
                    "backup_id": backup_id
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to apply optimization '{optimization.title}': {e}")
            return {
                "optimization": optimization.title,
                "status": "error",
                "error": str(e)
            }
    
    async def _create_configuration_backup(self) -> str:
        """Create backup of current configuration"""
        backup_id = f"backup_{int(datetime.now().timestamp())}"
        backup_dir = f"/tmp/vllm_backups/{backup_id}"
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup configuration files
            for config_name, config_path in self.config_paths.items():
                if os.path.exists(config_path):
                    backup_path = os.path.join(backup_dir, f"{config_name}.backup")
                    async with aiofiles.open(config_path, 'r') as src:
                        content = await src.read()
                    async with aiofiles.open(backup_path, 'w') as dst:
                        await dst.write(content)
            
            # Save current configuration state
            config_backup_path = os.path.join(backup_dir, "config_state.json")
            async with aiofiles.open(config_backup_path, 'w') as f:
                await f.write(json.dumps(self.current_config, indent=2, default=str))
            
            logger.info(f"💾 Created configuration backup: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return ""
    
    async def _apply_config_changes(self, config_changes: Dict[str, Any]):
        """Apply configuration changes to files"""
        for config_file, changes in config_changes.items():
            config_path = self.config_paths.get(config_file)
            if not config_path or not os.path.exists(config_path):
                continue
            
            try:
                if config_file == 'docker_compose':
                    await self._update_docker_compose_config(config_path, changes)
                elif config_file == 'env_file':
                    await self._update_env_file(config_path, changes)
                elif config_file.endswith('_config'):
                    await self._update_text_config(config_path, changes)
                
                logger.info(f"✅ Updated {config_file} configuration")
                
            except Exception as e:
                logger.error(f"❌ Failed to update {config_file}: {e}")
                raise
    
    async def _update_docker_compose_config(self, config_path: str, changes: Dict[str, Any]):
        """Update Docker Compose configuration"""
        async with aiofiles.open(config_path, 'r') as f:
            content = await f.read()
        
        config = yaml.safe_load(content)
        
        # Apply changes recursively
        def update_nested_dict(target, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in target:
                    update_nested_dict(target[key], value)
                else:
                    target[key] = value
        
        update_nested_dict(config, changes)
        
        async with aiofiles.open(config_path, 'w') as f:
            await f.write(yaml.dump(config, default_flow_style=False))
    
    async def _update_env_file(self, config_path: str, changes: Dict[str, Any]):
        """Update environment file"""
        async with aiofiles.open(config_path, 'r') as f:
            lines = (await f.read()).split('\n')
        
        # Update existing variables or add new ones
        updated_vars = set()
        new_lines = []
        
        for line in lines:
            if line.strip() and '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in changes:
                    new_lines.append(f"{key}={changes[key]}")
                    updated_vars.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Add new variables
        for key, value in changes.items():
            if key not in updated_vars:
                new_lines.append(f"{key}={value}")
        
        async with aiofiles.open(config_path, 'w') as f:
            await f.write('\n'.join(new_lines))
    
    async def _update_text_config(self, config_path: str, changes: Dict[str, Any]):
        """Update text-based configuration file"""
        async with aiofiles.open(config_path, 'r') as f:
            content = await f.read()
        
        # Apply simple key-value replacements
        for key, value in changes.items():
            # Find and replace configuration lines
            import re
            pattern = rf'^{re.escape(key)}\s*=?.*$'
            replacement = f'{key} {value}'
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        async with aiofiles.open(config_path, 'w') as f:
            await f.write(content)
    
    async def _execute_optimization_command(self, command: str) -> Dict[str, Any]:
        """Execute optimization command"""
        try:
            import subprocess
            
            logger.info(f"🔧 Executing: {command}")
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "command": command,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else ""
                }
            else:
                return {
                    "success": False,
                    "command": command,
                    "error": stderr.decode('utf-8') if stderr else "Command failed",
                    "return_code": process.returncode
                }
                
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": str(e)
            }
    
    async def _validate_optimization(self, check: str) -> Dict[str, Any]:
        """Validate optimization results"""
        try:
            if check.startswith("service_health:"):
                service_name = check.split(":", 1)[1]
                return await self._check_service_health(service_name)
            elif check.startswith("redis_config:"):
                return await self._check_redis_config()
            elif check.startswith("memory_usage:"):
                threshold = float(check.split(":", 1)[1])
                return await self._check_memory_usage(threshold)
            elif check.startswith("response_time:"):
                service, max_time = check.split(":", 1)[1].split(",")
                return await self._check_response_time(service, float(max_time))
            else:
                return {"success": False, "error": f"Unknown validation check: {check}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check if a service is healthy"""
        try:
            container = self.docker_client.containers.get(service_name)
            health = container.attrs.get('State', {}).get('Health', {}).get('Status')
            
            if health == 'healthy' or container.status == 'running':
                return {"success": True, "service": service_name, "status": "healthy"}
            else:
                return {"success": False, "service": service_name, "status": health or container.status}
                
        except docker.errors.NotFound:
            return {"success": False, "service": service_name, "error": "Service not found"}
        except Exception as e:
            return {"success": False, "service": service_name, "error": str(e)}
    
    async def _check_redis_config(self) -> Dict[str, Any]:
        """Check Redis configuration"""
        try:
            redis_client = redis.Redis.from_url(self.redis_url)
            info = await redis_client.info()
            await redis_client.close()
            
            return {"success": True, "redis_info": {"used_memory": info.get('used_memory_human')}}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_memory_usage(self, threshold: float) -> Dict[str, Any]:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent / 100.0
            
            success = usage_percent < threshold
            return {
                "success": success,
                "memory_usage": usage_percent,
                "threshold": threshold
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_response_time(self, service: str, max_time: float) -> Dict[str, Any]:
        """Check service response time"""
        try:
            import aiohttp
            import time
            
            endpoints = {
                'redis': 'redis://localhost:6379',
                'langfuse': 'http://localhost:3000/api/public/health',
                'qdrant': 'http://localhost:6333/health',
                'memory_api': 'http://localhost:8003/health'
            }
            
            endpoint = endpoints.get(service)
            if not endpoint:
                return {"success": False, "error": f"Unknown service: {service}"}
            
            if endpoint.startswith('redis://'):
                redis_client = redis.Redis.from_url(endpoint)
                start_time = time.time()
                await redis_client.ping()
                response_time = time.time() - start_time
                await redis_client.close()
            else:
                async with aiohttp.ClientSession() as session:
                    start_time = time.time()
                    async with session.get(endpoint, timeout=5) as response:
                        response_time = time.time() - start_time
            
            success = response_time <= max_time
            return {
                "success": success,
                "service": service,
                "response_time": response_time,
                "max_time": max_time
            }
            
        except Exception as e:
            return {"success": False, "service": service, "error": str(e)}
    
    async def _rollback_optimization(self, optimization: OptimizationAction, backup_id: str):
        """Rollback optimization changes"""
        logger.warning(f"🔄 Rolling back optimization: {optimization.title}")
        
        try:
            # Execute rollback commands
            for command in optimization.rollback_commands:
                await self._execute_optimization_command(command)
            
            # Restore configuration from backup
            if backup_id:
                await self._restore_configuration_backup(backup_id)
            
            logger.info(f"✅ Successfully rolled back: {optimization.title}")
            
        except Exception as e:
            logger.error(f"❌ Failed to rollback optimization: {e}")
    
    async def _restore_configuration_backup(self, backup_id: str):
        """Restore configuration from backup"""
        backup_dir = f"/tmp/vllm_backups/{backup_id}"
        
        if not os.path.exists(backup_dir):
            logger.error(f"❌ Backup directory not found: {backup_dir}")
            return
        
        try:
            for config_name, config_path in self.config_paths.items():
                backup_path = os.path.join(backup_dir, f"{config_name}.backup")
                if os.path.exists(backup_path):
                    async with aiofiles.open(backup_path, 'r') as src:
                        content = await src.read()
                    async with aiofiles.open(config_path, 'w') as dst:
                        await dst.write(content)
            
            logger.info(f"✅ Restored configuration from backup: {backup_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to restore backup: {e}")
    
    def _define_optimizations(self) -> List[OptimizationAction]:
        """Define available optimization actions"""
        return [
            # Redis/Cache Optimizations
            OptimizationAction(
                id="redis_memory_increase",
                type=OptimizationType.CACHE_TUNING,
                title="Increase Redis Memory Allocation",
                description="Increase Redis maxmemory from 2GB to 4GB to improve cache hit rates",
                target_improvement=25.0,
                risk_level="low",
                requires_restart=True,
                config_changes={
                    "docker_compose": {
                        "services": {
                            "redis": {
                                "command": "redis-server --appendonly yes --maxmemory 4gb --maxmemory-policy allkeys-lru"
                            }
                        }
                    }
                },
                commands=[
                    "docker-compose restart redis"
                ],
                rollback_commands=[
                    "docker-compose restart redis"
                ],
                validation_checks=[
                    "service_health:vllm-redis",
                    "redis_config:"
                ]
            ),
            
            OptimizationAction(
                id="enable_redis_clustering",
                type=OptimizationType.CACHE_TUNING,
                title="Enable Redis Clustering",
                description="Enable Redis clustering for improved performance and reliability",
                target_improvement=35.0,
                risk_level="medium",
                requires_restart=True,
                config_changes={
                    "env_file": {
                        "REDIS_CLUSTER_ENABLED": "true",
                        "REDIS_CLUSTER_NODES": "3"
                    }
                },
                commands=[
                    "docker-compose -f docker-compose.yml -f docker-compose.redis-cluster.yml up -d"
                ],
                rollback_commands=[
                    "docker-compose restart redis"
                ],
                validation_checks=[
                    "service_health:vllm-redis",
                    "redis_config:"
                ]
            ),
            
            # Resource Scaling Optimizations
            OptimizationAction(
                id="increase_ray_workers",
                type=OptimizationType.RESOURCE_SCALING,
                title="Increase Ray Worker Replicas",
                description="Increase Ray worker replicas from 2 to 4 for better task processing",
                target_improvement=40.0,
                risk_level="low",
                requires_restart=True,
                config_changes={
                    "env_file": {
                        "RAY_WORKER_REPLICAS": "4"
                    }
                },
                commands=[
                    "docker-compose up -d --scale ray-worker=4"
                ],
                rollback_commands=[
                    "docker-compose up -d --scale ray-worker=2"
                ],
                validation_checks=[
                    "service_health:vllm-ray-head"
                ]
            ),
            
            OptimizationAction(
                id="optimize_vllm_memory",
                type=OptimizationType.RESOURCE_SCALING,
                title="Optimize vLLM GPU Memory Utilization",
                description="Increase vLLM GPU memory utilization from 0.90 to 0.95 for better performance",
                target_improvement=15.0,
                risk_level="medium",
                requires_restart=True,
                config_changes={
                    "docker_compose": {
                        "services": {
                            "vllm-phi": {
                                "environment": {
                                    "VLLM_GPU_MEMORY_UTILIZATION": "0.95"
                                }
                            }
                        }
                    }
                },
                commands=[
                    "docker-compose restart vllm-phi"
                ],
                rollback_commands=[
                    "docker-compose restart vllm-phi"
                ],
                validation_checks=[
                    "service_health:vllm-phi-server",
                    "response_time:vllm_phi,2.0"
                ]
            ),
            
            # Network Optimization
            OptimizationAction(
                id="enable_http2",
                type=OptimizationType.NETWORK_OPTIMIZATION,
                title="Enable HTTP/2 for API Services",
                description="Enable HTTP/2 protocol for improved API performance",
                target_improvement=20.0,
                risk_level="low",
                requires_restart=True,
                config_changes={
                    "nginx_config": {
                        "listen": "443 ssl http2",
                        "http2_max_concurrent_streams": "100"
                    }
                },
                commands=[
                    "docker-compose restart nginx-auth"
                ],
                rollback_commands=[
                    "docker-compose restart nginx-auth"
                ],
                validation_checks=[
                    "response_time:nginx,1.0"
                ]
            ),
            
            # Coordination Improvements
            OptimizationAction(
                id="optimize_task_routing",
                type=OptimizationType.COORDINATION_IMPROVEMENT,
                title="Optimize Agent Task Routing",
                description="Enable hierarchical task routing for reduced coordination overhead",
                target_improvement=30.0,
                risk_level="low",
                requires_restart=False,
                config_changes={
                    "env_file": {
                        "AGENT_ROUTING_STRATEGY": "hierarchical",
                        "COORDINATION_CACHE_ENABLED": "true"
                    }
                },
                commands=[
                    "curl -X POST http://localhost:8006/admin/reload-config"
                ],
                rollback_commands=[
                    "curl -X POST http://localhost:8006/admin/reload-config"
                ],
                validation_checks=[
                    "response_time:orchestrator,1.0"
                ]
            ),
            
            # Memory System Optimization
            OptimizationAction(
                id="enable_memory_caching",
                type=OptimizationType.MEMORY_OPTIMIZATION,
                title="Enable Smart Memory Caching",
                description="Enable intelligent memory caching with preloading for frequently accessed data",
                target_improvement=35.0,
                risk_level="low",
                requires_restart=False,
                config_changes={
                    "env_file": {
                        "MEMORY_CACHE_ENABLED": "true",
                        "MEMORY_CACHE_SIZE": "1024MB",
                        "MEMORY_PRELOAD_ENABLED": "true"
                    }
                },
                commands=[
                    "curl -X POST http://localhost:8003/admin/enable-caching"
                ],
                rollback_commands=[
                    "curl -X POST http://localhost:8003/admin/disable-caching"
                ],
                validation_checks=[
                    "response_time:memory_api,0.5",
                    "service_health:vllm-qdrant"
                ]
            ),
            
            # Task Scheduling Optimization
            OptimizationAction(
                id="optimize_task_scheduling",
                type=OptimizationType.TASK_SCHEDULING,
                title="Optimize Task Queue Scheduling",
                description="Enable intelligent task scheduling with priority-based routing",
                target_improvement=25.0,
                risk_level="low",
                requires_restart=False,
                config_changes={
                    "env_file": {
                        "TASK_SCHEDULER_STRATEGY": "intelligent",
                        "PRIORITY_QUEUE_ENABLED": "true",
                        "LOAD_BALANCING_ENABLED": "true"
                    }
                },
                commands=[
                    "curl -X POST http://localhost:8006/admin/optimize-scheduling"
                ],
                rollback_commands=[
                    "curl -X POST http://localhost:8006/admin/reset-scheduling"
                ],
                validation_checks=[
                    "response_time:orchestrator,1.0"
                ]
            )
        ]


# Example usage and testing
async def test_performance_optimizer():
    """Test the performance optimizer"""
    
    # Sample bottleneck issues (from bottleneck detector)
    sample_issues = [
        {
            "category": "memory_system",
            "severity": "warning",
            "title": "Low Memory Cache Hit Rate",
            "impact_percentage": 25.0
        },
        {
            "category": "resource_usage",
            "severity": "critical",
            "title": "High CPU Utilization",
            "impact_percentage": 45.0
        },
        {
            "category": "communication",
            "severity": "warning",
            "title": "Agent Response Delays",
            "impact_percentage": 20.0
        }
    ]
    
    optimizer = PerformanceOptimizer(optimization_level=OptimizationLevel.MODERATE)
    
    try:
        logger.info("🚀 Testing Performance Optimizer...")
        
        # Perform dry run first
        logger.info("🔍 Performing dry run analysis...")
        dry_run_result = await optimizer.optimize_system(sample_issues, dry_run=True)
        print(f"\n📋 Dry Run Results:")
        print(json.dumps(dry_run_result, indent=2))
        
        # Ask user for confirmation in real scenario
        logger.info("\n🎯 Would perform optimizations with expected improvements:")
        for result in dry_run_result.get('results', []):
            print(f"  • {result['optimization']}: {result['expected_improvement']} improvement")
        
        logger.info("✅ Performance optimizer test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Performance optimizer test failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_performance_optimizer())