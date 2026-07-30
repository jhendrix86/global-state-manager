# Global State Manager

The central nervous system of the Autonomous Company OS. This service tracks global system state, engine state, resource usage, funnel/product lifecycle, autonomous tasks, governance decisions, failures/recovery, and market/strategy state. It provides state snapshots, diffs, subscriptions, and alerts.

## Features

- **Dual Storage** - Redis for fast in-memory state, PostgreSQL for persistent state with versioning
- **State Models** - 8 state types (Global, Engine, Funnel, Product, Task, Governance, Resource, Failure)
- **State Transitions** - Validated state updates with event emission and versioning
- **Event Consumption** - Consumes events from 7 event categories (funnel, governance, kg, engine, resource, failure, strategy)
- **API Endpoints** - Read/write state, snapshots, diffs, WebSocket subscriptions, alerts
- **Distributed Tracing** - OpenTelemetry integration with W3C traceparent support
- **DLQ Management** - Dead letter queue with replay capabilities
- **State Alerts** - Alert system for state changes and anomalies
- **WebSocket Subscriptions** - Real-time state change notifications

## Architecture

```
┌─────────────┐    Events    ┌──────────────┐
│   RabbitMQ  │ ────────────> │  Consumers   │
└─────────────┘              └──────┬───────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
            ┌───────▼──────┐ ┌────▼────┐ ┌────▼──────┐
            │    Redis     │ │PostgreSQL│ │  Tracer   │
            │  (In-Memory) │ │(Persistent)│ │  (OTel)   │
            └──────────────┘ └─────────┘ └───────────┘
                    │              │
                    └──────┬───────┘
                           │
                    ┌──────▼──────┐
                    │ State Manager│
                    └──────────────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │  (REST API) │
                    └─────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- Redis 7.2+
- PostgreSQL 15+
- RabbitMQ 3.12+
- Docker (optional, for containerized deployment)

### Local Development

```bash
# Clone repository
git clone https://github.com/autonomous-company/global-state-manager.git
cd global-state-manager

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the service
uvicorn app.main:app --reload --port 8035
```

### Docker Deployment

```bash
# Build and start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f global-state-manager

# Stop services
docker-compose down
```

## Configuration

Configuration is managed via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `password` | PostgreSQL password |
| `POSTGRES_DATABASE` | `global_state` | PostgreSQL database |
| `RABBITMQ_URL` | `amqp://localhost:5672` | RabbitMQ connection URL |
| `STATE_TTL` | `3600` | State TTL in seconds |
| `SNAPSHOT_INTERVAL` | `300` | Snapshot interval in seconds |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry tracing |
| `OTEL_ENDPOINT` | `http://localhost:4318` | OTLP endpoint |

## State Models

### Global State
- `system_status` - Overall system health (healthy, degraded, critical, maintenance)
- `active_engines` - List of active engine IDs
- `active_funnels` - List of active funnel IDs
- `active_products` - List of active product IDs
- `active_tasks` - List of active task IDs
- `active_strategies` - List of active strategy IDs
- `market_conditions` - Current market conditions
- `resource_usage` - Resource usage metrics
- `governance_status` - Governance decision status
- `failure_status` - Current failure status
- `recovery_status` - Recovery progress

### Engine State
- `engine_id` - Engine identifier
- `engine_type` - Engine type (orchestrator, content, etc.)
- `health` - Health status (healthy, degraded, critical, offline)
- `load` - Current load (0-1)
- `resource_usage` - CPU, memory, connections
- `last_event` - Last event type
- `last_error` - Last error message
- `uptime_seconds` - Engine uptime
- `request_count` - Total requests processed
- `error_count` - Total errors encountered

### Funnel State
- `funnel_id` - Funnel identifier
- `lifecycle_stage` - Stage (initializing, active, paused, archived, failed, recovering)
- `metrics` - Performance metrics
- `insights` - Generated insights
- `strategy` - Associated strategy
- `risk` - Risk assessment
- `niche` - Target niche
- `target_audience` - Target audience
- `channels` - Active channels
- `total_visitors` - Total visitors
- `total_conversions` - Total conversions
- `total_revenue` - Total revenue
- `conversion_rate` - Conversion rate (0-1)

### Product State
- `product_id` - Product identifier
- `lifecycle_stage` - Stage (initializing, active, paused, archived, failed, recovering)
- `pricing` - Pricing information
- `market_position` - Market position data
- `competitors` - Competitor list
- `total_sales` - Total sales
- `total_revenue` - Total revenue
- `average_rating` - Average rating (0-5)
- `review_count` - Number of reviews

### Task State
- `task_id` - Task identifier
- `type` - Task type
- `status` - Status (pending, running, completed, failed, cancelled)
- `progress` - Progress (0-1)
- `assigned_engine` - Assigned engine
- `priority` - Priority (low, normal, high)
- `created_at` - Creation timestamp
- `started_at` - Start timestamp
- `completed_at` - Completion timestamp
- `error_message` - Error message if failed
- `retry_count` - Number of retries
- `max_retries` - Maximum allowed retries

### Governance State
- `last_decision` - Last governance decision
- `decision_history` - Decision history
- `overrides` - Override history
- `kill_switch_status` - Kill switch status
- `active_rules` - Number of active rules
- `pending_approvals` - Pending approval count
- `rejected_count` - Rejected decision count
- `approved_count` - Approved decision count

