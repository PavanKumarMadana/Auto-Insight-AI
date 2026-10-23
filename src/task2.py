"""Reproducible EDA and text mining workflow for the supplied Task 2 CSV."""
from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

SEED = 42
TEXT_FIELDS = ["CAUSAL_VERBATIM", "CORRECTION_VERBATIM", "CUSTOMER_VERBATIM"]
DATE_FIELDS = ["Opened date", "BUILD_DATE", "IN_USE_DATE"]
TAG_FIELDS = ["Trigger", "Failure Component", "Failure Condition", "Additional Context", "Fix Component", "Fix Condition"]


def load_data(path: Path) -> pd.DataFrame:
    """Load as strings to retain source values and avoid guessing types."""
    df = pd.read_csv(path, dtype={"Event id": "string"})
    if "Event id" not in df:
        raise ValueError("Required identifier column 'Event id' is missing")
    return df


def parse_date(value: Any) -> pd.Timestamp | pd.NaT:
    """Parse mixed date formats without changing the original field."""
    return pd.to_datetime(value, errors="coerce", utc=True)


def tags_from_text(text: Any) -> list[str]:
    """Extract interpretable issue tags with transparent, auditable patterns."""
    if not isinstance(text, str) or not text.strip():
        return []
    t = re.sub(r"\s+", " ", text.lower())
    rules = {
        "radio/audio unit": r"\bradio\b|\baudio\b|\bspeaker\b|\bsound\b",
        "display/screen": r"\bdisplay\b|\bscreen\b|\bblack screen\b",
        "connectivity/network": r"\bwifi\b|\bwi-fi\b|\bethernet\b|\bnetwork\b|\bconnect(?:ion|ivity|ed)?\b|\bonstar\b",
        "software/programming": r"\bsoftware\b|\bprogram(?:ming|med)?\b|\bupdate\b|\breset\b|\bfirmware\b",
        "power/electrical": r"\bpower\b|\bvoltage\b|\bwiring\b|\bcircuit\b|\bshort(?:ed)?\b|\bfuse\b|\bbattery\b",
        "inoperative/intermittent": r"\binop(?:erative)?\b|\bintermitt(?:ent|ently)\b|\bcut out\b|\bnot work(?:ing)?\b|\bfailed\b",
        "diagnostic/communication": r"\bcommunication\b|\bdtc\b|\bcode\b|\bmodule\b|\bdiagnos(?:is|tic)\b",
        "replacement/repair": r"\breplac(?:e|ed|ement)\b|\brepair(?:ed)?\b|\binstall(?:ed)?\b",
    }
    return [label for label, pattern in rules.items() if re.search(pattern, t)]


def issue_category(tags: list[str]) -> str:
    """Map extracted terms to a compact issue grouping for stakeholder review."""
    if "connectivity/network" in tags or "diagnostic/communication" in tags:
        return "Connectivity / communication"
    if "power/electrical" in tags:
        return "Electrical / power"
    if "software/programming" in tags:
        return "Software / programming"
    if "display/screen" in tags:
        return "Display / screen"
    if "radio/audio unit" in tags:
        return "Radio / audio"
    if "inoperative/intermittent" in tags:
        return "Inoperative / intermittent"
    return "Other / unspecified"


def extract_array(value: Any) -> list[str]:
    """Parse the dataset's list-like entity columns safely."""
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
        return [str(x) for x in parsed] if isinstance(parsed, list) else []
    except (ValueError, SyntaxError):
        return []


