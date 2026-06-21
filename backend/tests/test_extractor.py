"""Unit tests for the extraction logic in services/extractor.py.

These cover the deterministic, network-free paths: JSON-LD parsing, the
regex-driven field extraction, and platform detection. They intentionally avoid
asserting on spaCy NER output so results are stable across the custom model
(local) and the en_core_web_sm fallback (CI).
"""
from services.extractor import _parse_jobposting, detect_platform, extract_fields


# ── detect_platform ──────────────────────────────────────────────────────────
def test_detect_platform_known_ats():
    assert detect_platform("https://boards.greenhouse.io/acme/jobs/123") == "Greenhouse"
    assert detect_platform("https://jobs.lever.co/acme/abc") == "Lever"
    assert detect_platform("https://www.linkedin.com/jobs/view/123") == "LinkedIn"
    assert detect_platform("https://acme.myworkdayjobs.com/job/123") == "Workday"


def test_detect_platform_unknown_defaults_to_company_site():
    assert detect_platform("https://acme.com/careers/123") == "Company Site"


# ── _parse_jobposting (JSON-LD) ──────────────────────────────────────────────
def test_parse_jobposting_basic_fields():
    data = {
        "@type": "JobPosting",
        "title": "Senior Data Scientist",
        "hiringOrganization": {"name": "Acme Corp"},
    }
    r = _parse_jobposting(data)
    assert r["title"] == "Senior Data Scientist"
    assert r["company"] == "Acme Corp"


def test_parse_jobposting_dedupes_city_region():
    data = {
        "title": "Eng",
        "jobLocation": {
            "address": {
                "addressLocality": "Berlin",
                "addressRegion": "Berlin",
                "addressCountry": "DE",
            }
        },
    }
    r = _parse_jobposting(data)
    assert r["location"] == "Berlin, DE"


def test_parse_jobposting_telecommute_sets_remote():
    r = _parse_jobposting({"title": "Eng", "jobLocationType": "TELECOMMUTE"})
    assert r["work_type"] == "Remote"
    assert r["location"] == "Remote"


def test_parse_jobposting_annualizes_hourly_salary():
    data = {
        "title": "Eng",
        "baseSalary": {"value": {"unitText": "HOUR", "minValue": 50, "maxValue": 60}},
    }
    r = _parse_jobposting(data)
    assert r["salary_min"] == 50 * 2080
    assert r["salary_max"] == 60 * 2080


def test_parse_jobposting_yearly_salary():
    data = {
        "title": "Eng",
        "baseSalary": {"value": {"unitText": "YEAR", "minValue": 150000, "maxValue": 200000}},
    }
    r = _parse_jobposting(data)
    assert r["salary_min"] == 150000
    assert r["salary_max"] == 200000


# ── extract_fields: title / company from the "Title:" line ────────────────────
def test_extract_title_company_at_pattern():
    r = extract_fields("Title: Senior Engineer at Acme\nSome body text.")
    assert r["title"] == "Senior Engineer"
    assert r["company"] == "Acme"


def test_extract_title_company_pipe_pattern():
    r = extract_fields("Title: Data Scientist | Globex\nBody.")
    assert r["title"] == "Data Scientist"
    assert r["company"] == "Globex"


def test_extract_strips_site_noise_from_title():
    r = extract_fields("Title: Backend Engineer - LinkedIn\nBody.")
    assert r["title"] == "Backend Engineer"


# ── extract_fields: salary ────────────────────────────────────────────────────
def test_extract_salary_range_with_k_suffix():
    r = extract_fields("Title: Eng\nCompensation: $120k - $160k per year")
    assert r["salary_min"] == 120000
    assert r["salary_max"] == 160000


def test_extract_salary_range_with_commas():
    r = extract_fields("Title: Eng\nSalary: $150,000 - $200,000")
    assert r["salary_min"] == 150000
    assert r["salary_max"] == 200000


def test_extract_ignores_hourly_rates():
    r = extract_fields("Title: Barista\nPay: $25 - $33 per hour")
    assert "salary_min" not in r
    assert "salary_max" not in r


# ── extract_fields: work type ─────────────────────────────────────────────────
def test_extract_work_type_hybrid_beats_remote():
    r = extract_fields("Title: Eng\nPotential for Remote Work: Hybrid")
    assert r["work_type"] == "Hybrid"


def test_extract_work_type_remote():
    r = extract_fields("Title: Eng\nThis is a fully remote position.")
    assert r["work_type"] == "Remote"


# ── extract_fields: location label ────────────────────────────────────────────
def test_extract_location_from_label():
    r = extract_fields("Title: Eng at Acme\nLocation: San Francisco, CA")
    assert r["location"] == "San Francisco, CA"
