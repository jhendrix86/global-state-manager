from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class ResourceConsumer(BaseConsumer):
    """Consumer for resource-related events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle resource events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "resource.compute_request":
                await self._handle_compute_request(payload, trace_id)
            elif event_type == "resource.api_request":
                await self._handle_api_request(payload, trace_id)
            elif event_type == "resource.budget_request":
                await self._handle_budget_request(payload, trace_id)
            else:
                logger.warning("unknown_resource_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown resource event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("resource_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_compute_request(self, payload: Dict[str, Any], trace_id: str):
        """Handle resource.compute_request event."""
        quantity = payload.get("quantity", 0)
        
        await self.state_manager.update_global_state(
            updates={"resource_usage": {"compute": quantity}},
            triggered_by="resource_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_api_request(self, payload: Dict[str, Any], trace_id: str):
        """Handle resource.api_request event."""
        rate_limit = payload.get("rate_limit", 0)
        
        await self.state_manager.update_global_state(
            updates={"resource_usage": {"api": rate_limit}},
            triggered_by="resource_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_budget_request(self, payload: Dict[str, Any], trace_id: str):
        """Handle resource.budget_request event."""
        amount = payload.get("amount", 0.0)
        
        await self.state_manager.update_global_state(
            updates={"resource_usage": {"budget": amount}},
            triggered_by="resource_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
