# AutoInsight AI — Task 1 Scraping and Sentiment Report

## Collection status

Selected product: Sony WH-RF400 Over-Ear Sound Isolating RF Headphones – Black. Best Buy's publicly indexed product/review page showed more than 50 reviews when assessed. The live review URL returned HTTP 403 during the bounded request attempt. The scraper stopped immediately. **Actual review records collected: 0.** No sentiment counts or customer satisfaction drivers are claimed.

## Scraping design and restrictions

`src/task1.py` accepts BestBuy.ca product URLs only, caps page attempts at 20, sets request timeouts, uses a modest delay, prefers public JSON-LD, and stops on HTTP 403/429. It fingerprints records when the public record has no stable identifier and deduplicates by that key. A parser fallback looks only for visible review-card markup. Current product review rendering is client-side or otherwise inaccessible in the returned page, and page/sort parameters need live verification if permitted access becomes available.

The assignment suggests rotating proxies and CAPTCHA bypass. Those measures are not implemented because they evade access restrictions. Appropriate responses are to stop on blocking, request permission or an authorized feed/export, reduce request frequency when access is allowed, and report what could not be collected. Retry only transient network/server failures and keep attempts bounded; do not retry a policy block.

## Analysis workflow

The separate `analyze` command can process an authorized CSV without scraping. It preserves raw title/body, normalizes whitespace and HTML entities, assigns Positive/Negative/Neutral using VADER if installed or a transparent lexical fallback otherwise, and adds keyword aspect tags. Scores are not calibrated probabilities. Both the VADER model and fallback have limitations around negation, irony, domain language, and aspect scope; evaluate against human-labeled examples before business use.

## Stakeholder use and current limitations

No product-specific findings are available because no reviews were collected. When an authorized dataset is supplied, compare rating distribution and sentiment/aspect counts, then review examples behind frequent complaints before prioritizing product changes. Tag mentions are not proof that a feature caused satisfaction or dissatisfaction. The collection target of 50 reviews was not met, so sentiment findings remain unavailable until a permitted source is provided.
