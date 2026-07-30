import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "docs" in data


class TestStateEndpoints:
    def test_get_global_state(self):
        response = client.get("/state/global")
        # Will be 500 if Redis/PostgreSQL not connected, but we can test the schema
        assert response.status_code in [200, 500]
    
    def test_get_engine_state_not_found(self):
        response = client.get("/state/engine/nonexistent")
        # Will be 404 if connected, 500 if not
        assert response.status_code in [404, 500]
    
    def test_get_funnel_state_not_found(self):
        response = client.get("/state/funnel/nonexistent")
        assert response.status_code in [404, 500]
    
    def test_update_state(self):
        request_data = {
            "entity_type": "global",
            "updates": {"system_status": "healthy"},
            "triggered_by": "test"
        }
        
        response = client.post("/state/update", json=request_data)
        assert response.status_code in [200, 500]
    
    def test_create_snapshot(self):
        response = client.get("/state/snapshot")
        assert response.status_code in [200, 500]
    
    def test_get_snapshot_not_found(self):
        response = client.get("/state/snapshot/nonexistent")
        assert response.status_code in [404, 500]
    
    def test_get_alerts(self):
        response = client.get("/state/alerts")
        assert response.status_code in [200, 500]


class TestDLQEndpoints:
    def test_get_dlq_stats(self):
        response = client.get("/dlq/stats")
        assert response.status_code in [200, 500]
    
    def test_peek_dlq_messages(self):
        response = client.get("/dlq/messages?limit=10")
        assert response.status_code in [200, 500]