### Resource State
- `compute_usage` - Compute resource usage
- `api_usage` - API usage metrics
- `budget_usage` - Budget usage
- `quotas` - Resource quotas
- `alerts` - Resource alerts

### Failure State
- `failure_id` - Failure identifier
- `type` - Failure type
- `severity` - Severity (low, medium, high, critical)
- `affected_entities` - Affected entity list
- `recovery_plan` - Recovery plan
- `recovery_progress` - Recovery progress (0-1)
- `detected_at` - Detection timestamp
- `resolved_at` - Resolution timestamp
- `resolved` - Resolution status

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - Service information

### State Read
- `GET /state/global` - Get global system state
- `GET /state/engine/{engine_id}` - Get engine state
- `GET /state/funnel/{funnel_id}` - Get funnel state
- `GET /state/product/{product_id}` - Get product state
- `GET /state/task/{task_id}` - Get task state

### State Write
- `POST /state/update` - Update state (global, engine, funnel, etc.)
- `POST /state/transition` - Trigger state transition

### State Snapshots
- `GET /state/snapshot` - Create new snapshot
- `GET /state/snapshot/{snapshot_id}` - Get snapshot by ID

### State Diffs
- `GET /state/diff/{entity_type}/{entity_id}/{from_version}/{to_version}` - Get state diff

### State Subscriptions
- `WebSocket /ws/state/subscribe` - Subscribe to state changes

### State Alerts
- `GET /state/alerts` - Get state alerts (optional filters: entity_type, entity_id, resolved)

### DLQ Management
- `GET /dlq/stats` - Get DLQ statistics
- `GET /dlq/messages` - Peek at DLQ messages
- `POST /dlq/replay/{event_id}` - Replay specific message
- `POST /dlq/replay-batch` - Replay batch of messages
- `POST /dlq/purge` - Purge old messages

## Usage Examples

### Get Global State

```python
import httpx

async def get_global_state():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8035/state/global")
        return response.json()
```

### Update Engine State

```python
async def update_engine_state(engine_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8035/state/update",
            json={
                "entity_type": "engine",
                "entity_id": engine_id,
                "updates": {
                    "health": "degraded",
                    "load": 0.8
                },
                "triggered_by": "monitoring-service"
            }
        )
        return response.json()
```

### Create Snapshot

```python
async def create_snapshot():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8035/state/snapshot")
        return response.json()
```

### Get State Diff

```python
async def get_state_diff(entity_type: str, entity_id: str, from_v: int, to_v: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8035/state/diff/{entity_type}/{entity_id}/{from_v}/{to_v}"
        )
        return response.json()
```

### WebSocket Subscription

```python
import websockets

async def subscribe_to_state_changes():
    async with websockets.connect("ws://localhost:8035/ws/state/subscribe") as ws:
        while True:
            message = await ws.recv()
            print(f"State change: {message}")
```

## Event Consumption

The service consumes events from RabbitMQ and updates state accordingly:

### Funnel Events
- `funnel.created` - Create funnel state
- `funnel.launched` - Update funnel to active
- `funnel.metrics` - Update funnel metrics
- `funnel.archived` - Archive funnel

### Governance Events
- `governance.approved` - Update governance status
- `governance.rejected` - Update governance status
- `governance.override` - Record override
- `governance.emergency_stop` - Trigger emergency stop

### KG Events
- `kg.entity_created` - Add entity to global state
- `kg.pattern_detected` - Update market conditions
- `kg.insight_generated` - Update strategy state

### Engine Events
- `engine.health_report` - Update engine health
- `engine.degraded` - Mark engine as degraded
- `engine.recovered` - Mark engine as recovered

### Resource Events
- `resource.compute_request` - Update compute usage
- `resource.api_request` - Update API usage
- `resource.budget_request` - Update budget usage

### Failure Events
- `failure.detected` - Record failure
- `failure.recovered` - Update recovery status

### Strategy Events
- `strategy.alignment_request` - Update strategy state
- `strategy.override` - Override strategy

## State Transitions

Every state change:
1. Validates the transition
2. Updates Redis (in-memory)
3. Updates PostgreSQL (persistent with versioning)
4. Emits state transition event
5. Includes tracing metadata
6. Publishes to pub/sub for subscribers

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_state_schemas.py
```

### Adding New State Types

1. Add state schema to `app/schemas/state_schemas.py`
2. Add validator to `app/transitions/transition_validator.py`
3. Add update method to `app/state/state_manager.py`
4. Add API endpoint to `app/controllers/state_controller.py`

## Monitoring

### OpenTelemetry Tracing

The service exports traces to OTLP endpoint (default: `http://localhost:4318`). View traces in Jaeger UI at `http://localhost:16686`.

### Health Check

```bash
curl http://localhost:8035/health
```

## Troubleshooting

### Redis Connection Failed

- Check Redis is running: `docker ps | grep redis`
- Verify connection details in environment variables
- Check Redis logs: `docker logs gsm-redis`

### PostgreSQL Connection Failed

- Check PostgreSQL is running: `docker ps | grep postgres`
- Verify connection details in environment variables
- Check PostgreSQL logs: `docker logs gsm-postgres`

### State Not Persisting

- Check PostgreSQL connection
- Verify schema is initialized
- Check for constraint violations

### Events Not Being Consumed

- Check consumer logs for errors
- Verify RabbitMQ exchange exists
- Check routing keys match event types
- Verify DLQ for failed messages

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
