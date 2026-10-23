"""Read-only API serving the project's generated analytics and reports."""
from __future__ import annotations

import ast
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "outputs/task2/events_enriched.csv"
REVIEWS_PATH = ROOT / "outputs/task1/reviews_with_sentiment.csv"
REPORT_DIR = ROOT / "reports"
ANNOTATION_COLUMNS = ["Trigger", "Failure Component", "Failure Condition", "Additional Context", "Fix Component", "Fix Condition"]
app = FastAPI(title="AutoInsight AI API", version="1.0.0")
def configured_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


app.add_middleware(CORSMiddleware, allow_origins=configured_origins(), allow_methods=["GET"], allow_headers=["*"])


def load_events() -> pd.DataFrame:
    if not EVENTS_PATH.exists():
        raise HTTPException(503, "Task 2 output is missing. Run the Task 2 pipeline first.")
    df = pd.read_csv(EVENTS_PATH, dtype={"Event id": "string"}).fillna("")
    for c in ["Opened date_parsed", "BUILD_DATE_parsed", "IN_USE_DATE_parsed"]:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    return df


def parse_list(value: Any) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    try:
        item = ast.literal_eval(value)
        return [str(x) for x in item] if isinstance(item, (list, tuple)) else []
    except (ValueError, SyntaxError):
        return []


def records_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    list_cols = ["extracted_tags", "Failure Component_parsed", "Failure Condition_parsed", "Fix Component_parsed", "Fix Condition_parsed"]
    for col in list_cols:
        if col in out:
            out[col] = out[col].map(parse_list)
    for col in ["Opened date_parsed", "BUILD_DATE_parsed", "IN_USE_DATE_parsed"]:
        if col in out:
            out[col] = out[col].map(lambda x: x.isoformat() if pd.notna(x) else None)
    return out.astype(object).where(pd.notna(out), None)


def filter_df(df: pd.DataFrame, date_from: str | None = None, date_to: str | None = None, make: str | None = None, model: str | None = None, plant: str | None = None, category: str | None = None) -> pd.DataFrame:
    if date_from:
        start = pd.to_datetime(date_from, errors="coerce", utc=True)
        if pd.notna(start): df = df[df["Opened date_parsed"] >= start]
    if date_to:
        end = pd.to_datetime(date_to, errors="coerce", utc=True) + pd.Timedelta(days=1)
        if pd.notna(end): df = df[df["Opened date_parsed"] < end]
    for col, val in [("MAKE", make), ("MODEL", model), ("BUILD_PLANT_DESC", plant), ("issue_category", category)]:
        if val: df = df[df[col].astype(str) == val]
    return df


def count_series(df: pd.DataFrame, column: str, limit: int = 12) -> list[dict[str, Any]]:
    if column not in df: return []
    values = df[column].replace("", "Not recorded").value_counts().head(limit)
    return [{"label": str(k), "count": int(v)} for k, v in values.items()]


def monthly_counts(source: pd.DataFrame, df: pd.DataFrame, date_from: str | None, date_to: str | None) -> list[dict[str, Any]]:
    """Return a continuous month axis, with zeroes for months lacking filtered records."""
    source_dates = source["Opened date_parsed"].dropna()
    if source_dates.empty:
        return []

    first_month = source_dates.min().strftime("%Y-%m")
    last_month = source_dates.max().strftime("%Y-%m")
    start = pd.to_datetime(date_from, errors="coerce", utc=True) if date_from else pd.NaT
    end = pd.to_datetime(date_to, errors="coerce", utc=True) if date_to else pd.NaT
    first_month = max(first_month, start.strftime("%Y-%m") if pd.notna(start) else first_month)
    last_month = min(last_month, end.strftime("%Y-%m") if pd.notna(end) else last_month)
    if first_month > last_month:
        return []

    periods = pd.period_range(start=first_month, end=last_month, freq="M")
    observed = df["Opened date_parsed"].dropna().dt.strftime("%Y-%m").value_counts()
    return [{"month": str(month), "events": int(observed.get(str(month), 0))} for month in periods]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AutoInsight AI", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/health", include_in_schema=False)
def render_health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    df = load_events()
    reviews = pd.read_csv(REVIEWS_PATH) if REVIEWS_PATH.exists() else pd.DataFrame()
    metadata_path = ROOT / "outputs/task1/scrape_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    newest = max((p.stat().st_mtime for p in [EVENTS_PATH, REVIEWS_PATH] if p.exists()), default=0)
    return {"event_count": len(df), "review_count": len(reviews), "last_refresh": datetime.fromtimestamp(newest, timezone.utc).isoformat() if newest else None, "review_collection": metadata, "dataset": EVENTS_PATH.name}


