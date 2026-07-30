from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Global State Manager Configuration."""
    
    # Service
    service_name: str = "global-state-manager"
    service_version: str = "1.0.0"
    port: int = 8035
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "password"
    postgres_database: str = "global_state"
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://localhost:5672"
    rabbitmq_exchange: str = "autonomy.events"
    rabbitmq_exchange_type: str = "topic"
    
    # State Management
    state_ttl: int = 3600  # seconds
    snapshot_interval: int = 300  # seconds
    max_snapshot_history: int = 100
    
    # Event Consumers
    consumer_prefetch_count: int = 10
    consumer_auto_ack: bool = False
    dlq_enabled: bool = True
    
    # State Transitions
    transition_validation: bool = True
    transition_versioning: bool = True
    transition_event_emission: bool = True
    
    # OpenTelemetry
    otel_enabled: bool = True
    otel_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "global-state-manager"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # WebSocket
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
