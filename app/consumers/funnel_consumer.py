from typing import Dict, Any
from datetime import datetime
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class FunnelConsumer(BaseConsumer):
    """Consumer for funnel-related events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle funnel events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "funnel.created":
                await self._handle_funnel_created(payload, trace_id)
            elif event_type == "funnel.launched":
                await self._handle_funnel_launched(payload, trace_id)
            elif event_type == "funnel.metrics":
                await self._handle_funnel_metrics(payload, trace_id)
            elif event_type == "funnel.archived":
                await self._handle_funnel_archived(payload, trace_id)
            else:
                logger.warning("unknown_funnel_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown funnel event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("funnel_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_funnel_created(self, payload: Dict[str, Any], trace_id: str):
        """Handle funnel.created event."""
        funnel_id = payload["funnel_id"]
        
        updates = {
            "funnel_id": funnel_id,
            "lifecycle_stage": "initializing",
            "niche": payload.get("niche"),
            "target_audience": payload.get("target_audience"),
            "channels": payload.get("channels", []),
            "strategy": payload.get("strategy")
        }
        
        await self.state_manager.update_funnel_state(
            funnel_id=funnel_id,
            updates=updates,
            triggered_by="funnel_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_funnel_launched(self, payload: Dict[str, Any], trace_id: str):
        """Handle funnel.launched event."""
        funnel_id = payload["funnel_id"]
        
        updates = {
            "lifecycle_stage": "active",
            "channels": payload.get("channels", [])
        }
        
        await self.state_manager.update_funnel_state(
            funnel_id=funnel_id,
            updates=updates,
            triggered_by="funnel_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_funnel_metrics(self, payload: Dict[str, Any], trace_id: str):
        """Handle funnel.metrics event."""
        funnel_id = payload["funnel_id"]
        
        updates = {
            "total_visitors": payload.get("visitors", 0),
            "total_conversions": payload.get("conversions", 0),
            "total_revenue": payload.get("revenue", 0.0),
            "conversion_rate": payload.get("conversion_rate", 0.0)
        }
        
        await self.state_manager.update_funnel_state(
            funnel_id=funnel_id,
            updates=updates,
            triggered_by="funnel_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_funnel_archived(self, payload: Dict[str, Any], trace_id: str):
        """Handle funnel.archived event."""
        funnel_id = payload["funnel_id"]
        
        updates = {
            "lifecycle_stage": "archived"
        }
        
        await self.state_manager.update_funnel_state(
            funnel_id=funnel_id,
            updates=updates,
            triggered_by="funnel_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
