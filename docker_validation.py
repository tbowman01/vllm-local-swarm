#!/usr/bin/env python3
"""
Docker Stack Validation for vLLM Local Swarm

Validates that deployed Docker services are working correctly:
- Redis connectivity and basic operations
- Qdrant connectivity and collection operations
- Service health checks
- Network connectivity between services
"""

import asyncio
import logging
import redis
import requests
import json
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class DockerStackValidator:
    """Validates Docker stack services."""
    
    def __init__(self):
        self.redis_client = None
        self.test_results = {}
        self.failed_tests = []
        
    async def run_all_validations(self):
        """Run all Docker stack validations."""
        logger.info("🐳 Starting Docker Stack Validation")
        logger.info("=" * 50)
        
        validations = [
            ("Redis Connectivity", self.validate_redis),
            ("Redis Operations", self.validate_redis_operations),
            ("Qdrant Connectivity", self.validate_qdrant),
            ("Qdrant Operations", self.validate_qdrant_operations),
            ("Service Health Checks", self.validate_health_checks),
            ("Network Connectivity", self.validate_network),
        ]
        
        for test_name, test_func in validations:
            logger.info(f"\n🔍 Validating {test_name}...")
            try:
                result = await test_func()
                self.test_results[test_name] = result
                if result:
                    logger.info(f"✅ {test_name} - PASSED")
                else:
                    logger.error(f"❌ {test_name} - FAILED")
                    self.failed_tests.append(test_name)
            except Exception as e:
                logger.error(f"💥 {test_name} - CRASHED: {e}")
                self.test_results[test_name] = False
                self.failed_tests.append(test_name)
        
        # Generate summary
        self.generate_summary()
        return len(self.failed_tests) == 0
    
    async def validate_redis(self):
        """Test Redis connectivity."""
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
            response = self.redis_client.ping()
            if not response:
                raise Exception("Redis ping failed")
            
            # Test Redis info
            info = self.redis_client.info()
            if 'redis_version' not in info:
                raise Exception("Redis info missing version")
            
            logger.info(f"Redis version: {info['redis_version']}")
            return True
        except Exception as e:
            logger.error(f"Redis connectivity failed: {e}")
            return False
    
    async def validate_redis_operations(self):
        """Test Redis basic operations."""
        try:
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            # Test SET/GET
            test_key = f"test_key_{int(time.time())}"
            test_value = f"test_value_{int(time.time())}"
            
            self.redis_client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = self.redis_client.get(test_key)
            
            if retrieved_value.decode('utf-8') != test_value:
                raise Exception("Redis SET/GET operation failed")
            
            # Test LIST operations
            list_key = f"test_list_{int(time.time())}"
            self.redis_client.lpush(list_key, "item1", "item2", "item3")
            list_length = self.redis_client.llen(list_key)
            
            if list_length != 3:
                raise Exception("Redis LIST operation failed")
            
            # Cleanup
            self.redis_client.delete(test_key, list_key)
            
            logger.info("Redis operations: SET/GET, LIST operations working")
            return True
        except Exception as e:
            logger.error(f"Redis operations failed: {e}")
            return False
    
    async def validate_qdrant(self):
        """Test Qdrant connectivity."""
        try:
            # Test REST API
            response = requests.get("http://localhost:6333/", timeout=10)
            if response.status_code != 200:
                raise Exception(f"Qdrant REST API returned {response.status_code}")
            
            # Test collections endpoint
            response = requests.get("http://localhost:6333/collections", timeout=10)
            if response.status_code != 200:
                raise Exception(f"Qdrant collections endpoint failed: {response.status_code}")
            
            collections = response.json()
            logger.info(f"Qdrant collections: {len(collections.get('result', {}).get('collections', []))}")
            return True
        except Exception as e:
            logger.error(f"Qdrant connectivity failed: {e}")
            return False
    
    async def validate_qdrant_operations(self):
        """Test Qdrant basic operations."""
        try:
            collection_name = f"test_collection_{int(time.time())}"
            
            # Create test collection
            create_payload = {
                "vectors": {
                    "size": 384,
                    "distance": "Cosine"
                }
            }
            
            response = requests.put(
                f"http://localhost:6333/collections/{collection_name}",
                json=create_payload,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to create collection: {response.status_code}")
            
            # Insert test vector
            test_vector = [0.1] * 384  # Simple test vector
            insert_payload = {
                "points": [
                    {
                        "id": 1,
                        "vector": test_vector,
                        "payload": {"test": "data"}
                    }
                ]
            }
            
            response = requests.put(
                f"http://localhost:6333/collections/{collection_name}/points",
                json=insert_payload,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to insert point: {response.status_code}")
            
            # Query test vector
            query_payload = {
                "vector": test_vector,
                "top": 1
            }
            
            response = requests.post(
                f"http://localhost:6333/collections/{collection_name}/points/search",
                json=query_payload,
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to search points: {response.status_code}")
            
            results = response.json()
            if len(results.get('result', [])) == 0:
                raise Exception("Search returned no results")
            
            # Cleanup - delete collection
            response = requests.delete(
                f"http://localhost:6333/collections/{collection_name}",
                timeout=10
            )
            
            logger.info("Qdrant operations: create collection, insert, search working")
            return True
        except Exception as e:
            logger.error(f"Qdrant operations failed: {e}")
            return False
    
    async def validate_health_checks(self):
        """Test service health checks."""
        try:
            # Redis health
            if not self.redis_client or not self.redis_client.ping():
                raise Exception("Redis health check failed")
            
            # Qdrant health
            response = requests.get("http://localhost:6333/healthz", timeout=10)
            if response.status_code != 200:
                raise Exception(f"Qdrant health check failed: {response.status_code}")
            
            logger.info("All service health checks passed")
            return True
        except Exception as e:
            logger.error(f"Health checks failed: {e}")
            return False
    
    async def validate_network(self):
        """Test network connectivity between services."""
        try:
            # Check that services are accessible on expected ports
            import socket
            
            # Test Redis port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            if result != 0:
                raise Exception("Redis port 6379 not accessible")
            
            # Test Qdrant HTTP port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 6333))
            sock.close()
            if result != 0:
                raise Exception("Qdrant HTTP port 6333 not accessible")
            
            # Test Qdrant gRPC port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 6334))
            sock.close()
            if result != 0:
                raise Exception("Qdrant gRPC port 6334 not accessible")
            
            logger.info("Network connectivity: all ports accessible")
            return True
        except Exception as e:
            logger.error(f"Network validation failed: {e}")
            return False
    
    def generate_summary(self):
        """Generate validation summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = len(self.failed_tests)
        
        logger.info("\n" + "=" * 50)
        logger.info("📊 Docker Stack Validation Results")
        logger.info("=" * 50)
        logger.info(f"Total Validations: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        
        if self.failed_tests:
            logger.error(f"\n🚨 Failed Validations:")
            for test in self.failed_tests:
                logger.error(f"  - {test}")
        
        if failed_tests == 0:
            logger.info("\n🎉 ALL DOCKER SERVICES VALIDATED!")
            logger.info("✅ Memory stack is operational")
            logger.info("✅ Ready for agent deployment")
        else:
            logger.error(f"\n💥 {failed_tests} validations failed")
            logger.error("❌ Fix issues before proceeding")
        
        return failed_tests == 0


async def main():
    """Run Docker stack validation."""
    validator = DockerStackValidator()
    success = await validator.run_all_validations()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)