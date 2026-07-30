import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog
from ..schemas.state_schemas import (
    GlobalState, EngineState, FunnelState, ProductState,
    TaskState, GovernanceState, ResourceState, FailureState
)
from ..schemas.transition_schemas import StateTransition, TransitionType
from .redis_store import RedisStateStore
from .postgres_store import PostgresStateStore


logger = structlog.get_logger()


class StateManager:
    """Central state manager coordinating Redis and PostgreSQL storage."""
    
    def __init__(
        self,
        redis_store: RedisStateStore,
        postgres_store: PostgresStateStore
    ):
        self.redis = redis_store
        self.postgres = postgres_store
        
        # In-memory version tracking
        self._versions: Dict[str, int] = {}
    
    async def get_global_state(self) -> Optional[GlobalState]:
        """Get global state."""
        data = await self.redis.get_state("global")
        if data:
            return GlobalState(**data)
        
        # Try PostgreSQL
        pg_data = await self.postgres.get_state("global", "global")
        if pg_data:
            state = GlobalState(**pg_data["state_data"])
            # Cache in Redis
            await self.redis.set_state("global", None, state.dict())
            return state
        
        return None
    
    async def update_global_state(
        self,
        updates: Dict[str, Any],
        triggered_by: str,
        trace_id: str,
        correlation_id: str,
        causation_id: Optional[str] = None
    ) -> StateTransition:
        """Update global state."""
        current = await self.get_global_state()
        if not current:
            current = GlobalState()
        
        previous_state = current.dict()
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        current.last_updated = datetime.utcnow()
        current.version += 1
        
        # Save to Redis
        await self.redis.set_state("global", None, current.dict())
        
        # Save to PostgreSQL
        await self.postgres.save_state("global", "global", current.dict(), current.version)
        
        # Create transition record
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            entity_type="global",
            entity_id="global",
            transition_type=TransitionType.UPDATE,
            previous_state=previous_state,
            new_state=current.dict(),
            diff=self._compute_diff(previous_state, current.dict()),
            version_before=current.version - 1,
            version_after=current.version,
            trace_id=trace_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            triggered_by=triggered_by
        )
        
        await self.postgres.save_transition(transition.dict())
        
        return transition
    
    async def get_engine_state(self, engine_id: str) -> Optional[EngineState]:
        """Get engine state."""
        data = await self.redis.get_state("engine", engine_id)
        if data:
            return EngineState(**data)
        
        pg_data = await self.postgres.get_state("engine", engine_id)
        if pg_data:
            state = EngineState(**pg_data["state_data"])
            await self.redis.set_state("engine", engine_id, state.dict())
            return state
        
        return None
    
    async def update_engine_state(
        self,
        engine_id: str,
        updates: Dict[str, Any],
        triggered_by: str,
        trace_id: str,
        correlation_id: str,
        causation_id: Optional[str] = None
    ) -> StateTransition:
        """Update engine state."""
        current = await self.get_engine_state(engine_id)
        if not current:
            current = EngineState(engine_id=engine_id, engine_type=updates.get("engine_type", "unknown"))
        
        previous_state = current.dict()
        
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        current.last_updated = datetime.utcnow()
        current.version += 1
        
        await self.redis.set_state("engine", engine_id, current.dict())
        await self.postgres.save_state("engine", engine_id, current.dict(), current.version)
        
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            entity_type="engine",
            entity_id=engine_id,
            transition_type=TransitionType.UPDATE,
            previous_state=previous_state,
            new_state=current.dict(),
            diff=self._compute_diff(previous_state, current.dict()),
            version_before=current.version - 1,
            version_after=current.version,
            trace_id=trace_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            triggered_by=triggered_by
        )
        
        await self.postgres.save_transition(transition.dict())
        
        return transition
    
    async def get_funnel_state(self, funnel_id: str) -> Optional[FunnelState]:
        """Get funnel state."""
        data = await self.redis.get_state("funnel", funnel_id)
        if data:
            return FunnelState(**data)
        
        pg_data = await self.postgres.get_state("funnel", funnel_id)
        if pg_data:
            state = FunnelState(**pg_data["state_data"])
            await self.redis.set_state("funnel", funnel_id, state.dict())
            return state
        
        return None
    
    async def update_funnel_state(
        self,
        funnel_id: str,
        updates: Dict[str, Any],
        triggered_by: str,
        trace_id: str,
        correlation_id: str,
        causation_id: Optional[str] = None
    ) -> StateTransition:
        """Update funnel state."""
        current = await self.get_funnel_state(funnel_id)
        if not current:
            current = FunnelState(funnel_id=funnel_id)
        
        previous_state = current.dict()
        
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        current.last_updated = datetime.utcnow()
        current.version += 1
        
        await self.redis.set_state("funnel", funnel_id, current.dict())
        await self.postgres.save_state("funnel", funnel_id, current.dict(), current.version)
        
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            entity_type="funnel",
            entity_id=funnel_id,
            transition_type=TransitionType.UPDATE,
            previous_state=previous_state,
            new_state=current.dict(),
            diff=self._compute_diff(previous_state, current.dict()),
            version_before=current.version - 1,
            version_after=current.version,
            trace_id=trace_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            triggered_by=triggered_by
        )
        
        await self.postgres.save_transition(transition.dict())
        
        return transition
    
    async def create_snapshot(self) -> Dict[str, Any]:
        """Create a full state snapshot."""
        snapshot_id = f"snapshot_{int(datetime.utcnow().timestamp())}"
        timestamp = datetime.utcnow()
        
        # Get all states
        global_state = (await self.get_global_state()).dict() if await self.get_global_state() else {}
        engine_states = await self.redis.get_all_states("engine")
        funnel_states = await self.redis.get_all_states("funnel")
        product_states = await self.redis.get_all_states("product")
        task_states = await self.redis.get_all_states("task")
        
        snapshot = {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "global_state": global_state,
            "engine_states": engine_states,
            "funnel_states": funnel_states,
            "product_states": product_states,
            "task_states": task_states,
            "governance_state": {},
            "resource_state": {},
            "failure_states": {},
            "metadata": {}
        }
        
        await self.postgres.save_snapshot(snapshot)
        
        logger.info("snapshot_created", snapshot_id=snapshot_id)
        
        return snapshot
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get snapshot by ID."""
        return await self.postgres.get_snapshot(snapshot_id)
    
    async def get_diff(
        self,
        entity_type: str,
        entity_id: Optional[str],
        from_version: int,
        to_version: int
    ) -> Optional[Dict[str, Any]]:
        """Get state diff between versions."""
        return await self.postgres.get_diff(entity_type, entity_id, from_version, to_version)
    
    def _compute_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Compute diff between two state dictionaries."""
        added = []
        removed = []
        modified = {}
        
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            if key not in old:
                added.append(key)
            elif key not in new:
                removed.append(key)
            elif old[key] != new[key]:
                modified[key] = {"old": old[key], "new": new[key]}
        
        return {
            "added": added,
            "removed": removed,
            "modified": modified
        }
