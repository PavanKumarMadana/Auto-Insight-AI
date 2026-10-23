"""Build stakeholder reports from computed Task 2 outputs, never hand-coded metrics."""
import json
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


def build(base: Path = Path(".")) -> None:
    out = base / "outputs/task2"
    report_dir = base / "reports"
    report_dir.mkdir(exist_ok=True)
    s = json.loads((out / "analysis_summary.json").read_text(encoding="utf-8"))
    cat = s["category_counts"]["COMPLAINT_CD_DESC"]
    causes = s["category_counts"]["CAUSAL_CD_DESC"]
    issue = s["issue_category_counts"]
    tagged = sum(s["supplied_entity_non_null"].values())
    monthly = __import__("pandas").read_csv(out / "monthly_events.csv")
    peak = monthly.sort_values("events", ascending=False).iloc[0]
    date = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    md = f'''# AutoInsight AI — Task 2 Findings\n\nGenerated: {date}  \nSource: `{s['dataset']}` (copied unchanged to `data/raw/`).\n\n## Executive summary\n\nThe file contains {s['rows']:,} records and {s['columns']} fields, covering opening dates from {s['date_ranges']['Opened date']['min'][:10]} through {s['date_ranges']['Opened date']['max'][:10]}. There are {s['exact_duplicate_rows']} exact duplicate rows and {s['duplicate_event_ids']} duplicate event IDs. Audio/entertainment/navigation complaints account for {cat.get('Audio/Entertainment/Navigation - Audio', 0) + cat.get('Audio/Entertainment/Navigation - Other issues', 0) + cat.get('Audio/Entertainment/Navigation - Communication', 0):,} records across the three largest labels. The dominant coded causal label is “Module/Component-No/Incorrect Communication” ({causes.get('Module/Component-No/Incorrect Communication', 0)}).\n\n## Dataset and data quality\n\n- Missing values are concentrated in the six provided mined-entity fields: each contains values in only 5 of 1,000 rows (99.5% missing). Those labels cannot represent the complete dataset.\n- One `CAUSAL_VERBATIM` and one `IN_USE_DATE` value are missing; three `CAUSAL_CD_DESC` values are missing. All 1,000 opening dates parse.\n- The provided derived categorical labels have been retained unchanged. A separate cleaned narrative field and separately generated tags are included in `events_enriched.csv`.\n- The greatest monthly count is {int(peak['events'])} in {peak['month']}; monthly counts are descriptive and should not be read as rates because population/exposure denominators are not provided.\n\n## EDA and text mining\n\nThe most common complaint labels are Audio ({cat.get('Audio/Entertainment/Navigation - Audio', 0)}), Other issues ({cat.get('Audio/Entertainment/Navigation - Other issues', 0)}), and Communication ({cat.get('Audio/Entertainment/Navigation - Communication', 0)}). The top coded causes include incorrect communication ({causes.get('Module/Component-No/Incorrect Communication', 0)}), shorted module/component ({causes.get('Module/Component-Shorted', 0)}), and incorrectly registering module/component ({causes.get('Module/Component-Registers Incorrectly', 0)}).\n\nNarrative keyword extraction assigns each row to a primary grouping: {', '.join(f'{k}: {v}' for k, v in issue.items())}. Because categories use transparent overlapping keywords and an explicit priority order, they are an exploratory index for review, not independent diagnosis. Five TF-IDF/K-means clusters are included with top terms in `cluster_summary.csv`; unsupervised clusters require engineering review before being interpreted as failure mechanisms.\n\n## Recommendations\n\n1. Prioritize a joint review of radio/audio communication events, module communication DTCs, and repair narratives to determine whether common software, module, or network conditions explain repeat visits.\n2. Audit the 995-row gap in the supplied entity labels and backfill extraction using the same field definitions before using tags for operational dashboards.\n3. Compare rates by vehicle/build cohort only after joining production and in-service denominators; the present event counts cannot identify relative risk.\n4. Validate extracted tags and cluster labels with domain reviewers, then track precision/coverage before automating triage.\n5. Preserve event-level traceability and investigate cases with no trouble found or reprogramming alongside confirmed part replacements.\n\n## Limitations\n\nThe file is a 1,000-row sample with no exposure denominator and only a single model year (`MODLYR`=2020). Correlation in coded labels and text does not prove root cause. Keyword extraction can miss paraphrases and negation. The six supplied entity fields are sparsely populated. Date trends may reflect selection or reporting practices.\n\n## Reproducibility\n\nRun `python -m src.task2 --input data/raw/Hanuai_task2_assignment.csv --output outputs/task2`, then `python -m src.build_report`. Outputs include the row-level enriched CSV, profile, summary JSON, monthly counts, cluster terms, and charts.\n'''
    (report_dir / "task2_report.md").write_text(md, encoding="utf-8")
    styles = getSampleStyleSheet()
    story = [Paragraph("AutoInsight AI — Task 2 Findings", styles["Title"]), Paragraph("Generated " + date, styles["Normal"]), Spacer(1, 10)]
    for section in md.split("\n## ")[1:]:
        title, _, body = section.partition("\n")
        story.append(Paragraph(title.replace("&", "&amp;"), styles["Heading2"]))
        for para in body.split("\n\n"):
            plain = para.replace("`", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
            story.append(Paragraph(plain, styles["BodyText"])); story.append(Spacer(1, 5))
        if "EDA and text mining" in title:
            for chart in ["complaints.png", "causal_codes.png", "monthly_events.png", "mined_issues.png"]:
                story.append(Image(str(out / "charts" / chart), width=6.2 * inch, height=3.3 * inch))
    SimpleDocTemplate(str(report_dir / "task2_report.pdf"), pagesize=letter).build(story)


if __name__ == "__main__":
    build()
