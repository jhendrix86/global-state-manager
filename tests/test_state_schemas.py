import pytest
from app.schemas.state_schemas import (
    GlobalState, EngineState, FunnelState, ProductState,
    TaskState, GovernanceState, ResourceState, FailureState,
    SystemStatus, LifecycleStage
)
from app.schemas.transition_schemas import (
    StateTransition, TransitionType, StateUpdateRequest
)
from app.schemas.alert_schemas import StateAlert, AlertSeverity, AlertType


class TestStateSchemas:
    def test_global_state(self):
        state = GlobalState(
            system_status=SystemStatus.HEALTHY,
            active_engines=["engine-1", "engine-2"],
            active_funnels=["funnel-1"]
        )
        
        assert state.system_status == SystemStatus.HEALTHY
        assert len(state.active_engines) == 2
        assert state.version == 1
    
    def test_engine_state(self):
        state = EngineState(
            engine_id="engine-1",
            engine_type="orchestrator",
            health="healthy",
            load=0.5
        )
        
        assert state.engine_id == "engine-1"
        assert state.load == 0.5
        assert version == 1
    
    def test_funnel_state(self):
        state = FunnelState(
            funnel_id="funnel-1",
            lifecycle_stage=LifecycleStage.ACTIVE,
            total_visitors=1000,
            total_conversions=50,
            conversion_rate=0.05
        )
        
        assert state.funnel_id == "funnel-1"
        assert state.lifecycle_stage == LifecycleStage.ACTIVE
        assert state.conversion_rate == 0.05
    
    def test_product_state(self):
        state = ProductState(
            product_id="product-1",
            lifecycle_stage=LifecycleStage.ACTIVE,
            total_sales=100,
            total_revenue=5000.0
        )
        
        assert state.product_id == "product-1"
        assert state.total_revenue == 5000.0
    
    def test_task_state(self):
        state = TaskState(
            task_id="task-1",
            type="content_generation",
            status="running",
            progress=0.5
        )
        
        assert state.task_id == "task-1"
        assert state.progress == 0.5
    
    def test_governance_state(self):
        state = GovernanceState(
            active_rules=10,
            approved_count=5,
            rejected_count=2
        )
        
        assert state.active_rules == 10
        assert state.approved_count == 5
    
    def test_resource_state(self):
        state = ResourceState(
            compute_usage={"cpu": 50.0, "memory": 60.0},
            api_usage={"requests": 1000}
        )
        
        assert state.compute_usage["cpu"] == 50.0
    
    def test_failure_state(self):
        state = FailureState(
            failure_id="failure-1",
            type="engine_crash",
            severity="high",
            affected_entities=["engine-1"]
        )
        
        assert state.failure_id == "failure-1"
        assert state.severity == "high"
    
    def test_system_status_enum(self):
        assert SystemStatus.HEALTHY == "healthy"
        assert SystemStatus.DEGRADED == "degraded"
        assert SystemStatus.CRITICAL == "critical"
    
    def test_lifecycle_stage_enum(self):
        assert LifecycleStage.INITIALIZING == "initializing"
        assert LifecycleStage.ACTIVE == "active"
        assert LifecycleStage.ARCHIVED == "archived"


class TestTransitionSchemas:
    def test_state_transition(self):
        from datetime import datetime
        
        transition = StateTransition(
            transition_id="trans-1",
            entity_type="engine",
            entity_id="engine-1",
            transition_type=TransitionType.UPDATE,
            previous_state={"health": "healthy"},
            new_state={"health": "degraded"},
            version_before=1,
            version_after=2,
            trace_id="trace-123",
            correlation_id="corr-123",
            triggered_by="engine_consumer"
        )
        
        assert transition.transition_id == "trans-1"
        assert transition.transition_type == TransitionType.UPDATE
    
    def test_state_update_request(self):
        request = StateUpdateRequest(
            entity_type="engine",
            entity_id="engine-1",
            updates={"health": "degraded"},
            triggered_by="engine_consumer"
        )
        
        assert request.entity_type == "engine"
        assert request.updates["health"] == "degraded"
    
    def test_transition_type_enum(self):
        assert TransitionType.CREATE == "create"
        assert TransitionType.UPDATE == "update"
        assert TransitionType.DELETE == "delete"


class TestAlertSchemas:
    def test_state_alert(self):
        alert = StateAlert(
            alert_id="alert-1",
            alert_type=AlertType.FAILURE_DETECTED,
            severity=AlertSeverity.HIGH,
            entity_type="engine",
            entity_id="engine-1",
            message="Engine degraded",
            triggered_by="engine_consumer"
        )
        
        assert alert.alert_id == "alert-1"
        assert alert.alert_type == AlertType.FAILURE_DETECTED
        assert alert.severity == AlertSeverity.HIGH
    
    def test_alert_severity_enum(self):
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.HIGH == "high"
        assert AlertSeverity.CRITICAL == "critical"
    
    def test_alert_type_enum(self):
        assert AlertType.STATE_CHANGE == "state_change"
        assert AlertType.FAILURE_DETECTED == "failure_detected"
        assert AlertType.KILL_SWITCH == "kill_switch"
