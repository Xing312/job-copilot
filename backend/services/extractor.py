import html
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def fetch_greenhouse(url: str) -> dict | None:
    """Extract a Greenhouse-backed posting via the Greenhouse Board API.

    Many career sites (e.g. fanduel.careers) are SPAs that embed Greenhouse and
    carry a ``?gh_jid=<id>`` query param. JSON-LD and Jina both fail on these, but
    the Board API returns clean structured fields. The board token is not in the
    page URL, so we resolve it from the embed endpoint's redirect
    (``/embed/job_app?token=<id>`` → ``...?for=<token>&token=<id>``)."""
    jid = parse_qs(urlparse(url).query).get("gh_jid", [None])[0]
    if not jid:
        return None
    try:
        embed = requests.get(
            "https://boards.greenhouse.io/embed/job_app",
            params={"token": jid},
            headers=_HTML_HEADERS, timeout=15, allow_redirects=True,
        )
        token = parse_qs(urlparse(embed.url).query).get("for", [None])[0]
        if not token:
            return None
        api = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{jid}",
            headers={"Accept": "application/json"}, timeout=15,
        )
        api.raise_for_status()
        data = api.json()
    except Exception:
        return None

    result = {}
    if title := data.get("title"):
        result["title"] = str(title).strip()
    if company := data.get("company_name"):
        result["company"] = str(company).strip()
    if loc := (data.get("location") or {}).get("name"):
        result["location"] = str(loc).strip()

    _fill_from_body(result, data.get("content"))

    if not result.get("title"):
        return None
    result["platform"] = "Greenhouse"
    return result


def _strip_html(raw: str | None) -> str:
    """Collapse an HTML fragment to plain text for regex/NER mining."""
    return html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))


def _fill_from_body(result: dict, raw_body: str | None) -> None:
    """Backfill location/salary/work_type from a JD text or HTML blob using the
    shared regex/NER extractor, never overwriting clean values already in `result`."""
    body = _strip_html(raw_body) if raw_body and "<" in raw_body else (raw_body or "")
    if not body.strip():
        return
    extra = extract_fields(body)
    for key in ("location", "salary_min", "salary_max", "work_type"):
        if not result.get(key) and extra.get(key) is not None:
            result[key] = extra[key]


def _company_from_token(token: str) -> str:
    """Best-effort company name from a URL slug (e.g. 'acme-corp' -> 'Acme Corp').
    APIs that key on a board token rarely return the display name; the user can edit."""
    return token.replace("-", " ").replace("_", " ").title()


def _norm_work_type(value: str | None) -> str | None:
    """Map a platform's free-form workplace value to our Remote/Hybrid/Onsite set."""
    v = (value or "").lower()
    if "hybrid" in v:
        return "Hybrid"
    if "remote" in v or "telecommute" in v:
        return "Remote"
    if "onsite" in v or "on-site" in v or "in office" in v or "in-office" in v:
        return "Onsite"
    return None


