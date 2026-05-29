import json
import re
from pathlib import Path

import requests
import spacy

_CUSTOM_MODEL_PATH = Path("/app/corpus/job_copilot_ner")


def _load_nlp():
    if _CUSTOM_MODEL_PATH.exists():
        try:
            model = spacy.load(str(_CUSTOM_MODEL_PATH))
            print(f"Loaded custom NER: {_CUSTOM_MODEL_PATH}")
            return model, True
        except Exception as e:
            print(f"Custom model load failed ({e}), falling back to en_core_web_sm")
    return spacy.load("en_core_web_sm"), False


nlp, _custom_ner = _load_nlp()

PLATFORM_PATTERNS = {
    "greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
    "workday.com": "Workday",
    "myworkdayjobs.com": "Workday",
    "icims.com": "iCIMS",
    "smartrecruiters.com": "SmartRecruiters",
    "ashbyhq.com": "Ashby",
    "jobvite.com": "Jobvite",
    "taleo.net": "Taleo",
    "brassring.com": "Brassring",
}


_HTML_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_jsonld(url: str) -> dict | None:
    """Fetch raw HTML and extract schema.org JobPosting JSON-LD.
    Returns mapped fields dict if found, None otherwise."""
    try:
        resp = requests.get(url, headers=_HTML_HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return None

    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        resp.text, re.DOTALL | re.IGNORECASE,
    )
    for raw_script in scripts:
        try:
            data = json.loads(raw_script.strip())
        except (json.JSONDecodeError, ValueError):
            continue

        # Unwrap @graph containers
        if isinstance(data, dict) and "@graph" in data:
            data = data["@graph"]

        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                result = _parse_jobposting(item)
                if result.get("title"):
                    return result

    return None


def _parse_jobposting(data: dict) -> dict:
    result = {}

    if title := data.get("title"):
        result["title"] = str(title).strip()

    org = data.get("hiringOrganization", {})
    if isinstance(org, dict) and (name := org.get("name")):
        result["company"] = str(name).strip()

    # Location — may be a single object or a list
    locations = data.get("jobLocation", [])
    if isinstance(locations, dict):
        locations = [locations]
    if locations:
        addr = locations[0].get("address", {})
        if isinstance(addr, str):
            result["location"] = addr.strip()
        elif isinstance(addr, dict):
            locality = addr.get("addressLocality")
            region = addr.get("addressRegion")
            country = addr.get("addressCountry")
            # Deduplicate: e.g. Berlin/Berlin (city == state) → just "Berlin"
            parts = list(dict.fromkeys(p for p in [locality, region] if p))
            if country and country not in (locality, region):
                parts.append(country)
            loc = ", ".join(parts)
            if loc:
                result["location"] = loc

    # jobLocationType TELECOMMUTE → Remote
    if data.get("jobLocationType") == "TELECOMMUTE":
        result["work_type"] = "Remote"
        if "location" not in result:
            result["location"] = "Remote"

    # Salary — handle YEAR and HOUR units
    base = data.get("baseSalary", {})
    if isinstance(base, dict):
        val = base.get("value", {})
        if isinstance(val, dict):
            unit = str(val.get("unitText", "YEAR")).upper()
            multiplier = 2080 if unit == "HOUR" else 1  # annualise hourly
            min_v = val.get("minValue")
            max_v = val.get("maxValue")
            single = val.get("value")
            if min_v is not None:
                result["salary_min"] = round(float(min_v) * multiplier)
            if max_v is not None:
                result["salary_max"] = round(float(max_v) * multiplier)
            elif single is not None and "salary_min" not in result:
                result["salary_min"] = round(float(single) * multiplier)

    return result


