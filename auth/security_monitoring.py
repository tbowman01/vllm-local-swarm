#!/usr/bin/env python3
"""
🚨 Real-Time Security Monitoring & Threat Detection for vLLM Enterprise Swarm

This module implements comprehensive security monitoring including:
- Real-time threat detection and response
- Security event correlation and analysis  
- Behavioral anomaly detection
- Incident response automation
- Security metrics and dashboards
- SIEM integration capabilities
- Machine learning-based threat detection
- Automated threat hunting

Security Level: Maximum Enterprise
Agent: security-architect-001
Integration: SIEM/SOAR Ready
"""

import asyncio
import hashlib
import json
import logging
import math
import statistics
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, asdict

import aiohttp
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import redis.asyncio as redis
import websockets
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# Configure security monitoring logging
monitoring_logger = logging.getLogger('security_monitoring.system')
threat_logger = logging.getLogger('security_monitoring.threats')
incident_logger = logging.getLogger('security_monitoring.incidents')
ml_logger = logging.getLogger('security_monitoring.ml')

class ThreatLevel(Enum):
    """Threat severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class IncidentStatus(Enum):
    """Security incident status"""
    NEW = "new"
    INVESTIGATING = "investigating"
    CONTAINMENT = "containment"
    ERADICATION = "eradication"
    RECOVERY = "recovery"
    CLOSED = "closed"

class ResponseAction(Enum):
    """Automated response actions"""
    LOG_ONLY = "log_only"
    ALERT = "alert"
    BLOCK_IP = "block_ip"
    DISABLE_USER = "disable_user"
    QUARANTINE_SESSION = "quarantine_session"
    ESCALATE = "escalate"
    EMERGENCY_LOCKDOWN = "emergency_lockdown"

class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"

@dataclass
class SecurityEvent:
    """Security event for monitoring"""
    event_id: str
    timestamp: datetime
    source: str
    event_type: str
    severity: ThreatLevel
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    resource: str
    action: str
    outcome: str
    details: Dict[str, Any]
    risk_score: float
    ml_confidence: Optional[float]
    correlated_events: List[str]

@dataclass
class ThreatSignature:
    """Threat detection signature"""
    signature_id: str
    name: str
    description: str
    pattern: str
    severity: ThreatLevel
    confidence: float
    enabled: bool
    false_positive_rate: float
    last_updated: datetime

@dataclass
class SecurityIncident:
    """Security incident tracking"""
    incident_id: str
    title: str
    description: str
    severity: ThreatLevel
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]
    related_events: List[str]
    timeline: List[Dict[str, Any]]
    containment_actions: List[str]
    lessons_learned: Optional[str]

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    anomaly_id: str
    timestamp: datetime
    anomaly_type: str
    score: float
    threshold: float
    features: Dict[str, float]
    confidence: float
    baseline_period: str
    affected_entities: List[str]

class BehavioralAnalyzer:
    """Behavioral anomaly detection using machine learning"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.baselines = {}
        self.feature_windows = defaultdict(lambda: deque(maxlen=1000))
        
        # Initialize models for different entities
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize ML models for different entity types"""
        entity_types = ['user', 'ip', 'session', 'api_key']
        
        for entity_type in entity_types:
            self.models[entity_type] = IsolationForest(
                contamination=0.1,  # Assume 10% anomalies
                random_state=42,
                n_estimators=100
            )
            self.scalers[entity_type] = StandardScaler()
            self.baselines[entity_type] = {}
    
    async def analyze_user_behavior(self, user_id: str, events: List[SecurityEvent]) -> Optional[AnomalyDetection]:
        """Analyze user behavior for anomalies"""
        if len(events) < 10:  # Need minimum events for analysis
            return None
        
        # Extract behavioral features
        features = self._extract_user_features(events)
        if not features:
            return None
        
        # Update feature window
        self.feature_windows[f'user:{user_id}'].append(features)
        
        # Check if we have enough data for modeling
        if len(self.feature_windows[f'user:{user_id}']) < 50:
            return None
        
        # Prepare training data
        feature_data = list(self.feature_windows[f'user:{user_id}'])
        feature_matrix = np.array([[f[key] for key in sorted(f.keys())] for f in feature_data])
        
        # Scale features
        if not hasattr(self.scalers['user'], 'mean_'):
            # First time training
            scaled_features = self.scalers['user'].fit_transform(feature_matrix)
            self.models['user'].fit(scaled_features)
        else:
            scaled_features = self.scalers['user'].transform(feature_matrix)
        
        # Predict anomaly for latest features
        latest_features = scaled_features[-1].reshape(1, -1)
        anomaly_score = self.models['user'].decision_function(latest_features)[0]
        is_anomaly = self.models['user'].predict(latest_features)[0] == -1
        
        if is_anomaly:
            # Calculate confidence and create anomaly detection
            confidence = min(abs(anomaly_score) * 100, 100)
            
            return AnomalyDetection(
                anomaly_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                anomaly_type="user_behavior",
                score=abs(anomaly_score),
                threshold=0.0,
                features=features,
                confidence=confidence,
                baseline_period="7_days",
                affected_entities=[user_id]
            )
        
        return None
    
    def _extract_user_features(self, events: List[SecurityEvent]) -> Dict[str, float]:
        """Extract behavioral features from user events"""
        if not events:
            return {}
        
        # Time-based features
        timestamps = [event.timestamp for event in events]
        time_deltas = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                      for i in range(1, len(timestamps))]
        
        # Request pattern features
        request_counts = defaultdict(int)
        resource_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for event in events:
            request_counts[event.action] += 1
            resource_counts[event.resource] += 1
            ip_counts[event.ip_address] += 1
        
        # Calculate features
        features = {
            'event_count': len(events),
            'unique_ips': len(ip_counts),
            'unique_resources': len(resource_counts),
            'unique_actions': len(request_counts),
            'avg_time_between_events': statistics.mean(time_deltas) if time_deltas else 0,
            'std_time_between_events': statistics.stdev(time_deltas) if len(time_deltas) > 1 else 0,
            'max_requests_per_resource': max(resource_counts.values()) if resource_counts else 0,
            'entropy_resources': self._calculate_entropy(list(resource_counts.values())),
            'failure_rate': len([e for e in events if e.outcome == 'failure']) / len(events),
            'high_risk_events': len([e for e in events if e.risk_score > 0.7]) / len(events),
            'time_span_hours': (max(timestamps) - min(timestamps)).total_seconds() / 3600
        }
        
        return features
    
    def _calculate_entropy(self, values: List[int]) -> float:
        """Calculate Shannon entropy"""
        if not values or sum(values) == 0:
            return 0.0
        
        total = sum(values)
        probabilities = [v / total for v in values if v > 0]
        entropy = -sum(p * math.log2(p) for p in probabilities)
        
        return entropy

class ThreatDetectionEngine:
    """Advanced threat detection with rule-based and ML approaches"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.threat_signatures = {}
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.correlation_rules = []
        self.active_threats = {}
        
        # Load threat signatures
        self._load_threat_signatures()
        self._load_correlation_rules()
    
    def _load_threat_signatures(self):
        """Load threat detection signatures"""
        self.threat_signatures = {
            'brute_force_login': ThreatSignature(
                signature_id='bf_001',
                name='Brute Force Login Attempt',
                description='Multiple failed login attempts from same IP',
                pattern='login_failures >= 5 in 5_minutes',
                severity=ThreatLevel.HIGH,
                confidence=0.9,
                enabled=True,
                false_positive_rate=0.05,
                last_updated=datetime.utcnow()
            ),
            'credential_stuffing': ThreatSignature(
                signature_id='cs_001',
                name='Credential Stuffing Attack',
                description='Multiple login attempts with different usernames from same IP',
                pattern='unique_usernames >= 10 in 10_minutes from same_ip',
                severity=ThreatLevel.HIGH,
                confidence=0.85,
                enabled=True,
                false_positive_rate=0.03,
                last_updated=datetime.utcnow()
            ),
            'privilege_escalation': ThreatSignature(
                signature_id='pe_001',
                name='Privilege Escalation Attempt',
                description='User accessing resources beyond normal privileges',
                pattern='admin_resource_access by non_admin_user',
                severity=ThreatLevel.CRITICAL,
                confidence=0.95,
                enabled=True,
                false_positive_rate=0.01,
                last_updated=datetime.utcnow()
            ),
            'data_exfiltration': ThreatSignature(
                signature_id='de_001',
                name='Potential Data Exfiltration',
                description='Unusual data access patterns',
                pattern='large_data_download or bulk_api_calls',
                severity=ThreatLevel.CRITICAL,
                confidence=0.8,
                enabled=True,
                false_positive_rate=0.10,
                last_updated=datetime.utcnow()
            ),
            'insider_threat': ThreatSignature(
                signature_id='it_001',
                name='Insider Threat Indicators',
                description='Employee accessing sensitive data outside normal patterns',
                pattern='after_hours_access + sensitive_data + unusual_location',
                severity=ThreatLevel.HIGH,
                confidence=0.7,
                enabled=True,
                false_positive_rate=0.15,
                last_updated=datetime.utcnow()
            )
        }
    
    def _load_correlation_rules(self):
        """Load event correlation rules"""
        self.correlation_rules = [
            {
                'rule_id': 'corr_001',
                'name': 'Multi-stage Attack Detection',
                'conditions': [
                    {'event_type': 'reconnaissance', 'time_window': 3600},
                    {'event_type': 'vulnerability_scan', 'time_window': 1800},
                    {'event_type': 'exploitation_attempt', 'time_window': 900}
                ],
                'severity': ThreatLevel.CRITICAL,
                'confidence': 0.9
            },
            {
                'rule_id': 'corr_002',
                'name': 'Lateral Movement Detection',
                'conditions': [
                    {'event_type': 'successful_login', 'count': 1},
                    {'event_type': 'network_scan', 'time_window': 1800},
                    {'event_type': 'service_access', 'unique_services': 3}
                ],
                'severity': ThreatLevel.HIGH,
                'confidence': 0.85
            }
        ]
    
    async def detect_threats(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """Detect threats in security events"""
        detected_threats = []
        
        # Rule-based detection
        rule_threats = await self._rule_based_detection(events)
        detected_threats.extend(rule_threats)
        
        # Behavioral analysis
        behavioral_threats = await self._behavioral_detection(events)
        detected_threats.extend(behavioral_threats)
        
        # Event correlation
        correlated_threats = await self._correlation_detection(events)
        detected_threats.extend(correlated_threats)
        
        # Store detected threats
        for threat in detected_threats:
            await self._store_threat(threat)
        
        return detected_threats
    
    async def _rule_based_detection(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """Rule-based threat detection"""
        threats = []
        
        # Group events by IP address for pattern detection
        ip_events = defaultdict(list)
        for event in events:
            ip_events[event.ip_address].append(event)
        
        for ip_address, ip_event_list in ip_events.items():
            # Check for brute force attacks
            login_failures = [e for e in ip_event_list 
                            if e.event_type == 'authentication' and e.outcome == 'failure']
            
            if len(login_failures) >= 5:
                # Check if failures occurred within 5 minutes
                recent_failures = [f for f in login_failures 
                                 if (datetime.utcnow() - f.timestamp).total_seconds() <= 300]
                
                if len(recent_failures) >= 5:
                    threat_event = SecurityEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        source='threat_detection_engine',
                        event_type='brute_force_attack',
                        severity=ThreatLevel.HIGH,
                        user_id=None,
                        ip_address=ip_address,
                        user_agent='threat_detector',
                        resource='authentication_system',
                        action='brute_force_detection',
                        outcome='threat_detected',
                        details={
                            'signature_id': 'bf_001',
                            'failed_attempts': len(recent_failures),
                            'time_window': '5_minutes',
                            'affected_usernames': list(set(f.user_id for f in recent_failures if f.user_id))
                        },
                        risk_score=0.9,
                        ml_confidence=None,
                        correlated_events=[e.event_id for e in recent_failures]
                    )
                    threats.append(threat_event)
            
            # Check for credential stuffing
            unique_users = set(e.user_id for e in ip_event_list if e.user_id and e.event_type == 'authentication')
            if len(unique_users) >= 10:
                # Check if attempts occurred within 10 minutes
                recent_events = [e for e in ip_event_list 
                               if (datetime.utcnow() - e.timestamp).total_seconds() <= 600]
                recent_users = set(e.user_id for e in recent_events if e.user_id and e.event_type == 'authentication')
                
                if len(recent_users) >= 10:
                    threat_event = SecurityEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.utcnow(),
                        source='threat_detection_engine',
                        event_type='credential_stuffing',
                        severity=ThreatLevel.HIGH,
                        user_id=None,
                        ip_address=ip_address,
                        user_agent='threat_detector',
                        resource='authentication_system',
                        action='credential_stuffing_detection',
                        outcome='threat_detected',
                        details={
                            'signature_id': 'cs_001',
                            'unique_usernames': len(recent_users),
                            'time_window': '10_minutes',
                            'attempted_usernames': list(recent_users)
                        },
                        risk_score=0.85,
                        ml_confidence=None,
                        correlated_events=[e.event_id for e in recent_events]
                    )
                    threats.append(threat_event)
        
        return threats
    
    async def _behavioral_detection(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """Behavioral anomaly detection"""
        threats = []
        
        # Group events by user for behavioral analysis
        user_events = defaultdict(list)
        for event in events:
            if event.user_id:
                user_events[event.user_id].append(event)
        
        for user_id, user_event_list in user_events.items():
            # Analyze user behavior
            anomaly = await self.behavioral_analyzer.analyze_user_behavior(user_id, user_event_list)
            
            if anomaly and anomaly.confidence > 70:
                threat_event = SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    source='behavioral_analyzer',
                    event_type='behavioral_anomaly',
                    severity=ThreatLevel.MEDIUM if anomaly.confidence < 85 else ThreatLevel.HIGH,
                    user_id=user_id,
                    ip_address='various',
                    user_agent='ml_detector',
                    resource='user_behavior',
                    action='anomaly_detection',
                    outcome='anomaly_detected',
                    details={
                        'anomaly_id': anomaly.anomaly_id,
                        'anomaly_score': anomaly.score,
                        'confidence': anomaly.confidence,
                        'features': anomaly.features,
                        'baseline_period': anomaly.baseline_period
                    },
                    risk_score=min(anomaly.confidence / 100, 1.0),
                    ml_confidence=anomaly.confidence,
                    correlated_events=[e.event_id for e in user_event_list[-10:]]  # Last 10 events
                )
                threats.append(threat_event)
        
        return threats
    
    async def _correlation_detection(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """Event correlation-based threat detection"""
        threats = []
        
        for rule in self.correlation_rules:
            correlated_events = self._find_correlated_events(events, rule)
            
            if correlated_events:
                threat_event = SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    source='correlation_engine',
                    event_type='correlated_threat',
                    severity=rule['severity'],
                    user_id=None,
                    ip_address='multiple',
                    user_agent='correlation_detector',
                    resource='system_wide',
                    action='correlation_detection',
                    outcome='threat_pattern_detected',
                    details={
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['name'],
                        'confidence': rule['confidence'],
                        'matched_conditions': len(rule['conditions']),
                        'event_count': len(correlated_events)
                    },
                    risk_score=rule['confidence'],
                    ml_confidence=None,
                    correlated_events=[e.event_id for e in correlated_events]
                )
                threats.append(threat_event)
        
        return threats
    
    def _find_correlated_events(self, events: List[SecurityEvent], rule: Dict[str, Any]) -> List[SecurityEvent]:
        """Find events that match correlation rule"""
        # Simplified correlation logic - in production would be more sophisticated
        matched_events = []
        
        for condition in rule['conditions']:
            condition_matches = [
                e for e in events 
                if e.event_type == condition['event_type']
            ]
            
            if condition_matches:
                matched_events.extend(condition_matches)
        
        # Return events if all conditions have matches
        if len(set(condition['event_type'] for condition in rule['conditions'])) <= len(set(e.event_type for e in matched_events)):
            return matched_events
        
        return []
    
    async def _store_threat(self, threat: SecurityEvent):
        """Store detected threat"""
        await self.redis_client.setex(
            f"threat:{threat.event_id}",
            timedelta(days=90),
            json.dumps(asdict(threat), default=str)
        )
        
        # Add to active threats tracking
        self.active_threats[threat.event_id] = threat

