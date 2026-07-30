from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TransitionType(str, Enum):
    """State transition types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SNAPSHOT = "snapshot"
    RESTORE = "restore"
    ROLLBACK = "rollback"


class StateTransition(BaseModel):
    """State transition record."""
    transition_id: str
    entity_type: str
    entity_id: str
    transition_type: TransitionType
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Dict[str, Any]
    diff: Optional[Dict[str, Any]] = None
    version_before: int
    version_after: int
    trace_id: str
    correlation_id: str
    causation_id: Optional[str] = None
    triggered_by: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateUpdateRequest(BaseModel):
    """Request to update state."""
    entity_type: str = Field(..., description="Type of entity (global, engine, funnel, product, task, governance, resource, failure)")
    entity_id: Optional[str] = Field(None, description="Entity ID (not required for global state)")
    updates: Dict[str, Any] = Field(..., description="State updates to apply")
    version: Optional[int] = Field(None, description="Expected version for optimistic locking")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    causation_id: Optional[str] = Field(None, description="Causation ID")
    triggered_by: str = Field(..., description="Who triggered the update")


class StateDiff(BaseModel):
    """State difference between two versions."""
    entity_type: str
    entity_id: str
    from_version: int
    to_version: int
    from_timestamp: datetime
    to_timestamp: datetime
    changes: List[Dict[str, Any]]
    added: List[str]
    removed: List[str]
    modified: Dict[str, Dict[str, Any]]


class StateSnapshot(BaseModel):
    """State snapshot at a point in time."""
    snapshot_id: str
    timestamp: datetime
    global_state: Dict[str, Any]
    engine_states: Dict[str, Dict[str, Any]]
    funnel_states: Dict[str, Dict[str, Any]]
    product_states: Dict[str, Dict[str, Any]]
    task_states: Dict[str, Dict[str, Any]]
    governance_state: Dict[str, Any]
    resource_state: Dict[str, Any]
    failure_states: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
