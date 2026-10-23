"""Compliant Best Buy Canada review workflow; scraping is bounded and opt-in."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

SORTS = {"Most Helpful": "HELPFUL", "Newest": "NEWEST", "Highest Rating": "HIGHEST_RATING", "Lowest Rating": "LOWEST_RATING", "Most Relevant": "RELEVANCE"}


def preprocess(value: object) -> str:
    """Normalize Unicode/HTML/whitespace while retaining punctuation and negation."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def review_id(row: dict) -> str:
    """Prefer a site identifier, otherwise use a stable content fingerprint."""
    explicit = row.get("Primary Key")
    if explicit:
        return str(explicit)
    material = "|".join(str(row.get(k, "")) for k in ("Product URL", "Reviewer Name", "Date", "Rating", "Title", "Review Text"))
    return "fp_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def sentiment(text: str) -> tuple[str, float]:
    """VADER lexicon when installed; otherwise a documented lexicon fallback."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        compound = SentimentIntensityAnalyzer().polarity_scores(text)["compound"]
    except (ImportError, LookupError):
        positive = {"love", "great", "excellent", "perfect", "easy", "beautiful", "recommend", "works", "good", "amazing", "comfortable", "fast"}
        negative = {"hate", "bad", "poor", "broken", "fail", "failed", "issue", "problem", "disappointed", "unfortunately", "waste", "return", "defective"}
        words = re.findall(r"[a-z]+", text.lower())
        score = sum(w in positive for w in words) - sum(w in negative for w in words)
        compound = score / max(1, len(words) ** .5)
        compound = max(-1.0, min(1.0, compound))
    label = "Positive" if compound >= .05 else "Negative" if compound <= -.05 else "Neutral"
    return label, float(compound)


def aspects(text: str, label: str) -> list[str]:
    """Transparent keyword aspect tags; mention and polarity are kept explicit."""
    rules = {
        "Design & Quality": r"design|build|quality|colour|color|look|feel|material",
        "Performance & Functionality": r"work|sound|picture|performance|feature|function|speed",
        "Ease of Use & Installation": r"easy|install|setup|set up|assemble|simple|interface",
        "Value for Money": r"price|value|cost|worth|cheap|expensive",
        "Reliability & Durability": r"reliable|durable|break|broken|defect|fail|lasted",
        "Battery & Power": r"battery|charge|power|hours",
        "Connectivity & Software": r"bluetooth|wifi|wi-fi|connect|app|software|update",
        "Customer Service & Support": r"support|service|warranty|return|exchange",
    }
    found = [f"{name} ({'Pos' if label == 'Positive' else 'Neg' if label == 'Negative' else 'Neu'})" for name, pattern in rules.items() if re.search(pattern, text, re.I)]
    return found or (["Satisfactory & Recommended (Pos)"] if label == "Positive" else ["Other / Unclassified"])


def scrape(product_url: str, max_pages: int = 20, delay: float = 1.5, sort: str = "Most Relevant") -> tuple[pd.DataFrame, dict]:
    """Fetch only public pages, with a strict page limit and no anti-bot evasion."""
    if urlparse(product_url).hostname not in {"bestbuy.ca", "www.bestbuy.ca"}:
        raise ValueError("Only bestbuy.ca product URLs are accepted")
    if max_pages < 1 or max_pages > 20:
        raise ValueError("max_pages must be between 1 and 20")
    session = requests.Session()
    session.headers.update({"User-Agent": "AutoInsightAI-assessment/1.0 (public review analysis)"})
    records, visited, errors = {}, [], []
    page_url = product_url.rstrip("/") + ("" if product_url.rstrip("/").endswith("/review") else "/review")
    sorts = list(SORTS) if sort == "All" else [sort]
    blocked = False
    # Best Buy may render reviews client-side. This static parser consumes visible JSON-LD/HTML only.
    for sort_name in sorts:
        for page in range(1, max_pages + 1):
            url = page_url + (f"?page={page}&sort={SORTS[sort_name]}" if page > 1 else f"?sort={SORTS[sort_name]}")
            try:
                response = session.get(url, timeout=20)
                if response.status_code in (403, 429):
                    errors.append(f"HTTP {response.status_code}; stopped to respect site restrictions")
                    blocked = True
                    break
                response.raise_for_status()
                visited.append(url)
                soup = BeautifulSoup(response.text, "html.parser")
                found = []
                for script in soup.select('script[type="application/ld+json"]'):
                    try:
                        payload = json.loads(script.string or script.get_text())
                        objs = payload if isinstance(payload, list) else [payload]
                        for obj in objs:
                            reviews = obj.get("review", []) if isinstance(obj, dict) else []
                            found.extend(reviews if isinstance(reviews, list) else [reviews])
                    except (ValueError, TypeError):
                        continue
                for card in soup.select('[data-testid*="review"], article[class*="review"], [class*="review-item"]'):
                    title = card.select_one("h2,h3,[class*=title]")
                    body = card.select_one("[class*=content],[class*=text],[class*=body]")
                    if title or body:
                        found.append({"name": title.get_text(" ", strip=True) if title else "", "reviewBody": body.get_text(" ", strip=True) if body else ""})
                if not found:
                    if page == 1:
                        errors.append(f"No public review records found for sort '{sort_name}'; client-rendered reviews may require manual inspection")
                    break
                for item in found:
                    author = item.get("author", "")
                    if isinstance(author, dict): author = author.get("name", "")
                    rating = item.get("reviewRating", {})
                    if isinstance(rating, dict): rating = rating.get("ratingValue", "")
                    date = pd.to_datetime(item.get("datePublished"), errors="coerce")
                    row = {"Primary Key": item.get("identifier", ""), "Title": preprocess(item.get("name", "")), "Review Text": preprocess(item.get("reviewBody", "")), "Date": date.strftime("%Y-%m-%d") if pd.notna(date) else "", "Rating": rating, "Source": "Best Buy Canada", "Reviewer Name": preprocess(author), "Product Name": soup.title.get_text(" ", strip=True) if soup.title else "", "Product URL": product_url, "Review Sort": sort_name}
                    if row["Title"] or row["Review Text"]:
                        row["Primary Key"] = review_id(row)
                        records[row["Primary Key"]] = row
                time.sleep(max(0.5, min(delay, 10)))
            except requests.RequestException as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                blocked = True
                break
        if blocked:
            break
    columns = ["Primary Key", "Title", "Review Text", "Date", "Rating", "Source", "Reviewer Name", "Product Name", "Product URL", "Review Sort"]
    frame = pd.DataFrame(records.values(), columns=columns)
    metadata = {"collected_at_utc": datetime.now(timezone.utc).isoformat(), "product_url": product_url, "sorts_requested": sorts, "pages_visited": visited, "unique_reviews": len(frame), "failed_requests": errors}
    return frame, metadata


def analyze(input_csv: Path, output: Path) -> pd.DataFrame:
    """Analyze saved reviews offline; never requires another scrape."""
    df = pd.read_csv(input_csv).fillna("")
    if "Review Text" not in df:
        raise ValueError("Input must contain 'Review Text'")
    title = df["Title"].astype(str) if "Title" in df else pd.Series("", index=df.index)
    df["clean_text"] = (title + " " + df["Review Text"].astype(str)).map(preprocess)
    results = df["clean_text"].map(sentiment)
    df["Sentiment"], df["Sentiment Score"] = zip(*results) if len(results) else ([], [])
    df["Aspect Tags"] = [json.dumps(aspects(t, s)) for t, s in zip(df["clean_text"], df["Sentiment"])]
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, encoding="utf-8-sig")
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scrape"); s.add_argument("--url", required=True); s.add_argument("--output", type=Path, default=Path("outputs/task1/raw_reviews.csv")); s.add_argument("--max-pages", type=int, default=20); s.add_argument("--sort", choices=[*SORTS, "All"], default="Most Relevant")
    a = sub.add_parser("analyze"); a.add_argument("--input", type=Path, default=Path("outputs/task1/raw_reviews.csv")); a.add_argument("--output", type=Path, default=Path("outputs/task1/reviews_with_sentiment.csv"))
    args = p.parse_args()
    if args.command == "scrape":
        df, meta = scrape(args.url, args.max_pages, sort=args.sort); args.output.parent.mkdir(parents=True, exist_ok=True); df.to_csv(args.output, index=False, encoding="utf-8-sig"); (args.output.parent / "scrape_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8"); print(json.dumps(meta, indent=2))
    else:
        print(f"Analyzed {len(analyze(args.input, args.output))} reviews into {args.output}")

if __name__ == "__main__": main()
