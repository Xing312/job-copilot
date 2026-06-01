TEST_PASSWORD = "testpassword"


def test_login_success(auth_client):
    r = auth_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_wrong_password(auth_client):
    r = auth_client.post("/api/auth/login", json={"password": "wrongpassword"})
    assert r.status_code == 401


def test_login_not_configured(client):
    # LOGIN_PASSWORD not set — auth endpoint returns 503
    r = client.post("/api/auth/login", json={"password": "anything"})
    assert r.status_code == 503


def test_protected_without_token(auth_client):
    r = auth_client.get("/api/applications")
    assert r.status_code == 401


def test_protected_with_valid_token(auth_client, token):
    r = auth_client.get("/api/applications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_protected_with_invalid_token(auth_client):
    r = auth_client.get("/api/applications", headers={"Authorization": "Bearer invalidtoken"})
    assert r.status_code == 401


def test_extract_is_public(client):
    # /api/extract is whitelisted — no auth header required
    r = client.post("/api/extract", json={"text": "Software Engineer at Acme Corp"})
    assert r.status_code != 401


def test_extract_requires_url_or_text(client):
    r = client.post("/api/extract", json={})
    assert r.status_code == 422


def test_rate_limit(auth_client):
    # 10 failed attempts exhaust the window; the 11th is blocked
    for _ in range(10):
        auth_client.post("/api/auth/login", json={"password": "wrong"})
    r = auth_client.post("/api/auth/login", json={"password": "wrong"})
    assert r.status_code == 429


def test_rate_limit_clears_on_success(auth_client):
    # 5 failed attempts, then a success — failures cleared
    for _ in range(5):
        auth_client.post("/api/auth/login", json={"password": "wrong"})
    auth_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    # Should be able to fail again without hitting the limit
    r = auth_client.post("/api/auth/login", json={"password": "wrong"})
    assert r.status_code == 401
