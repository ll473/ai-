from fastapi.testclient import TestClient

from backend.app.main import app


def test_root_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_health_uses_response_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "OK"
    assert body["data"]["status"] == "healthy"


def test_openapi_contains_catalog_routes() -> None:
    schema = app.openapi()

    assert "/api/v1/catalog/products" in schema["paths"]
    assert "/api/v1/catalog/products/{product_id}" in schema["paths"]
    assert "/api/v1/admin/catalog/products/{product_id}/images" in schema["paths"]
    assert "/api/v1/cart/items" in schema["paths"]
    assert "/api/v1/wallet/recharge" in schema["paths"]
    assert "/api/v1/orders/{order_id}/pay" in schema["paths"]
    assert "/api/v1/orders/{order_id}/complete" in schema["paths"]
    assert "/api/v1/catalog/products/{product_id}/reviews" in schema["paths"]
    assert "/api/v1/admin/orders/{order_id}/ship" in schema["paths"]
    assert "/api/v1/admin/reviews/{review_id}" in schema["paths"]
    assert "/api/v1/admin/ai/models" in schema["paths"]
    assert "/api/v1/admin/ai/tools/seed-builtins" in schema["paths"]
    assert "/api/v1/admin/ai/tool-logs" in schema["paths"]
    assert "/api/v1/ai/shopping-guide" in schema["paths"]
    assert "/api/v1/ai/runs" in schema["paths"]
    assert "/api/v1/favorites/{product_id}" in schema["paths"]
