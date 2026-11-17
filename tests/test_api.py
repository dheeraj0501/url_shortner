from fastapi.testclient import TestClient

from src.api import create_app
from src.service import ShortLinkService


def make_client(tmp_path):
    service = ShortLinkService(tmp_path / "test.sqlite3")
    return TestClient(create_app(service))


def test_home_page_is_a_runnable_demo(tmp_path):
    response = make_client(tmp_path).get("/")

    assert response.status_code == 200
    assert "Shortlink" in response.text
    assert "/api/v1/links" in response.text


def test_create_redirect_and_analytics_flow(tmp_path):
    client = make_client(tmp_path)

    create_response = client.post(
        "/api/v1/links",
        json={"url": "https://example.com/articles/hello"},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    short_code = created["short_code"]
    assert len(short_code) == 8
    assert created["original_url"] == "https://example.com/articles/hello"
    assert created["short_url"] == f"http://testserver/r/{short_code}"
    assert created["click_count"] == 0

    redirect_response = client.get(f"/r/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://example.com/articles/hello"

    analytics_response = client.get(f"/api/v1/analytics/{short_code}")
    assert analytics_response.status_code == 200
    assert analytics_response.json()["click_count"] == 1


def test_link_persists_across_service_instances(tmp_path):
    database_path = tmp_path / "persistent.sqlite3"
    first_service = ShortLinkService(database_path)
    created = first_service.create("https://example.com/persist")

    second_service = ShortLinkService(database_path)

    assert second_service.get(created.short_code).original_url == "https://example.com/persist"


def test_invalid_urls_are_rejected(tmp_path):
    response = make_client(tmp_path).post(
        "/api/v1/links",
        json={"url": "ftp://example.com/file"},
    )

    assert response.status_code == 422


def test_unknown_short_code_returns_not_found(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/r/unknown").status_code == 404
    assert client.get("/api/v1/analytics/unknown").status_code == 404


def test_openapi_documents_shortener_endpoints(tmp_path):
    schema = make_client(tmp_path).get("/openapi.json").json()

    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/links",
        "/api/v1/links/{short_code}",
        "/api/v1/analytics/{short_code}",
        "/r/{short_code}",
    }
