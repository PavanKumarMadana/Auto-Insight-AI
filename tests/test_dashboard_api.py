import json
from collections import Counter
from io import StringIO
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import app
from src.task2 import extract_array, issue_category, parse_date, tags_from_text

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


def test_overview_kpis_categories_and_months_match_source_and_outputs():
    root = Path(__file__).resolve().parents[1]
    source = pd.read_csv(root / "data/raw/Hanuai_task2_assignment.csv", dtype=str).fillna("")
    enriched = pd.read_csv(root / "outputs/task2/events_enriched.csv", dtype=str).fillna("")
    summary_output = json.loads((root / "outputs/task2/analysis_summary.json").read_text(encoding="utf-8"))
    monthly_output = pd.read_csv(root / "outputs/task2/monthly_events.csv", dtype={"month": str})

    assert len(source) == 1000
    assert source["Event id"].is_unique
    assert source.equals(enriched[source.columns])

    expected_categories = Counter(
        issue_category(tags_from_text(" ".join(row[column] for column in ["CAUSAL_VERBATIM", "CORRECTION_VERBATIM", "CUSTOMER_VERBATIM"])))
        for _, row in source.iterrows()
    )
    expected_months = (
        source["Opened date"].map(parse_date).dropna().dt.strftime("%Y-%m").value_counts().sort_index().to_dict()
    )
    api = client.get("/api/overview").json()
    options = client.get("/api/options").json()
    actual_categories = {item["label"]: item["count"] for item in api["issues"]}
    actual_months = {item["month"]: item["events"] for item in api["monthly"]}

    assert api["summary"]["total_events"] == len(source) == 1000
    opened_dates = source["Opened date"].map(parse_date)
    assert opened_dates.min().date().isoformat() == "2019-08-27"
    assert opened_dates.max().date().isoformat() == "2021-06-01"
    assert options["date_min"] == opened_dates.min().date().isoformat()
    assert options["date_max"] == opened_dates.max().date().isoformat()
    assert api["summary"]["unique_event_ids"] == source["Event id"].nunique() == 1000
    assert api["summary"]["distinct_categories"] == len(expected_categories) == 6
    assert api["summary"]["distinct_complaint_codes"] == source["COMPLAINT_CD_DESC"].nunique()
    assert actual_categories == dict(expected_categories) == summary_output["issue_category_counts"]
    assert actual_categories["Connectivity / communication"] == 608
    assert actual_categories["Connectivity / communication"] / len(source) == 0.608

    output_months = dict(zip(monthly_output["month"], monthly_output["events"]))
    assert len(expected_months) == len(actual_months) == 23
    assert actual_months == expected_months == output_months
    assert sum(actual_months.values()) == len(source)

    entity_fields = ["Trigger", "Failure Component", "Failure Condition", "Additional Context", "Fix Component", "Fix Condition"]
    expected_annotation_counts = {field: sum(bool(extract_array(value)) for value in source[field]) for field in entity_fields}
    expected_annotated_records = sum(any(bool(extract_array(row[field])) for field in entity_fields) for _, row in source.iterrows())
    expected_component_condition_records = sum(bool(extract_array(row["Failure Component"])) and bool(extract_array(row["Failure Condition"])) for _, row in source.iterrows())
    assert api["summary"]["annotation_field_counts"] == expected_annotation_counts
    assert api["summary"]["annotated_records"] == expected_annotated_records == 5
    assert api["summary"]["component_condition_records"] == expected_component_condition_records == 5
    assert all(count == 5 for count in expected_annotation_counts.values())
    assert all(len(extract_array(value)) for field in entity_fields for value in source[field] if value)

    expected_components = {value for item in source["Failure Component"] for value in extract_array(item)}
    assert api["summary"]["distinct_components"] == len(expected_components)
    assert api["summary"]["distinct_causal_codes"] == source["CAUSAL_CD_DESC"].replace("", pd.NA).nunique()
    assert api["summary"]["distinct_plants"] == source["BUILD_PLANT_DESC"].nunique()
    assert api["summary"]["model_years"] == ["2020"]

    displayed_ids = []
    displayed_rows = []
    for page in range(1, 11):
        response = client.get("/api/events", params={"page": page, "page_size": 100})
        assert response.status_code == 200
        page_rows = response.json()["rows"]
        displayed_rows.extend(page_rows)
        displayed_ids.extend(row["Event id"] for row in page_rows)
    assert len(displayed_ids) == len(source)
    assert set(displayed_ids) == set(source["Event id"])
    source_by_id = source.set_index("Event id").to_dict(orient="index")
    for row in displayed_rows:
        expected = source_by_id[row["Event id"]]
        for column in source.columns:
            actual = row[column]
            expected_value = row["Event id"] if column == "Event id" else expected[column]
            assert ("" if actual is None else str(actual)) == expected_value, (row["Event id"], column)


