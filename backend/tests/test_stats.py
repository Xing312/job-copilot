def _post(client, company, title, **kwargs):
    payload = {"company": company, "title": title, **kwargs}
    return client.post("/api/applications", json=payload).json()


def test_stats_empty(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["offers"] == 0
    assert data["interviews"] == 0
    assert data["response_rate"] == 0
    assert data["by_status"] == []
    assert len(data["by_week"]) == 12


def test_stats_totals(client):
    for company, status in [
        ("A", "Applied"),
        ("B", "Interview"),
        ("C", "Offer"),
        ("D", "Rejected"),
        ("E", "Ghosted"),
    ]:
        _post(client, company, "Eng", status=status)

    data = client.get("/api/stats").json()
    assert data["total"] == 5
    assert data["offers"] == 1
    assert data["interviews"] == 1
    # responded = Interview + Offer + Rejected = 3 / 5 = 60.0
    assert data["response_rate"] == 60.0


def test_stats_by_status_canonical_order(client):
    for status in ["Offer", "Applied", "OA"]:
        _post(client, "X", "Y", status=status)

    names = [s["name"] for s in client.get("/api/stats").json()["by_status"]]
    assert names == ["Applied", "OA", "Offer"]


def test_stats_excludes_zero_statuses(client):
    _post(client, "X", "Y", status="Applied")

    by_status = client.get("/api/stats").json()["by_status"]
    # Only Applied should appear — all others have value 0
    assert len(by_status) == 1
    assert by_status[0]["name"] == "Applied"


def test_stats_by_platform(client):
    for platform in ["Greenhouse", "Greenhouse", "LinkedIn"]:
        _post(client, "X", "Y", platform=platform)

    by_platform = {p["name"]: p["value"] for p in client.get("/api/stats").json()["by_platform"]}
    assert by_platform["Greenhouse"] == 2
    assert by_platform["LinkedIn"] == 1


def test_stats_by_work_type(client):
    for work_type in ["Remote", "Hybrid", "Remote"]:
        _post(client, "X", "Y", work_type=work_type)

    by_work_type = {p["name"]: p["value"] for p in client.get("/api/stats").json()["by_work_type"]}
    assert by_work_type["Remote"] == 2
    assert by_work_type["Hybrid"] == 1


def test_stats_by_week_always_12_entries(client):
    _post(client, "X", "Y", applied_date="2026-05-01")
    assert len(client.get("/api/stats").json()["by_week"]) == 12
