#!/usr/bin/env python3
"""
End-to-end integration test for vLLM Local Swarm.

This script tests the entire system from setup to teardown, validating
that all services can be built, started, and function correctly together.
"""

import subprocess
import time
import requests
import sys
import os
import json
from typing import Dict, List, Tuple, Optional

class IntegrationTester:
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def run_command(self, cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
    
    def test_prerequisites(self) -> bool:
        """Test that prerequisites are installed"""
        print("🔍 Testing Prerequisites...")
        
        # Check Docker
        rc, stdout, stderr = self.run_command(["docker", "--version"])
        if rc != 0:
            self.failed_tests.append("Docker not installed or not working")
            return False
        print(f"✅ Docker: {stdout.strip()}")
        
        # Check Docker Compose
        rc, stdout, stderr = self.run_command(["docker-compose", "--version"])
        if rc != 0:
            self.failed_tests.append("Docker Compose not installed or not working")
            return False
        print(f"✅ Docker Compose: {stdout.strip()}")
        
        # Check make
        rc, stdout, stderr = self.run_command(["make", "--version"])
        if rc != 0:
            self.failed_tests.append("Make not installed or not working")
            return False
        print(f"✅ Make: {stdout.strip().split()[0]}")
        
        return True
    
    def test_environment_setup(self) -> bool:
        """Test environment file setup"""
        print("🛠️  Testing Environment Setup...")
        
        # Check if .env exists, create if needed
        if not os.path.exists(".env"):
            rc, stdout, stderr = self.run_command(["cp", ".env.example", ".env"])
            if rc != 0:
                self.failed_tests.append("Failed to create .env file")
                return False
            print("✅ Created .env file from .env.example")
        else:
            print("✅ .env file already exists")
        
        return True
    
    def test_service_builds(self) -> bool:
        """Test building custom services"""
        print("🔨 Testing Service Builds...")
        
        # Test building Ray services
        rc, stdout, stderr = self.run_command(["make", "build-ray"], timeout=300)
        if rc != 0:
            self.failed_tests.append(f"Ray build failed: {stderr}")
            return False
        print("✅ Ray services built successfully")
        
        return True
    
    def test_basic_services_startup(self) -> bool:
        """Test starting basic services"""
        print("🚀 Testing Basic Services Startup...")
        
        # Start basic services
        rc, stdout, stderr = self.run_command(["make", "up-basic"], timeout=120)
        if rc != 0:
            self.failed_tests.append(f"Basic services startup failed: {stderr}")
            return False
        print("✅ Basic services started")
        
        # Wait for services to be ready
        print("⏳ Waiting for services to be ready...")
        time.sleep(30)
        
        return True
    
    def test_service_health(self) -> bool:
        """Test service health checks"""
        print("🏥 Testing Service Health...")
        
        # Test Redis
        try:
            rc, stdout, stderr = self.run_command(["docker", "exec", "vllm-redis", "redis-cli", "ping"])
            if rc == 0 and "PONG" in stdout:
                print("✅ Redis: Healthy")
            else:
                self.failed_tests.append("Redis health check failed")
                return False
        except Exception as e:
            self.failed_tests.append(f"Redis health check error: {e}")
            return False
        
        # Test Qdrant
        try:
            response = requests.get("http://localhost:6333/health", timeout=10)
            if response.status_code == 200:
                print("✅ Qdrant: Healthy")
            else:
                self.failed_tests.append(f"Qdrant health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.failed_tests.append(f"Qdrant health check error: {e}")
            return False
        
        # Test Langfuse DB
        try:
            rc, stdout, stderr = self.run_command(["docker", "exec", "vllm-langfuse-db", "pg_isready", "-U", "langfuse"])
            if rc == 0:
                print("✅ Langfuse DB: Healthy")
            else:
                self.failed_tests.append("Langfuse DB health check failed")
                return False
        except Exception as e:
            self.failed_tests.append(f"Langfuse DB health check error: {e}")
            return False
        
        # Test Langfuse Web (may take longer to be ready)
        max_retries = 5
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:3000/api/public/health", timeout=10)
                if response.status_code == 200:
                    print("✅ Langfuse Web: Healthy")
                    break
                else:
                    if i == max_retries - 1:
                        self.failed_tests.append(f"Langfuse Web health check failed: {response.status_code}")
                        return False
            except Exception as e:
                if i == max_retries - 1:
                    self.failed_tests.append(f"Langfuse Web health check error: {e}")
                    return False
                time.sleep(10)
        
        return True
    
    def test_ray_services(self) -> bool:
        """Test Ray services"""
        print("📡 Testing Ray Services...")
        
        # Start Ray head
        rc, stdout, stderr = self.run_command(["make", "up-ray-head"], timeout=120)
        if rc != 0:
            self.failed_tests.append(f"Ray head startup failed: {stderr}")
            return False
        print("✅ Ray head started")
        
        # Wait for Ray head to be ready
        print("⏳ Waiting for Ray head to be ready...")
        time.sleep(30)
        
        # Test Ray head status
        max_retries = 3
        for i in range(max_retries):
            try:
                rc, stdout, stderr = self.run_command(["docker", "exec", "vllm-ray-head", "ray", "status"])
                if rc == 0:
                    print("✅ Ray head: Status check passed")
                    break
                else:
                    if i == max_retries - 1:
                        self.failed_tests.append(f"Ray head status check failed: {stderr}")
                        return False
            except Exception as e:
                if i == max_retries - 1:
                    self.failed_tests.append(f"Ray head status check error: {e}")
                    return False
                time.sleep(10)
        
        # Test Ray dashboard
        try:
            response = requests.get("http://localhost:8265", timeout=10)
            if response.status_code == 200:
                print("✅ Ray Dashboard: Accessible")
            else:
                self.failed_tests.append(f"Ray dashboard check failed: {response.status_code}")
                return False
        except Exception as e:
            self.failed_tests.append(f"Ray dashboard check error: {e}")
            return False
        
        return True
    
    def test_service_management(self) -> bool:
        """Test service management commands"""
        print("🔧 Testing Service Management...")
        
        # Test health check command
        rc, stdout, stderr = self.run_command(["make", "health-basic"])
        if rc != 0:
            self.failed_tests.append(f"Health check command failed: {stderr}")
            return False
        print("✅ Health check command works")
        
        # Test service restart
        rc, stdout, stderr = self.run_command(["make", "restart-basic"])
        if rc != 0:
            self.failed_tests.append(f"Service restart failed: {stderr}")
            return False
        print("✅ Service restart works")
        
        # Wait for services to be ready after restart
        time.sleep(20)
        
        return True
    
    def test_individual_service_builds(self) -> bool:
        """Test individual service build commands"""
        print("🏗️  Testing Individual Service Builds...")
        
        # Test building individual Ray services
        rc, stdout, stderr = self.run_command(["make", "build-ray-head"], timeout=180)
        if rc != 0:
            self.failed_tests.append(f"Ray head individual build failed: {stderr}")
            return False
        print("✅ Ray head individual build works")
        
        return True
    
    def test_logs_and_monitoring(self) -> bool:
        """Test logging and monitoring commands"""
        print("📊 Testing Logs and Monitoring...")
        
        # Test status command
        rc, stdout, stderr = self.run_command(["make", "status-detailed"])
        if rc != 0:
            self.failed_tests.append(f"Status command failed: {stderr}")
            return False
        print("✅ Status command works")
        
        # Test log command (with timeout since it's interactive)
        rc, stdout, stderr = self.run_command(["timeout", "2", "make", "logs-redis"], timeout=5)
        # Exit code 124 means timeout, which is expected for log tailing
        if rc not in [0, 124]:
            self.failed_tests.append(f"Log command failed: {stderr}")
            return False
        print("✅ Log command works")
        
        return True
    
    def cleanup(self):
        """Clean up test environment"""
        print("🧹 Cleaning up test environment...")
        
        # Stop all services
        self.run_command(["make", "compose-down"], timeout=60)
        
        # Clean up Docker resources
        self.run_command(["make", "compose-clean"], timeout=60)
        
        print("✅ Cleanup completed")
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print("🧪 Starting vLLM Local Swarm Integration Tests")
        print("=" * 50)
        
        tests = [
            ("Prerequisites", self.test_prerequisites),
            ("Environment Setup", self.test_environment_setup),
            ("Service Builds", self.test_service_builds),
            ("Basic Services Startup", self.test_basic_services_startup),
            ("Service Health", self.test_service_health),
            ("Ray Services", self.test_ray_services),
            ("Service Management", self.test_service_management),
            ("Individual Service Builds", self.test_individual_service_builds),
            ("Logs and Monitoring", self.test_logs_and_monitoring),
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            try:
                if not test_func():
                    print(f"❌ {test_name} FAILED")
                    self.cleanup()
                    return False
                print(f"✅ {test_name} PASSED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
                self.failed_tests.append(f"{test_name}: {e}")
                self.cleanup()
                return False
        
        self.cleanup()
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🏁 Integration Test Summary")
        print("=" * 50)
        
        if not self.failed_tests:
            print("🎉 ALL TESTS PASSED!")
            print("✅ vLLM Local Swarm is ready for development")
        else:
            print("❌ SOME TESTS FAILED:")
            for failure in self.failed_tests:
                print(f"  - {failure}")
            print("\n🔧 Please check the troubleshooting guide: docs/TROUBLESHOOTING.md")

def main():
    """Main test runner"""
    tester = IntegrationTester()
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        if success:
            print("\n🚀 Ready to start development!")
            print("Next steps:")
            print("  1. Visit Ray Dashboard: http://localhost:8265")
            print("  2. Check Langfuse: http://localhost:3000")
            print("  3. See docs/QUICK_START.md for usage guide")
            sys.exit(0)
        else:
            print("\n❌ Integration tests failed!")
            print("Check the error messages above and refer to docs/TROUBLESHOOTING.md")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        tester.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()