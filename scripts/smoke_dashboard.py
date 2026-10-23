"""Smoke-check the locally running UI and its real-data API."""
from __future__ import annotations

import json
from urllib.request import urlopen


def get(url: str):
    with urlopen(url, timeout=10) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


ui = "http://127.0.0.1:5173"
api = "http://127.0.0.1:8000"
for route in ["/", "/failures", "/root-causes", "/explorer", "/sentiment", "/reports"]:
    code, content_type, _ = get(ui + route)
    assert code == 200 and "text/html" in content_type
    print(f"UI route {route}: {code}")

status, _, body = get(api + "/api/status")
assert status == 200
status_data = json.loads(body)
assert status_data["event_count"] == 1000
print(f"Data status: {status_data['event_count']} source events, {status_data['review_count']} reviews")

_, _, overview_body = get(api + "/api/overview")
overview = json.loads(overview_body)
assert overview["summary"]["total_events"] == 1000
print(f"Overview: {len(overview['monthly'])} monthly points, {len(overview['issues'])} mined categories")

_, _, filtered_body = get(api + "/api/events?make=ThunderVolt&page_size=10")
filtered = json.loads(filtered_body)
assert filtered["total"] == 488 and len(filtered["rows"]) == 10
print("Event filters and pagination: 488 make-filtered records, 10 returned on page 1")

_, _, cluster_body = get(api + "/api/events?cluster=0&page_size=10")
cluster = json.loads(cluster_body)
assert cluster["total"] > 0
print(f"Cluster drill-down: {cluster['total']} records in cluster 1")

_, _, export_body = get(api + "/api/events/export?make=ThunderVolt")
assert export_body.count(b"Event id") == 1 and len(export_body) > 1000
print("Filtered CSV export: available")

_, _, report_body = get(api + "/api/reports")
reports = json.loads(report_body)["files"]
assert any(f["name"] == "task2_report.pdf" for f in reports)
print(f"Reports: {len(reports)} existing files available for download")
