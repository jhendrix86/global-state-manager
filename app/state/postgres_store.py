import json
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncpg
from ..utils.config import settings


logger = structlog.get_logger()


class PostgresStateStore:
    """PostgreSQL-based persistent state store with versioning."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        self.host = host or settings.postgres_host
        self.port = port or settings.postgres_port
        self.user = user or settings.postgres_user
        self.password = password or settings.postgres_password
        self.database = database or settings.postgres_database
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Connect to PostgreSQL and create tables."""
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        
        # Initialize schema
        await self._init_schema()
        
        logger.info("postgres_connected", host=self.host, database=self.database)
    
    async def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self._pool:
            await self._pool.close()
        logger.info("postgres_disconnected")
    
    async def _init_schema(self):
        """Initialize database schema."""
        async with self._pool.acquire() as conn:
            # State table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255),
                    state_data JSONB NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(entity_type, entity_id, version)
                )
            """)
            
            # State transitions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state_transitions (
                    id SERIAL PRIMARY KEY,
                    transition_id VARCHAR(255) UNIQUE NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255),
                    transition_type VARCHAR(50) NOT NULL,
                    previous_state JSONB,
                    new_state JSONB NOT NULL,
                    diff JSONB,
                    version_before INTEGER NOT NULL,
                    version_after INTEGER NOT NULL,
                    trace_id VARCHAR(255) NOT NULL,
                    correlation_id VARCHAR(255) NOT NULL,
                    causation_id VARCHAR(255),
                    triggered_by VARCHAR(255) NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Snapshots table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id SERIAL PRIMARY KEY,
                    snapshot_id VARCHAR(255) UNIQUE NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    global_state JSONB NOT NULL,
                    engine_states JSONB DEFAULT '{}'::jsonb,
                    funnel_states JSONB DEFAULT '{}'::jsonb,
                    product_states JSONB DEFAULT '{}'::jsonb,
                    task_states JSONB DEFAULT '{}'::jsonb,
                    governance_state JSONB DEFAULT '{}'::jsonb,
                    resource_state JSONB DEFAULT '{}'::jsonb,
                    failure_states JSONB DEFAULT '{}'::jsonb,
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state_alerts (
                    id SERIAL PRIMARY KEY,
                    alert_id VARCHAR(255) UNIQUE NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255),
                    message TEXT NOT NULL,
                    details JSONB DEFAULT '{}'::jsonb,
                    triggered_by VARCHAR(255) NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_by VARCHAR(255),
                    acknowledged_at TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_state_entity ON state(entity_type, entity_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_state_version ON state(entity_type, entity_id, version)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_entity ON state_transitions(entity_type, entity_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_trace ON state_transitions(trace_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON state_snapshots(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_entity ON state_alerts(entity_type, entity_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON state_alerts(resolved)")
    
    async def get_state(
        self,
        entity_type: str,
        entity_id: Optional[str] = None,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get state from PostgreSQL."""
        async with self._pool.acquire() as conn:
            if version:
                query = """
                    SELECT state_data, version, updated_at
                    FROM state
                    WHERE entity_type = $1 AND entity_id = $2 AND version = $3
                """
                row = await conn.fetchrow(query, entity_type, entity_id or "global", version)
            else:
                query = """
                    SELECT state_data, version, updated_at
                    FROM state
                    WHERE entity_type = $1 AND entity_id = $2
                    ORDER BY version DESC
                    LIMIT 1
                """
                row = await conn.fetchrow(query, entity_type, entity_id or "global")
            
            if row:
                return {
                    "state_data": row["state_data"],
                    "version": row["version"],
                    "updated_at": row["updated_at"].isoformat()
                }
            return None
    
    async def save_state(
        self,
        entity_type: str,
        entity_id: Optional[str],
        state: Dict[str, Any],
        version: int
    ):
        """Save state to PostgreSQL."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO state (entity_type, entity_id, state_data, version)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (entity_type, entity_id, version)
                DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
            """, entity_type, entity_id or "global", json.dumps(state), version)
    
    async def save_transition(
        self,
        transition: Dict[str, Any]
    ):
        """Save state transition to PostgreSQL."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO state_transitions (
                    transition_id, entity_type, entity_id, transition_type,
                    previous_state, new_state, diff, version_before, version_after,
                    trace_id, correlation_id, causation_id, triggered_by, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                transition["transition_id"],
                transition["entity_type"],
                transition.get("entity_id") or "global",
                transition["transition_type"],
                json.dumps(transition.get("previous_state")) if transition.get("previous_state") else None,
                json.dumps(transition["new_state"]),
                json.dumps(transition.get("diff")) if transition.get("diff") else None,
                transition["version_before"],
                transition["version_after"],
                transition["trace_id"],
                transition["correlation_id"],
                transition.get("causation_id"),
                transition["triggered_by"],
                json.dumps(transition.get("metadata", {}))
            )
    
    async def save_snapshot(self, snapshot: Dict[str, Any]):
        """Save state snapshot to PostgreSQL."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO state_snapshots (
                    snapshot_id, timestamp, global_state, engine_states,
                    funnel_states, product_states, task_states, governance_state,
                    resource_state, failure_states, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                snapshot["snapshot_id"],
                snapshot["timestamp"],
                json.dumps(snapshot["global_state"]),
                json.dumps(snapshot.get("engine_states", {})),
                json.dumps(snapshot.get("funnel_states", {})),
                json.dumps(snapshot.get("product_states", {})),
                json.dumps(snapshot.get("task_states", {})),
                json.dumps(snapshot.get("governance_state", {})),
                json.dumps(snapshot.get("resource_state", {})),
                json.dumps(snapshot.get("failure_states", {})),
                json.dumps(snapshot.get("metadata", {}))
            )
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get snapshot by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM state_snapshots WHERE snapshot_id = $1",
                snapshot_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def get_snapshots(
        self,
        limit: int = 10,
        before: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get snapshots."""
        async with self._pool.acquire() as conn:
            if before:
                query = """
                    SELECT * FROM state_snapshots
                    WHERE timestamp < $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """
                rows = await conn.fetch(query, before, limit)
            else:
                query = """
                    SELECT * FROM state_snapshots
                    ORDER BY timestamp DESC
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
            
            return [dict(row) for row in rows]
    
    async def get_transitions(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get state transitions."""
        async with self._pool.acquire() as conn:
            if entity_type and entity_id:
                query = """
                    SELECT * FROM state_transitions
                    WHERE entity_type = $1 AND entity_id = $2
                    ORDER BY triggered_at DESC
                    LIMIT $3
                """
                rows = await conn.fetch(query, entity_type, entity_id, limit)
            elif entity_type:
                query = """
                    SELECT * FROM state_transitions
                    WHERE entity_type = $1
                    ORDER BY triggered_at DESC
                    LIMIT $2
                """
                rows = await conn.fetch(query, entity_type, limit)
            else:
                query = """
                    SELECT * FROM state_transitions
                    ORDER BY triggered_at DESC
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
            
            return [dict(row) for row in rows]
    
    async def save_alert(self, alert: Dict[str, Any]):
        """Save alert to PostgreSQL."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO state_alerts (
                    alert_id, alert_type, severity, entity_type, entity_id,
                    message, details, triggered_by, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                alert["alert_id"],
                alert["alert_type"],
                alert["severity"],
                alert["entity_type"],
                alert.get("entity_id"),
                alert["message"],
                json.dumps(alert.get("details", {})),
                alert["triggered_by"],
                json.dumps(alert.get("metadata", {}))
            )
    
    async def get_alerts(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts."""
        async with self._pool.acquire() as conn:
            conditions = []
            params = []
            param_count = 1
            
            if entity_type:
                conditions.append(f"entity_type = ${param_count}")
                params.append(entity_type)
                param_count += 1
            
            if entity_id:
                conditions.append(f"entity_id = ${param_count}")
                params.append(entity_id)
                param_count += 1
            
            if resolved is not None:
                conditions.append(f"resolved = ${param_count}")
                params.append(resolved)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            params.append(limit)
            
            query = f"""
                SELECT * FROM state_alerts
                WHERE {where_clause}
                ORDER BY triggered_at DESC
                LIMIT ${param_count}
            """
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_diff(
        self,
        entity_type: str,
        entity_id: Optional[str],
        from_version: int,
        to_version: int
    ) -> Optional[Dict[str, Any]]:
        """Get state diff between versions."""
        async with self._pool.acquire() as conn:
            from_state = await self.get_state(entity_type, entity_id, from_version)
            to_state = await self.get_state(entity_type, entity_id, to_version)
            
            if not from_state or not to_state:
                return None
            
            diff = self._compute_diff(
                from_state["state_data"],
                to_state["state_data"]
            )
            
            return {
                "entity_type": entity_type,
                "entity_id": entity_id or "global",
                "from_version": from_version,
                "to_version": to_version,
                "from_timestamp": from_state["updated_at"],
                "to_timestamp": to_state["updated_at"],
                "changes": diff
            }
    
    def _compute_diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Compute diff between two state dictionaries."""
        added = []
        removed = []
        modified = {}
        
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            if key not in old:
                added.append(key)
            elif key not in new:
                removed.append(key)
            elif old[key] != new[key]:
                modified[key] = {"old": old[key], "new": new[key]}
        
        return {
            "added": added,
            "removed": removed,
            "modified": modified
        }
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
