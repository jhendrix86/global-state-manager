from typing import Dict, Any
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from .base import BaseConsumer


logger = structlog.get_logger()


class StrategyConsumer(BaseConsumer):
    """Consumer for strategy-related events."""
    
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle strategy events."""
        event_type = envelope.event_type
        payload = envelope.payload
        trace_id = trace_parent.trace_context.trace_id if trace_parent else None
        
        try:
            if event_type == "strategy.alignment_request":
                await self._handle_alignment_request(payload, trace_id)
            elif event_type == "strategy.override":
                await self._handle_strategy_override(payload, trace_id)
            else:
                logger.warning("unknown_strategy_event", event_type=event_type)
                return ConsumeResult(
                    success=False,
                    event_id=envelope.event_id,
                    event_type=event_type,
                    error=f"Unknown strategy event type: {event_type}"
                )
            
            return ConsumeResult(
                success=True,
                event_id=envelope.event_id,
                event_type=event_type
            )
        
        except Exception as e:
            logger.error("strategy_consumer_error", error=str(e))
            return ConsumeResult(
                success=False,
                event_id=envelope.event_id,
                event_type=event_type,
                error=str(e)
            )
    
    async def _handle_alignment_request(self, payload: Dict[str, Any], trace_id: str):
        """Handle strategy.alignment_request event."""
        strategy_id = payload.get("strategy_id")
        
        await self.state_manager.update_global_state(
            updates={"active_strategies": [strategy_id] if strategy_id else []},
            triggered_by="strategy_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
    
    async def _handle_strategy_override(self, payload: Dict[str, Any], trace_id: str):
        """Handle strategy.override event."""
        strategy_id = payload.get("strategy_id")
        
        await self.state_manager.update_global_state(
            updates={"active_strategies": [strategy_id] if strategy_id else []},
            triggered_by="strategy_consumer",
            trace_id=trace_id,
            correlation_id=trace_id
        )
