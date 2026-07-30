from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class KGConsumer(BaseConsumer):
    """Consumer for knowledge graph events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle KG events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "kg.entity_created":
                await self._handle_entity_created(payload, trace_id)
            elif event_type == "kg.pattern_detected":
                await self._handle_pattern_detected(payload, trace_id)
            elif event_type == "kg.insight_generated":
                await self._handle_insight_generated(payload, trace_id)
            else:
                logger.warning("unknown_kg_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown KG event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("kg_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_entity_created(self, payload: Dict[str, Any], trace_id: str):
        """Handle kg.entity_created event."""
        entity_type = payload["entity_type"]
        entity_id = payload["entity_id"]
        
        # Update global state with new entity
        if entity_type == "funnel":
            await self.state_manager.update_global_state(
                updates={"active_funnels": [entity_id]},
                triggered_by="kg_consumer",
                trace_id=trace_id,
                correlation_id=trace_id
            )
        elif entity_type == "product":
            await self.state_manager.update_global_state(
                updates={"active_products": [entity_id]},
                triggered_by="kg_consumer",
                trace_id=trace_id,
                correlation_id=trace_id
            )
    
    async def _handle_pattern_detected(self, payload: Dict[str, Any], trace_id: str):
        """Handle kg.pattern_detected event."""
        # Update market conditions with pattern data
        await self.state_manager.update_global_state(
            updates={"market_conditions": {"pattern": payload}},
            triggered_by="kg_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_insight_generated(self, payload: Dict[str, Any], trace_id: str):
        """Handle kg.insight_generated event."""
        # Update strategy state
        await self.state_manager.update_global_state(
            updates={"active_strategies": [payload.get("insight_id")]},
            triggered_by="kg_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
