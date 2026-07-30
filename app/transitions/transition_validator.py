from typing import Dict, Any, Optional
import structlog
from ..schemas.state_schemas import (
    GlobalState, EngineState, FunnelState, ProductState,
    TaskState, GovernanceState, ResourceState, FailureState
)


logger = structlog.get_logger()


class TransitionValidator:
    """Validates state transitions."""
    
    def __init__(self):
        self._validators = {
            "global": self._validate_global,
            "engine": self._validate_engine,
            "funnel": self._validate_funnel,
            "product": self._validate_product,
            "task": self._validate_task,
            "governance": self._validate_governance,
            "resource": self._validate_resource,
            "failure": self._validate_failure,
        }
    
    async def validate(
        self,
        entity_type: str,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate a state transition."""
        validator = self._validators.get(entity_type)
        if not validator:
            return True, None  # Unknown entity type, allow by default
        
        try:
            return await validator(entity_id, updates, current_state)
        except Exception as e:
            logger.error("validation_error", entity_type=entity_type, error=str(e))
            return False, f"Validation error: {str(e)}"
    
    async def _validate_global(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate global state updates."""
        # Validate system status
        if "system_status" in updates:
            valid_statuses = ["healthy", "degraded", "critical", "maintenance"]
            if updates["system_status"] not in valid_statuses:
                return False, f"Invalid system status: {updates['system_status']}"
        
        # Validate lists
        for list_field in ["active_engines", "active_funnels", "active_products", "active_tasks", "active_strategies"]:
            if list_field in updates and not isinstance(updates[list_field], list):
                return False, f"{list_field} must be a list"
        
        return True, None
    
    async def _validate_engine(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate engine state updates."""
        # Validate load
        if "load" in updates:
            load = updates["load"]
            if not isinstance(load, (int, float)) or load < 0 or load > 1:
                return False, "Load must be between 0 and 1"
        
        # Validate health
        if "health" in updates:
            valid_health = ["healthy", "degraded", "critical", "offline"]
            if updates["health"] not in valid_health:
                return False, f"Invalid health status: {updates['health']}"
        
        return True, None
    
    async def _validate_funnel(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate funnel state updates."""
        # Validate lifecycle stage
        if "lifecycle_stage" in updates:
            valid_stages = ["initializing", "active", "paused", "archived", "failed", "recovering"]
            if updates["lifecycle_stage"] not in valid_stages:
                return False, f"Invalid lifecycle stage: {updates['lifecycle_stage']}"
        
        # Validate metrics
        if "conversion_rate" in updates:
            cr = updates["conversion_rate"]
            if not isinstance(cr, (int, float)) or cr < 0 or cr > 1:
                return False, "Conversion rate must be between 0 and 1"
        
        return True, None
    
    async def _validate_product(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate product state updates."""
        # Validate lifecycle stage
        if "lifecycle_stage" in updates:
            valid_stages = ["initializing", "active", "paused", "archived", "failed", "recovering"]
            if updates["lifecycle_stage"] not in valid_stages:
                return False, f"Invalid lifecycle stage: {updates['lifecycle_stage']}"
        
        # Validate rating
        if "average_rating" in updates:
            rating = updates["average_rating"]
            if not isinstance(rating, (int, float)) or rating < 0 or rating > 5:
                return False, "Average rating must be between 0 and 5"
        
        return True, None
    
    async def _validate_task(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate task state updates."""
        # Validate progress
        if "progress" in updates:
            progress = updates["progress"]
            if not isinstance(progress, (int, float)) or progress < 0 or progress > 1:
                return False, "Progress must be between 0 and 1"
        
        # Validate status
        if "status" in updates:
            valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
            if updates["status"] not in valid_statuses:
                return False, f"Invalid task status: {updates['status']}"
        
        return True, None
    
    async def _validate_governance(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate governance state updates."""
        # Validate counts are non-negative
        for count_field in ["active_rules", "pending_approvals", "rejected_count", "approved_count"]:
            if count_field in updates:
                if not isinstance(updates[count_field], int) or updates[count_field] < 0:
                    return False, f"{count_field} must be a non-negative integer"
        
        return True, None
    
    async def _validate_resource(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate resource state updates."""
        # Resource usage should be non-negative
        for field in ["compute_usage", "api_usage", "budget_usage"]:
            if field in updates:
                if not isinstance(updates[field], dict):
                    return False, f"{field} must be a dictionary"
        
        return True, None
    
    async def _validate_failure(
        self,
        entity_id: Optional[str],
        updates: Dict[str, Any],
        current_state: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """Validate failure state updates."""
        # Validate severity
        if "severity" in updates:
            valid_severities = ["low", "medium", "high", "critical"]
            if updates["severity"] not in valid_severities:
                return False, f"Invalid severity: {updates['severity']}"
        
        # Validate recovery progress
        if "recovery_progress" in updates:
            progress = updates["recovery_progress"]
            if not isinstance(progress, (int, float)) or progress < 0 or progress > 1:
                return False, "Recovery progress must be between 0 and 1"
        
        return True, None
