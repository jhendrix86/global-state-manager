from typing import Dict, Any
import structlog
from autonomy_events import EventPublisher, EventEnvelope, EventPriority, TraceParent
from ..schemas.transition_schemas import StateTransition


logger = structlog.get_logger()


class TransitionEmitter:
    """Emit state transition events to RabbitMQ."""
    
    def __init__(self, rabbitmq_url: str, exchange_name: str = "autonomy.events"):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self._publisher: EventPublisher = None
    
    async def connect(self):
        """Connect to RabbitMQ."""
        self._publisher = EventPublisher(
            rabbitmq_url=self.rabbitmq_url,
            exchange_name=self.exchange_name
        )
        await self._publisher.connect()
        logger.info("transition_emitter_connected")
    
    async def disconnect(self):
        """Disconnect from RabbitMQ."""
        if self._publisher:
            await self._publisher.disconnect()
        logger.info("transition_emitter_disconnected")
    
    async def emit_transition(
        self,
        transition: StateTransition,
        trace_parent: TraceParent = None
    ):
        """Emit a state transition event."""
        event_type = f"state.{transition.transition_type.value}"
        
        payload = {
            "transition_id": transition.transition_id,
            "entity_type": transition.entity_type,
            "entity_id": transition.entity_id,
            "transition_type": transition.transition_type.value,
            "previous_state": transition.previous_state,
            "new_state": transition.new_state,
            "diff": transition.diff,
            "version_before": transition.version_before,
            "version_after": transition.version_after,
            "triggered_by": transition.triggered_by,
            "metadata": transition.metadata
        }
        
        envelope = EventEnvelope(
            event_type=event_type,
            engine_id="global-state-manager",
            priority=EventPriority.NORMAL,
            payload=payload
        )
        
        # Inject tracing
        if trace_parent:
            envelope.correlation_id = trace_parent.correlation_id
            envelope.causation_id = trace_parent.causation_id
        else:
            envelope.correlation_id = transition.correlation_id
            envelope.causation_id = transition.causation_id
        
        # Publish event
        routing_key = f"state.{transition.entity_type}.{transition.transition_type.value}"
        result = await self._publisher.publish(envelope, routing_key, trace_parent)
        
        if result.success:
            logger.info(
                "state_transition_emitted",
                event_type=event_type,
                transition_id=transition.transition_id,
                message_id=result.message_id
            )
        else:
            logger.error(
                "state_transition_emit_failed",
                event_type=event_type,
                transition_id=transition.transition_id,
                error=result.error
            )
    
    async def emit_alert(
        self,
        alert_type: str,
        severity: str,
        entity_type: str,
        entity_id: str,
        message: str,
        details: Dict[str, Any],
        triggered_by: str,
        trace_parent: TraceParent = None
    ):
        """Emit a state alert event."""
        event_type = "state.alert"
        
        payload = {
            "alert_type": alert_type,
            "severity": severity,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "message": message,
            "details": details,
            "triggered_by": triggered_by
        }
        
        envelope = EventEnvelope(
            event_type=event_type,
            engine_id="global-state-manager",
            priority=self._map_alert_priority(severity),
            payload=payload
        )
        
        if trace_parent:
            envelope.correlation_id = trace_parent.correlation_id
            envelope.causation_id = trace_parent.causation_id
        
        routing_key = "state.alert"
        result = await self._publisher.publish(envelope, routing_key, trace_parent)
        
        logger.info(
            "state_alert_emitted",
            alert_type=alert_type,
            entity_type=entity_type,
            entity_id=entity_id
        )
    
    def _map_alert_priority(self, severity: str) -> EventPriority:
        """Map alert severity to event priority."""
        mapping = {
            "info": EventPriority.LOW,
            "low": EventPriority.NORMAL,
            "medium": EventPriority.NORMAL,
            "high": EventPriority.HIGH,
            "critical": EventPriority.CRITICAL
        }
        return mapping.get(severity.lower(), EventPriority.NORMAL)
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