@app.get("/api/options")
def options():
    df = load_events()
    result = {}
    for key, col in [("makes", "MAKE"), ("models", "MODEL"), ("plants", "BUILD_PLANT_DESC"), ("categories", "issue_category")]:
        result[key] = sorted(str(x) for x in df[col].dropna().unique() if str(x).strip()) if col in df else []
    dates = df["Opened date_parsed"].dropna()
    result["date_min"] = dates.min().date().isoformat() if not dates.empty else None
    result["date_max"] = dates.max().date().isoformat() if not dates.empty else None
    return result


@app.get("/api/overview")
def overview(date_from: str | None = None, date_to: str | None = None, make: str | None = None, model: str | None = None, plant: str | None = None, category: str | None = None):
    source = load_events()
    df = filter_df(source, date_from, date_to, make, model, plant, category)
    components = df["Failure Component_parsed"].map(parse_list).explode().dropna() if "Failure Component_parsed" in df else pd.Series(dtype=str)
    conditions = df["Failure Condition_parsed"].map(parse_list).explode().dropna() if "Failure Condition_parsed" in df else pd.Series(dtype=str)
    fixes = df["Fix Condition_parsed"].map(parse_list).explode().dropna() if "Fix Condition_parsed" in df else pd.Series(dtype=str)
    combinations: list[str] = []
    if "Failure Component_parsed" in df and "Failure Condition_parsed" in df:
        for _, row in df[["Failure Component_parsed", "Failure Condition_parsed"]].iterrows():
            parts, states = parse_list(row["Failure Component_parsed"]), parse_list(row["Failure Condition_parsed"])
            combinations.extend([f"{part} · {state}" for part, state in zip(parts, states)])
    comp_counts = components.value_counts().head(12)
    cond_counts = conditions.value_counts().head(10)
    annotation_counts = {col: int(df[col].map(lambda value: bool(parse_list(value))).sum()) for col in ANNOTATION_COLUMNS if col in df}
    has_annotations = df[[col for col in ANNOTATION_COLUMNS if col in df]].apply(lambda col: col.map(lambda value: bool(parse_list(value)))).any(axis=1) if any(col in df for col in ANNOTATION_COLUMNS) else pd.Series(False, index=df.index)
    component_condition_records = int((df.get("Failure Component_parsed", pd.Series(False, index=df.index)).map(lambda value: bool(parse_list(value))) & df.get("Failure Condition_parsed", pd.Series(False, index=df.index)).map(lambda value: bool(parse_list(value)))).sum())
    model_years = sorted({str(int(value)) for value in pd.to_numeric(df.get("MODLYR", pd.Series(dtype=float)), errors="coerce").dropna().unique()})
    summary = {"total_events": len(df), "unique_event_ids": int(df["Event id"].nunique()), "distinct_components": int(components.nunique()), "distinct_categories": int(df["issue_category"].nunique()), "distinct_causal_codes": int(df["CAUSAL_CD_DESC"].replace("", pd.NA).nunique()), "distinct_complaint_codes": int(df["COMPLAINT_CD_DESC"].replace("", pd.NA).nunique()), "annotated_records": int(has_annotations.sum()), "annotation_field_counts": annotation_counts, "component_condition_records": component_condition_records, "distinct_plants": int(df["BUILD_PLANT_DESC"].replace("", pd.NA).nunique()), "model_years": model_years, "denominator": len(df)}
    recent = df.sort_values("Opened date_parsed", ascending=False).head(8)
    return {"summary": summary, "monthly": monthly_counts(source, df, date_from, date_to), "complaints": count_series(df, "COMPLAINT_CD_DESC"), "causes": count_series(df, "CAUSAL_CD_DESC"), "issues": count_series(df, "issue_category"), "makes": count_series(df, "MAKE"), "models": count_series(df, "MODEL"), "plants": count_series(df, "BUILD_PLANT_DESC", limit=100), "components": [{"label": str(k), "count": int(v)} for k, v in comp_counts.items()], "conditions": [{"label": str(k), "count": int(v)} for k, v in cond_counts.items()], "fixes": [{"label": str(k), "count": int(v)} for k, v in fixes.value_counts().head(10).items()], "combinations": [{"label": str(k), "count": int(v)} for k, v in pd.Series(combinations).value_counts().head(10).items()], "recent": records_frame(recent).to_dict(orient="records")}


