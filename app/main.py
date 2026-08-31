import asyncio
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from autonomy_events import EventConsumer, EventPublisher
from consumers import DLQRemediationConsumer  # autonomy-events' sibling package, editable-installed
from .controllers import state_controller, dlq_controller
from .consumers import FailureConsumer
from .state import StateManager, RedisStateStore, PostgresStateStore
from .transitions import TransitionValidator, TransitionEmitter
from .tracing import Tracer
from .utils.config import settings


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Global State Manager",
    description="Central nervous system of the Autonomous Company OS - tracks global system state, engine state, resource usage, funnel/product lifecycle, autonomous tasks, governance decisions, failures/recovery, and market/strategy state",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
def _cors_allowed_origins() -> list:
    # SECURITY_REVIEW.md #1 - no wildcard with credentials. Set
    # ALLOWED_ORIGINS (comma-separated) when a browser client exists.
    import os
    return [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(state_controller.router)
app.include_router(dlq_controller.router)

# Global clients
state_manager: StateManager = None
transition_validator: TransitionValidator = None
transition_emitter: TransitionEmitter = None
tracer: Tracer = None

# Failure-event consumer layer (2026-08-10 Stage 3 close-out). FailureConsumer
# and DLQRemediationConsumer existed as handler classes since Stage 3 first
# landed, but neither was ever connected to RabbitMQ or started - see
# OS42_REPAIR_PLAN.md's Stage 3 reconciliation notes. Both are bound to the
# same "failure.detected" routing key on separate queues (a topic exchange
# delivers an independent copy of the message to every bound queue), so one
# tracks global system status while the other applies retry/escalation -
# they're independent consumers of the same event, not a pipeline.
failure_event_consumer: Optional[EventConsumer] = None
dlq_remediation_event_consumer: Optional[EventConsumer] = None
dlq_remediation_publisher: Optional[EventPublisher] = None
_consumer_tasks: List[asyncio.Task] = []


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global state_manager, transition_validator, transition_emitter, tracer
    global failure_event_consumer, dlq_remediation_event_consumer, dlq_remediation_publisher

    logger.info("service_starting", service=settings.service_name)

    # Initialize tracer
    tracer = Tracer(settings.service_name)

    # Initialize state stores
    redis_store = RedisStateStore()
    await redis_store.connect()

    postgres_store = PostgresStateStore()
    await postgres_store.connect()

    # Initialize state manager
    state_manager = StateManager(redis_store, postgres_store)
    logger.info("state_manager_initialized")

    # Initialize transition validator
    transition_validator = TransitionValidator()
    logger.info("transition_validator_initialized")

    # Initialize transition emitter
    transition_emitter = TransitionEmitter(settings.rabbitmq_url)
    await transition_emitter.connect()
    logger.info("transition_emitter_initialized")

    # Wire the failure-event consumers (see module-level comment above)
    failure_handler = FailureConsumer(state_manager, transition_validator, transition_emitter, tracer)
    failure_event_consumer = EventConsumer(
        rabbitmq_url=settings.rabbitmq_url,
        queue_name="global-state-manager.failures",
        exchange_name=settings.rabbitmq_exchange,
        exchange_type=settings.rabbitmq_exchange_type,
        routing_keys=["failure.detected", "failure.recovered"],
    )
    failure_event_consumer.register_handler("failure.detected", failure_handler.handle_event)
    failure_event_consumer.register_handler("failure.recovered", failure_handler.handle_event)
    await failure_event_consumer.connect()

    dlq_remediation_publisher = EventPublisher(
        rabbitmq_url=settings.rabbitmq_url, exchange_name=settings.rabbitmq_exchange
    )
    await dlq_remediation_publisher.connect()

    dlq_remediation_handler = DLQRemediationConsumer()
    dlq_remediation_handler.publisher = dlq_remediation_publisher
    dlq_remediation_event_consumer = EventConsumer(
        rabbitmq_url=settings.rabbitmq_url,
        queue_name="autonomy-events.dlq-remediation",
        exchange_name=settings.rabbitmq_exchange,
        exchange_type=settings.rabbitmq_exchange_type,
        routing_keys=["failure.detected"],
    )
    dlq_remediation_event_consumer.register_handler("failure.detected", dlq_remediation_handler.handle_event)
    await dlq_remediation_event_consumer.connect()

    # start_consuming() runs an internal `async for` loop until disconnected -
    # must be a background task, not awaited directly, or it would block
    # startup_event from ever returning.
    _consumer_tasks.append(asyncio.create_task(failure_event_consumer.start_consuming()))
    _consumer_tasks.append(asyncio.create_task(dlq_remediation_event_consumer.start_consuming()))
    logger.info("failure_consumers_started")

    logger.info("service_started", service=settings.service_name)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global state_manager, transition_emitter
    global failure_event_consumer, dlq_remediation_event_consumer, dlq_remediation_publisher

    logger.info("service_stopping")

    for task in _consumer_tasks:
        task.cancel()
    _consumer_tasks.clear()

    if failure_event_consumer:
        await failure_event_consumer.disconnect()
    if dlq_remediation_event_consumer:
        await dlq_remediation_event_consumer.disconnect()
    if dlq_remediation_publisher:
        await dlq_remediation_publisher.disconnect()

    if transition_emitter:
        await transition_emitter.disconnect()

    if state_manager:
        await state_manager.redis.disconnect()
        await state_manager.postgres.disconnect()

    logger.info("service_stopped")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "healthy"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Global State Manager",
        "version": "1.0.0",
        "description": "Central nervous system of the Autonomous Company OS",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    asyncio.run(uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True
    ))
