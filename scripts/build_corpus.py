"""
Build NER training corpus from training_candidates.json.

For each candidate:
1. Fetch full page text via Jina (rate-limited)
2. Clean company / role labels
3. Auto-annotate JOB_TITLE and COMPANY entity spans
4. Save to corpus/annotations.json for human review

The annotations.json can then be converted to spaCy .spacy format
inside the Docker container using corpus/to_spacy.py.

Usage:
  python scripts/build_corpus.py
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

CANDIDATES_PATH = Path(__file__).parent / "training_candidates.json"
CORPUS_DIR = Path(__file__).parent.parent / "corpus"
ANNOTATIONS_PATH = CORPUS_DIR / "annotations.json"

JINA_CONCURRENCY = 2
JINA_TIMEOUT = 30

# Truncate text to this length for training examples — enough context
# without feeding the whole page into every training doc
TEXT_WINDOW = 4000

# Patterns that indicate location noise in job titles, e.g. "Data Scientist - Atlanta, GA"
TITLE_LOCATION = re.compile(
    r'\s*[-–—]\s*[A-Z][a-z][\w\s]+(?:,\s*[A-Z]{2})?\s*$'
)

# Minimum text length to be considered a usable training example
MIN_TEXT_LEN = 300


# ── Label cleaning ────────────────────────────────────────────────────────────

def clean_title(raw: str) -> str:
    title = raw.strip()
    # Take first line only (CSV role sometimes has location on line 2+)
    title = title.splitlines()[0].strip()
    # Strip trailing "- City, ST" patterns
    title = TITLE_LOCATION.sub("", title).strip()
    return title


def clean_company(raw: str) -> str:
    return raw.strip()


# ── Jina fetch ────────────────────────────────────────────────────────────────

def jina_fetch(candidate: dict) -> dict:
    url = candidate["url"]
    for attempt in range(4):
        try:
            resp = requests.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "application/json"},
                timeout=JINA_TIMEOUT,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            data = resp.json().get("data", {})
            page_title = data.get("title", "")
            content = data.get("content", "")
            # Prepend title as a labelled line so it appears in the text window
            full_text = (f"Title: {page_title}\n" if page_title else "") + content
            return {**candidate, "text": full_text, "fetch_ok": True}
        except requests.exceptions.HTTPError:
            pass
        except Exception as e:
            return {**candidate, "text": "", "fetch_ok": False, "fetch_error": str(e)[:80]}
    return {**candidate, "text": "", "fetch_ok": False, "fetch_error": "429 after retries"}


# ── Auto-annotation ───────────────────────────────────────────────────────────

def find_span(text: str, value: str) -> tuple[int, int] | None:
    """Return (start, end) of the first occurrence of value in text,
    trying exact match then a 3-word prefix match."""
    if not value:
        return None

    window = text[:TEXT_WINDOW]

    # Exact match (case-insensitive)
    m = re.search(re.escape(value), window, re.IGNORECASE)
    if m:
        return m.start(), m.end()

    # Fuzzy: match first 3 significant words (handles minor formatting diffs)
    words = [w for w in value.split() if len(w) > 2][:3]
    if len(words) >= 2:
        pattern = r"[\s\W]*".join(re.escape(w) for w in words)
        m = re.search(pattern, window, re.IGNORECASE)
        if m:
            return m.start(), m.end()

    return None


def annotate(candidate: dict) -> dict | None:
    text = candidate.get("text", "")
    if not text or len(text) < MIN_TEXT_LEN:
        return None

    title = clean_title(candidate.get("role", ""))
    company = clean_company(candidate.get("company", ""))

    entities = []

    title_span = find_span(text, title)
    if title_span:
        entities.append({"start": title_span[0], "end": title_span[1], "label": "JOB_TITLE"})

    company_span = find_span(text, company)
    if company_span:
        entities.append({"start": company_span[0], "end": company_span[1], "label": "COMPANY"})

    # Require at least one entity found to include this example
    if not entities:
        return None

    # Remove overlapping spans (keep longer one)
    entities = _remove_overlaps(entities)

    return {
        "text": text[:TEXT_WINDOW],
        "entities": entities,
        "meta": {
            "url": candidate["url"],
            "domain": candidate["domain"],
            "label_company": company,
            "label_title": title,
            "source": candidate["source"],
        },
    }


def _remove_overlaps(entities: list[dict]) -> list[dict]:
    """Remove overlapping entity spans, keeping the longer span."""
    entities = sorted(entities, key=lambda e: e["end"] - e["start"], reverse=True)
    kept = []
    for ent in entities:
        if not any(ent["start"] < k["end"] and ent["end"] > k["start"] for k in kept):
            kept.append(ent)
    return sorted(kept, key=lambda e: e["start"])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    CORPUS_DIR.mkdir(exist_ok=True)

    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(candidates)} candidates")

    # 1. Fetch Jina text for all candidates
    print(f"\nFetching Jina text (concurrency={JINA_CONCURRENCY})...")
    fetched = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=JINA_CONCURRENCY) as pool:
        futs = {pool.submit(jina_fetch, c): c for c in candidates}
        done = 0
        for fut in as_completed(futs):
            fetched.append(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(candidates)}")
    print(f"Fetch done in {time.time() - t0:.1f}s")

    fetch_ok = [f for f in fetched if f.get("fetch_ok") and len(f.get("text", "")) >= MIN_TEXT_LEN]
    fetch_fail = [f for f in fetched if not f.get("fetch_ok")]
    print(f"  Fetched successfully: {len(fetch_ok)}")
    print(f"  Failed:               {len(fetch_fail)}")
    if fetch_fail[:3]:
        for f in fetch_fail[:3]:
            print(f"    [{f['domain']}] {f.get('fetch_error', '')}")

    # 2. Auto-annotate
    print(f"\nAuto-annotating entity spans...")
    annotations = []
    skipped_no_entity = 0
    for entry in fetch_ok:
        result = annotate(entry)
        if result:
            annotations.append(result)
        else:
            skipped_no_entity += 1

    print(f"  Annotated:            {len(annotations)}")
    print(f"  Skipped (no span):    {skipped_no_entity}")

    # 3. Entity coverage stats
    has_title = sum(1 for a in annotations if any(e["label"] == "JOB_TITLE" for e in a["entities"]))
    has_company = sum(1 for a in annotations if any(e["label"] == "COMPANY" for e in a["entities"]))
    has_both = sum(1 for a in annotations if len(a["entities"]) == 2)
    print(f"\n  Has JOB_TITLE span:   {has_title}/{len(annotations)}")
    print(f"  Has COMPANY span:     {has_company}/{len(annotations)}")
    print(f"  Has both:             {has_both}/{len(annotations)}")

    # 4. Save annotations JSON
    ANNOTATIONS_PATH.write_text(
        json.dumps(annotations, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSaved {len(annotations)} annotated examples → {ANNOTATIONS_PATH}")

    # 5. Write the spaCy converter script (to run inside Docker)
    _write_converter()
    print(f"Wrote corpus/to_spacy.py  (run inside Docker to produce train/dev .spacy files)")


def _write_converter():
    script = '''\
"""
Convert corpus/annotations.json to spaCy .spacy training files.
Run this inside the Docker backend container:

  docker compose exec backend python /app/corpus/to_spacy.py