def test_dashboard_filters_match_source_individually_and_combined_and_reset():
    root = Path(__file__).resolve().parents[1]
    source = pd.read_csv(root / "outputs/task2/events_enriched.csv", dtype={"Event id": str}).fillna("")
    source["Opened date_parsed"] = pd.to_datetime(source["Opened date_parsed"], errors="coerce", utc=True)
    sample = source.iloc[0]
    filter_cases = [
        {"date_from": "2020-03-01", "date_to": "2020-08-31"},
        {"make": "ThunderVolt"},
        {"model": str(source["MODEL"].iloc[0])},
        {"plant": str(source["BUILD_PLANT_DESC"].iloc[0])},
        {"category": str(source["issue_category"].iloc[0])},
        {
            "date_from": str(pd.Timestamp(sample["Opened date_parsed"]).date()),
            "date_to": str(pd.Timestamp(sample["Opened date_parsed"]).date()),
            "make": str(sample["MAKE"]),
            "model": str(sample["MODEL"]),
            "plant": str(sample["BUILD_PLANT_DESC"]),
            "category": str(sample["issue_category"]),
        },
    ]
    columns = {"make": "MAKE", "model": "MODEL", "plant": "BUILD_PLANT_DESC", "category": "issue_category"}
    for params in filter_cases:
        expected = source
        if params.get("date_from"):
            expected = expected[expected["Opened date_parsed"] >= pd.Timestamp(params["date_from"], tz="UTC")]
        if params.get("date_to"):
            expected = expected[expected["Opened date_parsed"] < pd.Timestamp(params["date_to"], tz="UTC") + pd.Timedelta(days=1)]
        for key, column in columns.items():
            if params.get(key):
                expected = expected[expected[column].astype(str) == params[key]]

        overview = client.get("/api/overview", params=params).json()
        events = client.get("/api/events", params={**params, "page_size": 100}).json()
        assert overview["summary"]["total_events"] == events["total"] == len(expected), params
        assert sum(month["events"] for month in overview["monthly"]) == len(expected), params

    # A no-parameter request is the API state restored when the six UI filters reset.
    reset = client.get("/api/overview").json()
    assert reset["summary"]["total_events"] == 1000
    assert client.get("/api/events", params={"page": 1, "page_size": 100}).json()["total"] == 1000


def test_filtered_month_axis_includes_zero_count_months_and_date_window():
    all_months = client.get("/api/overview").json()["monthly"]
    filtered = client.get("/api/overview", params={"make": "NebulaCruiser"}).json()["monthly"]
    assert [item["month"] for item in filtered] == [item["month"] for item in all_months]
    assert filtered[0]["events"] == 0
    assert filtered[-1]["events"] == 0

    date_window = client.get("/api/overview", params={"date_from": "2020-03-01", "date_to": "2020-08-31"}).json()["monthly"]
    assert [item["month"] for item in date_window] == ["2020-03", "2020-04", "2020-05", "2020-06", "2020-07", "2020-08"]
