from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class EngineConsumer(BaseConsumer):
    """Consumer for engine health events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle engine events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "engine.health_report":
                await self._handle_health_report(payload, trace_id)
            elif event_type == "engine.degraded":
                await self._handle_engine_degraded(payload, trace_id)
            elif event_type == "engine.recovered":
                await self._handle_engine_recovered(payload, trace_id)
            else:
                logger.warning("unknown_engine_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown engine event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("engine_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_health_report(self, payload: Dict[str, Any], trace_id: str):
        """Handle engine.health_report event."""
        engine_id = payload["engine_id"]
        
        updates = {
            "engine_id": engine_id,
            "engine_type": payload.get("engine_type"),
            "health": payload.get("status", "healthy"),
            "load": payload.get("cpu_usage", 0.0) / 100.0,  # Convert to 0-1
            "resource_usage": {
                "cpu": payload.get("cpu_usage", 0.0),
                "memory": payload.get("memory_usage", 0.0),
                "active_connections": payload.get("active_connections", 0)
            },
            "last_event": "health_report",
            "last_event_time": payload.get("reported_at")
        }
        
        await self.state_manager.update_engine_state(
            engine_id=engine_id,
            updates=updates,
            triggered_by="engine_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
        
        # Also update global state
        await self.state_manager.update_global_state(
            updates={"active_engines": [engine_id]},
            triggered_by="engine_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_engine_degraded(self, payload: Dict[str, Any], trace_id: str):
        """Handle engine.degraded event."""
        engine_id = payload["engine_id"]
        
        updates = {
            "health": "degraded",
            "last_error": payload.get("degradation_type"),
            "last_error_time": payload.get("detected_at")
        }
        
        await self.state_manager.update_engine_state(
            engine_id=engine_id,
            updates=updates,
            triggered_by="engine_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_engine_recovered(self, payload: Dict[str, Any], trace_id: str):
        """Handle engine.recovered event."""
        engine_id = payload["engine_id"]
        
        updates = {
            "health": "healthy",
            "last_event": "recovered",
            "last_event_time": payload.get("recovered_at")
        }
        
        await self.state_manager.update_engine_state(
            engine_id=engine_id,
            updates=updates,
            triggered_by="engine_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
