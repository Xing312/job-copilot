"""
Test whether live_no_keywords URLs can be recovered via Jina.

These URLs returned HTTP 200 but had no job keywords in the first 8 KB,
suggesting they are JavaScript-rendered SPAs whose content is invisible
to a plain requests.get() call.

Steps:
1. Load CSV and run the same HTTP check as test_training_urls.py
2. Isolate the live_no_keywords batch
3. Run Jina on all of them (concurrent, rate-limited)
4. Report how many are recoverable and from which platforms
5. Save a combined candidate list (live + recovered) to JSON for the
   next step: building the actual training corpus

Usage:
  python scripts/test_spa_urls.py
"""

import csv
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

CSV_PATH = Path(__file__).parent.parent / "Copy of JOB APPLICATION TEMPLATE - Tracking Template.csv"
OUT_PATH = Path(__file__).parent / "training_candidates.json"

HTTP_CONCURRENCY = 20
JINA_CONCURRENCY = 2   # keep very low to avoid Jina rate limits
HTTP_TIMEOUT = 10
JINA_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

JOB_KEYWORDS = re.compile(
    r'\b(responsibilities|qualifications|requirements|apply|job description'
    r'|about the role|what you.ll do|minimum qualifications)\b',
    re.IGNORECASE,
)

ROLE_NOISE = re.compile(r'\n.*', re.DOTALL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_domain(url: str) -> str:
    try:
        parts = urlparse(url).netloc.lower().split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else parts[0]
    except Exception:
        return "unknown"


def http_check(row: dict) -> dict:
    url = row["Link to Job Req"].strip()
    role_raw = row["Role"].strip()
    result = {
        "url": url,
        "company": row["Company Name"].strip(),
        "role": ROLE_NOISE.sub("", role_raw).strip(),
        "domain": get_domain(url),
        "category": None,
    }
    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=HTTP_TIMEOUT,
            allow_redirects=True, stream=True,
        )
        content = b""
        for chunk in resp.iter_content(8192):
            content += chunk
            break
        has_keywords = bool(JOB_KEYWORDS.search(content.decode("utf-8", errors="ignore")))

        if resp.status_code == 200:
            result["category"] = "live" if has_keywords else "live_no_keywords"
        elif resp.status_code == 403:
            result["category"] = "blocked"
        elif resp.status_code == 404:
            result["category"] = "dead"
        else:
            result["category"] = f"http_{resp.status_code}"
    except requests.exceptions.Timeout:
        result["category"] = "timeout"
    except Exception as e:
        result["category"] = f"error"
    return result


def jina_check(row: dict) -> dict:
    """Fetch full page text via Jina with retry on 429 rate limit."""
    url = row["url"]
    for attempt in range(4):
        try:
            resp = requests.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "application/json"},
                timeout=JINA_TIMEOUT,
            )
            if resp.status_code == 429:
                wait = 2 ** attempt  # 1s, 2s, 4s, 8s
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json().get("data", {})
            content = data.get("content", "")
            has_keywords = bool(JOB_KEYWORDS.search(content))
            return {
                **row,
                "jina_ok": True,
                "jina_title": data.get("title", ""),
                "jina_text_len": len(content),
                "jina_has_keywords": has_keywords,
                "recovered": has_keywords and len(content) > 500,
            }
        except requests.exceptions.HTTPError:
            pass
        except Exception as e:
            return {**row, "jina_ok": False, "recovered": False, "jina_error": str(e)[:80]}
    return {**row, "jina_ok": False, "recovered": False, "jina_error": "429 after retries"}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["Link to Job Req"].strip()]
    print(f"Total URLs in CSV: {len(rows)}")

    # 1. HTTP check — same as script 1, fast
    print(f"\nRunning HTTP check (concurrency={HTTP_CONCURRENCY})...")
    t0 = time.time()
    http_results = []
    with ThreadPoolExecutor(max_workers=HTTP_CONCURRENCY) as pool:
        futs = {pool.submit(http_check, row): row for row in rows}
        done = 0
        for fut in as_completed(futs):
            http_results.append(fut.result())
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(rows)}")
    print(f"HTTP check done in {time.time() - t0:.1f}s")

    cats = Counter(r["category"] for r in http_results)
    live_confirmed = [r for r in http_results if r["category"] == "live"]
    spa_batch = [r for r in http_results if r["category"] == "live_no_keywords"]
    print(f"\nHTTP breakdown: {dict(cats)}")
    print(f"Already confirmed live: {len(live_confirmed)}")
    print(f"live_no_keywords (SPA candidates): {len(spa_batch)}")

    # 2. Run Jina on the full live_no_keywords batch
    print(f"\nRunning Jina on {len(spa_batch)} SPA candidates "
          f"(concurrency={JINA_CONCURRENCY}, ~{len(spa_batch) // JINA_CONCURRENCY * 5}s est.)...")
    t0 = time.time()
    jina_results = []
    with ThreadPoolExecutor(max_workers=JINA_CONCURRENCY) as pool:
        futs = {pool.submit(jina_check, row): row for row in spa_batch}
        done = 0
        for fut in as_completed(futs):
            jina_results.append(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(spa_batch)}")
    print(f"Jina check done in {time.time() - t0:.1f}s")

    # 3. Results breakdown
    recovered = [r for r in jina_results if r.get("recovered")]
    jina_failed = [r for r in jina_results if not r.get("jina_ok")]
    jina_no_keywords = [r for r in jina_results if r.get("jina_ok") and not r.get("recovered")]

    print(f"\n── Jina results for SPA batch ──")
    print(f"  Recovered (has keywords + text > 500 chars): {len(recovered)}")
    print(f"  Fetched but no job keywords:                 {len(jina_no_keywords)}")
    print(f"  Jina fetch failed:                           {len(jina_failed)}")

    # Platform breakdown of recovered
    dom_count = Counter(r["domain"] for r in recovered)
    print(f"\n── Recovered by platform ──")
    for d, n in dom_count.most_common(12):
        print(f"  {n:3d}  {d}")

    # Sample recovered entries
    if recovered[:3]:
        print(f"\n── Recovered examples ──")
        for r in recovered[:3]:
            print(f"  [{r['domain']}] {r.get('jina_title', '')[:60]}")
            print(f"    company={r['company']!r}  role={r['role']!r}")
            print(f"    text_len={r.get('jina_text_len')}")

    # Sample failures
    if jina_failed[:3]:
        print(f"\n── Jina failure examples ──")
        for r in jina_failed[:3]:
            print(f"  [{r['domain']}] {r.get('jina_error', '')}")

    # 4. Save combined candidate list
    all_candidates = [
        {**r, "source": "live_confirmed"} for r in live_confirmed
    ] + [
        {**r, "source": "spa_recovered"} for r in recovered
    ]

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, indent=2, ensure_ascii=False)

    # 5. Final summary
    total_usable = len(live_confirmed) + len(recovered)
    print(f"\n====== Summary ======")
    print(f"  live_no_keywords tested:  {len(spa_batch)}")
    print(f"  Recovered via Jina:       {len(recovered)}")
    print(f"  ── Combined usable ──")
    print(f"  Confirmed live:           {len(live_confirmed)}")
    print(f"  SPA recovered:            {len(recovered)}")
    print(f"  Total training candidates:{total_usable}")
    print(f"\n  Saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
