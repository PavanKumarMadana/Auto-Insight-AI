from io import StringIO

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_dashboard_routes_use_real_project_outputs():
    for path in ["/api/health", "/api/status", "/api/options", "/api/overview", "/api/events?page=1&page_size=10", "/api/investigations", "/api/reviews", "/api/reports"]:
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)
    assert client.get("/api/status").json()["event_count"] == 1000
    assert client.get("/api/reviews").json()["total"] == 0


def test_dashboard_filters_and_event_detail_fields():
    response = client.get("/api/events", params={"make": "ThunderVolt", "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 488
    assert len(body["rows"]) == 10
    assert body["rows"][0]["Event id"]
    assert isinstance(body["rows"][0]["extracted_tags"], list)


def test_dashboard_exports_only_existing_files():
    assert client.get("/api/download/task2_report.pdf").status_code == 200
    assert client.get("/api/download/not-a-project-file.txt").status_code == 404
    exported = client.get("/api/events/export", params={"make": "ThunderVolt"})
    assert exported.status_code == 200
    assert "Event id" in exported.text
    assert len(pd.read_csv(StringIO(exported.text))) == 488
    clustered = client.get("/api/events", params={"cluster": 0, "page_size": 10}).json()
    assert clustered["total"] > 0
    assert all(int(row["text_cluster"]) == 0 for row in clustered["rows"])
