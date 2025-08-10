#!/usr/bin/env python3
"""
Code Review & Testing Workflow
==============================

Demonstrates an automated code review and testing pipeline with:
- Multi-agent code analysis and security scanning
- Automated test generation and quality assurance
- Real-time collaboration between specialist agents
- Continuous integration workflow simulation

Workflow Steps:
1. Code Review Coordinator receives pull request
2. Static analysis and security scanning performed
3. Automated test generation and execution
4. Code quality metrics calculated
5. Review summary and recommendations generated

Agents Involved:
- Code Review Coordinator: Orchestrates the review process
- Security Analyst: Performs security vulnerability scanning
- Test Generator: Creates comprehensive test suites
- Code Quality Analyst: Analyzes code metrics and maintainability
- Documentation Reviewer: Reviews and suggests documentation improvements
"""

import asyncio
import logging
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from agents.communication import (
    RealtimeHub, AgentClient, ConnectionConfig, 
    AgentRole, MessageType
)
from agents.communication.integration import SmartAgentClient

logger = logging.getLogger(__name__)


class CodeReviewCoordinator(SmartAgentClient):
    """
    Coordinates the code review workflow
    """
    
    def __init__(self):
        config = ConnectionConfig(
            agent_id="code_review_coordinator",
            role=AgentRole.COORDINATOR,
            capabilities=["coordination", "code_review", "quality_control"],
            metadata={
                "type": "coordinator",
                "workflow": "code_review",
                "integrations": ["github", "gitlab", "azure_devops"]
            }
        )
        super().__init__(config, auto_accept_tasks=False)
        
        self.active_reviews: Dict[str, Dict[str, Any]] = {}
        self.review_templates = {
            "security": ["vulnerability_scan", "dependency_check", "secrets_scan"],
            "quality": ["complexity_analysis", "maintainability", "code_coverage"],
            "testing": ["unit_tests", "integration_tests", "edge_cases"],
            "documentation": ["code_comments", "api_docs", "readme_update"]
        }
        
    async def start_code_review(self, pr_config: Dict[str, Any]) -> str:
        """Start a new code review workflow"""
        review_id = f"review_{int(datetime.now().timestamp())}"
        
        self.active_reviews[review_id] = {
            "config": pr_config,
            "started_at": datetime.now().isoformat(),
            "status": "analysis",
            "tasks": [],
            "results": {},
            "metrics": {
                "files_changed": pr_config.get("files_changed", 0),
                "lines_added": pr_config.get("lines_added", 0),
                "lines_deleted": pr_config.get("lines_deleted", 0)
            }
        }
        
        logger.info(f"🔍 Starting code review: {pr_config.get('title', review_id)}")
        
        # Analyze code changes and create review plan
        review_plan = await self._create_review_plan(pr_config)
        
        # Distribute review tasks
        await self._distribute_review_tasks(review_id, review_plan)
        
        return review_id
        
    async def _create_review_plan(self, pr_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed review plan based on PR configuration"""
        
        files_changed = pr_config.get("files_changed", 0)
        languages = pr_config.get("languages", ["python"])
        change_type = pr_config.get("change_type", "feature")  # feature, bugfix, refactor
        
        # Determine required review tasks based on change characteristics
        review_tasks = []
        
        # Always perform basic security and quality checks
        review_tasks.extend([
            {
                "task_type": "security_scan",
                "description": "Perform comprehensive security vulnerability scan",
                "priority": "critical",
                "estimated_time": 10,
                "required_capabilities": ["security", "analysis"]
            },
            {
                "task_type": "code_quality",
                "description": "Analyze code quality metrics and maintainability",
                "priority": "high", 
                "estimated_time": 15,
                "required_capabilities": ["code_analysis", "quality_metrics"]
            }
        ])
        
        # Add language-specific tasks
        if "python" in languages:
            review_tasks.append({
                "task_type": "python_analysis",
                "description": "Python-specific code analysis and PEP8 compliance",
                "priority": "high",
                "estimated_time": 8,
                "required_capabilities": ["python", "code_analysis"]
            })
            
        if "javascript" in languages or "typescript" in languages:
            review_tasks.append({
                "task_type": "js_analysis", 
                "description": "JavaScript/TypeScript analysis and best practices",
                "priority": "high",
                "estimated_time": 8,
                "required_capabilities": ["javascript", "code_analysis"]
            })
            
        # Add test generation for feature changes
        if change_type in ["feature", "refactor"] or files_changed > 5:
            review_tasks.append({
                "task_type": "test_generation",
                "description": "Generate comprehensive test suite for changes",
                "priority": "high",
                "estimated_time": 20,
                "required_capabilities": ["testing", "test_generation"]
            })
            
        # Add documentation review for significant changes
        if files_changed > 3 or change_type == "feature":
            review_tasks.append({
                "task_type": "documentation_review",
                "description": "Review and update documentation",
                "priority": "medium",
                "estimated_time": 12,
                "required_capabilities": ["documentation", "writing"]
            })
            
        # Final synthesis task
        review_tasks.append({
            "task_type": "review_synthesis",
            "description": "Synthesize all review findings and generate report",
            "priority": "critical",
            "estimated_time": 15,
            "required_capabilities": ["analysis", "writing"],
            "depends_on": ["security_scan", "code_quality"]
        })
        
        return {
            "files_changed": files_changed,
            "languages": languages,
            "change_type": change_type,
            "total_tasks": len(review_tasks),
            "estimated_duration": sum(task["estimated_time"] for task in review_tasks),
            "tasks": review_tasks
        }
        
    async def _distribute_review_tasks(self, review_id: str, review_plan: Dict[str, Any]):
        """Distribute code review tasks to appropriate agents"""
        
        review = self.active_reviews[review_id]
        review["status"] = "in_progress"
        
        # Notify about review start
        await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {
                "event": "code_review_started",
                "review_id": review_id,
                "plan": review_plan,
                "coordinator": self.config.agent_id
            },
            channel="code_review_coordination"
        )
        
        # Create and send task assignments
        for task_config in review_plan["tasks"]:
            task_id = f"{review_id}_{task_config['task_type']}"
            
            task_data = {
                "task_id": task_id,
                "review_id": review_id,
                "task_type": task_config["task_type"],
                "description": task_config["description"],
                "priority": task_config["priority"],
                "estimated_time": task_config["estimated_time"],
                "required_capabilities": task_config["required_capabilities"],
                "depends_on": task_config.get("depends_on", []),
                "context": {
                    "files_changed": review_plan["files_changed"],
                    "languages": review_plan["languages"],
                    "change_type": review_plan["change_type"]
                }
            }
            
            await self.send_message(
                MessageType.TASK_ASSIGNMENT,
                task_data,
                channel="task_updates"
            )
            
            review["tasks"].append(task_id)
            
        logger.info(f"📋 Distributed {len(review_plan['tasks'])} review tasks for {review_id}")
        
    async def handle_review_completion(self, message_data: Dict[str, Any]):
        """Handle completion of review tasks"""
        data = message_data.get("data", {})
        task_id = data.get("task_id")
        review_id = data.get("review_id")
        result = data.get("result", {})
        
        if review_id not in self.active_reviews:
            return
            
        review = self.active_reviews[review_id]
        review["results"][task_id] = result
        
        logger.info(f"✅ Review task {task_id} completed for {review_id}")
        
        # Check if all tasks are complete
        completed_tasks = len(review["results"])
        total_tasks = len(review["tasks"])
        
        await self.send_message(
            MessageType.TASK_PROGRESS,
            {
                "review_id": review_id,
                "progress": completed_tasks / total_tasks,
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
                "status": f"{completed_tasks}/{total_tasks} tasks completed"
            },
            channel="code_review_coordination"
        )
        
        if completed_tasks == total_tasks:
            await self._finalize_code_review(review_id)
            
    async def _finalize_code_review(self, review_id: str):
        """Finalize completed code review"""
        review = self.active_reviews[review_id]
        review["status"] = "completed"
        review["completed_at"] = datetime.now().isoformat()
        
        # Generate final review summary
        summary = await self._generate_review_summary(review_id)
        
        # Send completion notification
        await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {
                "event": "code_review_completed",
                "review_id": review_id,
                "summary": summary
            },
            channel="code_review_coordination"
        )
        
        logger.info(f"🎉 Code review {review_id} completed!")
        
    async def _generate_review_summary(self, review_id: str) -> Dict[str, Any]:
        """Generate comprehensive review summary"""
        review = self.active_reviews[review_id]
        results = review["results"]
        
        # Aggregate findings
        security_issues = 0
        quality_issues = 0
        test_coverage = 0
        overall_score = 0
        
        critical_findings = []
        recommendations = []
        
        for task_id, result in results.items():
            if "security" in task_id:
                security_issues += result.get("issues_found", 0)
                critical_findings.extend(result.get("critical_issues", []))
                
            if "quality" in task_id:
                quality_issues += result.get("issues_found", 0)
                overall_score = result.get("quality_score", 0)
                
            if "test" in task_id:
                test_coverage = result.get("coverage_percentage", 0)
                
            recommendations.extend(result.get("recommendations", []))
            
        # Determine review outcome
        if security_issues == 0 and quality_issues < 5 and test_coverage > 80:
            outcome = "approved"
        elif security_issues > 0:
            outcome = "requires_changes" 
        else:
            outcome = "approved_with_comments"
            
        return {
            "review_id": review_id,
            "outcome": outcome,
            "overall_score": overall_score,
            "metrics": {
                "security_issues": security_issues,
                "quality_issues": quality_issues,
                "test_coverage": test_coverage
            },
            "critical_findings": critical_findings[:5],  # Top 5 critical issues
            "recommendations": recommendations[:10],  # Top 10 recommendations
            "review_duration": self._calculate_duration(review),
            "tasks_completed": len(results)
        }
        
    def _calculate_duration(self, review: Dict[str, Any]) -> str:
        """Calculate review duration"""
        if "completed_at" not in review:
            return "in_progress"
            
        start = datetime.fromisoformat(review["started_at"])
        end = datetime.fromisoformat(review["completed_at"])
        duration = end - start
        
        return f"{duration.total_seconds():.0f} seconds"


class SecurityAnalyst(SmartAgentClient):
    """
    Specialized agent for security analysis
    """
    
    def __init__(self, agent_id: str = "security_analyst"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["security", "vulnerability_analysis", "code_analysis"],
            metadata={
                "type": "security_analyst", 
                "tools": ["bandit", "safety", "semgrep", "sonarqube"],
                "specialization": "application_security"
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process security analysis tasks"""
        logger.info(f"🔒 Security Analyst processing: {description}")
        
        task_type = requirements.get("task_type", "general_security")
        languages = requirements.get("context", {}).get("languages", ["python"])
        
        if task_type == "security_scan":
            result = await self._perform_security_scan(languages)
        elif task_type == "python_analysis" and "python" in languages:
            result = await self._python_security_analysis()
        else:
            result = await self._general_security_analysis(languages)
            
        await self.report_task_completion(task_id, result)
        
    async def _perform_security_scan(self, languages: List[str]) -> Dict[str, Any]:
        """Perform comprehensive security scanning"""
        await asyncio.sleep(8)  # Simulate scanning time
        
        # Simulate security scan results
        vulnerabilities = []
        if "python" in languages:
            vulnerabilities.extend([
                {
                    "severity": "medium",
                    "type": "insecure_random",
                    "file": "auth.py",
                    "line": 45,
                    "description": "Use of insecure random number generator"
                }
            ])
            
        return {
            "type": "security_scan",
            "languages_scanned": languages,
            "vulnerabilities_found": len(vulnerabilities),
            "critical_issues": [v for v in vulnerabilities if v["severity"] == "critical"],
            "high_issues": [v for v in vulnerabilities if v["severity"] == "high"],
            "medium_issues": [v for v in vulnerabilities if v["severity"] == "medium"],
            "scan_tools": ["bandit", "safety", "semgrep"],
            "recommendations": [
                "Replace insecure random with cryptographically secure alternative",
                "Add input validation for user-provided data",
                "Implement proper error handling to prevent information disclosure"
            ],
            "security_score": 85,
            "issues_found": len(vulnerabilities)
        }
        
    async def _python_security_analysis(self) -> Dict[str, Any]:
        """Python-specific security analysis"""
        await asyncio.sleep(5)
        
        return {
            "type": "python_security",
            "checks_performed": [
                "SQL injection detection",
                "Command injection detection", 
                "Hardcoded credentials scan",
                "Insecure deserialization check"
            ],
            "pep8_compliance": 92,
            "security_issues": [
                {
                    "type": "hardcoded_secret",
                    "severity": "high",
                    "file": "config.py",
                    "description": "Potential hardcoded API key detected"
                }
            ],
            "recommendations": [
                "Move secrets to environment variables",
                "Use parameterized queries for database operations",
                "Implement proper input sanitization"
            ],
            "issues_found": 1
        }
        
    async def _general_security_analysis(self, languages: List[str]) -> Dict[str, Any]:
        """General security analysis"""
        await asyncio.sleep(4)
        
        return {
            "type": "general_security",
            "languages": languages,
            "security_patterns_checked": 25,
            "issues_found": 0,
            "security_score": 90,
            "recommendations": [
                "Continue following security best practices",
                "Regular security audits recommended"
            ]
        }


class TestGenerator(SmartAgentClient):
    """
    Specialized agent for test generation
    """
    
    def __init__(self, agent_id: str = "test_generator"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["testing", "test_generation", "code_analysis", "quality_assurance"],
            metadata={
                "type": "test_generator",
                "frameworks": ["pytest", "unittest", "jest", "mocha"],
                "test_types": ["unit", "integration", "e2e", "performance"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process test generation tasks"""
        logger.info(f"🧪 Test Generator processing: {description}")
        
        languages = requirements.get("context", {}).get("languages", ["python"])
        files_changed = requirements.get("context", {}).get("files_changed", 1)
        
        result = await self._generate_comprehensive_tests(languages, files_changed)
        await self.report_task_completion(task_id, result)
        
    async def _generate_comprehensive_tests(self, languages: List[str], files_changed: int) -> Dict[str, Any]:
        """Generate comprehensive test suite"""
        await asyncio.sleep(12)  # Simulate test generation time
        
        # Calculate test metrics based on changes
        base_tests = files_changed * 3
        edge_case_tests = files_changed * 2
        integration_tests = max(1, files_changed // 2)
        
        generated_tests = {
            "unit_tests": base_tests,
            "edge_case_tests": edge_case_tests,
            "integration_tests": integration_tests,
            "total_tests": base_tests + edge_case_tests + integration_tests
        }
        
        # Simulate test execution
        test_results = {
            "tests_passed": int(generated_tests["total_tests"] * 0.95),
            "tests_failed": int(generated_tests["total_tests"] * 0.05),
            "coverage_percentage": 87
        }
        
        return {
            "type": "test_generation",
            "languages": languages,
            "files_analyzed": files_changed,
            "generated_tests": generated_tests,
            "test_results": test_results,
            "frameworks_used": self._select_frameworks(languages),
            "test_quality_score": 88,
            "recommendations": [
                "Add more edge case testing for error conditions",
                "Implement performance tests for critical paths",
                "Consider adding integration tests for external dependencies"
            ],
            "coverage_percentage": test_results["coverage_percentage"]
        }
        
    def _select_frameworks(self, languages: List[str]) -> List[str]:
        """Select appropriate testing frameworks"""
        frameworks = []
        if "python" in languages:
            frameworks.append("pytest")
        if any(lang in languages for lang in ["javascript", "typescript"]):
            frameworks.append("jest")
        return frameworks or ["generic"]


class CodeQualityAnalyst(SmartAgentClient):
    """
    Specialized agent for code quality analysis
    """
    
    def __init__(self, agent_id: str = "code_quality_analyst"):
        config = ConnectionConfig(
            agent_id=agent_id,
            role=AgentRole.SPECIALIST,
            capabilities=["code_analysis", "quality_metrics", "refactoring"],
            metadata={
                "type": "quality_analyst",
                "metrics": ["complexity", "maintainability", "duplication", "coverage"],
                "tools": ["pylint", "sonarqube", "codeclimate"]
            }
        )
        super().__init__(config)
        
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process code quality analysis tasks"""
        logger.info(f"📏 Code Quality Analyst processing: {description}")
        
        languages = requirements.get("context", {}).get("languages", ["python"])
        files_changed = requirements.get("context", {}).get("files_changed", 1)
        
        result = await self._analyze_code_quality(languages, files_changed)
        await self.report_task_completion(task_id, result)
        
    async def _analyze_code_quality(self, languages: List[str], files_changed: int) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        await asyncio.sleep(10)  # Simulate analysis time
        
        # Simulate quality metrics
        metrics = {
            "cyclomatic_complexity": 3.2,
            "maintainability_index": 78,
            "code_duplication": 2.1,
            "technical_debt_ratio": 0.8,
            "lines_of_code": files_changed * 150
        }
        
        # Calculate overall quality score
        quality_score = int(
            (100 - min(metrics["cyclomatic_complexity"] * 10, 40)) * 0.3 +
            metrics["maintainability_index"] * 0.4 +
            (100 - metrics["code_duplication"] * 10) * 0.2 +
            (100 - metrics["technical_debt_ratio"] * 10) * 0.1
        )
        
        issues = []
        if metrics["cyclomatic_complexity"] > 5:
            issues.append("High cyclomatic complexity detected in some functions")
        if metrics["code_duplication"] > 5:
            issues.append("Code duplication above recommended threshold")
            
        return {
            "type": "code_quality",
            "languages": languages,
            "files_analyzed": files_changed,
            "quality_metrics": metrics,
            "quality_score": quality_score,
            "issues_found": len(issues),
            "quality_issues": issues,
            "recommendations": [
                "Consider breaking down complex functions into smaller units",
                "Extract common code patterns into reusable functions",
                "Add more descriptive variable and function names",
                "Implement consistent error handling patterns"
            ],
            "tools_used": ["pylint", "complexity_analyzer", "duplication_detector"]
        }


async def run_code_review_demo():
    """
    Demonstrate the code review workflow
    """
    logger.info("🚀 Starting Code Review Workflow Demo")
    
    # Start infrastructure
    realtime_hub = RealtimeHub()
    
    # Start hub in background
    hub_task = asyncio.create_task(realtime_hub.start())
    await asyncio.sleep(2)  # Give hub time to start
    
    # Create and connect agents
    coordinator = CodeReviewCoordinator()
    security_analyst = SecurityAnalyst()
    test_generator = TestGenerator()
    quality_analyst = CodeQualityAnalyst()
    
    agents = [coordinator, security_analyst, test_generator, quality_analyst]
    
    try:
        # Connect all agents
        for agent in agents:
            await agent.connect()
            await agent.subscribe_to_channel("code_review_coordination")
            await agent.subscribe_to_channel("task_updates")
            
        logger.info("✅ All review agents connected and subscribed")
        
        # Register task completion handler for coordinator
        coordinator.register_message_handler(
            MessageType.TASK_COMPLETION,
            coordinator.handle_review_completion
        )
        
        # Wait for connections to stabilize
        await asyncio.sleep(3)
        
        # Start a code review
        pr_config = {
            "title": "Add user authentication system",
            "author": "dev@example.com",
            "files_changed": 8,
            "lines_added": 250,
            "lines_deleted": 15,
            "languages": ["python", "javascript"],
            "change_type": "feature",
            "branch": "feature/auth-system",
            "target_branch": "main"
        }
        
        review_id = await coordinator.start_code_review(pr_config)
        
        # Monitor review progress
        logger.info("📊 Monitoring code review progress...")
        
        # Let the workflow run
        await asyncio.sleep(45)  # Give time for all tasks to complete
        
        # Check review status
        if review_id in coordinator.active_reviews:
            review = coordinator.active_reviews[review_id]
            logger.info(f"📈 Review Status: {review['status']}")
            logger.info(f"📋 Tasks Completed: {len(review['results'])}/{len(review['tasks'])}")
            
            # Display key findings
            for task_id, result in review["results"].items():
                task_type = result.get('type', 'unknown')
                score = result.get('security_score', result.get('quality_score', 'N/A'))
                issues = result.get('issues_found', 0)
                logger.info(f"✅ {task_type}: Score: {score}, Issues: {issues}")
                
        logger.info("🎉 Code Review Workflow Demo completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in code review demo: {e}")
        raise
    finally:
        # Cleanup
        for agent in agents:
            await agent.disconnect()
        
        # Stop hub
        hub_task.cancel()
        try:
            await hub_task
        except asyncio.CancelledError:
            pass
            
        await realtime_hub.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(run_code_review_demo())
    except KeyboardInterrupt:
        logger.info("⏹️ Code review demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Code review demo failed: {e}")
        raise