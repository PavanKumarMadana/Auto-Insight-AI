# HanuAi ML Assessment

AutoInsight AI is an intelligent analytics platform for automotive quality insights, combining NLP based sentiment analysis, exploratory data analysis, text mining, failure classification, clustering, and evidence based root cause investigation.

This project implements the supplied two task assessment. The source CSV is preserved at `data/raw/Hanuai_task2_assignment.csv`; derived files are written under `outputs/` and reports under `reports/`.

## Contents

- `src/task1.py`: bounded public-page scraper and offline review sentiment/aspect analysis.
- `src/task2.py`: data validation/profile, date and narrative preprocessing, transparent keyword tags, issue grouping, TF-IDF/K-means clustering, charts, and row-level enriched data.
- `src/build_report.py`: Task 2 Markdown and PDF stakeholder reports.
- `notebooks/`: executable Task 1 and Task 2 notebooks.
- `tests/`: lightweight checks for parsing and transform behavior.
- `outputs/task1/`: scrape metadata and review outputs (currently no reviews were collected).
- `outputs/task2/`: profile, enriched records, cluster terms, monthly counts, summary JSON, and charts.

## Setup

Python 3.10+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The project ran with Python 3.12. Available libraries were installed into the active Python environment during implementation.

## Task 2: run analysis

```powershell
python -m src.task2 --input data/raw/Hanuai_task2_assignment.csv --output outputs/task2
python -m src.build_report
```

The output `events_enriched.csv` retains all raw fields and adds parsed dates, separate whitespace-normalized narrative columns, combined analysis text, extracted tags, issue group, parsed versions of provided entity lists, and cluster labels. Dates that cannot be parsed remain `NaT`; missing source values remain missing in their original columns. See `reports/task2_report.md` for the evidence-based analysis and caveats.

## Task 1: scrape and analyze reviews

The selected product for the attempt was the Sony WH-RF400 headphones, whose Best Buy page was publicly indexed with more than 50 reviews at the time of research. The direct request to the review page returned HTTP 403. The scraper stopped immediately, as required by the site's access restriction; it did not try proxies, CAPTCHA bypass, stealth, or authentication. Accordingly the raw file has a header only and no sentiment findings are reported.

If the product's review page is available through permitted public access, run:

```powershell
python -m src.task1 scrape --url "https://www.bestbuy.ca/en-ca/product/..." --max-pages 10 --sort "Most Relevant"
# Request all five sort orders in one run and deduplicate across responses
python -m src.task1 scrape --url "https://www.bestbuy.ca/en-ca/product/..." --max-pages 10 --sort "All"
python -m src.task1 analyze --input outputs/task1/raw_reviews.csv
```

Current scraping uses public JSON-LD or conservatively detected visible review cards and bounded `page` requests. Best Buy currently serves reviews client-side and may change routes/markup, so review pagination, sort values, and parsing need to be revalidated against a permitted live page before production use. Supported sort choices: `Most Helpful`, `Newest`, `Highest Rating`, `Lowest Rating`, and `Most Relevant`; `All` attempts each until access is denied. A successful response is not assumed to mean all filters were honored. If denied, stop, document the status, or use a review export obtained with permission.

Sentiment uses VADER when installed; otherwise a small documented lexical scoring fallback is used. The fallback is for demonstration and is not calibrated, context-aware, or a substitute for validating a model against labeled data. Sentiment scores are not probabilities. Aspect tagging uses transparent keyword rules; each tag is a text mention plus coarse review polarity, not a validated aspect model.

## Notebooks and QA

Open notebooks from the repository root or adjust paths to the notebook directory. Run them with Jupyter or:

```powershell
jupyter nbconvert --to notebook --execute notebooks/task2_advanced_eda_text_mining.ipynb --output task2_executed.ipynb
jupyter nbconvert --to notebook --execute notebooks/task1_bestbuy_reviews.ipynb --output task1_executed.ipynb
python -m pytest -q
```

## AutoInsight AI web dashboard

The React/TypeScript dashboard is in `ui/`; the read-only FastAPI adapter is in `backend/app.py`. The API reads the current generated CSV/report files from this repository, paginates event records, filters them by actual date/make/model/plant/category values, and only serves explicitly allowed files. The UI does not reimplement the Task 2 analysis. It presents API summaries, supports record drill-down and current-page CSV export, and shows the Task 1 access block rather than inventing reviews.