Outputs:
  corpus/train.spacy  (80%)
  corpus/dev.spacy    (20%)
"""

import json
import random
from pathlib import Path

import spacy
from spacy.tokens import DocBin

ANNOTATIONS_PATH = Path(__file__).parent / "annotations.json"
TRAIN_PATH = Path(__file__).parent / "train.spacy"
DEV_PATH = Path(__file__).parent / "dev.spacy"
SEED = 42


def main():
    nlp = spacy.blank("en")
    examples = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))

    random.seed(SEED)
    random.shuffle(examples)
    split = int(len(examples) * 0.8)
    train_data, dev_data = examples[:split], examples[split:]

    def to_docbin(data: list) -> DocBin:
        db = DocBin()
        skipped = 0
        for ex in data:
            doc = nlp.make_doc(ex["text"])
            ents = []
            for e in ex["entities"]:
                span = doc.char_span(e["start"], e["end"], label=e["label"])
                if span is None:
                    skipped += 1
                    continue
                ents.append(span)
            doc.ents = ents
            db.add(doc)
        if skipped:
            print(f"  Skipped {skipped} misaligned spans")
        return db

    print(f"Train: {len(train_data)} examples")
    to_docbin(train_data).to_disk(TRAIN_PATH)

    print(f"Dev:   {len(dev_data)} examples")
    to_docbin(dev_data).to_disk(DEV_PATH)

    print(f"Saved → {TRAIN_PATH}, {DEV_PATH}")


if __name__ == "__main__":
    main()
'''
    out = Path(__file__).parent.parent / "corpus" / "to_spacy.py"
    out.write_text(script, encoding="utf-8")


if __name__ == "__main__":
    main()
