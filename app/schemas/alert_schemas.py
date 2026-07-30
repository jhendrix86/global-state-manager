from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert types."""
    STATE_CHANGE = "state_change"
    RESOURCE_LIMIT = "resource_limit"
    FAILURE_DETECTED = "failure_detected"
    GOVERNANCE_OVERRIDE = "governance_override"
    KILL_SWITCH = "kill_switch"
    SYSTEM_DEGRADED = "system_degraded"
    ANOMALY_DETECTED = "anomaly_detected"


class StateAlert(BaseModel):
    """State alert."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    entity_type: str
    entity_id: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    triggered_by: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