def fetch_lever(url: str) -> dict | None:
    """Lever posting via the public v0 API.

    Public URL:  https://jobs.lever.co/{site}/{id}
    API:         https://api.lever.co/v0/postings/{site}/{id}?mode=json
    """
    parsed = urlparse(url)
    if "lever.co" not in parsed.netloc:
        return None
    segs = [s for s in parsed.path.split("/") if s]
    if len(segs) < 2:
        return None
    site, job_id = segs[0], segs[1]
    try:
        resp = requests.get(
            f"https://api.lever.co/v0/postings/{site}/{job_id}",
            params={"mode": "json"}, headers={"Accept": "application/json"}, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("text"):
        return None

    cats = data.get("categories") or {}
    result = {
        "title": str(data["text"]).strip(),
        "company": _company_from_token(site),
        "platform": "Lever",
    }
    if loc := cats.get("location"):
        result["location"] = str(loc).strip()
    if wt := _norm_work_type(data.get("workplaceType")):
        result["work_type"] = wt
    salary = data.get("salaryRange") or {}
    if salary.get("min"):
        result["salary_min"] = round(float(salary["min"]))
    if salary.get("max"):
        result["salary_max"] = round(float(salary["max"]))

    _fill_from_body(result, data.get("description") or data.get("descriptionPlain"))
    return result


def fetch_ashby(url: str) -> dict | None:
    """Ashby posting. The public job-board API returns every listed job; we filter
    by the posting UUID from the URL.

    Public URL:  https://jobs.ashbyhq.com/{org}/{uuid}
    API:         https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true
    """
    parsed = urlparse(url)
    if "ashbyhq.com" not in parsed.netloc:
        return None
    segs = [s for s in parsed.path.split("/") if s]
    if len(segs) < 2:
        return None
    org, job_id = segs[0], segs[1]
    try:
        resp = requests.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{org}",
            params={"includeCompensation": "true"},
            headers={"Accept": "application/json"}, timeout=15,
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except Exception:
        return None

    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job or not job.get("title"):
        return None

    result = {
        "title": str(job["title"]).strip(),
        "company": _company_from_token(org),
        "platform": "Ashby",
    }
    if loc := job.get("location"):
        result["location"] = str(loc).strip()
    if wt := _norm_work_type(job.get("workplaceType")):
        result["work_type"] = wt
    elif job.get("isRemote"):
        result["work_type"] = "Remote"
    # Compensation is a free-form summary string (e.g. "$120K – $150K"); the shared
    # extractor parses USD ranges and safely ignores other currencies.
    comp = job.get("compensation") or {}
    _fill_from_body(result, comp.get("scrapeableCompensationSalarySummary")
                    or comp.get("compensationTierSummary"))
    return result


def fetch_smartrecruiters(url: str) -> dict | None:
    """SmartRecruiters posting via the public API.

    Public URL:  https://jobs.smartrecruiters.com/{company}/{postingId}-{slug}
    API:         https://api.smartrecruiters.com/v1/companies/{company}/postings/{postingId}
    """
    parsed = urlparse(url)
    if "smartrecruiters.com" not in parsed.netloc:
        return None
    segs = [s for s in parsed.path.split("/") if s]
    if len(segs) < 2:
        return None
    company = segs[0]
    posting_id = segs[1].split("-")[0]  # leading numeric id; drop the slug tail
    try:
        resp = requests.get(
            f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}",
            headers={"Accept": "application/json"}, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    if not data.get("name"):
        return None

    result = {"title": str(data["name"]).strip(), "platform": "SmartRecruiters"}
    if co := (data.get("company") or {}).get("name"):
        result["company"] = str(co).strip()
    loc = data.get("location") or {}
    parts = [str(p).strip() for p in (loc.get("city"), loc.get("region")) if p]
    if parts:
        result["location"] = ", ".join(dict.fromkeys(parts))
    if loc.get("remote"):
        result["work_type"] = "Remote"

    sections = (data.get("jobAd") or {}).get("sections") or {}
    body = " ".join(
        sec.get("text", "") for sec in sections.values() if isinstance(sec, dict)
    )
    _fill_from_body(result, body)
    return result


def fetch_workday(url: str) -> dict | None:
    """Workday SPA posting via the internal CXS JSON API.

    Public URL:  https://{tenant}.{dc}.myworkdayjobs.com/{lang}/{site}/job/{path}
    CXS API:     https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{path}
    The language segment (e.g. en-US) is optional; the tenant is the first subdomain
    label and the site is the path segment immediately before `job`.
    """
    parsed = urlparse(url)
    host = parsed.netloc
    if "myworkdayjobs.com" not in host:
        return None
    tenant = host.split(".")[0]
    segs = [s for s in parsed.path.split("/") if s]
    if "job" not in segs:
        return None
    ji = segs.index("job")
    if ji < 1:
        return None
    site = segs[ji - 1]
    job_path = "/".join(segs[ji:])  # job/{location}/{title}_{reqId}
    try:
        resp = requests.get(
            f"https://{host}/wday/cxs/{tenant}/{site}/{job_path}",
            headers={"Accept": "application/json", **_HTML_HEADERS}, timeout=15,
        )
        resp.raise_for_status()
        info = resp.json().get("jobPostingInfo", {})
    except Exception:
        return None
    if not info.get("title"):
        return None

    # CXS omits the company name; the tenant slug is the best available proxy.
    result = {
        "title": str(info["title"]).strip(),
        "company": _company_from_token(tenant),
        "platform": "Workday",
    }
    if loc := info.get("location"):
        result["location"] = str(loc).strip()

    # Work type / salary aren't structured in CXS — mine them from the JD body.
    _fill_from_body(result, info.get("jobDescription"))
    return result


def fetch_text_from_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    headers = {"Accept": "application/json"}
    # Jina Reader now requires auth; a free key (jina.ai) lifts the 401/rate limit.
    if key := os.getenv("JINA_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    resp = requests.get(
        f"https://r.jina.ai/{url}",
        headers=headers,
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
