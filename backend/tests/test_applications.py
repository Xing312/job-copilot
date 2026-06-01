def test_list_empty(client):
    r = client.get("/api/applications")
    assert r.status_code == 200
    assert r.json() == []


def test_create_returns_201(client):
    r = client.post("/api/applications", json={"company": "Acme", "title": "Engineer"})
    assert r.status_code == 201
    data = r.json()
    assert data["company"] == "Acme"
    assert data["title"] == "Engineer"
    assert data["status"] == "Applied"
    assert "id" in data


def test_create_and_list(client):
    client.post("/api/applications", json={"company": "Acme", "title": "Eng"})
    r = client.get("/api/applications")
    assert len(r.json()) == 1


def test_create_with_optional_fields(client):
    payload = {
        "company": "Stripe",
        "title": "SWE",
        "location": "Remote",
        "work_type": "Remote",
        "platform": "Greenhouse",
        "status": "Interview",
    }
    r = client.post("/api/applications", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["location"] == "Remote"
    assert data["platform"] == "Greenhouse"
    assert data["status"] == "Interview"


def test_get_by_id(client):
    created = client.post("/api/applications", json={"company": "X", "title": "Y"}).json()
    r = client.get(f"/api/applications/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_not_found(client):
    r = client.get("/api/applications/9999")
    assert r.status_code == 404


def test_update(client):
    created = client.post("/api/applications", json={"company": "Old Co", "title": "Dev"}).json()
    r = client.put(
        f"/api/applications/{created['id']}",
        json={"company": "New Co", "title": "Dev"},
    )
    assert r.status_code == 200
    assert r.json()["company"] == "New Co"


def test_update_not_found(client):
    r = client.put("/api/applications/9999", json={"company": "X", "title": "Y"})
    assert r.status_code == 404


def test_update_status(client):
    created = client.post("/api/applications", json={"company": "X", "title": "Y"}).json()
    r = client.patch(
        f"/api/applications/{created['id']}/status",
        json={"status": "Interview"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "Interview"


def test_update_status_invalid(client):
    created = client.post("/api/applications", json={"company": "X", "title": "Y"}).json()
    r = client.patch(
        f"/api/applications/{created['id']}/status",
        json={"status": "NotAStatus"},
    )
    assert r.status_code == 422


def test_update_status_not_found(client):
    r = client.patch("/api/applications/9999/status", json={"status": "Applied"})
    assert r.status_code == 404


def test_delete(client):
    created = client.post("/api/applications", json={"company": "X", "title": "Y"}).json()
    r = client.delete(f"/api/applications/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/applications/{created['id']}").status_code == 404


def test_delete_not_found(client):
    r = client.delete("/api/applications/9999")
    assert r.status_code == 404


def test_list_multiple(client):
    client.post("/api/applications", json={"company": "Alpha", "title": "A"})
    client.post("/api/applications", json={"company": "Beta", "title": "B"})
    companies = {a["company"] for a in client.get("/api/applications").json()}
    assert companies == {"Alpha", "Beta"}
