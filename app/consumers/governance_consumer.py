from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class GovernanceConsumer(BaseConsumer):
    """Consumer for governance-related events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle governance events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "governance.approved":
                await self._handle_governance_approved(payload, trace_id)
            elif event_type == "governance.rejected":
                await self._handle_governance_rejected(payload, trace_id)
            elif event_type == "governance.override":
                await self._handle_governance_override(payload, trace_id)
            elif event_type == "governance.emergency_stop":
                await self._handle_emergency_stop(payload, trace_id)
            else:
                logger.warning("unknown_governance_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown governance event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("governance_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_governance_approved(self, payload: Dict[str, Any], trace_id: str):
        """Handle governance.approved event."""
        updates = {
            "last_decision": payload,
            "approved_count": 1  # Will be incremented in actual implementation
        }
        
        await self.state_manager.update_global_state(
            updates={"governance_status": updates},
            triggered_by="governance_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_governance_rejected(self, payload: Dict[str, Any], trace_id: str):
        """Handle governance.rejected event."""
        updates = {
            "last_decision": payload,
            "rejected_count": 1
        }
        
        await self.state_manager.update_global_state(
            updates={"governance_status": updates},
            triggered_by="governance_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_governance_override(self, payload: Dict[str, Any], trace_id: str):
        """Handle governance.override event."""
        # Add to overrides list
        await self.state_manager.update_global_state(
            updates={"governance_status": {"override": payload}},
            triggered_by="governance_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_emergency_stop(self, payload: Dict[str, Any], trace_id: str):
        """Handle governance.emergency_stop event."""
        await self.state_manager.update_global_state(
            updates={
                "system_status": "critical",
                "governance_status": {"kill_switch": payload}
            },
            triggered_by="governance_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