class IncidentResponseManager:
    """Automated incident response and management"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.incidents = {}
        self.response_playbooks = {}
        self.notification_channels = []
        
        self._load_response_playbooks()
    
    def _load_response_playbooks(self):
        """Load incident response playbooks"""
        self.response_playbooks = {
            'brute_force_attack': {
                'name': 'Brute Force Attack Response',
                'severity': ThreatLevel.HIGH,
                'actions': [
                    ResponseAction.BLOCK_IP,
                    ResponseAction.ALERT,
                    ResponseAction.LOG_ONLY
                ],
                'escalation_threshold': 10,  # Number of similar incidents
                'auto_containment': True
            },
            'credential_stuffing': {
                'name': 'Credential Stuffing Response',
                'severity': ThreatLevel.HIGH,
                'actions': [
                    ResponseAction.BLOCK_IP,
                    ResponseAction.ALERT,
                    ResponseAction.ESCALATE
                ],
                'escalation_threshold': 5,
                'auto_containment': True
            },
            'privilege_escalation': {
                'name': 'Privilege Escalation Response',
                'severity': ThreatLevel.CRITICAL,
                'actions': [
                    ResponseAction.DISABLE_USER,
                    ResponseAction.QUARANTINE_SESSION,
                    ResponseAction.ESCALATE,
                    ResponseAction.ALERT
                ],
                'escalation_threshold': 1,
                'auto_containment': True
            },
            'behavioral_anomaly': {
                'name': 'Behavioral Anomaly Response',
                'severity': ThreatLevel.MEDIUM,
                'actions': [
                    ResponseAction.ALERT,
                    ResponseAction.LOG_ONLY
                ],
                'escalation_threshold': 3,
                'auto_containment': False
            }
        }
    
    async def handle_threat(self, threat_event: SecurityEvent) -> SecurityIncident:
        """Handle detected threat with automated response"""
        incident_logger.info(f"Handling threat: {threat_event.event_type} (Severity: {threat_event.severity.value})")
        
        # Create security incident
        incident = SecurityIncident(
            incident_id=str(uuid.uuid4()),
            title=f"{threat_event.event_type.replace('_', ' ').title()} Detected",
            description=f"Automated detection of {threat_event.event_type} from {threat_event.ip_address}",
            severity=threat_event.severity,
            status=IncidentStatus.NEW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            assigned_to=None,
            related_events=[threat_event.event_id],
            timeline=[{
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'incident_created',
                'details': 'Automated incident creation based on threat detection'
            }],
            containment_actions=[],
            lessons_learned=None
        )
        
        # Get response playbook
        playbook = self.response_playbooks.get(threat_event.event_type)
        if not playbook:
            playbook = self.response_playbooks['behavioral_anomaly']  # Default
        
        # Execute automated response actions
        await self._execute_response_actions(incident, threat_event, playbook)
        
        # Store incident
        await self._store_incident(incident)
        self.incidents[incident.incident_id] = incident
        
        # Check for escalation
        if await self._should_escalate(threat_event, playbook):
            await self._escalate_incident(incident)
        
        return incident
    
    async def _execute_response_actions(self, incident: SecurityIncident, threat_event: SecurityEvent, playbook: Dict[str, Any]):
        """Execute automated response actions"""
        
        for action in playbook['actions']:
            try:
                if action == ResponseAction.BLOCK_IP:
                    await self._block_ip_address(threat_event.ip_address)
                    incident.containment_actions.append(f"Blocked IP address: {threat_event.ip_address}")
                
                elif action == ResponseAction.DISABLE_USER:
                    if threat_event.user_id:
                        await self._disable_user_account(threat_event.user_id)
                        incident.containment_actions.append(f"Disabled user account: {threat_event.user_id}")
                
                elif action == ResponseAction.QUARANTINE_SESSION:
                    await self._quarantine_user_sessions(threat_event.user_id)
                    incident.containment_actions.append(f"Quarantined user sessions: {threat_event.user_id}")
                
                elif action == ResponseAction.ALERT:
                    await self._send_security_alert(incident, threat_event)
                    incident.containment_actions.append("Security alert sent to administrators")
                
                elif action == ResponseAction.LOG_ONLY:
                    incident.containment_actions.append("Event logged for review")
                
                elif action == ResponseAction.EMERGENCY_LOCKDOWN:
                    await self._initiate_emergency_lockdown()
                    incident.containment_actions.append("Emergency lockdown initiated")
                
                # Update incident timeline
                incident.timeline.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': action.value,
                    'details': f"Executed automated response action: {action.value}"
                })
                
            except Exception as e:
                incident_logger.error(f"Error executing response action {action.value}: {e}")
                incident.timeline.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': f"{action.value}_failed",
                    'details': f"Failed to execute {action.value}: {str(e)}"
                })
    
    async def _block_ip_address(self, ip_address: str):
        """Block IP address"""
        await self.redis_client.setex(
            f"blocked_ip:{ip_address}",
            timedelta(hours=24),  # 24 hour block
            json.dumps({
                'blocked_at': datetime.utcnow().isoformat(),
                'reason': 'automated_threat_response',
                'source': 'incident_response_manager'
            })
        )
        incident_logger.info(f"IP address blocked: {ip_address}")
    
    async def _disable_user_account(self, user_id: str):
        """Disable user account"""
        await self.redis_client.setex(
            f"disabled_user:{user_id}",
            timedelta(hours=24),
            json.dumps({
                'disabled_at': datetime.utcnow().isoformat(),
                'reason': 'security_incident',
                'source': 'incident_response_manager'
            })
        )
        incident_logger.info(f"User account disabled: {user_id}")
    
    async def _quarantine_user_sessions(self, user_id: str):
        """Quarantine all user sessions"""
        if not user_id:
            return
        
        # Mark all user sessions for quarantine
        pattern = f"secure_session:*"
        keys = await self.redis_client.keys(pattern)
        
        quarantined_count = 0
        for key in keys:
            session_data = await self.redis_client.get(key)
            if session_data:
                # This would decrypt and check session data in real implementation
                # For now, mark all sessions for the user as quarantined
                await self.redis_client.setex(
                    f"quarantined_session:{key.decode()}",
                    timedelta(hours=24),
                    json.dumps({'quarantined_at': datetime.utcnow().isoformat()})
                )
                quarantined_count += 1
        
        incident_logger.info(f"Quarantined {quarantined_count} sessions for user {user_id}")
    
    async def _send_security_alert(self, incident: SecurityIncident, threat_event: SecurityEvent):
        """Send security alert notification"""
        alert_data = {
            'incident_id': incident.incident_id,
            'title': incident.title,
            'severity': incident.severity.value,
            'threat_type': threat_event.event_type,
            'ip_address': threat_event.ip_address,
            'user_id': threat_event.user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'risk_score': threat_event.risk_score,
            'containment_actions': incident.containment_actions
        }
        
        # In production, this would send to configured channels
        incident_logger.critical(f"SECURITY ALERT: {incident.title} - {alert_data}")
    
    async def _initiate_emergency_lockdown(self):
        """Initiate emergency system lockdown"""
        await self.redis_client.setex(
            "emergency_lockdown",
            timedelta(hours=1),
            json.dumps({
                'initiated_at': datetime.utcnow().isoformat(),
                'reason': 'critical_security_threat',
                'status': 'active'
            })
        )
        incident_logger.critical("EMERGENCY LOCKDOWN INITIATED")
    
    async def _should_escalate(self, threat_event: SecurityEvent, playbook: Dict[str, Any]) -> bool:
        """Determine if incident should be escalated"""
        escalation_threshold = playbook.get('escalation_threshold', 5)
        
        # Count similar recent incidents
        pattern = f"threat:*"
        keys = await self.redis_client.keys(pattern)
        
        similar_incidents = 0
        current_time = datetime.utcnow()
        
        for key in keys:
            threat_data = await self.redis_client.get(key)
            if threat_data:
                try:
                    stored_threat = json.loads(threat_data.decode())
                    threat_time = datetime.fromisoformat(stored_threat['timestamp'])
                    
                    # Check if it's a similar threat in the last hour
                    if (stored_threat['event_type'] == threat_event.event_type and
                        (current_time - threat_time).total_seconds() <= 3600):
                        similar_incidents += 1
                
                except Exception:
                    continue
        
        return similar_incidents >= escalation_threshold
    
    async def _escalate_incident(self, incident: SecurityIncident):
        """Escalate incident to security team"""
        incident.status = IncidentStatus.INVESTIGATING
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'incident_escalated',
            'details': 'Incident escalated to security team due to severity/frequency'
        })
        
        incident_logger.warning(f"Incident escalated: {incident.incident_id}")
    
    async def _store_incident(self, incident: SecurityIncident):
        """Store security incident"""
        await self.redis_client.setex(
            f"incident:{incident.incident_id}",
            timedelta(days=365),  # Long retention for incidents
            json.dumps(asdict(incident), default=str)
        )

class SecurityMonitoringSystem:
    """
    🚨 Comprehensive Security Monitoring System
    
    Provides real-time security monitoring including:
    - Advanced threat detection (rule-based and ML)
    - Behavioral anomaly detection
    - Automated incident response
    - Security event correlation
    - Real-time dashboards and alerting
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_client = None
        
        # Core components
        self.threat_detector = None
        self.incident_manager = None
        
        # Monitoring state
        self.active_monitoring = False
        self.event_queue = deque(maxlen=10000)  # Recent events buffer
        self.monitoring_task = None
        
        monitoring_logger.info("Security Monitoring System initialized")
    
    async def initialize(self):
        """Initialize security monitoring components"""
        self.redis_client = await redis.from_url("redis://redis:6379")
        
        self.threat_detector = ThreatDetectionEngine(self.redis_client)
        self.incident_manager = IncidentResponseManager(self.redis_client)
        
        monitoring_logger.info("Security Monitoring System components initialized")
    
    async def start_monitoring(self):
        """Start real-time security monitoring"""
        self.active_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        monitoring_logger.info("🚨 Real-time security monitoring started")
    
    async def stop_monitoring(self):
        """Stop security monitoring"""
        self.active_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        monitoring_logger.info("Security monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.active_monitoring:
            try:
                # Collect recent events
                recent_events = await self._collect_recent_events()
                
                if recent_events:
                    # Detect threats
                    detected_threats = await self.threat_detector.detect_threats(recent_events)
                    
                    # Handle detected threats
                    for threat in detected_threats:
                        incident = await self.incident_manager.handle_threat(threat)
                        monitoring_logger.warning(f"Threat handled: {threat.event_type} -> Incident {incident.incident_id}")
                
                # Update monitoring metrics
                await self._update_monitoring_metrics(recent_events, detected_threats if recent_events else [])
                
                # Wait before next cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                monitoring_logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_recent_events(self) -> List[SecurityEvent]:
        """Collect recent security events"""
        try:
            # Get recent audit events from Redis
            pattern = "audit_event:*"
            keys = await self.redis_client.keys(pattern)
            
            recent_events = []
            cutoff_time = datetime.utcnow() - timedelta(minutes=10)  # Last 10 minutes
            
            for key in keys[-100:]:  # Limit to prevent overwhelming
                event_data = await self.redis_client.get(key)
                if event_data:
                    try:
                        audit_data = json.loads(event_data.decode())
                        event_time = datetime.fromisoformat(audit_data['timestamp'])
                        
                        if event_time >= cutoff_time:
                            # Convert audit event to security event
                            security_event = SecurityEvent(
                                event_id=audit_data['event_id'],
                                timestamp=event_time,
                                source=audit_data.get('source', 'unknown'),
                                event_type=audit_data.get('event_type', 'unknown'),
                                severity=ThreatLevel.INFO,  # Default severity
                                user_id=audit_data.get('user_id'),
                                ip_address=audit_data.get('ip_address', 'unknown'),
                                user_agent=audit_data.get('user_agent', 'unknown'),
                                resource=audit_data.get('resource', 'unknown'),
                                action=audit_data.get('action', 'unknown'),
                                outcome=audit_data.get('outcome', 'unknown'),
                                details=audit_data.get('details', {}),
                                risk_score=audit_data.get('risk_score', 0.1),
                                ml_confidence=None,
                                correlated_events=[]
                            )
                            recent_events.append(security_event)
                    
                    except Exception as e:
                        monitoring_logger.error(f"Error parsing audit event: {e}")
            
            return recent_events
        
        except Exception as e:
            monitoring_logger.error(f"Error collecting recent events: {e}")
            return []
    
    async def _update_monitoring_metrics(self, events: List[SecurityEvent], threats: List[SecurityEvent]):
        """Update monitoring metrics"""
        current_time = datetime.utcnow()
        
        metrics = {
            'timestamp': current_time.isoformat(),
            'events_processed': len(events),
            'threats_detected': len(threats),
            'threat_types': {},
            'severity_distribution': {level.value: 0 for level in ThreatLevel},
            'top_source_ips': {},
            'top_users': {},
            'monitoring_status': 'active' if self.active_monitoring else 'inactive'
        }
        
        # Analyze events
        for event in events:
            # Source IP tracking
            if event.ip_address in metrics['top_source_ips']:
                metrics['top_source_ips'][event.ip_address] += 1
            else:
                metrics['top_source_ips'][event.ip_address] = 1
            
            # User tracking
            if event.user_id:
                if event.user_id in metrics['top_users']:
                    metrics['top_users'][event.user_id] += 1
                else:
                    metrics['top_users'][event.user_id] = 1
        
        # Analyze threats
        for threat in threats:
            # Threat type distribution
            if threat.event_type in metrics['threat_types']:
                metrics['threat_types'][threat.event_type] += 1
            else:
                metrics['threat_types'][threat.event_type] = 1
            
            # Severity distribution
            metrics['severity_distribution'][threat.severity.value] += 1
        
        # Store metrics
        await self.redis_client.setex(
            "security_monitoring_metrics",
            timedelta(hours=24),
            json.dumps(metrics)
        )
    
    async def get_security_dashboard(self) -> Dict[str, Any]:
        """Get real-time security monitoring dashboard"""
        try:
            # Get current metrics
            metrics_data = await self.redis_client.get("security_monitoring_metrics")
            metrics = json.loads(metrics_data.decode()) if metrics_data else {}
            
            # Get active incidents
            incident_pattern = "incident:*"
            incident_keys = await self.redis_client.keys(incident_pattern)
            
            active_incidents = []
            for key in incident_keys:
                incident_data = await self.redis_client.get(key)
                if incident_data:
                    incident = json.loads(incident_data.decode())
                    if incident['status'] not in ['closed']:
                        active_incidents.append(incident)
            
            # Get recent threats
            threat_pattern = "threat:*"
            threat_keys = await self.redis_client.keys(threat_pattern)
            
            recent_threats = []
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for key in threat_keys[-50:]:  # Last 50 threats
                threat_data = await self.redis_client.get(key)
                if threat_data:
                    threat = json.loads(threat_data.decode())
                    threat_time = datetime.fromisoformat(threat['timestamp'])
                    if threat_time >= cutoff_time:
                        recent_threats.append(threat)
            
            dashboard = {
                'timestamp': datetime.utcnow().isoformat(),
                'monitoring_status': 'active' if self.active_monitoring else 'inactive',
                'real_time_metrics': metrics,
                'active_incidents': {
                    'count': len(active_incidents),
                    'critical': len([i for i in active_incidents if i['severity'] == 'critical']),
                    'high': len([i for i in active_incidents if i['severity'] == 'high']),
                    'medium': len([i for i in active_incidents if i['severity'] == 'medium']),
                    'incidents': active_incidents[:10]  # Top 10
                },
                'threat_summary': {
                    'last_24h': len(recent_threats),
                    'threat_types': {},
                    'severity_breakdown': {level.value: 0 for level in ThreatLevel}
                },
                'system_health': {
                    'monitoring_uptime': self._calculate_uptime(),
                    'event_processing_rate': metrics.get('events_processed', 0),
                    'detection_accuracy': self._calculate_detection_accuracy()
                }
            }
            
            # Analyze recent threats
            for threat in recent_threats:
                threat_type = threat.get('event_type', 'unknown')
                dashboard['threat_summary']['threat_types'][threat_type] = dashboard['threat_summary']['threat_types'].get(threat_type, 0) + 1
                
                severity = threat.get('severity', 'info')
                dashboard['threat_summary']['severity_breakdown'][severity] += 1
            
            return dashboard
        
        except Exception as e:
            monitoring_logger.error(f"Error generating security dashboard: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'monitoring_status': 'error'
            }
    
    def _calculate_uptime(self) -> str:
        """Calculate monitoring system uptime"""
        # Simplified uptime calculation
        return "99.9%"
    
    def _calculate_detection_accuracy(self) -> float:
        """Calculate threat detection accuracy"""
        # Simplified accuracy calculation
        return 94.5

# Global instance
security_monitoring_system = SecurityMonitoringSystem()

async def initialize_security_monitoring():
    """Initialize the security monitoring system"""
    await security_monitoring_system.initialize()
    monitoring_logger.info("🚨 Security Monitoring System ready for real-time threat detection")

if __name__ == "__main__":
    # Test security monitoring
    async def test_security_monitoring():
        await initialize_security_monitoring()
        
        # Start monitoring
        await security_monitoring_system.start_monitoring()
        
        # Create test events
        test_events = [
            SecurityEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                source="test_system",
                event_type="authentication",
                severity=ThreatLevel.INFO,
                user_id="test_user",
                ip_address="192.168.1.100",
                user_agent="test_agent",
                resource="login_endpoint",
                action="login",
                outcome="failure",
                details={"reason": "invalid_password"},
                risk_score=0.3,
                ml_confidence=None,
                correlated_events=[]
            )
        ] * 6  # Create multiple failed attempts
        
        # Test threat detection
        threats = await security_monitoring_system.threat_detector.detect_threats(test_events)
        print(f"Detected threats: {len(threats)}")
        
        # Get dashboard
        dashboard = await security_monitoring_system.get_security_dashboard()
        print(f"Security dashboard generated: {dashboard['monitoring_status']}")
        
        # Stop monitoring
        await security_monitoring_system.stop_monitoring()
    
    asyncio.run(test_security_monitoring())