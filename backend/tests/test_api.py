from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db_operational"] is True

def test_zones_endpoints():
    response = client.get("/zones")
    assert response.status_code == 200
    zones = response.json()
    assert isinstance(zones, list)
    assert len(zones) >= 3

def test_sku_endpoints():
    response = client.get("/sku/list")
    assert response.status_code == 200
    skus = response.json()
    assert isinstance(skus, list)
    assert len(skus) >= 3

def test_dashboard_endpoints():
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_active_stockouts" in data
    assert "lost_sales_prevented_dollars" in data

    response_ins = client.get("/dashboard/insights")
    assert response_ins.status_code == 200
    assert isinstance(response_ins.json(), list)

if __name__ == "__main__":
    test_health_endpoint()
    test_zones_endpoints()
    test_sku_endpoints()
    test_dashboard_endpoints()
    print("API tests passed!")
