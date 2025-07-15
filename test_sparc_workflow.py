#!/usr/bin/env python3
"""
SPARC Workflow Test - Direct Agent Testing

Tests the SPARC methodology without requiring the full orchestrator service.
This simulates the complete workflow: Planner → Researcher → Coder → QA → Critic → Judge
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class MockSPARCWorkflow:
    """Mock SPARC workflow for testing without full infrastructure."""
    
    def __init__(self):
        self.session_id = f"test_session_{int(datetime.now().timestamp())}"
        self.task_history = []
        
    async def run_sparc_workflow(self, task_description: str) -> Dict[str, Any]:
        """Run complete SPARC workflow simulation."""
        logger.info("🚀 Starting SPARC Workflow Test")
        logger.info(f"📋 Task: {task_description}")
        logger.info("=" * 60)
        
        task_id = str(uuid.uuid4())[:8]
        workflow_result = {
            "task_id": task_id,
            "description": task_description,
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "status": "in_progress",
            "stages": {}
        }
        
        # SPARC Methodology: Define → Infer → Synthesize
        stages = [
            ("planner", "🎯 Planning", self._planner_stage),
            ("researcher", "🔍 Research", self._researcher_stage),
            ("coder", "💻 Implementation", self._coder_stage),
            ("qa", "🧪 Testing", self._qa_stage),
            ("critic", "🔍 Review", self._critic_stage),
            ("judge", "⚖️ Evaluation", self._judge_stage)
        ]
        
        context = {"task_description": task_description}
        
        for stage_name, stage_display, stage_func in stages:
            logger.info(f"\n{stage_display} - {stage_name.upper()} Agent")
            logger.info("-" * 40)
            
            try:
                stage_result = await stage_func(context)
                workflow_result["stages"][stage_name] = stage_result
                
                # Add stage output to context for next stage
                context[f"{stage_name}_output"] = stage_result["output"]
                
                logger.info(f"✅ {stage_display} completed")
                logger.info(f"📄 Output: {stage_result['output'][:100]}...")
                
                # Simulate processing time
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ {stage_display} failed: {e}")
                workflow_result["status"] = "failed"
                workflow_result["error"] = str(e)
                return workflow_result
        
        workflow_result["status"] = "completed"
        workflow_result["completed_at"] = datetime.now().isoformat()
        
        # Store in history
        self.task_history.append(workflow_result)
        
        return workflow_result
    
    async def _planner_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Planner agent: Task breakdown and planning."""
        task = context["task_description"]
        
        # Simulate planning logic
        plan = {
            "approach": "Break down the task into manageable components",
            "steps": [
                "1. Analyze requirements and constraints",
                "2. Research best practices and solutions",
                "3. Design implementation approach",
                "4. Implement solution with proper structure",
                "5. Test and validate functionality",
                "6. Review and optimize"
            ],
            "estimated_complexity": "medium",
            "required_resources": ["research", "coding", "testing"]
        }
        
        output = f"Task Analysis: {task}\n\nProposed Approach:\n" + "\n".join(plan["steps"])
        
        return {
            "agent_type": "planner",
            "status": "completed",
            "output": output,
            "metadata": plan,
            "processing_time": 1.2
        }
    
    async def _researcher_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Researcher agent: Information gathering and analysis."""
        
        # Simulate research based on the task
        research_findings = {
            "key_concepts": [
                "Best practices for the given task",
                "Common implementation patterns",
                "Potential challenges and solutions"
            ],
            "recommendations": [
                "Use established libraries where possible",
                "Follow industry standards",
                "Implement proper error handling"
            ],
            "references": [
                "Industry documentation",
                "Open source examples",
                "Technical specifications"
            ]
        }
        
        output = f"""Research Findings:

Key Concepts:
{chr(10).join(f"• {concept}" for concept in research_findings["key_concepts"])}

Recommendations:
{chr(10).join(f"• {rec}" for rec in research_findings["recommendations"])}

This research provides the foundation for implementation."""
        
        return {
            "agent_type": "researcher", 
            "status": "completed",
            "output": output,
            "metadata": research_findings,
            "processing_time": 2.1
        }
    
    async def _coder_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Coder agent: Implementation and development."""
        
        # Simulate code generation based on plan and research
        implementation = {
            "language": "python",
            "structure": {
                "main_function": "Primary implementation logic",
                "helper_functions": "Supporting utilities",
                "error_handling": "Comprehensive exception management",
                "documentation": "Clear docstrings and comments"
            },
            "code_example": '''def solve_task(input_data):
    """
    Main implementation function based on requirements.
    
    Args:
        input_data: Input parameters for the task
    
    Returns:
        Processed results according to specifications
    """
    try:
        # Implementation logic here
        result = process_data(input_data)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}'''
        }
        
        output = f"""Implementation Complete:

Architecture:
• {implementation['structure']['main_function']}
• {implementation['structure']['helper_functions']}
• {implementation['structure']['error_handling']}

Code Structure:
{implementation['code_example']}

Implementation follows research recommendations and planning guidelines."""
        
        return {
            "agent_type": "coder",
            "status": "completed", 
            "output": output,
            "metadata": implementation,
            "processing_time": 3.5
        }
    
    async def _qa_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """QA agent: Testing and validation."""
        
        # Simulate testing and validation
        test_results = {
            "test_categories": [
                "Unit tests for core functionality",
                "Integration tests for component interaction", 
                "Edge case testing",
                "Error handling validation"
            ],
            "coverage": "92%",
            "issues_found": [
                "Minor: Improve error message clarity",
                "Suggestion: Add input validation"
            ],
            "overall_quality": "High"
        }
        
        output = f"""Quality Assurance Report:

Test Coverage: {test_results['coverage']}
Overall Quality: {test_results['overall_quality']}

Test Categories:
{chr(10).join(f"✅ {test}" for test in test_results["test_categories"])}

Issues Identified:
{chr(10).join(f"• {issue}" for issue in test_results["issues_found"])}

Recommendation: Implementation meets quality standards with minor improvements needed."""
        
        return {
            "agent_type": "qa",
            "status": "completed",
            "output": output,
            "metadata": test_results,
            "processing_time": 2.8
        }
    
    async def _critic_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Critic agent: Critical review and improvement suggestions."""
        
        # Simulate critical analysis
        critique = {
            "strengths": [
                "Clear implementation structure",
                "Good error handling approach",
                "Follows research recommendations"
            ],
            "areas_for_improvement": [
                "Could benefit from additional documentation",
                "Consider performance optimizations",
                "Add more comprehensive logging"
            ],
            "alternative_approaches": [
                "Alternative design pattern consideration",
                "Different error handling strategy",
                "Performance vs. readability trade-offs"
            ],
            "overall_assessment": "Solid implementation with room for enhancement"
        }
        
        output = f"""Critical Analysis:

Strengths:
{chr(10).join(f"✅ {strength}" for strength in critique["strengths"])}

Areas for Improvement:
{chr(10).join(f"🔄 {improvement}" for improvement in critique["areas_for_improvement"])}

Alternative Approaches:
{chr(10).join(f"💡 {alt}" for alt in critique["alternative_approaches"])}

Assessment: {critique['overall_assessment']}"""
        
        return {
            "agent_type": "critic",
            "status": "completed",
            "output": output,
            "metadata": critique,
            "processing_time": 2.3
        }
    
    async def _judge_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Judge agent: Final evaluation and decision."""
        
        # Simulate final evaluation
        evaluation = {
            "completion_score": 85,
            "quality_score": 88,
            "adherence_to_requirements": 90,
            "overall_score": 87,
            "decision": "APPROVED",
            "reasoning": [
                "Task requirements successfully met",
                "Implementation quality is high",
                "Testing coverage is adequate",
                "Critical review recommendations are valuable"
            ],
            "next_steps": [
                "Implement minor improvements suggested by Critic",
                "Conduct final integration testing",
                "Prepare for deployment"
            ]
        }
        
        output = f"""Final Evaluation:

Scores:
• Completion: {evaluation['completion_score']}/100
• Quality: {evaluation['quality_score']}/100  
• Requirements Adherence: {evaluation['adherence_to_requirements']}/100
• Overall: {evaluation['overall_score']}/100

Decision: {evaluation['decision']}

Reasoning:
{chr(10).join(f"• {reason}" for reason in evaluation["reasoning"])}

Next Steps:
{chr(10).join(f"→ {step}" for step in evaluation["next_steps"])}"""
        
        return {
            "agent_type": "judge",
            "status": "completed",
            "output": output,
            "metadata": evaluation,
            "processing_time": 1.8
        }
    
    def generate_summary(self, workflow_result: Dict[str, Any]) -> None:
        """Generate workflow summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 SPARC Workflow Summary")
        logger.info("=" * 60)
        
        logger.info(f"Task ID: {workflow_result['task_id']}")
        logger.info(f"Status: {workflow_result['status'].upper()}")
        logger.info(f"Session: {workflow_result['session_id']}")
        
        if workflow_result["status"] == "completed":
            logger.info("\n🎯 Stage Results:")
            for stage_name, stage_data in workflow_result["stages"].items():
                agent_type = stage_data["agent_type"].upper()
                processing_time = stage_data["processing_time"]
                logger.info(f"  ✅ {agent_type}: {processing_time:.1f}s")
            
            # Calculate total processing time
            total_time = sum(stage["processing_time"] for stage in workflow_result["stages"].values())
            logger.info(f"\n⏱️ Total Processing Time: {total_time:.1f} seconds")
            
            # Show final decision
            judge_result = workflow_result["stages"]["judge"]
            decision = judge_result["metadata"]["decision"]
            overall_score = judge_result["metadata"]["overall_score"]
            logger.info(f"⚖️ Final Decision: {decision} (Score: {overall_score}/100)")
            
            logger.info("\n🎉 SPARC Workflow Completed Successfully!")
        else:
            logger.error(f"\n💥 Workflow Failed: {workflow_result.get('error', 'Unknown error')}")


async def main():
    """Run SPARC workflow test."""
    logger.info("🧪 SPARC Workflow Testing")
    
    # Test scenarios
    test_tasks = [
        "Create a Python script that analyzes log files and generates a summary report",
        "Design a simple REST API for user management with authentication",
        "Build a data processing pipeline that validates CSV input and outputs JSON"
    ]
    
    workflow = MockSPARCWorkflow()
    
    # Let user choose or run first task
    task_description = test_tasks[0]
    logger.info(f"🎯 Testing with task: {task_description}")
    
    try:
        result = await workflow.run_sparc_workflow(task_description)
        workflow.generate_summary(result)
        
        return result["status"] == "completed"
        
    except Exception as e:
        logger.error(f"❌ Workflow test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)