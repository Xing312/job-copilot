"""
Test whether job URLs from the CSV are usable as NER training data.

Checks:
1. HTTP status of each URL (concurrent, fast)
2. Whether the page looks like a real job posting (vs. homepage / 404)
3. Whether Jina can fetch meaningful text (sampled subset)
4. Label quality in the company / role columns

Usage:
  python scripts/test_training_urls.py
"""

import csv
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

CSV_PATH = Path(__file__).parent.parent / "Copy of JOB APPLICATION TEMPLATE - Tracking Template.csv"
JINA_SAMPLE = 20    # number of live URLs to test with Jina
CONCURRENCY = 20    # parallel threads for HTTP checks
TIMEOUT = 10        # per-request timeout in seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Keywords that indicate a real job posting page
JOB_KEYWORDS = re.compile(
    r'\b(responsibilities|qualifications|requirements|apply|job description'
    r'|about the role|what you.ll do|minimum qualifications)\b',
    re.IGNORECASE,
)

# Role column often has location/extra info after the first line
ROLE_NOISE = re.compile(r'\n.*', re.DOTALL)


# ── Helpers ──────────────────────────────────────────────────────────────────

def domain(url: str) -> str:
    try:
        parts = urlparse(url).netloc.lower().split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else parts[0]
    except Exception:
        return "unknown"


def check_url(row: dict) -> dict:
    url = row["Link to Job Req"].strip()
    company = row["Company Name"].strip()
    role_raw = row["Role"].strip()
    role = ROLE_NOISE.sub("", role_raw).strip()

    result = {
        "url": url,
        "company": company,
        "role": role,
        "role_has_noise": "\n" in role_raw,
        "domain": domain(url),
        "status": None,
        "category": None,
        "has_job_keywords": None,
    }

    try:
        resp = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT,
            allow_redirects=True, stream=True,
        )
        result["status"] = resp.status_code

        # Read first 8 KB to check for job-related keywords
        content = b""
        for chunk in resp.iter_content(8192):
            content += chunk
            break
        snippet = content.decode("utf-8", errors="ignore")
        result["has_job_keywords"] = bool(JOB_KEYWORDS.search(snippet))

        if resp.status_code == 200:
            result["category"] = "live" if result["has_job_keywords"] else "live_no_keywords"
        elif resp.status_code in (301, 302, 303, 307, 308):
            result["category"] = "redirect"
        elif resp.status_code == 403:
            result["category"] = "blocked"
        elif resp.status_code == 404:
            result["category"] = "dead"
        else:
            result["category"] = f"http_{resp.status_code}"

    except requests.exceptions.Timeout:
        result["category"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["category"] = "connection_error"
    except Exception as e:
        result["category"] = f"error: {e!s:.40}"

    return result


def jina_fetch(url: str) -> dict:
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "application/json"},
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        content = data.get("content", "")
        return {
            "url": url,
            "ok": True,
            "title": data.get("title", ""),
            "text_len": len(content),
            "has_job_keywords": bool(JOB_KEYWORDS.search(content)),
        }
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e)[:60]}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["Link to Job Req"].strip()]
    print(f"Total URLs: {len(rows)}\n")

    # 1. Concurrent HTTP status check
    print(f"Checking {len(rows)} URLs (concurrency={CONCURRENCY})...")
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(check_url, row): row for row in rows}
        done = 0
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(rows)}")
    print(f"Done in {time.time() - t0:.1f}s\n")

    # 2. Status breakdown
    cat_count = Counter(r["category"] for r in results)
    print("── URL status breakdown ──")
    for cat, n in cat_count.most_common():
        print(f"  {n:3d}  {cat}")

    live = [r for r in results if r["category"] == "live"]
    print(f"\nLive URLs usable for training: {len(live)} / {len(results)}")

    # 3. Platform distribution (live only)
    dom_count = Counter(r["domain"] for r in live)
    print("\n── Platform distribution (live) ──")
    for d, n in dom_count.most_common(12):
        print(f"  {n:3d}  {d}")

    # 4. Label quality
    noisy_roles = [r for r in results if r["role_has_noise"]]
    empty_company = [r for r in results if not r["company"]]
    print(f"\n── Label quality ──")
    print(f"  Roles with newline noise: {len(noisy_roles)}")
    print(f"  Missing company label:    {len(empty_company)}")
    if noisy_roles[:3]:
        print("  Noisy role examples:")
        for r in noisy_roles[:3]:
            print(f"    {r['role']!r}")

    # 5. Jina sample test
    import random
    sample = random.sample(live, min(JINA_SAMPLE, len(live)))
    print(f"\n── Jina sample test ({len(sample)} URLs) ──")
    jina_results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(jina_fetch, r["url"]): r for r in sample}
        for fut in as_completed(futs):
            jina_results.append((futs[fut], fut.result()))

    jina_ok = [(row, jr) for row, jr in jina_results if jr["ok"] and jr["has_job_keywords"]]
    jina_fail = [(row, jr) for row, jr in jina_results if not jr["ok"] or not jr["has_job_keywords"]]

    print(f"  Success (has job keywords): {len(jina_ok)}")
    print(f"  Failed or no keywords:      {len(jina_fail)}")

    if jina_ok[:3]:
        print("\n  Success examples:")
        for row, jr in jina_ok[:3]:
            print(f"    [{row['domain']}] {jr.get('title', '')[:60]}")
            print(f"      company={row['company']!r}  role={row['role']!r}")
            print(f"      text_len={jr['text_len']}")

    if jina_fail:
        print("\n  Failure examples:")
        for row, jr in jina_fail[:3]:
            print(f"    [{row['domain']}] {jr.get('error') or 'no job keywords'}")

    # 6. Training data summary
    est_jina = round(len(live) * len(jina_ok) / len(sample)) if sample else 0
    print("\n====== Training data summary ======")
    print(f"  Total URLs:              {len(results)}")
    print(f"  Live (with keywords):    {len(live)}")
    print(f"  Estimated Jina-fetchable: ~{est_jina} (based on sample)")
    print(f"  Has company label:       {len(results) - len(empty_company)}")
    print(f"  Roles need cleaning:     {len(noisy_roles)}")


if __name__ == "__main__":
    main()