def fetch_text_from_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    resp = requests.get(
        f"https://r.jina.ai/{url}",
        headers={"Accept": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    title = data.get("title", "")
    content = data.get("content", "")
    # Prepend title as a standard header so extract_fields can parse it
    prefix = f"Title: {title}\n" if title else ""
    return prefix + content


def detect_platform(url: str) -> str | None:
    url_lower = url.lower()
    for domain, name in PLATFORM_PATTERNS.items():
        if domain in url_lower:
            return name
    return "Company Site"


def extract_fields(text: str) -> dict:
    doc = nlp(text[:15000])
    result = {}

    # Strip inline markdown links [text](url) → text for all regex searches
    clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)

    # Jina returns "Title: <page title>" — formats vary by platform
    jina_title_line = re.search(r"^Title:\s+(.+)$", text, re.MULTILINE)
    if jina_title_line:
        raw = jina_title_line.group(1).strip()

        # Strip "Apply for/to" prefix (Greenhouse)
        raw = re.sub(r"^Apply (?:for|to)\s+", "", raw, flags=re.IGNORECASE)

        # Strip trailing site-name noise: "- LinkedIn", "| Careers", "| Apply Now", etc.
        _SITE_NOISE = r"LinkedIn|Greenhouse|Lever|Indeed|Glassdoor|Workday|ZipRecruiter|Careers?|Jobs?|Apply(?: Now)?"
        raw = re.sub(rf"\s*[|\-–—]\s*(?:{_SITE_NOISE})\s*$", "", raw, flags=re.IGNORECASE).strip()

        # "TITLE at/@ COMPANY [extra]"
        at_company = re.match(r"(.+?)\s+(?:at|@)\s+(.+)", raw, re.IGNORECASE)
        # "TITLE | COMPANY"
        pipe_split = re.match(r"(.+?)\s*\|\s*(.+)", raw)
        # "TITLE in City, State[, Country]" — Jina often appends location to page title
        in_location = re.match(r"(.+?)\s+in\s+(\S.+,.+)", raw, re.IGNORECASE)

        if at_company:
            result["title"] = at_company.group(1).strip()
            # Strip trailing "- Location", "| extra", or "in City" from company
            company_raw = re.split(r"\s*(?:[-–—|]|\bin\b)\s*", at_company.group(2), flags=re.IGNORECASE)[0].strip()
            result["company"] = company_raw
        elif pipe_split:
            result["title"] = pipe_split.group(1).strip()
            result["company"] = pipe_split.group(2).strip()
        elif in_location:
            # No company in title — falls back to spaCy ORG below
            result["title"] = in_location.group(1).strip()
            result["location"] = in_location.group(2).strip()
        else:
            result["title"] = raw

    # Fallback title: first markdown heading
    if "title" not in result:
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if heading:
            result["title"] = heading.group(1).strip()

    # Fallback title: JOB_TITLE entity from custom model
    if "title" not in result and _custom_ner:
        titles = [ent.text.strip() for ent in doc.ents if ent.label_ == "JOB_TITLE"]
        if titles:
            result["title"] = titles[0]

    # Fallback company: COMPANY entity (custom model) or ORG (en_core_web_sm)
    if "company" not in result:
        company_label = "COMPANY" if _custom_ner else "ORG"
        cands = [ent.text.strip() for ent in doc.ents if ent.label_ == company_label]
        if cands:
            result["company"] = cands[0]

    # Location: explicit label first, then GPE entity (use clean to avoid markdown link junk)
    loc_label = re.search(
        r"(?:location|based in|office)[:\s]+([^\n,]{3,50}(?:,\s*[A-Z]{2})?)",
        clean, re.IGNORECASE
    )
    if loc_label:
        result["location"] = loc_label.group(1).strip()
    else:
        # Only use GPE if it looks like a real place (not a dept/technology name)
        skip_words = {"engineering", "software", "data", "product", "design", "research"}
        gpes = [
            ent.text.strip() for ent in doc.ents
            if ent.label_ == "GPE"
            and ent.text.lower() not in skip_words
            and len(ent.text.strip()) >= 4  # filter "US", "EU", "GCP", "AWS"
        ]
        if gpes:
            result["location"] = gpes[0]

    # Salary: handles $80k-$120k, $80,000-$120,000; skips hourly rates (< 1000)
    salary = re.search(
        r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?\s*[-–—]\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?",
        clean,
    )
    if salary:
        min_val = int(salary.group(1).replace(",", ""))
        max_val = int(salary.group(3).replace(",", ""))
        if salary.group(2):
            min_val *= 1000
        if salary.group(4):
            max_val *= 1000
        if min_val >= 1000:  # ignore hourly wages like $25-$33
            result["salary_min"] = min_val
            result["salary_max"] = max_val
    else:
        # single salary like $120,000 or $120k
        single = re.search(r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?", clean)
        if single:
            val = int(single.group(1).replace(",", ""))
            if single.group(2):
                val *= 1000
            if val >= 1000:
                result["salary_min"] = val

    # Work type: check hybrid before remote — "Potential for Remote Work: Hybrid" should be Hybrid
    clean_lower = clean.lower()
    if "hybrid" in clean_lower:
        result["work_type"] = "Hybrid"
    elif "remote" in clean_lower:
        result["work_type"] = "Remote"
    elif "on-site" in clean_lower or "onsite" in clean_lower or "in office" in clean_lower:
        result["work_type"] = "Onsite"

    return result