@app.get("/api/events")
def events(q: str = "", category: str = "", make: str = "", model: str = "", plant: str = "", cluster: int | None = None, date_from: str | None = None, date_to: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=10, le=100), sort_by: str = "Opened date_parsed", sort_dir: str = "desc"):
    df = filter_df(load_events(), date_from, date_to, make or None, model or None, plant or None, category or None)
    if cluster is not None:
        df = df[pd.to_numeric(df["text_cluster"], errors="coerce") == cluster]
    if q.strip():
        mask = df.select_dtypes(include=["object", "string"]).fillna("").astype(str).apply(lambda c: c.str.contains(q.strip(), case=False, regex=False)).any(axis=1)
        df = df[mask]
    allowed = set(df.columns)
    if sort_by not in allowed: sort_by = "Opened date_parsed"
    df = df.sort_values(sort_by, ascending=sort_dir.lower() == "asc", na_position="last")
    total = len(df)
    start = (page - 1) * page_size
    return {"rows": records_frame(df.iloc[start:start + page_size]).to_dict(orient="records"), "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@app.get("/api/events/export")
def export_events(q: str = "", category: str = "", make: str = "", model: str = "", plant: str = "", cluster: int | None = None, date_from: str | None = None, date_to: str | None = None):
    df = filter_df(load_events(), date_from, date_to, make or None, model or None, plant or None, category or None)
    if cluster is not None:
        df = df[pd.to_numeric(df["text_cluster"], errors="coerce") == cluster]
    if q.strip():
        mask = df.select_dtypes(include=["object", "string"]).fillna("").astype(str).apply(lambda c: c.str.contains(q.strip(), case=False, regex=False)).any(axis=1)
        df = df[mask]
    content = df.to_csv(index=False, encoding="utf-8-sig")
    return StreamingResponse(io.StringIO(content), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=autoinsight-filtered-events.csv"})


@app.get("/api/investigations")
def investigations():
    df = load_events()
    output = []
    for category, group in df.groupby("issue_category", dropna=False):
        sample_cols = [c for c in ["Event id", "CAUSAL_VERBATIM", "CUSTOMER_VERBATIM", "CAUSAL_CD_DESC", "Fix Component", "Fix Condition", "MODEL", "BUILD_PLANT_DESC"] if c in group]
        samples = group[sample_cols].head(3).fillna("").to_dict(orient="records")
        output.append({"category": str(category), "count": len(group), "denominator": len(df), "share": len(group) / len(df) if len(df) else 0, "evidence": "Observed keyword grouping", "hypothesis": "This grouping may help prioritize a review of related records; it does not establish a causal mechanism.", "samples": samples, "causes": count_series(group, "CAUSAL_CD_DESC", 5), "fixes": count_series(group, "Fix Condition", 5)})
    cluster_path = ROOT / "outputs/task2/cluster_summary.csv"
    clusters = pd.read_csv(cluster_path).fillna("").to_dict(orient="records") if cluster_path.exists() else []
    return {"denominator": len(df), "findings": sorted(output, key=lambda x: x["count"], reverse=True), "clusters": clusters}


@app.get("/api/reviews")
def reviews(q: str = "", sentiment: str = "", aspect: str = ""):
    if not REVIEWS_PATH.exists(): return {"rows": [], "total": 0, "available": False}
    df = pd.read_csv(REVIEWS_PATH).fillna("")
    if sentiment: df = df[df.get("Sentiment", "") == sentiment]
    if q:
        mask = df.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)
        df = df[mask]
    if aspect:
        df = df[df.get("Aspect Tags", "").astype(str).str.contains(aspect, case=False, regex=False)]
    return {"rows": df.to_dict(orient="records"), "total": len(df), "available": len(df) > 0}


@app.get("/api/reports")
def reports():
    files = []
    candidates = [ROOT / "reports/task1_report.md", ROOT / "reports/task2_report.md", ROOT / "reports/task2_report.pdf", ROOT / "outputs/task2/events_enriched.csv", ROOT / "outputs/task2/data_profile.csv", ROOT / "outputs/task2/cluster_summary.csv", ROOT / "outputs/task2/monthly_events.csv", ROOT / "outputs/task1/reviews_with_sentiment.csv"]
    descriptions = {"task1_report.md": "Review collection status, access limits, and sentiment methodology", "task2_report.md": "Stakeholder findings and analytical limitations", "task2_report.pdf": "Printable Task 2 findings with charts", "events_enriched.csv": "Event-level source records with derived tags and clusters", "data_profile.csv": "Column types, missingness, and cardinality", "cluster_summary.csv": "TF-IDF cluster terms and record counts", "monthly_events.csv": "Events by opening month", "reviews_with_sentiment.csv": "Task 1 sentiment output; currently no collected reviews"}
    for p in candidates:
        if p.exists():
            files.append({"name": p.name, "path": "/api/download/" + p.name, "bytes": p.stat().st_size, "updated": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(), "description": descriptions.get(p.name, "Generated project output")})
    return {"files": files}


@app.get("/api/download/{filename}")
def download(filename: str):
    allowed = {"task1_report.md": ROOT / "reports/task1_report.md", "task2_report.md": ROOT / "reports/task2_report.md", "task2_report.pdf": ROOT / "reports/task2_report.pdf", "events_enriched.csv": ROOT / "outputs/task2/events_enriched.csv", "data_profile.csv": ROOT / "outputs/task2/data_profile.csv", "cluster_summary.csv": ROOT / "outputs/task2/cluster_summary.csv", "monthly_events.csv": ROOT / "outputs/task2/monthly_events.csv", "reviews_with_sentiment.csv": REVIEWS_PATH}
    path = allowed.get(filename)
    if not path or not path.exists(): raise HTTPException(404, "File not available")
    return FileResponse(path, filename=filename)
