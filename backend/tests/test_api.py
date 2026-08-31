from fastapi.testclient import TestClient
from backend.main import app
from backend.app.database import init_db
from demo_seed import seed_database

def test_health_endpoint():
    init_db()
    with TestClient(app) as client:
        # 1. Test liveness
        res_live = client.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "alive"

        # 2. Test readiness
        res_ready = client.get("/health/ready")
        assert res_ready.status_code in [200, 503]

        # 3. Test comprehensive health
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["db_operational"] is True
        assert "system_metrics" in data

def test_zones_endpoints():
    init_db()
    seed_database()
    with TestClient(app) as client:
        response = client.get("/zones")
        assert response.status_code == 200
        zones = response.json()
        assert isinstance(zones, list)
        assert len(zones) >= 3

def test_sku_endpoints():
    init_db()
    seed_database()
    with TestClient(app) as client:
        response = client.get("/sku/list")
        assert response.status_code == 200
        skus = response.json()
        assert isinstance(skus, list)
        assert len(skus) >= 3

def test_dashboard_endpoints():
    init_db()
    seed_database()
    with TestClient(app) as client:
        response = client.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_active_stockouts" in data
        assert "lost_sales_prevented_dollars" in data

        response_ins = client.get("/dashboard/insights")
        assert response_ins.status_code == 200
        assert isinstance(response_ins.json(), list)

def test_video_endpoints():
    init_db()
    with TestClient(app) as client:
        # Test privacy toggle
        res_toggle = client.post("/video/privacy-toggle", json={"enabled": True})
        assert res_toggle.status_code == 200
        assert res_toggle.json()["privacy_blur_enabled"] is True

        # Test video status
        res_status = client.get("/video/status")
        assert res_status.status_code == 200

        # Test video source switch
        res_src = client.post("/video/source", json={"source": "synthetic", "rotation_deg": 0})
        assert res_src.status_code == 200
        assert res_src.json()["source"] == "synthetic"

if __name__ == "__main__":
    test_health_endpoint()
    test_zones_endpoints()
    test_sku_endpoints()
    test_dashboard_endpoints()
    test_video_endpoints()
    print("API tests passed successfully!")