Run the complete local application from PowerShell:

```powershell
cd ui
npm install
npm run dev:full
```

Open **http://127.0.0.1:5173**. `dev:full` starts Vite and the local API on port 8000 together. To update the source outputs before launch, run the Task 2 commands above. Production frontend assets can be built with `cd ui; npm run build`; the API is local and read-only, with CORS limited to the Vite localhost origins.

The application includes Overview, Failure analytics, Root cause intelligence, Data explorer, Sentiment intelligence, and Reports & exports. Event counts are not presented as failure rates because no exposure denominator exists. The entity-derived component and condition charts are explicitly marked sparse because those fields are populated on only five source records. Review sentiment remains empty because the public review request returned HTTP 403.

## Production build and API

Build the production frontend with:

```powershell
cd ui
npm ci
npm run build
```

Run the API from the repository root with:

```powershell
python -m pip install -r requirements-api.txt
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

The API serves `/health` for platform health checks and `/api/health` for application status. It is read-only and loads the committed Task 2 output. The production frontend uses `VITE_API_BASE_URL` as the API origin; leave it unset for the local Vite proxy. The API uses `CORS_ORIGINS`, a comma-separated list of allowed browser origins. Local development defaults to `http://localhost:5173,http://127.0.0.1:5173`.

## Render deployment

The root `render.yaml` defines two services in a Render Blueprint:

- **`autoinsight-dashboard`** is a Static Site. Render runs `cd ui && npm ci && npm run build`, publishes `ui/dist`, and rewrites unknown paths to `index.html` for React Router refreshes.
- **`autoinsight-api`** is a Python Web Service. Render installs `requirements-api.txt`, starts Uvicorn on `0.0.0.0:$PORT`, and checks `/health`. The service reads the CSVs/reports included in the repository.

In Render, create a **New Blueprint Instance** and connect this GitHub repository. Review the two services and apply the Blueprint. The Blueprint wires `VITE_API_BASE_URL` to the API's Render URL and `CORS_ORIGINS` to the dashboard's Render URL. No API keys, database, or manually supplied secret variables are required for the current app. If using a custom dashboard domain, add its origin to `CORS_ORIGINS`; if changing the API domain, update `VITE_API_BASE_URL` and redeploy the static site.

The API is configured on Render's free plan. Free web services can spin down when idle, so the first request after inactivity can take longer. Its filesystem is ephemeral; this application only reads committed data and has no persistent user uploads. New analytics outputs must be regenerated locally and committed, then deployed. Use a paid persistent service or external storage before adding runtime writes that must survive restarts.

For local API plus frontend development, `npm run dev:full` from `ui/` starts both processes. For frontend-only production preview, run `npm run preview` after building; configure `VITE_API_BASE_URL` to a reachable API origin.

## Findings at a glance

- 1,000 rows, 20 columns; zero exact duplicate rows and zero duplicate event IDs.
- `Opened date` spans 2019-08-27 to 2021-06-01; one missing `IN_USE_DATE`, one missing causal narrative, and three missing causal codes.
- Provided mined entity fields are each populated for only 5 records (995 missing each).
- Top complaint codes are Audio (337), Other issues (263), and Communication (194); top causal code is incorrect module/component communication (377).
- Keyword extraction assigns 608 records to connectivity/communication; the report cautions that these exploratory tags are not root cause findings.

## Responsible scraping and limitations

The assessment mentions proxy rotation and CAPTCHA bypass as possible anti-scraping responses. This implementation instead follows public access boundaries: bounded requests, ordinary delays, stop-on-403/429, and no evasion. Seek permission, use official/authorized exports or APIs, or provide the analysis with already collected lawful data. Dataset limitations include one model year, a sample with no population/exposure denominator, sparse supplied entity annotations, and text-mining rules that need human validation.

## Submission checklist

- [x] Task 1 script and notebook
- [x] Task 2 script and notebook
- [x] Preserved input dataset copy
- [x] Task 2 enriched CSV, profile, cluster summary, counts, charts, and Markdown/PDF report
- [ ] Task 1 review CSV with 50+ actual public reviews (not achieved because of HTTP 403)
- [ ] Validated Task 1 sentiment findings based on actual reviews (blocked by no collected reviews)
