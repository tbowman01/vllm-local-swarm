"""
Analytics Tools for Memory Analysis

Provides tools for analyzing memory data and generating insights.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from ..core import MemoryManager, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


class AnalyticsTool:
    """
    Tool for analyzing memory data and generating insights.
    
    Provides analytics for agent performance, coordination patterns,
    and system optimization opportunities.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize analytics tool.
        
        Args:
            memory_manager: Initialized memory manager instance
        """
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(f"{__name__}.AnalyticsTool")
    
    async def analyze_agent_performance(self, agent_id: str, 
                                       time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Analyze performance metrics for a specific agent.
        
        Args:
            agent_id: ID of the agent to analyze
            time_range: Optional time range (start, end)
            
        Returns:
            Dict containing performance analysis
        """
        # Default to last 7 days if no time range specified
        if not time_range:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            time_range = (start_time, end_time)
        
        start_time, end_time = time_range
        
        # Search for agent activities
        query = MemoryQuery(
            query="*",
            agent_id=agent_id,
            time_range=time_range,
            limit=1000
        )
        
        activities = await self.memory_manager.search(query)
        
        # Analyze activities
        analysis = {
            "agent_id": agent_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_activities": len(activities),
            "activity_breakdown": defaultdict(int),
            "memory_usage": {
                "session_entries": 0,
                "semantic_entries": 0,
                "agent_entries": 0
            },
            "coordination_metrics": {
                "handoffs_sent": 0,
                "handoffs_received": 0,
                "context_shared": 0,
                "assistance_requests": 0
            },
            "performance_metrics": {
                "avg_response_time": 0,
                "error_rate": 0,
                "task_completion_rate": 0
            },
            "learning_metrics": {
                "knowledge_stored": 0,
                "learnings_created": 0,
                "effectiveness_scores": []
            },
            "activity_timeline": [],
            "insights": []
        }
        
        # Process each activity
        total_duration = 0
        duration_count = 0
        error_count = 0
        completed_tasks = 0
        total_tasks = 0
        
        for activity in activities:
            # Count by memory type
            analysis["memory_usage"][f"{activity.type.value}_entries"] += 1
            
            # Count by tags
            for tag in activity.tags:
                analysis["activity_breakdown"][tag] += 1
            
            # Coordination metrics
            if "handoff" in activity.tags:
                content = activity.content
                if isinstance(content, dict):
                    if content.get("from_agent") == agent_id:
                        analysis["coordination_metrics"]["handoffs_sent"] += 1
                    elif content.get("to_agent") == agent_id:
                        analysis["coordination_metrics"]["handoffs_received"] += 1
            
            if "shared_context" in activity.tags:
                analysis["coordination_metrics"]["context_shared"] += 1
            
            if "assistance_request" in activity.tags:
                analysis["coordination_metrics"]["assistance_requests"] += 1
            
            # Performance metrics
            metadata = activity.metadata
            if "performance" in metadata:
                perf = metadata["performance"]
                if "duration_ms" in perf:
                    total_duration += perf["duration_ms"]
                    duration_count += 1
            
            if "error" in metadata:
                error_count += 1
            
            # Task completion tracking
            if "task" in activity.tags:
                total_tasks += 1
                if "completed" in activity.tags:
                    completed_tasks += 1
            
            # Learning metrics
            if "learning" in activity.tags:
                analysis["learning_metrics"]["learnings_created"] += 1
                content = activity.content
                if isinstance(content, dict) and "effectiveness_score" in content:
                    analysis["learning_metrics"]["effectiveness_scores"].append(
                        content["effectiveness_score"]
                    )
            
            if activity.type == MemoryType.SEMANTIC:
                analysis["learning_metrics"]["knowledge_stored"] += 1
            
            # Activity timeline (sample recent activities)
            if len(analysis["activity_timeline"]) < 20:
                analysis["activity_timeline"].append({
                    "timestamp": activity.timestamp.isoformat(),
                    "type": activity.type.value,
                    "tags": activity.tags[:3],  # First 3 tags
                    "description": activity.metadata.get("description", "")[:100]
                })
        
        # Calculate performance metrics
        if duration_count > 0:
            analysis["performance_metrics"]["avg_response_time"] = total_duration / duration_count
        
        if len(activities) > 0:
            analysis["performance_metrics"]["error_rate"] = error_count / len(activities)
        
        if total_tasks > 0:
            analysis["performance_metrics"]["task_completion_rate"] = completed_tasks / total_tasks
        
        # Calculate learning effectiveness
        effectiveness_scores = analysis["learning_metrics"]["effectiveness_scores"]
        if effectiveness_scores:
            analysis["learning_metrics"]["avg_effectiveness"] = sum(effectiveness_scores) / len(effectiveness_scores)
            analysis["learning_metrics"]["learning_trend"] = self._calculate_trend(effectiveness_scores)
        
        # Generate insights
        analysis["insights"] = self._generate_agent_insights(analysis)
        
        # Sort activity breakdown by count
        analysis["activity_breakdown"] = dict(
            sorted(analysis["activity_breakdown"].items(), 
                  key=lambda x: x[1], reverse=True)
        )
        
        return analysis
    
    async def analyze_coordination_patterns(self, session_id: Optional[str] = None,
                                          time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Analyze coordination patterns between agents.
        
        Args:
            session_id: Optional specific session to analyze
            time_range: Optional time range
            
        Returns:
            Dict containing coordination analysis
        """
        # Default to last 24 hours if no time range specified
        if not time_range:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            time_range = (start_time, end_time)
        
        start_time, end_time = time_range
        
        # Search for coordination activities
        query = MemoryQuery(
            query="coordination",
            session_id=session_id,
            time_range=time_range,
            tags=["coordination"],
            limit=1000
        )
        
        coordination_activities = await self.memory_manager.search(query)
        
        analysis = {
            "session_id": session_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_coordination_events": len(coordination_activities),
            "agent_interactions": {},
            "handoff_analysis": {
                "total_handoffs": 0,
                "completed_handoffs": 0,
                "pending_handoffs": 0,
                "failed_handoffs": 0,
                "avg_completion_time": 0,
                "handoff_chains": []
            },
            "communication_patterns": {
                "context_sharing_events": 0,
                "status_broadcasts": 0,
                "assistance_requests": 0,
                "most_active_agents": []
            },
            "coordination_efficiency": {
                "response_time_avg": 0,
                "coordination_overhead": 0,
                "bottlenecks": []
            },
            "insights": []
        }
        
        # Track agent interactions
        agent_activity = defaultdict(int)
        handoff_completion_times = []
        handoffs_by_agent = defaultdict(list)
        
        for activity in coordination_activities:
            content = activity.content
            agent_id = activity.agent_id
            
            if agent_id:
                agent_activity[agent_id] += 1
            
            # Analyze handoffs
            if "handoff" in activity.tags:
                analysis["handoff_analysis"]["total_handoffs"] += 1
                
                if isinstance(content, dict):
                    from_agent = content.get("from_agent")
                    to_agent = content.get("to_agent")
                    status = content.get("status", "unknown")
                    
                    if status == "completed":
                        analysis["handoff_analysis"]["completed_handoffs"] += 1
                        
                        # Calculate completion time
                        handoff_time = content.get("handoff_time")
                        completed_time = content.get("completed_time")
                        if handoff_time and completed_time:
                            try:
                                start = datetime.fromisoformat(handoff_time)
                                end = datetime.fromisoformat(completed_time)
                                completion_time = (end - start).total_seconds()
                                handoff_completion_times.append(completion_time)
                            except:
                                pass
                    
                    elif status == "pending":
                        analysis["handoff_analysis"]["pending_handoffs"] += 1
                    elif status == "failed":
                        analysis["handoff_analysis"]["failed_handoffs"] += 1
                    
                    # Track handoff chains
                    if from_agent and to_agent:
                        handoffs_by_agent[from_agent].append({
                            "to": to_agent,
                            "status": status,
                            "timestamp": activity.timestamp.isoformat()
                        })
            
            # Analyze communication patterns
            if "shared_context" in activity.tags:
                analysis["communication_patterns"]["context_sharing_events"] += 1
            
            if "status" in activity.tags and "broadcast" in activity.tags:
                analysis["communication_patterns"]["status_broadcasts"] += 1
            
            if "assistance_request" in activity.tags:
                analysis["communication_patterns"]["assistance_requests"] += 1
        
        # Calculate handoff metrics
        if handoff_completion_times:
            analysis["handoff_analysis"]["avg_completion_time"] = sum(handoff_completion_times) / len(handoff_completion_times)
        
        # Identify most active agents
        analysis["communication_patterns"]["most_active_agents"] = [
            {"agent_id": agent_id, "activity_count": count}
            for agent_id, count in sorted(agent_activity.items(), 
                                        key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Analyze handoff chains
        analysis["handoff_analysis"]["handoff_chains"] = self._analyze_handoff_chains(handoffs_by_agent)
        
        # Identify bottlenecks
        analysis["coordination_efficiency"]["bottlenecks"] = self._identify_coordination_bottlenecks(
            coordination_activities, handoffs_by_agent
        )
        
        # Generate insights
        analysis["insights"] = self._generate_coordination_insights(analysis)
        
        return analysis
    
    async def analyze_memory_usage(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Analyze memory system usage patterns.
        
        Args:
            time_range: Optional time range
            
        Returns:
            Dict containing memory usage analysis
        """
        # Get system stats
        system_stats = await self.memory_manager.get_system_stats()
        
        # Default to last 24 hours for time-based analysis
        if not time_range:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            time_range = (start_time, end_time)
        
        start_time, end_time = time_range
        
        analysis = {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "system_stats": system_stats,
            "memory_type_distribution": {
                "session": 0,
                "semantic": 0,
                "agent": 0,
                "trace": 0
            },
            "storage_growth": [],
            "access_patterns": {
                "read_operations": 0,
                "write_operations": 0,
                "search_operations": 0,
                "delete_operations": 0
            },
            "popular_tags": {},
            "agent_memory_usage": {},
            "session_memory_usage": {},
            "optimization_opportunities": [],
            "insights": []
        }
        
        # Analyze different memory types
        for memory_type in MemoryType:
            query = MemoryQuery(
                query="*",
                type=memory_type,
                time_range=time_range,
                limit=1000
            )
            
            entries = await self.memory_manager.search(query)
            analysis["memory_type_distribution"][memory_type.value] = len(entries)
            
            # Analyze tags
            for entry in entries:
                for tag in entry.tags:
                    analysis["popular_tags"][tag] = analysis["popular_tags"].get(tag, 0) + 1
                
                # Track by agent
                if entry.agent_id:
                    if entry.agent_id not in analysis["agent_memory_usage"]:
                        analysis["agent_memory_usage"][entry.agent_id] = {
                            "total_entries": 0,
                            "by_type": defaultdict(int)
                        }
                    analysis["agent_memory_usage"][entry.agent_id]["total_entries"] += 1
                    analysis["agent_memory_usage"][entry.agent_id]["by_type"][memory_type.value] += 1
                
                # Track by session
                if entry.session_id:
                    if entry.session_id not in analysis["session_memory_usage"]:
                        analysis["session_memory_usage"][entry.session_id] = {
                            "total_entries": 0,
                            "by_type": defaultdict(int),
                            "agents_involved": set()
                        }
                    analysis["session_memory_usage"][entry.session_id]["total_entries"] += 1
                    analysis["session_memory_usage"][entry.session_id]["by_type"][memory_type.value] += 1
                    if entry.agent_id:
                        analysis["session_memory_usage"][entry.session_id]["agents_involved"].add(entry.agent_id)
        
        # Convert sets to lists for JSON serialization
        for session_data in analysis["session_memory_usage"].values():
            session_data["agents_involved"] = list(session_data["agents_involved"])
            session_data["by_type"] = dict(session_data["by_type"])
        
        # Convert defaultdicts to dicts
        for agent_data in analysis["agent_memory_usage"].values():
            agent_data["by_type"] = dict(agent_data["by_type"])
        
        # Sort popular tags
        analysis["popular_tags"] = dict(
            sorted(analysis["popular_tags"].items(), 
                  key=lambda x: x[1], reverse=True)[:20]
        )
        
        # Generate optimization opportunities
        analysis["optimization_opportunities"] = self._identify_memory_optimization_opportunities(analysis)
        
        # Generate insights
        analysis["insights"] = self._generate_memory_insights(analysis)
        
        return analysis
    
    async def analyze_learning_effectiveness(self, agent_id: Optional[str] = None,
                                           time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Analyze learning effectiveness across the system.
        
        Args:
            agent_id: Optional specific agent to analyze
            time_range: Optional time range
            
        Returns:
            Dict containing learning analysis
        """
        # Default to last 30 days for learning analysis
        if not time_range:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            time_range = (start_time, end_time)
        
        start_time, end_time = time_range
        
        # Search for learning-related entries
        query = MemoryQuery(
            query="learning",
            agent_id=agent_id,
            time_range=time_range,
            tags=["learning"],
            limit=1000
        )
        
        learning_entries = await self.memory_manager.search(query)
        
        analysis = {
            "agent_id": agent_id,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_learning_events": len(learning_entries),
            "learning_by_agent": {},
            "effectiveness_metrics": {
                "avg_effectiveness": 0,
                "effectiveness_trend": [],
                "high_effectiveness_count": 0,
                "low_effectiveness_count": 0
            },
            "learning_types": {},
            "knowledge_growth": {
                "semantic_entries_added": 0,
                "knowledge_domains": set(),
                "reuse_rate": 0
            },
            "improvement_areas": [],
            "insights": []
        }
        
        effectiveness_scores = []
        effectiveness_over_time = []
        
        for entry in learning_entries:
            content = entry.content
            agent = entry.agent_id
            
            if agent:
                if agent not in analysis["learning_by_agent"]:
                    analysis["learning_by_agent"][agent] = {
                        "learning_count": 0,
                        "avg_effectiveness": 0,
                        "effectiveness_scores": []
                    }
                analysis["learning_by_agent"][agent]["learning_count"] += 1
            
            if isinstance(content, dict):
                # Track learning types
                learning_type = content.get("learning_type", "unknown")
                analysis["learning_types"][learning_type] = analysis["learning_types"].get(learning_type, 0) + 1
                
                # Track effectiveness
                effectiveness = content.get("effectiveness_score")
                if effectiveness is not None:
                    effectiveness_scores.append(effectiveness)
                    effectiveness_over_time.append({
                        "timestamp": entry.timestamp.isoformat(),
                        "effectiveness": effectiveness,
                        "agent": agent
                    })
                    
                    if agent:
                        analysis["learning_by_agent"][agent]["effectiveness_scores"].append(effectiveness)
                    
                    # Count high/low effectiveness
                    if effectiveness >= 0.8:
                        analysis["effectiveness_metrics"]["high_effectiveness_count"] += 1
                    elif effectiveness <= 0.3:
                        analysis["effectiveness_metrics"]["low_effectiveness_count"] += 1
                
                # Track knowledge domains
                if "domain" in content:
                    analysis["knowledge_growth"]["knowledge_domains"].add(content["domain"])
        
        # Calculate effectiveness metrics
        if effectiveness_scores:
            analysis["effectiveness_metrics"]["avg_effectiveness"] = sum(effectiveness_scores) / len(effectiveness_scores)
            analysis["effectiveness_metrics"]["effectiveness_trend"] = self._calculate_trend(effectiveness_scores)
        
        # Calculate per-agent averages
        for agent_data in analysis["learning_by_agent"].values():
            scores = agent_data["effectiveness_scores"]
            if scores:
                agent_data["avg_effectiveness"] = sum(scores) / len(scores)
        
        # Convert set to list
        analysis["knowledge_growth"]["knowledge_domains"] = list(analysis["knowledge_growth"]["knowledge_domains"])
        
        # Count semantic entries (knowledge storage)
        semantic_query = MemoryQuery(
            query="*",
            type=MemoryType.SEMANTIC,
            agent_id=agent_id,
            time_range=time_range,
            limit=1000
        )
        
        semantic_entries = await self.memory_manager.search(semantic_query)
        analysis["knowledge_growth"]["semantic_entries_added"] = len(semantic_entries)
        
        # Identify improvement areas
        analysis["improvement_areas"] = self._identify_learning_improvement_areas(analysis)
        
        # Generate insights
        analysis["insights"] = self._generate_learning_insights(analysis)
        
        return analysis
    
    async def generate_system_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive system health report.
        
        Returns:
            Dict containing system health analysis
        """
        current_time = datetime.utcnow()
        last_24h = (current_time - timedelta(hours=24), current_time)
        last_7d = (current_time - timedelta(days=7), current_time)
        
        report = {
            "timestamp": current_time.isoformat(),
            "summary": {
                "overall_health": "unknown",
                "critical_issues": 0,
                "warnings": 0,
                "recommendations": 0
            },
            "system_stats": await self.memory_manager.get_system_stats(),
            "recent_activity": {},
            "performance_trends": {},
            "coordination_health": {},
            "learning_health": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Analyze recent activity (last 24 hours)
            activity_query = MemoryQuery(
                query="*",
                time_range=last_24h,
                limit=500
            )
            
            recent_activities = await self.memory_manager.search(activity_query)
            
            report["recent_activity"] = {
                "total_activities": len(recent_activities),
                "activities_by_type": {},
                "active_agents": set(),
                "active_sessions": set(),
                "error_count": 0
            }
            
            for activity in recent_activities:
                # Count by type
                activity_type = activity.type.value
                report["recent_activity"]["activities_by_type"][activity_type] = \
                    report["recent_activity"]["activities_by_type"].get(activity_type, 0) + 1
                
                # Track active agents and sessions
                if activity.agent_id:
                    report["recent_activity"]["active_agents"].add(activity.agent_id)
                if activity.session_id:
                    report["recent_activity"]["active_sessions"].add(activity.session_id)
                
                # Count errors
                if "error" in activity.metadata:
                    report["recent_activity"]["error_count"] += 1
            
            # Convert sets to counts
            report["recent_activity"]["active_agents"] = len(report["recent_activity"]["active_agents"])
            report["recent_activity"]["active_sessions"] = len(report["recent_activity"]["active_sessions"])
            
            # Analyze coordination health
            coordination_analysis = await self.analyze_coordination_patterns(time_range=last_24h)
            report["coordination_health"] = {
                "total_coordination_events": coordination_analysis["total_coordination_events"],
                "handoff_success_rate": 0,
                "avg_response_time": coordination_analysis["coordination_efficiency"]["response_time_avg"],
                "bottlenecks_count": len(coordination_analysis["coordination_efficiency"]["bottlenecks"])
            }
            
            # Calculate handoff success rate
            handoff_analysis = coordination_analysis["handoff_analysis"]
            total_handoffs = handoff_analysis["total_handoffs"]
            if total_handoffs > 0:
                success_rate = handoff_analysis["completed_handoffs"] / total_handoffs
                report["coordination_health"]["handoff_success_rate"] = success_rate
            
            # Analyze learning health
            learning_analysis = await self.analyze_learning_effectiveness(time_range=last_7d)
            report["learning_health"] = {
                "total_learning_events": learning_analysis["total_learning_events"],
                "avg_effectiveness": learning_analysis["effectiveness_metrics"]["avg_effectiveness"],
                "knowledge_growth": learning_analysis["knowledge_growth"]["semantic_entries_added"],
                "learning_agents": len(learning_analysis["learning_by_agent"])
            }
            
            # Identify issues and recommendations
            report["issues"], report["recommendations"] = self._analyze_system_health(report)
            
            # Calculate overall health score
            report["summary"]["overall_health"] = self._calculate_health_score(report)
            report["summary"]["critical_issues"] = len([i for i in report["issues"] if i["severity"] == "critical"])
            report["summary"]["warnings"] = len([i for i in report["issues"] if i["severity"] == "warning"])
            report["summary"]["recommendations"] = len(report["recommendations"])
            
        except Exception as e:
            self.logger.error(f"Error generating system health report: {e}")
            report["error"] = str(e)
        
        return report
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        n = len(values)
        x_avg = (n - 1) / 2
        y_avg = sum(values) / n
        
        numerator = sum((i - x_avg) * (values[i] - y_avg) for i in range(n))
        denominator = sum((i - x_avg) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _generate_agent_insights(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights for agent performance analysis."""
        insights = []
        
        # Check error rate
        error_rate = analysis["performance_metrics"]["error_rate"]
        if error_rate > 0.1:  # More than 10% error rate
            insights.append({
                "type": "performance_issue",
                "severity": "high" if error_rate > 0.2 else "medium",
                "message": f"High error rate detected: {error_rate:.1%}",
                "recommendation": "Review error patterns and implement error handling improvements"
            })
        
        # Check response time
        avg_response = analysis["performance_metrics"]["avg_response_time"]
        if avg_response > 10000:  # More than 10 seconds
            insights.append({
                "type": "performance_issue",
                "severity": "medium",
                "message": f"Slow average response time: {avg_response:.0f}ms",
                "recommendation": "Optimize agent processing or add performance monitoring"
            })
        
        # Check coordination activity
        handoffs_sent = analysis["coordination_metrics"]["handoffs_sent"]
        handoffs_received = analysis["coordination_metrics"]["handoffs_received"]
        
        if handoffs_sent == 0 and handoffs_received == 0:
            insights.append({
                "type": "coordination_pattern",
                "severity": "low",
                "message": "Agent appears to be working in isolation",
                "recommendation": "Consider increasing collaboration with other agents"
            })
        
        # Check learning effectiveness
        effectiveness_scores = analysis["learning_metrics"]["effectiveness_scores"]
        if effectiveness_scores:
            avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
            if avg_effectiveness < 0.5:
                insights.append({
                    "type": "learning_issue",
                    "severity": "medium",
                    "message": f"Low learning effectiveness: {avg_effectiveness:.1%}",
                    "recommendation": "Review learning strategies and feedback mechanisms"
                })
        
        return insights
    
    def _generate_coordination_insights(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights for coordination analysis."""
        insights = []
        
        # Check handoff completion rate
        handoff_analysis = analysis["handoff_analysis"]
        total_handoffs = handoff_analysis["total_handoffs"]
        completed_handoffs = handoff_analysis["completed_handoffs"]
        
        if total_handoffs > 0:
            completion_rate = completed_handoffs / total_handoffs
            if completion_rate < 0.8:  # Less than 80% completion rate
                insights.append({
                    "type": "coordination_issue",
                    "severity": "high" if completion_rate < 0.5 else "medium",
                    "message": f"Low handoff completion rate: {completion_rate:.1%}",
                    "recommendation": "Review handoff processes and agent availability"
                })
        
        # Check for bottlenecks
        bottlenecks = analysis["coordination_efficiency"]["bottlenecks"]
        if bottlenecks:
            insights.append({
                "type": "coordination_bottleneck",
                "severity": "medium",
                "message": f"Detected {len(bottlenecks)} coordination bottlenecks",
                "recommendation": "Address identified bottlenecks to improve coordination flow"
            })
        
        return insights
    
    def _generate_memory_insights(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights for memory usage analysis."""
        insights = []
        
        # Check memory distribution
        memory_dist = analysis["memory_type_distribution"]
        total_entries = sum(memory_dist.values())
        
        if total_entries > 0:
            session_ratio = memory_dist["session"] / total_entries
            if session_ratio > 0.8:  # More than 80% session memory
                insights.append({
                    "type": "memory_usage",
                    "severity": "medium",
                    "message": "High proportion of session memory usage",
                    "recommendation": "Consider moving stable knowledge to semantic memory"
                })
        
        # Check for inactive sessions
        session_usage = analysis["session_memory_usage"]
        inactive_sessions = 0
        for session_id, data in session_usage.items():
            if data["total_entries"] < 5:  # Very few entries
                inactive_sessions += 1
        
        if inactive_sessions > len(session_usage) * 0.5:  # More than 50% inactive
            insights.append({
                "type": "memory_cleanup",
                "severity": "low",
                "message": f"{inactive_sessions} sessions with minimal activity",
                "recommendation": "Consider cleaning up inactive sessions"
            })
        
        return insights
    
    def _generate_learning_insights(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights for learning analysis."""
        insights = []
        
        # Check overall learning effectiveness
        avg_effectiveness = analysis["effectiveness_metrics"]["avg_effectiveness"]
        if avg_effectiveness < 0.6:  # Less than 60% effectiveness
            insights.append({
                "type": "learning_effectiveness",
                "severity": "medium",
                "message": f"Low average learning effectiveness: {avg_effectiveness:.1%}",
                "recommendation": "Review learning strategies and feedback mechanisms"
            })
        
        # Check learning distribution across agents
        learning_by_agent = analysis["learning_by_agent"]
        if len(learning_by_agent) < 2:
            insights.append({
                "type": "learning_distribution",
                "severity": "low",
                "message": "Learning concentrated in few agents",
                "recommendation": "Encourage broader participation in learning activities"
            })
        
        return insights
    
    def _analyze_handoff_chains(self, handoffs_by_agent: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Analyze handoff chains between agents."""
        chains = []
        
        for from_agent, handoffs in handoffs_by_agent.items():
            completed_handoffs = [h for h in handoffs if h["status"] == "completed"]
            if len(completed_handoffs) > 1:
                chains.append({
                    "from_agent": from_agent,
                    "handoff_count": len(completed_handoffs),
                    "target_agents": list(set(h["to"] for h in completed_handoffs)),
                    "latest_handoff": max(h["timestamp"] for h in completed_handoffs)
                })
        
        return sorted(chains, key=lambda x: x["handoff_count"], reverse=True)[:10]
    
    def _identify_coordination_bottlenecks(self, activities: List[Any], 
                                         handoffs_by_agent: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Identify coordination bottlenecks."""
        bottlenecks = []
        
        # Look for agents with many pending handoffs
        for from_agent, handoffs in handoffs_by_agent.items():
            pending_count = len([h for h in handoffs if h["status"] == "pending"])
            if pending_count > 3:  # More than 3 pending handoffs
                bottlenecks.append({
                    "type": "pending_handoffs",
                    "agent": from_agent,
                    "count": pending_count,
                    "description": f"Agent {from_agent} has {pending_count} pending handoffs"
                })
        
        return bottlenecks
    
    def _identify_memory_optimization_opportunities(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify memory optimization opportunities."""
        opportunities = []
        
        # Check for memory type imbalance
        memory_dist = analysis["memory_type_distribution"]
        total = sum(memory_dist.values())
        
        if total > 0:
            session_ratio = memory_dist["session"] / total
            if session_ratio > 0.8:
                opportunities.append({
                    "type": "memory_rebalancing",
                    "priority": "medium",
                    "description": "High session memory usage - consider promoting stable content to semantic memory"
                })
        
        # Check for popular tags that could benefit from indexing
        popular_tags = analysis["popular_tags"]
        if popular_tags:
            top_tag_count = list(popular_tags.values())[0]
            if top_tag_count > 100:
                opportunities.append({
                    "type": "indexing_optimization",
                    "priority": "low",
                    "description": "Consider optimizing indexing for frequently used tags"
                })
        
        return opportunities
    
    def _identify_learning_improvement_areas(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify areas for learning improvement."""
        areas = []
        
        # Check for agents with low effectiveness
        learning_by_agent = analysis["learning_by_agent"]
        for agent_id, data in learning_by_agent.items():
            if data["avg_effectiveness"] < 0.5:
                areas.append({
                    "type": "agent_learning",
                    "agent_id": agent_id,
                    "effectiveness": data["avg_effectiveness"],
                    "description": f"Agent {agent_id} has low learning effectiveness"
                })
        
        # Check for learning type imbalances
        learning_types = analysis["learning_types"]
        total_learning = sum(learning_types.values())
        
        if total_learning > 0 and len(learning_types) == 1:
            areas.append({
                "type": "learning_diversity",
                "description": "Learning activities are concentrated in a single type",
                "recommendation": "Explore diverse learning approaches"
            })
        
        return areas
    
    def _analyze_system_health(self, report: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Analyze system health and return issues and recommendations."""
        issues = []
        recommendations = []
        
        # Check recent activity levels
        recent_activity = report["recent_activity"]
        if recent_activity["total_activities"] < 10:
            issues.append({
                "type": "low_activity",
                "severity": "warning",
                "message": "Low system activity in the last 24 hours",
                "details": f"Only {recent_activity['total_activities']} activities recorded"
            })
        
        # Check error rate
        if recent_activity["total_activities"] > 0:
            error_rate = recent_activity["error_count"] / recent_activity["total_activities"]
            if error_rate > 0.1:
                issues.append({
                    "type": "high_error_rate",
                    "severity": "critical" if error_rate > 0.2 else "warning",
                    "message": f"High error rate: {error_rate:.1%}",
                    "details": f"{recent_activity['error_count']} errors out of {recent_activity['total_activities']} activities"
                })
        
        # Check coordination health
        coordination_health = report["coordination_health"]
        if coordination_health["handoff_success_rate"] < 0.8:
            issues.append({
                "type": "coordination_issues",
                "severity": "warning",
                "message": f"Low handoff success rate: {coordination_health['handoff_success_rate']:.1%}",
                "details": "Agents may be having trouble coordinating tasks"
            })
        
        # Generate recommendations based on issues
        if any(issue["type"] == "high_error_rate" for issue in issues):
            recommendations.append({
                "type": "error_monitoring",
                "priority": "high",
                "description": "Implement enhanced error monitoring and alerting",
                "action": "Review error patterns and add error handling improvements"
            })
        
        if any(issue["type"] == "coordination_issues" for issue in issues):
            recommendations.append({
                "type": "coordination_improvement",
                "priority": "medium",
                "description": "Improve agent coordination mechanisms",
                "action": "Review handoff processes and agent availability"
            })
        
        if recent_activity["active_agents"] < 2:
            recommendations.append({
                "type": "agent_activation",
                "priority": "low",
                "description": "Consider activating more agents for better coverage",
                "action": "Review agent deployment and activation policies"
            })
        
        return issues, recommendations
    
    def _calculate_health_score(self, report: Dict[str, Any]) -> str:
        """Calculate overall system health score."""
        score = 100
        
        # Deduct points for issues
        for issue in report["issues"]:
            if issue["severity"] == "critical":
                score -= 30
            elif issue["severity"] == "warning":
                score -= 15
            else:
                score -= 5
        
        # Determine health status
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 50:
            return "fair"
        elif score >= 25:
            return "poor"
        else:
            return "critical"