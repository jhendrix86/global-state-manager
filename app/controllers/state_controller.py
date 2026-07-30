from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import structlog
from ..schemas import StateUpdateRequest
from ..state import StateManager
from ..transitions import TransitionValidator, TransitionEmitter
from ..tracing import Tracer, TraceParent


logger = structlog.get_logger()
router = APIRouter(prefix="/state", tags=["State Management"])


def get_state_manager():
    """Dependency for state manager."""
    from ..state.state_manager import StateManager
    from ..state.redis_store import RedisStateStore
    from ..state.postgres_store import PostgresStateStore
    from ..utils.config import settings
    
    redis_store = RedisStateStore()
    postgres_store = PostgresStateStore()
    return StateManager(redis_store, postgres_store)


def get_tracer():
    """Dependency for tracer."""
    from ..tracing import Tracer
    return Tracer("global-state-manager")


@router.get("/global")
async def get_global_state(
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Get global system state."""
    trace_parent = tracer.start_span("api.get_global_state")
    
    try:
        state = await state_manager.get_global_state()
        tracer.finish_span(trace_parent, "api.get_global_state", True)
        
        if not state:
            return {"system_status": "initializing"}
        
        return state.dict()
    except Exception as e:
        logger.error("get_global_state_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_global_state", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engine/{engine_id}")
async def get_engine_state(
    engine_id: str,
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Get engine state."""
    trace_parent = tracer.start_span("api.get_engine_state")
    
    try:
        state = await state_manager.get_engine_state(engine_id)
        tracer.finish_span(trace_parent, "api.get_engine_state", True)
        
        if not state:
            raise HTTPException(status_code=404, detail="Engine not found")
        
        return state.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_engine_state_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_engine_state", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funnel/{funnel_id}")
async def get_funnel_state(
    funnel_id: str,
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Get funnel state."""
    trace_parent = tracer.start_span("api.get_funnel_state")
    
    try:
        state = await state_manager.get_funnel_state(funnel_id)
        tracer.finish_span(trace_parent, "api.get_funnel_state", True)
        
        if not state:
            raise HTTPException(status_code=404, detail="Funnel not found")
        
        return state.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_funnel_state_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_funnel_state", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_state(
    request: StateUpdateRequest,
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Update state."""
    trace_parent = tracer.start_span("api.update_state")
    
    trace_id = request.trace_id or trace_parent.trace_context.trace_id
    correlation_id = request.correlation_id or trace_parent.trace_context.trace_id
    causation_id = request.causation_id
    
    try:
        if request.entity_type == "global":
            transition = await state_manager.update_global_state(
                updates=request.updates,
                triggered_by=request.triggered_by,
                trace_id=trace_id,
                correlation_id=correlation_id,
                causation_id=causation_id
            )
        elif request.entity_type == "engine":
            transition = await state_manager.update_engine_state(
                engine_id=request.entity_id,
                updates=request.updates,
                triggered_by=request.triggered_by,
                trace_id=trace_id,
                correlation_id=correlation_id,
                causation_id=causation_id
            )
        elif request.entity_type == "funnel":
            transition = await state_manager.update_funnel_state(
                funnel_id=request.entity_id,
                updates=request.updates,
                triggered_by=request.triggered_by,
                trace_id=trace_id,
                correlation_id=correlation_id,
                causation_id=causation_id
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported entity type: {request.entity_type}")
        
        tracer.finish_span(trace_parent, "api.update_state", True)
        
        return {
            "success": True,
            "transition_id": transition.transition_id,
            "version": transition.version_after
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_state_error", error=str(e))
        tracer.finish_span(trace_parent, "api.update_state", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Get state snapshot by ID."""
    trace_parent = tracer.start_span("api.get_snapshot")
    
    try:
        snapshot = await state_manager.get_snapshot(snapshot_id)
        tracer.finish_span(trace_parent, "api.get_snapshot", True)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_snapshot_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_snapshot", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot")
async def create_snapshot(
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Create a new state snapshot."""
    trace_parent = tracer.start_span("api.create_snapshot")
    
    try:
        snapshot = await state_manager.create_snapshot()
        tracer.finish_span(trace_parent, "api.create_snapshot", True)
        
        return {
            "success": True,
            "snapshot_id": snapshot["snapshot_id"],
            "timestamp": snapshot["timestamp"]
        }
    except Exception as e:
        logger.error("create_snapshot_error", error=str(e))
        tracer.finish_span(trace_parent, "api.create_snapshot", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff/{entity_type}/{entity_id}/{from_version}/{to_version}")
async def get_diff(
    entity_type: str,
    entity_id: str,
    from_version: int,
    to_version: int,
    state_manager: StateManager = Depends(get_state_manager),
    tracer: Tracer = Depends(get_tracer)
):
    """Get state diff between versions."""
    trace_parent = tracer.start_span("api.get_diff")
    
    try:
        diff = await state_manager.get_diff(entity_type, entity_id, from_version, to_version)
        tracer.finish_span(trace_parent, "api.get_diff", True)
        
        if not diff:
            raise HTTPException(status_code=404, detail="Diff not found")
        
        return diff
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_diff_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_diff", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/subscribe")
async def websocket_subscribe(websocket: WebSocket):
    """WebSocket endpoint for state change subscriptions."""
    await websocket.accept()
    
    from ..state.redis_store import RedisStateStore
    from ..utils.config import settings
    
    redis_store = RedisStateStore()
    await redis_store.connect()
    
    try:
        # Subscribe to all state changes
        await redis_store.subscribe_to_changes()
        
        while True:
            message = await redis_store.get_next_message()
            if message:
                await websocket.send_json(message)
            else:
                # Small delay to prevent busy loop
                import asyncio
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("websocket_disconnected")
    finally:
        await redis_store.disconnect()


@router.get("/alerts")
async def get_alerts(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
    tracer: Tracer = Depends(get_tracer)
):
    """Get state alerts."""
    trace_parent = tracer.start_span("api.get_alerts")
    
    try:
        from ..state.postgres_store import PostgresStateStore
        from ..utils.config import settings
        
        postgres_store = PostgresStateStore()
        async with postgres_store:
            alerts = await postgres_store.get_alerts(
                entity_type=entity_type,
                entity_id=entity_id,
                resolved=resolved,
                limit=limit
            )
        
        tracer.finish_span(trace_parent, "api.get_alerts", True)
        
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error("get_alerts_error", error=str(e))
        tracer.finish_span(trace_parent, "api.get_alerts", False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
