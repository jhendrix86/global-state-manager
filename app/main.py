from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from .controllers import state_controller, dlq_controller
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global state_manager, transition_validator, transition_emitter, tracer
    
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
    
    logger.info("service_started", service=settings.service_name)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global state_manager, transition_emitter
    
    logger.info("service_stopping")
    
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
