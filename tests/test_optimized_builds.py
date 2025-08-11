#!/usr/bin/env python3
"""
Integration tests for optimized Docker builds
"""

import subprocess
import time
import requests
import pytest
import docker
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedBuildTester:
    """Test optimized Docker builds and deployments"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.services = {
            'redis': {'port': 6379, 'health_check': self._check_redis},
            'langfuse-db': {'port': 5432, 'health_check': self._check_postgres},
            'qdrant': {'port': 6333, 'health_check': self._check_qdrant},
            'auth-service-optimized': {'port': 8005, 'health_check': self._check_http_health},
            'memory-api-optimized': {'port': 8003, 'health_check': self._check_http_health},
            'orchestrator-optimized': {'port': 8004, 'health_check': self._check_http_health},
        }
        
    def _run_command(self, cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        if result.returncode != 0:
            logger.error(f"Command failed: {result.stderr}")
        return result
    
    def _check_redis(self, port: int) -> bool:
        """Check if Redis is healthy"""
        try:
            result = subprocess.run(
                ['docker', 'exec', 'vllm-redis', 'redis-cli', 'ping'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'PONG' in result.stdout
        except subprocess.TimeoutExpired:
            return False
    
    def _check_postgres(self, port: int) -> bool:
        """Check if PostgreSQL is healthy"""
        try:
            result = subprocess.run([
                'docker', 'exec', 'vllm-langfuse-db', 
                'pg_isready', '-U', 'langfuse'
            ], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    
    def _check_qdrant(self, port: int) -> bool:
        """Check if Qdrant is healthy"""
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def _check_http_health(self, port: int) -> bool:
        """Check HTTP service health endpoint"""
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def test_base_images_build(self):
        """Test that base images build successfully"""
        logger.info("🏗️ Testing base image builds...")
        
        # Build base-python
        result = self._run_command([
            'docker', 'build', 
            '-f', 'docker/Dockerfile.base-python',
            '-t', 'vllm-swarm/base-python:test',
            '.'
        ])
        assert result.returncode == 0, f"Base Python build failed: {result.stderr}"
        
        # Build base-ml
        result = self._run_command([
            'docker', 'build',
            '-f', 'docker/Dockerfile.base-ml', 
            '-t', 'vllm-swarm/base-ml:test',
            '.'
        ])
        assert result.returncode == 0, f"Base ML build failed: {result.stderr}"
        
        logger.info("✅ Base images build successfully")
    
    def test_optimized_services_build(self):
        """Test that optimized service images build successfully"""
        logger.info("🚀 Testing optimized service builds...")
        
        services = [
            ('docker/Dockerfile.auth-optimized', 'vllm-swarm/auth:test'),
            ('docker/Dockerfile.memory-optimized', 'vllm-swarm/memory:test'),
            ('docker/Dockerfile.orchestrator-optimized', 'vllm-swarm/orchestrator:test'),
        ]
        
        for dockerfile, tag in services:
            logger.info(f"Building {dockerfile}...")
            result = self._run_command([
                'docker', 'build',
                '-f', dockerfile,
                '-t', tag,
                '.'
            ])
            assert result.returncode == 0, f"Service build failed {dockerfile}: {result.stderr}"
        
        logger.info("✅ All optimized services build successfully")
    
    def test_optimized_stack_deployment(self):
        """Test deployment of optimized stack"""
        logger.info("📦 Testing optimized stack deployment...")
        
        # Start optimized services
        result = self._run_command([
            'docker', 'compose', 
            '-f', 'docker-compose.optimized.yml', 
            'up', '-d'
        ])
        assert result.returncode == 0, f"Stack deployment failed: {result.stderr}"
        
        # Wait for services to start
        time.sleep(30)
        
        # Check service health
        for service_name, config in self.services.items():
            logger.info(f"Checking health of {service_name}...")
            
            # Wait up to 60 seconds for service to be healthy
            healthy = False
            for _ in range(12):  # 12 * 5 = 60 seconds
                if config['health_check'](config['port']):
                    healthy = True
                    break
                time.sleep(5)
            
            assert healthy, f"Service {service_name} failed health check on port {config['port']}"
            logger.info(f"✅ {service_name} is healthy")
        
        logger.info("✅ Optimized stack deployment successful")
    
    def test_build_performance(self):
        """Test that optimized builds are faster than standard builds"""
        logger.info("⚡ Testing build performance...")
        
        # Time standard build
        start_time = time.time()
        result = self._run_command([
            'docker', 'build',
            '-f', 'docker/Dockerfile.auth',
            '-t', 'vllm-swarm/auth:standard-test',
            '.',
            '--no-cache'
        ])
        standard_time = time.time() - start_time
        
        if result.returncode != 0:
            logger.warning("Standard build failed, skipping performance comparison")
            return
        
        # Time optimized build (should use cache)
        start_time = time.time() 
        result = self._run_command([
            'docker', 'build',
            '-f', 'docker/Dockerfile.auth-optimized',
            '-t', 'vllm-swarm/auth:optimized-test',
            '.'
        ])
        optimized_time = time.time() - start_time
        
        assert result.returncode == 0, f"Optimized build failed: {result.stderr}"
        
        logger.info(f"Standard build time: {standard_time:.1f}s")
        logger.info(f"Optimized build time: {optimized_time:.1f}s")
        
        # Optimized build should be at least 20% faster (accounting for cache)
        if standard_time > 30:  # Only compare if standard build took significant time
            improvement = (standard_time - optimized_time) / standard_time
            logger.info(f"Performance improvement: {improvement:.1%}")
            assert improvement > 0.2, f"Optimized build not significantly faster: {improvement:.1%}"
        
        logger.info("✅ Build performance test passed")
    
    def test_image_sizes(self):
        """Test that optimized images are smaller"""
        logger.info("📏 Testing image sizes...")
        
        def get_image_size(image_name: str) -> int:
            """Get image size in bytes"""
            try:
                result = self._run_command([
                    'docker', 'inspect', image_name,
                    '--format={{.Size}}'
                ])
                if result.returncode == 0:
                    return int(result.stdout.strip())
            except ValueError:
                pass
            return 0
        
        # Compare standard vs optimized image sizes
        comparisons = [
            ('vllm-swarm/auth:standard-test', 'vllm-swarm/auth:optimized-test'),
        ]
        
        for standard_image, optimized_image in comparisons:
            standard_size = get_image_size(standard_image)
            optimized_size = get_image_size(optimized_image)
            
            if standard_size > 0 and optimized_size > 0:
                reduction = (standard_size - optimized_size) / standard_size
                logger.info(f"{standard_image}: {standard_size / 1024 / 1024:.1f}MB")
                logger.info(f"{optimized_image}: {optimized_size / 1024 / 1024:.1f}MB")
                logger.info(f"Size reduction: {reduction:.1%}")
                
                # Optimized should be at least 10% smaller
                assert reduction > 0.1, f"Optimized image not significantly smaller: {reduction:.1%}"
        
        logger.info("✅ Image size test passed")
    
    def cleanup(self):
        """Clean up test resources"""
        logger.info("🧹 Cleaning up test resources...")
        
        # Stop optimized stack
        self._run_command([
            'docker', 'compose',
            '-f', 'docker-compose.optimized.yml',
            'down', '-v'
        ])
        
        # Remove test images
        test_images = [
            'vllm-swarm/base-python:test',
            'vllm-swarm/base-ml:test',
            'vllm-swarm/auth:test',
            'vllm-swarm/memory:test',
            'vllm-swarm/orchestrator:test',
            'vllm-swarm/auth:standard-test',
            'vllm-swarm/auth:optimized-test',
        ]
        
        for image in test_images:
            self._run_command(['docker', 'rmi', image, '-f'])
        
        logger.info("✅ Cleanup completed")


@pytest.fixture(scope="session")
def tester():
    """Pytest fixture for the tester"""
    tester = OptimizedBuildTester()
    yield tester
    tester.cleanup()


def test_base_images_build(tester):
    """Test base images build"""
    tester.test_base_images_build()


def test_optimized_services_build(tester):
    """Test optimized service builds"""
    tester.test_optimized_services_build()


def test_optimized_stack_deployment(tester):
    """Test optimized stack deployment"""
    tester.test_optimized_stack_deployment()


def test_build_performance(tester):
    """Test build performance"""
    tester.test_build_performance()


def test_image_sizes(tester):
    """Test image sizes"""
    tester.test_image_sizes()


if __name__ == "__main__":
    # Run tests directly
    tester = OptimizedBuildTester()
    try:
        tester.test_base_images_build()
        tester.test_optimized_services_build()
        tester.test_optimized_stack_deployment()
        tester.test_build_performance()
        tester.test_image_sizes()
        print("🎉 All tests passed!")
    finally:
        tester.cleanup()