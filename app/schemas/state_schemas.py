from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SystemStatus(str, Enum):
    """System status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class LifecycleStage(str, Enum):
    """Lifecycle stages."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    FAILED = "failed"
    RECOVERING = "recovering"


class GlobalState(BaseModel):
    """Global system state."""
    # StateManager.update_global_state() does a blind setattr(current, key,
    # value) loop from a raw updates dict (e.g. {"system_status": "degraded"})
    # - without this, pydantic doesn't validate/coerce on assignment, so
    # system_status silently ends up holding a plain str instead of a real
    # SystemStatus member (caught live: a PydanticSerializationUnexpectedValue
    # warning on every such update).
    model_config = ConfigDict(validate_assignment=True)

    system_status: SystemStatus = Field(default=SystemStatus.HEALTHY)
    active_engines: List[str] = Field(default_factory=list)
    active_funnels: List[str] = Field(default_factory=list)
    active_products: List[str] = Field(default_factory=list)
    active_tasks: List[str] = Field(default_factory=list)
    active_strategies: List[str] = Field(default_factory=list)
    market_conditions: Dict[str, Any] = Field(default_factory=dict)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    governance_status: Dict[str, Any] = Field(default_factory=dict)
    failure_status: Dict[str, Any] = Field(default_factory=dict)
    recovery_status: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class EngineState(BaseModel):
    """Engine state."""
    # Same reason as GlobalState.model_config - update_engine_state() also
    # does a blind setattr loop.
    model_config = ConfigDict(validate_assignment=True)

    engine_id: str
    engine_type: str
    health: str = Field(default="healthy")
    load: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    last_event: Optional[str] = None
    last_event_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    uptime_seconds: int = Field(default=0)
    request_count: int = Field(default=0)
    error_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class FunnelState(BaseModel):
    """Funnel state."""
    # Same reason as GlobalState.model_config - update_funnel_state() also
    # does a blind setattr loop.
    model_config = ConfigDict(validate_assignment=True)

    funnel_id: str
    lifecycle_stage: LifecycleStage = Field(default=LifecycleStage.INITIALIZING)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    insights: List[Dict[str, Any]] = Field(default_factory=list)
    strategy: Optional[str] = None
    risk: Dict[str, Any] = Field(default_factory=dict)
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    channels: List[str] = Field(default_factory=list)
    total_visitors: int = Field(default=0)
    total_conversions: int = Field(default=0)
    total_revenue: float = Field(default=0.0)
    conversion_rate: float = Field(default=0.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class ProductState(BaseModel):
    """Product state."""
    product_id: str
    lifecycle_stage: LifecycleStage = Field(default=LifecycleStage.INITIALIZING)
    pricing: Dict[str, Any] = Field(default_factory=dict)
    market_position: Dict[str, Any] = Field(default_factory=dict)
    competitors: List[str] = Field(default_factory=list)
    total_sales: int = Field(default=0)
    total_revenue: float = Field(default=0.0)
    average_rating: float = Field(default=0.0)
    review_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class TaskState(BaseModel):
    """Task state."""
    task_id: str
    type: str
    status: str = Field(default="pending")
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    assigned_engine: Optional[str] = None
    priority: str = Field(default="normal")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class GovernanceState(BaseModel):
    """Governance state."""
    last_decision: Optional[Dict[str, Any]] = None
    decision_history: List[Dict[str, Any]] = Field(default_factory=list)
    overrides: List[Dict[str, Any]] = Field(default_factory=list)
    kill_switch_status: Dict[str, Any] = Field(default_factory=dict)
    active_rules: int = Field(default=0)
    pending_approvals: int = Field(default=0)
    rejected_count: int = Field(default=0)
    approved_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class ResourceState(BaseModel):
    """Resource state."""
    compute_usage: Dict[str, Any] = Field(default_factory=dict)
    api_usage: Dict[str, Any] = Field(default_factory=dict)
    budget_usage: Dict[str, Any] = Field(default_factory=dict)
    quotas: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)


class FailureState(BaseModel):
    """Failure state."""
    failure_id: str
    type: str
    severity: str = Field(default="medium")
    affected_entities: List[str] = Field(default_factory=list)
    recovery_plan: Optional[Dict[str, Any]] = None
    recovery_progress: float = Field(default=0.0)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
