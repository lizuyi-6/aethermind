import app


def test_legacy_api_is_gone():
    client = app.app.test_client()
    resp = client.get("/api/config")
    assert resp.status_code == 410
    payload = resp.get_json() or {}
    assert payload.get("error", {}).get("code") == "API_VERSION_MIGRATED"


def test_v1_config_available():
    client = app.app.test_client()
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    payload = resp.get_json() or {}
    assert "provider" in payload