def run(input_csv: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    charts = out_dir / "charts"
    charts.mkdir(exist_ok=True)
    df = load_data(input_csv)
    logging.info("Loaded %s rows x %s columns", *df.shape)
    # Preserve a source copy; derived dates and clean text are separate fields.
    source_duplicates = int(df.duplicated().sum())
    duplicate_ids = int(df["Event id"].duplicated().sum())
    profile = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "non_null": [int(df[c].notna().sum()) for c in df.columns],
        "missing": [int(df[c].isna().sum()) for c in df.columns],
        "unique_non_null": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    profile.to_csv(out_dir / "data_profile.csv", index=False)
    cleaned = df.copy()
    for col in DATE_FIELDS:
        if col in df:
            cleaned[col + "_parsed"] = df[col].map(parse_date)
    # A single analysis text field combines only the three narrative sources.
    for col in TEXT_FIELDS:
        cleaned[col + "_clean"] = df[col].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    cleaned["analysis_text"] = cleaned[[c + "_clean" for c in TEXT_FIELDS]].agg(" ".join, axis=1).str.strip()
    cleaned["extracted_tags"] = cleaned["analysis_text"].map(tags_from_text)
    cleaned["issue_category"] = cleaned["extracted_tags"].map(issue_category)
    # Report the supplied sparse labels separately from newly extracted tags.
    for col in TAG_FIELDS:
        if col in df:
            cleaned[col + "_parsed"] = df[col].map(extract_array)
    cleaned.to_csv(out_dir / "events_enriched.csv", index=False, encoding="utf-8-sig")
    # Monthly frequency is descriptive. The dataset ends mid-2021 and is not exposure-adjusted.
    opened = cleaned["Opened date_parsed"].dropna()
    month_counts = opened.dt.to_period("M").value_counts().sort_index()
    month_counts.rename_axis("month").rename("events").to_csv(out_dir / "monthly_events.csv")
    summaries = {
        "dataset": input_csv.name,
        "rows": len(df), "columns": len(df.columns), "exact_duplicate_rows": source_duplicates,
        "duplicate_event_ids": duplicate_ids,
        "date_ranges": {c: {"min": str(cleaned[c + "_parsed"].min()), "max": str(cleaned[c + "_parsed"].max()), "invalid_or_missing": int(cleaned[c + "_parsed"].isna().sum())} for c in DATE_FIELDS},
        "missing_by_column": {c: int(n) for c, n in df.isna().sum().items()},
        "category_counts": {c: df[c].fillna("(missing)").value_counts().head(20).to_dict() for c in ["MAKE", "BUILD_PLANT_DESC", "CAUSAL_CD_DESC", "COMPLAINT_CD_DESC"] if c in df},
        "issue_category_counts": cleaned["issue_category"].value_counts().to_dict(),
        "supplied_entity_non_null": {c: int(df[c].notna().sum()) for c in TAG_FIELDS if c in df},
        "text_length": {c: {"mean": float(df[c].fillna("").astype(str).str.len().mean()), "median": float(df[c].fillna("").astype(str).str.len().median()), "empty": int(df[c].fillna("").astype(str).str.strip().eq("").sum())} for c in TEXT_FIELDS},
    }
    # Cluster document vectors deterministically. Very short or blank documents stay unassigned.
    valid = cleaned["analysis_text"].str.len().ge(20)
    docs = cleaned.loc[valid, "analysis_text"]
    if len(docs) >= 4:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1200, ngram_range=(1, 2), min_df=2, max_df=0.95)
        X = vectorizer.fit_transform(docs)
        k = min(5, max(2, int(round(len(docs) ** 0.5 / 5))))
        model = KMeans(n_clusters=k, random_state=SEED, n_init=10)
        labels = model.fit_predict(X)
        cleaned["text_cluster"] = pd.NA
        cleaned.loc[valid, "text_cluster"] = labels
        terms = vectorizer.get_feature_names_out()
        cluster_rows = []
        for cl in range(k):
            center = model.cluster_centers_[cl]
            top = [terms[i] for i in center.argsort()[-10:][::-1]]
            n = int((labels == cl).sum())
            score = float(silhouette_score(X, labels, sample_size=min(500, len(docs)), random_state=SEED)) if len(set(labels)) > 1 and len(docs) > k else None
            cluster_rows.append({"cluster": cl, "records": n, "top_terms": "; ".join(top), "silhouette_sample": score})
        pd.DataFrame(cluster_rows).to_csv(out_dir / "cluster_summary.csv", index=False)
        cleaned.drop(columns=[], errors="ignore").to_csv(out_dir / "events_enriched.csv", index=False, encoding="utf-8-sig")
    summaries["cluster_count"] = k if len(docs) >= 4 else 0
    with (out_dir / "analysis_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, default=str)
    # Reproducible, simple charts from observed counts.
    for col, filename, title in [("COMPLAINT_CD_DESC", "complaints.png", "Complaint category counts"), ("CAUSAL_CD_DESC", "causal_codes.png", "Top causal codes"), ("MAKE", "make.png", "Events by make"), ("issue_category", "mined_issues.png", "Text-mined issue groupings")]:
        values = (cleaned[col] if col == "issue_category" else df[col]).fillna("(missing)").value_counts().head(12).sort_values()
        fig, ax = plt.subplots(figsize=(10, max(4, len(values) * .34)))
        values.plot.barh(ax=ax, color="#2878A5")
        ax.set_title(title); ax.set_xlabel("Events"); ax.set_ylabel(""); fig.tight_layout()
        fig.savefig(charts / filename, dpi=160); plt.close(fig)
    if len(month_counts):
        fig, ax = plt.subplots(figsize=(10, 4)); month_counts.plot(ax=ax, marker="o", color="#2878A5")
        ax.set_title("Events by opening month"); ax.set_ylabel("Events"); fig.tight_layout(); fig.savefig(charts / "monthly_events.png", dpi=160); plt.close(fig)
    return summaries


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/task2"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(json.dumps(run(args.input, args.output), indent=2, default=str))
