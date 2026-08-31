from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class FailureConsumer(BaseConsumer):
    """Consumer for failure-related events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle failure events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "failure.detected":
                await self._handle_failure_detected(payload, trace_id)
            elif event_type == "failure.recovered":
                await self._handle_failure_recovered(payload, trace_id)
            else:
                logger.warning("unknown_failure_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown failure event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("failure_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_failure_detected(self, payload: Dict[str, Any], trace_id: str):
        """Handle failure.detected event."""
        failure_id = payload["failure_id"]
        
        updates = {
            "failure_id": failure_id,
            "type": payload.get("failure_type"),
            "severity": payload.get("severity"),
            # Real FailureDetected schema field is affected_operations, not
            # affected_entities - this always read as [] regardless of what
            # the publisher actually sent.
            "affected_entities": payload.get("affected_operations", []),
            "detected_at": payload.get("detected_at")
        }
        
        # Update global failure status
        await self.state_manager.update_global_state(
            updates={
                "system_status": "degraded",
                "failure_status": updates
            },
            triggered_by="failure_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_failure_recovered(self, payload: Dict[str, Any], trace_id: str):
        """Handle failure.recovered event."""
        failure_id = payload["failure_id"]
        
        # Update recovery status
        await self.state_manager.update_global_state(
            updates={
                "recovery_status": {
                    "failure_id": failure_id,
                    "recovered_at": payload.get("recovered_at"),
                    "recovered_by": payload.get("recovered_by")
                }
            },
            triggered_by="failure_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
