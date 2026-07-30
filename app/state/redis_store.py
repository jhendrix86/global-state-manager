import json
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime
import redis.asyncio as aioredis
from ..utils.config import settings


logger = structlog.get_logger()


class RedisStateStore:
    """Redis-based in-memory state store with pub/sub support."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None
    ):
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self.password = password or settings.redis_password
        self._client: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.PubSub] = None
    
    async def connect(self):
        """Connect to Redis."""
        self._client = aioredis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True
        )
        
        # Test connection
        await self._client.ping()
        
        # Initialize pub/sub
        self._pubsub = self._pubsub = self._client.pubsub()
        
        logger.info("redis_connected", host=self.host, port=self.port, db=self.db)
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()
        logger.info("redis_disconnected")
    
    async def get_state(
        self,
        entity_type: str,
        entity_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get state from Redis."""
        key = self._make_key(entity_type, entity_id)
        data = await self._client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def set_state(
        self,
        entity_type: str,
        entity_id: Optional[str],
        state: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Set state in Redis."""
        key = self._make_key(entity_type, entity_id)
        ttl = ttl or settings.state_ttl
        
        await self._client.setex(
            key,
            ttl,
            json.dumps(state)
        )
        
        # Publish state change
        await self._publish_state_change(entity_type, entity_id, state)
    
    async def delete_state(
        self,
        entity_type: str,
        entity_id: Optional[str] = None
    ):
        """Delete state from Redis."""
        key = self._make_key(entity_type, entity_id)
        await self._client.delete(key)
        
        # Publish state change
        await self._publish_state_change(entity_type, entity_id, None, deleted=True)
    
    async def get_all_states(self, entity_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all states of a given type."""
        pattern = self._make_key(entity_type, "*")
        keys = await self._client.keys(pattern)
        
        states = {}
        for key in keys:
            data = await self._client.get(key)
            if data:
                entity_id = self._extract_entity_id(key)
                states[entity_id] = json.loads(data)
        
        return states
    
    async def subscribe_to_changes(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ):
        """Subscribe to state changes."""
        channel = self._make_channel(entity_type, entity_id)
        await self._pubsub.subscribe(channel)
        logger.info("redis_subscribed", channel=channel)
    
    async def unsubscribe_from_changes(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ):
        """Unsubscribe from state changes."""
        channel = self._make_channel(entity_type, entity_id)
        await self._pubsub.unsubscribe(channel)
        logger.info("redis_unsubscribed", channel=channel)
    
    async def get_next_message(self):
        """Get next pub/sub message."""
        if self._pubsub:
            message = await self._pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                return message
        return None
    
    async def _publish_state_change(
        self,
        entity_type: str,
        entity_id: Optional[str],
        state: Optional[Dict[str, Any]],
        deleted: bool = False
    ):
        """Publish state change to pub/sub."""
        channel = self._make_channel(entity_type, entity_id)
        
        message = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": state,
            "deleted": deleted,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._client.publish(channel, json.dumps(message))
    
    def _make_key(self, entity_type: str, entity_id: Optional[str] = None) -> str:
        """Make Redis key for state."""
        if entity_id:
            return f"state:{entity_type}:{entity_id}"
        return f"state:{entity_type}:global"
    
    def _make_channel(self, entity_type: Optional[str], entity_id: Optional[str]) -> str:
        """Make pub/sub channel."""
        if entity_type and entity_id:
            return f"state_changes:{entity_type}:{entity_id}"
        elif entity_type:
            return f"state_changes:{entity_type}"
        return "state_changes:all"
    
    def _extract_entity_id(self, key: str) -> str:
        """Extract entity ID from Redis key."""
        parts = key.split(":")
        if len(parts) >= 3:
            return parts[2]
        return "global"
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
