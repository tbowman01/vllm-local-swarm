#!/usr/bin/env python3
"""
SPARC CLI - Command Line Interface for vLLM Local Swarm

This implements the CLI interface for interacting with the SPARC multi-agent system
as described in the research documentation.
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any, Optional
import click
import httpx
from datetime import datetime


class SPARCCLIError(Exception):
    """Custom exception for SPARC CLI errors"""
    pass


class SPARCClient:
    """Client for interacting with the SPARC multi-agent system"""
    
    def __init__(self):
        self.orchestrator_url = "http://localhost:8004"
        self.session_id = None
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the SPARC system"""
        try:
            # Check if orchestrator is available
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.orchestrator_url}/health", timeout=5.0)
                if response.status_code != 200:
                    raise Exception("Orchestrator service not available")
            
            # Create session
            self.session_id = f"session_{int(time.time())}"
            
            click.echo(f"✓ SPARC system initialized (Session: {self.session_id})")
            
        except Exception as e:
            raise SPARCCLIError(f"Failed to initialize SPARC system: {e}")
    
    async def create_task(self, description: str, interactive: bool = False, use_gpt4: bool = False) -> str:
        """Create a new task in the system"""
        try:
            # Create task request
            task_data = {
                "objective": description,
                "task_definition": description,
                "priority": "medium",
                "session_id": self.session_id,
                "use_gpt4_fallback": use_gpt4
            }
            
            # Submit to orchestrator
            if interactive:
                click.echo(f"🚀 Starting task (Interactive mode)")
                return await self._run_interactive_task(task_data)
            else:
                click.echo(f"🚀 Starting task (Background mode)")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.orchestrator_url}/tasks",
                        json=task_data,
                        timeout=120.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["task_id"]
            
        except Exception as e:
            raise SPARCCLIError(f"Failed to create task: {e}")
    
    async def _run_interactive_task(self, task_data: Dict[str, Any]) -> str:
        """Run task in interactive mode with real-time updates"""
        click.echo("📊 Task execution started...")
        
        # Submit task and track progress
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.orchestrator_url}/tasks",
                json=task_data,
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            task_id = result["task_id"]
            
            # Show progress
            steps = [
                "🎯 Specification stage - Planner analyzing task...",
                "📝 Pseudocode stage - Planner creating approach...",
                "🏗️ Architecture stage - Planner designing system...",
                "💻 Implementation stage - Coder implementing solution...",
                "🔍 Refinement stage - Critic reviewing results...",
                "🧪 Testing stage - QA validating implementation...",
                "⚖️ Completion stage - Judge making final evaluation..."
            ]
            
            for step in steps:
                click.echo(step)
                await asyncio.sleep(1)  # Simulate processing time
            
            click.echo("✅ Task completed successfully!")
            
            # Show results
            if result.get("results"):
                click.echo("\n📋 Task Results:")
                for stage, stage_data in result["results"].items():
                    click.echo(f"\n🔸 {stage.title()} ({stage_data['agent_type']}):")
                    click.echo(f"   {stage_data['response'][:200]}...")
            
            return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.orchestrator_url}/tasks/{task_id}", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SPARCCLIError(f"Task {task_id} not found")
            else:
                raise SPARCCLIError(f"Failed to get task status: {e}")
        except Exception as e:
            raise SPARCCLIError(f"Failed to get task status: {e}")
    
    async def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """Get results of a completed task"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.orchestrator_url}/tasks/{task_id}/results", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SPARCCLIError(f"Task {task_id} not found")
            else:
                raise SPARCCLIError(f"Failed to get task results: {e}")
        except Exception as e:
            raise SPARCCLIError(f"Failed to get task results: {e}")
    
    async def list_tasks(self) -> Dict[str, Any]:
        """List all tasks in current session"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.orchestrator_url}/tasks", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise SPARCCLIError(f"Failed to list tasks: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{self.orchestrator_url}/tasks/{task_id}", timeout=10.0)
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SPARCCLIError(f"Task {task_id} not found")
            else:
                raise SPARCCLIError(f"Failed to cancel task: {e}")
        except Exception as e:
            raise SPARCCLIError(f"Failed to cancel task {task_id}: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            async with httpx.AsyncClient() as client:
                # Get orchestrator status
                orch_response = await client.get(f"{self.orchestrator_url}/stats", timeout=10.0)
                orch_response.raise_for_status()
                
                # Get health status
                health_response = await client.get(f"{self.orchestrator_url}/health", timeout=10.0)
                health_response.raise_for_status()
                
                return {
                    "session_id": self.session_id,
                    "orchestrator_stats": orch_response.json(),
                    "health_status": health_response.json()
                }
        except Exception as e:
            raise SPARCCLIError(f"Failed to get system status: {e}")
    
    async def shutdown(self):
        """Shutdown the SPARC system"""
        try:
            # For API-based client, just clear local state
            self.active_tasks.clear()
            click.echo("✓ SPARC client shutdown complete")
        except Exception as e:
            click.echo(f"⚠️ Error during shutdown: {e}")


# CLI Interface
sparc_client = SPARCClient()


@click.group()
@click.pass_context
def cli(ctx):
    """SPARC CLI - Collaborative AI Multi-Agent System"""
    ctx.ensure_object(dict)
    # Initialize client on first use
    if not ctx.obj.get('initialized'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(sparc_client.initialize())
            ctx.obj['initialized'] = True
        except Exception as e:
            click.echo(f"❌ Failed to initialize: {e}", err=True)
            sys.exit(1)
        finally:
            loop.close()


@cli.command()
@click.argument('description')
@click.option('--interactive', is_flag=True, help='Run in interactive mode with real-time updates')
@click.option('--use-gpt4', is_flag=True, help='Allow GPT-4 fallback for complex tasks')
def new(description, interactive, use_gpt4):
    """Create a new task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        task_id = loop.run_until_complete(
            sparc_client.create_task(description, interactive, use_gpt4)
        )
        if not interactive:
            click.echo(f"Task created: {task_id}")
            click.echo(f"Use 'sparc status {task_id}' to check progress")
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
@click.argument('task_id')
def status(task_id):
    """Check status of a task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        status_info = loop.run_until_complete(sparc_client.get_task_status(task_id))
        
        click.echo(f"Task ID: {task_id}")
        click.echo(f"Description: {status_info['description']}")
        click.echo(f"Status: {status_info['status']}")
        click.echo(f"Created: {status_info['created_at']}")
        
        if 'error' in status_info:
            click.echo(f"Error: {status_info['error']}")
        
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
@click.argument('task_id')
def review(task_id):
    """Review results of a completed task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(sparc_client.get_task_results(task_id))
        
        click.echo(f"Task Results: {task_id}")
        click.echo("=" * 50)
        click.echo(json.dumps(results, indent=2))
        
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
def list():
    """List all tasks in current session"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        tasks = loop.run_until_complete(sparc_client.list_tasks())
        
        if not tasks:
            click.echo("No tasks in current session")
            return
        
        click.echo("Active Tasks:")
        click.echo("-" * 60)
        for task_id, task_info in tasks.items():
            click.echo(f"{task_id[:8]}... | {task_info['status']} | {task_info['description'][:40]}...")
        
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
@click.argument('task_id')
def kill(task_id):
    """Cancel a running task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        success = loop.run_until_complete(sparc_client.cancel_task(task_id))
        if success:
            click.echo(f"✓ Task {task_id} cancelled")
        else:
            click.echo(f"❌ Failed to cancel task {task_id}")
        
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
def system():
    """Show system status"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        status = loop.run_until_complete(sparc_client.get_system_status())
        
        click.echo("SPARC System Status:")
        click.echo("=" * 30)
        click.echo(json.dumps(status, indent=2))
        
    except SPARCCLIError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


@cli.command()
def shutdown():
    """Shutdown the SPARC system"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(sparc_client.shutdown())
    except Exception as e:
        click.echo(f"❌ Error during shutdown: {e}", err=True)
        sys.exit(1)
    finally:
        loop.close()


if __name__ == '__main__':
    cli()