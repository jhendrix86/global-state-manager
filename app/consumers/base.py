from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
import structlog
from autonomy_events import EventEnvelope, ConsumeResult, TraceParent
from ..state import StateManager
from ..transitions import TransitionValidator, TransitionEmitter
from ..tracing import Tracer


logger = structlog.get_logger()


class BaseConsumer(ABC):
    """Base class for all event consumers."""
    
    def __init__(
        self,
        state_manager: StateManager,
        transition_validator: TransitionValidator,
        transition_emitter: TransitionEmitter,
        tracer: Tracer
    ):
        self.state_manager = state_manager
        self.validator = transition_validator
        self.emitter = transition_emitter
        self.tracer = tracer
    
    @abstractmethod
    async def handle_event(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent
    ) -> ConsumeResult:
        """Handle the event. Must be implemented by subclasses."""
        pass
    
    async def process_with_retry(
        self,
        envelope: EventEnvelope,
        trace_parent: TraceParent,
        max_retries: int = 3
    ) -> ConsumeResult:
        """Process event with retry logic."""
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                result = await self.handle_event(envelope, trace_parent)
                if result.success:
                    return result
                else:
                    last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.error(
                    "consumer_error",
                    event_id=envelope.event_id,
                    event_type=envelope.event_type,
                    retry_count=retry_count,
                    error=str(e)
                )
            
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        return ConsumeResult(
            success=False,
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            error=last_error or "Max retries exceeded",
            should_ack=False,
            should_requeue=True
        )
