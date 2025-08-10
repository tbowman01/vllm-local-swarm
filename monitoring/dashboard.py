#!/usr/bin/env python3
"""
Real-Time Monitoring Dashboard for vLLM Local Swarm
=================================================

Comprehensive monitoring dashboard with:
- Real-time agent activity and performance metrics
- Task queue monitoring and health status
- Memory usage and semantic search analytics
- Interactive web-based dashboard with live updates
- Alert system for system issues
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import os

try:
    from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    import uvicorn
    import websockets
except ImportError:
    print("Installing dashboard dependencies...")
    import subprocess
    subprocess.run([
        "pip", "install", 
        "fastapi", "uvicorn[standard]", "websockets"
    ], check=True)
    from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    import uvicorn
    import websockets

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    agent_id: str
    name: str
    role: str
    status: str
    tasks_completed: int
    tasks_failed: int
    average_response_time: float
    success_rate: float
    current_load: int
    memory_usage_mb: float
    last_activity: datetime
    specialization_scores: Dict[str, float]


@dataclass
class TaskQueueMetrics:
    """Task queue performance metrics"""
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    queue_sizes: Dict[str, int]
    average_processing_time: float
    throughput_per_hour: float
    success_rate: float


@dataclass
class MemoryMetrics:
    """Memory system metrics"""
    total_entries: int
    memory_types: Dict[str, int]
    storage_size_mb: float
    search_performance: Dict[str, float]
    cache_hit_rate: float
    recent_activity: List[Dict[str, Any]]


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: str  # healthy, warning, critical
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    error_rate: float
    response_time: float


class MonitoringDashboard:
    """
    Real-time monitoring dashboard for the vLLM Local Swarm
    """
    
    def __init__(self, port: int = 8009):
        self.port = port
        self.app = FastAPI(title="vLLM Swarm Monitor", version="1.0.0")
        
        # Data storage
        self.current_metrics = {
            'agents': {},
            'task_queue': {},
            'memory': {},
            'system_health': {},
            'alerts': []
        }
        
        # WebSocket connections for live updates
        self.websocket_connections: List[WebSocket] = []
        
        # Configuration
        self.refresh_interval = 5  # seconds
        self.alert_thresholds = {
            'error_rate': 0.1,      # 10%
            'response_time': 10.0,   # 10 seconds
            'memory_usage': 0.9,     # 90%
            'cpu_usage': 0.85,       # 85%
            'success_rate': 0.8      # 80%
        }
        
        # Background tasks
        self._running = False
        self._metrics_task = None
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return await self._get_dashboard_html()
            
        @self.app.get("/api/metrics")
        async def get_metrics():
            return self.current_metrics
            
        @self.app.get("/api/agents")
        async def get_agents():
            return self.current_metrics.get('agents', {})
            
        @self.app.get("/api/tasks")
        async def get_task_queue():
            return self.current_metrics.get('task_queue', {})
            
        @self.app.get("/api/memory")
        async def get_memory():
            return self.current_metrics.get('memory', {})
            
        @self.app.get("/api/health")
        async def get_health():
            return self.current_metrics.get('system_health', {})
            
        @self.app.get("/api/alerts")
        async def get_alerts():
            return self.current_metrics.get('alerts', [])
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)
            
        @self.app.post("/api/alerts/acknowledge/{alert_id}")
        async def acknowledge_alert(alert_id: str):
            return await self._acknowledge_alert(alert_id)
            
    async def start(self):
        """Start the monitoring dashboard"""
        if self._running:
            return
            
        self._running = True
        
        logger.info(f"🚀 Starting Monitoring Dashboard on port {self.port}")
        
        # Start background metrics collection
        self._metrics_task = asyncio.create_task(self._metrics_loop())
        
        # Start FastAPI server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"❌ Dashboard server error: {e}")
            raise
            
    async def stop(self):
        """Stop the monitoring dashboard"""
        self._running = False
        
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
                
        logger.info("🛑 Monitoring Dashboard stopped")
        
    async def _metrics_loop(self):
        """Background metrics collection loop"""
        while self._running:
            try:
                # Collect metrics from all components
                await self._collect_agent_metrics()
                await self._collect_task_queue_metrics()
                await self._collect_memory_metrics()
                await self._collect_system_health()
                
                # Check for alerts
                await self._check_alerts()
                
                # Broadcast updates to WebSocket clients
                await self._broadcast_updates()
                
                # Wait before next collection
                await asyncio.sleep(self.refresh_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in metrics collection: {e}")
                await asyncio.sleep(10)
                
    async def _collect_agent_metrics(self):
        """Collect metrics from agent communication hub"""
        try:
            # Connect to real-time hub to get agent metrics
            hub_url = "ws://localhost:8008"
            
            # Simulate agent metrics collection
            # In a real implementation, this would connect to the actual hub
            sample_agents = {
                "research_specialist": AgentMetrics(
                    agent_id="research_specialist",
                    name="Research Specialist",
                    role="specialist",
                    status="active",
                    tasks_completed=45,
                    tasks_failed=2,
                    average_response_time=3.2,
                    success_rate=0.96,
                    current_load=2,
                    memory_usage_mb=256.5,
                    last_activity=datetime.now(),
                    specialization_scores={"research": 0.95, "analysis": 0.88}
                ),
                "content_creator": AgentMetrics(
                    agent_id="content_creator",
                    name="Content Creator",
                    role="specialist", 
                    status="active",
                    tasks_completed=32,
                    tasks_failed=1,
                    average_response_time=5.8,
                    success_rate=0.97,
                    current_load=1,
                    memory_usage_mb=312.1,
                    last_activity=datetime.now() - timedelta(minutes=2),
                    specialization_scores={"writing": 0.93, "creativity": 0.91}
                ),
                "code_reviewer": AgentMetrics(
                    agent_id="code_reviewer",
                    name="Code Reviewer",
                    role="specialist",
                    status="idle",
                    tasks_completed=28,
                    tasks_failed=0,
                    average_response_time=4.1,
                    success_rate=1.0,
                    current_load=0,
                    memory_usage_mb=189.3,
                    last_activity=datetime.now() - timedelta(minutes=15),
                    specialization_scores={"security": 0.89, "quality": 0.94}
                )
            }
            
            self.current_metrics['agents'] = {
                agent_id: asdict(metrics) 
                for agent_id, metrics in sample_agents.items()
            }
            
        except Exception as e:
            logger.error(f"❌ Error collecting agent metrics: {e}")
            
    async def _collect_task_queue_metrics(self):
        """Collect metrics from task queue system"""
        try:
            # Simulate task queue metrics
            # In a real implementation, this would connect to the actual queue
            metrics = TaskQueueMetrics(
                total_tasks=156,
                pending_tasks=8,
                processing_tasks=3,
                completed_tasks=140,
                failed_tasks=5,
                queue_sizes={
                    "critical": 1,
                    "high": 2,
                    "normal": 4,
                    "low": 1,
                    "background": 0
                },
                average_processing_time=4.7,
                throughput_per_hour=28.5,
                success_rate=0.97
            )
            
            self.current_metrics['task_queue'] = asdict(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error collecting task queue metrics: {e}")
            
    async def _collect_memory_metrics(self):
        """Collect metrics from memory system"""
        try:
            # Simulate memory metrics
            metrics = MemoryMetrics(
                total_entries=1247,
                memory_types={
                    "session": 523,
                    "semantic": 389,
                    "agent": 267,
                    "trace": 68
                },
                storage_size_mb=89.4,
                search_performance={
                    "avg_search_time": 0.032,
                    "cache_hit_rate": 0.78,
                    "index_size": 1247
                },
                cache_hit_rate=0.78,
                recent_activity=[
                    {
                        "type": "search",
                        "query": "AI implementation best practices",
                        "results": 12,
                        "time": 0.028,
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "type": "insert",
                        "memory_type": "semantic",
                        "content_size": 1024,
                        "timestamp": (datetime.now() - timedelta(minutes=3)).isoformat()
                    }
                ]
            )
            
            self.current_metrics['memory'] = asdict(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error collecting memory metrics: {e}")
            
    async def _collect_system_health(self):
        """Collect overall system health metrics"""
        try:
            # Simulate system health metrics
            # In a real implementation, this would use psutil or similar
            health = SystemHealth(
                status="healthy",
                uptime=3600.5,  # seconds
                cpu_usage=0.35,
                memory_usage=0.67,
                disk_usage=0.45,
                active_connections=12,
                error_rate=0.03,
                response_time=1.2
            )
            
            self.current_metrics['system_health'] = asdict(health)
            
        except Exception as e:
            logger.error(f"❌ Error collecting system health: {e}")
            
    async def _check_alerts(self):
        """Check for system alerts based on thresholds"""
        try:
            new_alerts = []
            current_time = datetime.now()
            
            # Check system health alerts
            health = self.current_metrics.get('system_health', {})
            
            if health.get('error_rate', 0) > self.alert_thresholds['error_rate']:
                new_alerts.append({
                    'id': f"alert_{int(current_time.timestamp())}",
                    'type': 'error_rate',
                    'severity': 'warning',
                    'title': 'High Error Rate',
                    'message': f"Error rate {health['error_rate']:.1%} exceeds threshold",
                    'timestamp': current_time.isoformat(),
                    'acknowledged': False
                })
                
            if health.get('response_time', 0) > self.alert_thresholds['response_time']:
                new_alerts.append({
                    'id': f"alert_{int(current_time.timestamp()) + 1}",
                    'type': 'response_time',
                    'severity': 'warning',
                    'title': 'Slow Response Time',
                    'message': f"Response time {health['response_time']:.1f}s exceeds threshold",
                    'timestamp': current_time.isoformat(),
                    'acknowledged': False
                })
                
            # Check agent alerts
            agents = self.current_metrics.get('agents', {})
            for agent_id, agent_data in agents.items():
                if agent_data.get('success_rate', 1.0) < self.alert_thresholds['success_rate']:
                    new_alerts.append({
                        'id': f"alert_agent_{agent_id}_{int(current_time.timestamp())}",
                        'type': 'agent_performance',
                        'severity': 'warning',
                        'title': f'Agent {agent_id} Low Success Rate',
                        'message': f"Success rate {agent_data['success_rate']:.1%} below threshold",
                        'timestamp': current_time.isoformat(),
                        'acknowledged': False
                    })
                    
            # Add new alerts
            if not hasattr(self, '_last_alert_check'):
                self._last_alert_check = current_time
                
            # Only add new alerts to avoid duplicates
            time_threshold = current_time - timedelta(minutes=5)
            existing_alerts = [
                alert for alert in self.current_metrics.get('alerts', [])
                if datetime.fromisoformat(alert['timestamp']) > time_threshold
            ]
            
            self.current_metrics['alerts'] = existing_alerts + new_alerts
            
            # Limit alert history
            if len(self.current_metrics['alerts']) > 50:
                self.current_metrics['alerts'] = self.current_metrics['alerts'][-50:]
                
        except Exception as e:
            logger.error(f"❌ Error checking alerts: {e}")
            
    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections for live updates"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            # Send initial data
            await websocket.send_json({
                'type': 'initial_data',
                'data': self.current_metrics
            })
            
            # Keep connection alive
            while True:
                await websocket.receive_text()
                
        except Exception as e:
            logger.debug(f"WebSocket connection closed: {e}")
        finally:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
                
    async def _broadcast_updates(self):
        """Broadcast updates to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
            
        message = {
            'type': 'metrics_update',
            'data': self.current_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to all connected clients
        disconnected_clients = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_clients.append(websocket)
                
        # Remove disconnected clients
        for client in disconnected_clients:
            self.websocket_connections.remove(client)
            
    async def _acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        alerts = self.current_metrics.get('alerts', [])
        
        for alert in alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now().isoformat()
                return {"status": "acknowledged"}
                
        raise HTTPException(status_code=404, detail="Alert not found")
        
    async def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vLLM Swarm Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background: #34c759; }
        .status-warning { background: #ff9500; }
        .status-critical { background: #ff3b30; }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            border: 1px solid #e5e5e7;
        }
        
        .metric-card h3 {
            color: #1d1d1f;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007aff;
            margin-bottom: 5px;
        }
        
        .metric-label {
            color: #86868b;
            font-size: 0.9em;
        }
        
        .agents-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .agent-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #007aff;
        }
        
        .agent-name {
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .agent-stats {
            font-size: 0.9em;
            color: #86868b;
        }
        
        .alerts {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .alert {
            padding: 10px;
            margin: 10px 0;
            border-radius: 6px;
            border-left: 4px solid #ff9500;
            background: #fff5e6;
        }
        
        .alert.critical {
            border-left-color: #ff3b30;
            background: #ffe6e6;
        }
        
        .live-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #34c759;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            z-index: 1000;
        }
        
        .live-indicator::before {
            content: "●";
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="live-indicator" id="liveIndicator">
        LIVE
    </div>
    
    <div class="header">
        <h1>🤖 vLLM Swarm Monitor</h1>
        <p>Real-time monitoring dashboard for agent coordination system</p>
        <div id="systemStatus" style="margin-top: 10px;">
            <span class="status-indicator status-healthy"></span>
            <span>System Status: <span id="statusText">Healthy</span></span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Active Agents</h3>
                <div class="metric-value" id="activeAgents">-</div>
                <div class="metric-label">Connected and operational</div>
            </div>
            
            <div class="metric-card">
                <h3>Task Queue</h3>
                <div class="metric-value" id="taskQueue">-</div>
                <div class="metric-label">Pending tasks</div>
            </div>
            
            <div class="metric-card">
                <h3>Success Rate</h3>
                <div class="metric-value" id="successRate">-</div>
                <div class="metric-label">Overall system performance</div>
            </div>
            
            <div class="metric-card">
                <h3>Memory Usage</h3>
                <div class="metric-value" id="memoryUsage">-</div>
                <div class="metric-label">System memory utilization</div>
            </div>
        </div>
        
        <div class="metric-card">
            <h3>🤖 Active Agents</h3>
            <div class="agents-list" id="agentsList">
                <!-- Agents will be populated here -->
            </div>
        </div>
        
        <div class="alerts">
            <h3>🚨 System Alerts</h3>
            <div id="alertsList">
                <!-- Alerts will be populated here -->
            </div>
        </div>
    </div>

    <script>
        class DashboardMonitor {
            constructor() {
                this.ws = null;
                this.reconnectTimeout = null;
                this.isConnected = false;
                
                this.initWebSocket();
                this.updateLiveIndicator();
            }
            
            initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.updateLiveIndicator();
                    if (this.reconnectTimeout) {
                        clearTimeout(this.reconnectTimeout);
                        this.reconnectTimeout = null;
                    }
                };
                
                this.ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.isConnected = false;
                    this.updateLiveIndicator();
                    this.scheduleReconnect();
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }
            
            scheduleReconnect() {
                if (this.reconnectTimeout) return;
                
                this.reconnectTimeout = setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    this.initWebSocket();
                }, 3000);
            }
            
            handleMessage(message) {
                if (message.type === 'initial_data' || message.type === 'metrics_update') {
                    this.updateDashboard(message.data);
                }
            }
            
            updateDashboard(data) {
                this.updateMetrics(data);
                this.updateAgents(data.agents || {});
                this.updateAlerts(data.alerts || []);
            }
            
            updateMetrics(data) {
                const agents = data.agents || {};
                const taskQueue = data.task_queue || {};
                const systemHealth = data.system_health || {};
                
                // Update metric cards
                document.getElementById('activeAgents').textContent = 
                    Object.keys(agents).filter(id => agents[id].status === 'active').length;
                    
                document.getElementById('taskQueue').textContent = 
                    taskQueue.pending_tasks || 0;
                    
                document.getElementById('successRate').textContent = 
                    ((taskQueue.success_rate || 0) * 100).toFixed(1) + '%';
                    
                document.getElementById('memoryUsage').textContent = 
                    ((systemHealth.memory_usage || 0) * 100).toFixed(1) + '%';
                
                // Update system status
                const status = systemHealth.status || 'unknown';
                const statusText = document.getElementById('statusText');
                const statusIndicator = document.querySelector('.status-indicator');
                
                statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                
                statusIndicator.className = 'status-indicator';
                if (status === 'healthy') statusIndicator.classList.add('status-healthy');
                else if (status === 'warning') statusIndicator.classList.add('status-warning');
                else statusIndicator.classList.add('status-critical');
            }
            
            updateAgents(agents) {
                const agentsList = document.getElementById('agentsList');
                agentsList.innerHTML = '';
                
                for (const [agentId, agent] of Object.entries(agents)) {
                    const agentCard = document.createElement('div');
                    agentCard.className = 'agent-card';
                    
                    const statusColor = agent.status === 'active' ? '#34c759' : 
                                       agent.status === 'idle' ? '#ff9500' : '#ff3b30';
                    
                    agentCard.style.borderLeftColor = statusColor;
                    
                    agentCard.innerHTML = `
                        <div class="agent-name">
                            ${agent.name || agentId}
                            <span style="color: ${statusColor}; font-size: 0.8em;">[${agent.status}]</span>
                        </div>
                        <div class="agent-stats">
                            Tasks: ${agent.tasks_completed}/${agent.tasks_completed + agent.tasks_failed}<br>
                            Success: ${(agent.success_rate * 100).toFixed(1)}%<br>
                            Load: ${agent.current_load}/${agent.current_load + 2}
                        </div>
                    `;
                    
                    agentsList.appendChild(agentCard);
                }
            }
            
            updateAlerts(alerts) {
                const alertsList = document.getElementById('alertsList');
                
                if (alerts.length === 0) {
                    alertsList.innerHTML = '<p style="color: #34c759;">No active alerts - system running smoothly! ✅</p>';
                    return;
                }
                
                alertsList.innerHTML = '';
                
                alerts.slice(-10).forEach(alert => {
                    if (alert.acknowledged) return;
                    
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `alert ${alert.severity}`;
                    
                    alertDiv.innerHTML = `
                        <strong>${alert.title}</strong><br>
                        ${alert.message}<br>
                        <small>${new Date(alert.timestamp).toLocaleString()}</small>
                    `;
                    
                    alertsList.appendChild(alertDiv);
                });
            }
            
            updateLiveIndicator() {
                const indicator = document.getElementById('liveIndicator');
                if (this.isConnected) {
                    indicator.textContent = 'LIVE';
                    indicator.style.backgroundColor = '#34c759';
                } else {
                    indicator.textContent = 'DISCONNECTED';
                    indicator.style.backgroundColor = '#ff3b30';
                }
            }
        }
        
        // Initialize dashboard when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new DashboardMonitor();
        });
    </script>
</body>
</html>
        """


# Example usage and testing
async def test_monitoring_dashboard():
    """Test the monitoring dashboard"""
    
    dashboard = MonitoringDashboard(port=8009)
    
    try:
        logger.info("🚀 Starting Monitoring Dashboard test...")
        logger.info("📊 Dashboard available at: http://localhost:8009")
        
        # Start dashboard
        await dashboard.start()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down dashboard...")
        await dashboard.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_monitoring_dashboard())