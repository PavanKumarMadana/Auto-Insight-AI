# AutoInsight AI — Task 2 Findings

Generated: 2026-10-23 12:38 India Standard Time  
Source: `Hanuai_task2_assignment.csv` (copied unchanged to `data/raw/`).

## Executive summary

The file contains 1,000 records and 20 fields, covering opening dates from 2019-08-27 through 2021-06-01. There are 0 exact duplicate rows and 0 duplicate event IDs. Audio/entertainment/navigation complaints account for 794 records across the three largest labels. The dominant coded causal label is “Module/Component-No/Incorrect Communication” (377).

## Dataset and data quality

- Missing values are concentrated in the six provided mined-entity fields: each contains values in only 5 of 1,000 rows (99.5% missing). Those labels cannot represent the complete dataset.
- One `CAUSAL_VERBATIM` and one `IN_USE_DATE` value are missing; three `CAUSAL_CD_DESC` values are missing. All 1,000 opening dates parse.
- The provided derived categorical labels have been retained unchanged. A separate cleaned narrative field and separately generated tags are included in `events_enriched.csv`.
- The greatest monthly count is 69 in 2020-02; monthly counts are descriptive and should not be read as rates because population/exposure denominators are not provided.

## EDA and text mining

The most common complaint labels are Audio (337), Other issues (263), and Communication (194). The top coded causes include incorrect communication (377), shorted module/component (237), and incorrectly registering module/component (121).

Narrative keyword extraction assigns each row to a primary grouping: Connectivity / communication: 608, Software / programming: 177, Electrical / power: 108, Radio / audio: 59, Display / screen: 45, Other / unspecified: 3. Because categories use transparent overlapping keywords and an explicit priority order, they are an exploratory index for review, not independent diagnosis. Five TF-IDF/K-means clusters are included with top terms in `cluster_summary.csv`; unsupervised clusters require engineering review before being interpreted as failure mechanisms.

## Recommendations

1. Prioritize a joint review of radio/audio communication events, module communication DTCs, and repair narratives to determine whether common software, module, or network conditions explain repeat visits.
2. Audit the 995-row gap in the supplied entity labels and backfill extraction using the same field definitions before using tags for operational dashboards.
3. Compare rates by vehicle/build cohort only after joining production and in-service denominators; the present event counts cannot identify relative risk.
4. Validate extracted tags and cluster labels with domain reviewers, then track precision/coverage before automating triage.
5. Preserve event-level traceability and investigate cases with no trouble found or reprogramming alongside confirmed part replacements.

## Limitations

The file is a 1,000-row sample with no exposure denominator and only a single model year (`MODLYR`=2020). Correlation in coded labels and text does not prove root cause. Keyword extraction can miss paraphrases and negation. The six supplied entity fields are sparsely populated. Date trends may reflect selection or reporting practices.

## Reproducibility

Run `python -m src.task2 --input data/raw/Hanuai_task2_assignment.csv --output outputs/task2`, then `python -m src.build_report`. Outputs include the row-level enriched CSV, profile, summary JSON, monthly counts, cluster terms, and charts.
