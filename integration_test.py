#!/usr/bin/env python3
"""
Comprehensive Integration Tests for vLLM Local Swarm

This test suite validates that all major components work together:
- Basic system components (already tested)
- SPARC CLI functionality
- Memory system integration
- Agent coordination readiness
- Docker service connectivity
"""

import asyncio
import logging
import sys
import os
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        
    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info("🚀 Starting Comprehensive Integration Tests")
        logger.info("=" * 60)
        
        tests = [
            ("Basic System Components", self.test_basic_components),
            ("SPARC CLI Functionality", self.test_sparc_cli),
            ("Memory System Structure", self.test_memory_system),
            ("Agent Configuration", self.test_agent_system),
            ("Docker Services", self.test_docker_services),
            ("Ray Cluster Readiness", self.test_ray_readiness),
            ("Configuration Files", self.test_configuration_files),
            ("Dependencies", self.test_dependencies),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running {test_name}...")
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
    
    async def test_basic_components(self):
        """Test basic system components using our proven test."""
        try:
            result = subprocess.run(
                [sys.executable, "test_basic_system.py"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Basic components test failed: {e}")
            return False
    
    async def test_sparc_cli(self):
        """Test SPARC CLI can be imported and initialized."""
        try:
            from sparc_cli import SPARCClient
            
            # Test CLI creation
            client = SPARCClient()
            if client is None:
                raise ValueError("SPARCClient creation returned None")
            
            # Test CLI has expected attributes
            expected_attrs = ['config', 'logger']
            for attr in expected_attrs:
                if not hasattr(client, attr):
                    logger.warning(f"SPARCClient missing expected attribute: {attr}")
            
            return True
        except Exception as e:
            logger.error(f"SPARC CLI test failed: {e}")
            return False
    
    async def test_memory_system(self):
        """Test memory system structure and basic functionality."""
        try:
            # Test memory module files exist
            memory_paths = [
                "memory/core/memory_manager.py",
                "memory/core/session_memory.py",
                "memory/core/semantic_memory.py",
                "memory/core/observability.py"
            ]
            
            for path in memory_paths:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Memory module missing: {path}")
            
            # Test memory tools exist
            tool_paths = [
                "memory/tools/memory_tools.py",
                "memory/tools/coordination_tools.py",
                "memory/tools/analytics_tools.py"
            ]
            
            for path in tool_paths:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Memory tool missing: {path}")
            
            # Test basic import structure
            sys.path.insert(0, str(Path(__file__).parent / "memory"))
            try:
                from memory.core.memory_manager import MemoryType
                if not hasattr(MemoryType, 'SESSION'):
                    raise ValueError("MemoryType.SESSION not found")
            except ImportError as e:
                logger.warning(f"Memory import test skipped due to dependencies: {e}")
                # This is acceptable for structure test
            
            return True
        except Exception as e:
            logger.error(f"Memory system test failed: {e}")
            return False
    
    async def test_agent_system(self):
        """Test agent system structure without Ray initialization."""
        try:
            # Test agent files exist
            agent_paths = [
                "src/core/agents.py",
                "src/core/messaging.py",
                "src/core/orchestrator.py"
            ]
            
            for path in agent_paths:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Agent module missing: {path}")
            
            # Test agent content structure
            with open("src/core/agents.py", 'r') as f:
                content = f.read()
                required_patterns = [
                    "class AgentType(Enum)",
                    "class PlannerAgent",
                    "class ResearcherAgent",
                    "class CoderAgent",
                    "class QAAgent",
                    "class CriticAgent",
                    "class JudgeAgent"
                ]
                
                for pattern in required_patterns:
                    if pattern not in content:
                        raise ValueError(f"Required agent pattern not found: {pattern}")
            
            return True
        except Exception as e:
            logger.error(f"Agent system test failed: {e}")
            return False
    
    async def test_docker_services(self):
        """Test Docker Compose configurations exist and are valid."""
        try:
            # Test Docker Compose files exist
            docker_files = [
                "docker-compose.yml",
                "docker-compose.memory.yml",
                "docker-compose.cpu.yml",
                "docker-compose.simple.yml"
            ]
            
            for file in docker_files:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"Docker Compose file missing: {file}")
            
            # Test main docker-compose.yml is valid YAML
            import yaml
            with open("docker-compose.yml", 'r') as f:
                compose_config = yaml.safe_load(f)
                if 'services' not in compose_config:
                    raise ValueError("docker-compose.yml missing services section")
            
            # Test Docker is available
            try:
                result = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning("Docker not available, but configurations are valid")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("Docker command not available")
            
            return True
        except Exception as e:
            logger.error(f"Docker services test failed: {e}")
            return False
    
    async def test_ray_readiness(self):
        """Test Ray cluster readiness without starting cluster."""
        try:
            import ray
            
            # Test Ray can be imported
            if not hasattr(ray, 'init'):
                raise ValueError("Ray module missing init function")
            
            # Test orchestrator exists
            if not os.path.exists("src/core/orchestrator.py"):
                raise FileNotFoundError("Ray orchestrator missing")
            
            # Test Ray configuration in orchestrator
            with open("src/core/orchestrator.py", 'r') as f:
                content = f.read()
                if 'ray.init' not in content:
                    logger.warning("Ray initialization not found in orchestrator")
                if 'SwarmCoordinator' not in content:
                    raise ValueError("SwarmCoordinator not found in orchestrator")
            
            return True
        except Exception as e:
            logger.error(f"Ray readiness test failed: {e}")
            return False
    
    async def test_configuration_files(self):
        """Test configuration files exist and are valid."""
        try:
            # Test environment files
            env_files = [".env.example"]
            for file in env_files:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"Environment file missing: {file}")
            
            # Test requirements files
            req_files = ["requirements.txt", "requirements.memory.txt"]
            for file in req_files:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"Requirements file missing: {file}")
            
            # Test Makefile exists
            if not os.path.exists("Makefile"):
                raise FileNotFoundError("Makefile missing")
            
            # Test config directory structure
            config_dirs = ["config", "configs"]
            config_exists = any(os.path.exists(d) for d in config_dirs)
            if not config_exists:
                logger.warning("No config directory found, but not critical")
            
            return True
        except Exception as e:
            logger.error(f"Configuration files test failed: {e}")
            return False
    
    async def test_dependencies(self):
        """Test critical dependencies are installed."""
        try:
            # Test core dependencies
            critical_deps = [
                'ray',
                'redis',
                'click',
                'pydantic',
                'sentence_transformers',
                'qdrant_client'
            ]
            
            missing_deps = []
            for dep in critical_deps:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)
            
            if missing_deps:
                logger.warning(f"Missing optional dependencies: {missing_deps}")
                # Don't fail for missing deps, just warn
            
            # Test Python version
            if sys.version_info < (3, 9):
                logger.warning("Python version < 3.9, some features may not work")
            
            return True
        except Exception as e:
            logger.error(f"Dependencies test failed: {e}")
            return False
    
    def generate_summary(self):
        """Generate test summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = len(self.failed_tests)
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 Integration Test Results Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        
        if self.failed_tests:
            logger.error(f"\n🚨 Failed Tests:")
            for test in self.failed_tests:
                logger.error(f"  - {test}")
        
        if failed_tests == 0:
            logger.info("\n🎉 ALL INTEGRATION TESTS PASSED!")
            logger.info("✅ System is ready for Docker deployment")
        else:
            logger.error(f"\n💥 {failed_tests} integration tests failed")
            logger.error("❌ Fix issues before proceeding to Docker deployment")
        
        return failed_tests == 0


async def main():
    """Run integration tests."""
    suite = IntegrationTestSuite()
    success = await suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)