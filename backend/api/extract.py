
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.extractor import (
    detect_platform,
    extract_fields,
    fetch_ashby,
    fetch_greenhouse,
    fetch_jsonld,
    fetch_lever,
    fetch_smartrecruiters,
    fetch_text_from_url,
    fetch_workday,
)
from services.llm_extractor import extract_fields_llm

router = APIRouter()

# Dedicated ATS APIs, tried in order. Each returns None fast when the URL's host
# doesn't match, so ordering between them is cheap.
_ATS_FETCHERS = (
    fetch_greenhouse,
    fetch_lever,
    fetch_ashby,
    fetch_smartrecruiters,
    fetch_workday,
)


class ExtractRequest(BaseModel):
    url: str | None = None
    text: str | None = None


class ExtractResponse(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    work_type: str | None = None
    platform: str | None = None
    source_url: str | None = None


@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest):
    if not payload.url and not payload.text:
        raise HTTPException(status_code=422, detail="Provide either url or text")

    if payload.url:
        platform = detect_platform(payload.url)
        source_url = payload.url

        # 1. Dedicated ATS APIs (Greenhouse, Lever, Ashby, SmartRecruiters, Workday)
        for fetch in _ATS_FETCHERS:
            fields = fetch(payload.url)
            if fields:
                fields["platform"] = fields.get("platform") or platform
                fields["source_url"] = source_url
                return ExtractResponse(**fields)

        # 2. Try JSON-LD structured data (schema.org JobPosting)
        fields = fetch_jsonld(payload.url)
        if fields:
            fields["platform"] = platform
            fields["source_url"] = source_url
            return ExtractResponse(**fields)

        # 3. Fall back to Jina + NLP
        try:
            text = fetch_text_from_url(payload.url)
        except Exception as e:
            detail = f"Failed to fetch URL: {e}"
            if "401" in str(e):
                detail += " (Jina Reader requires auth — set JINA_API_KEY)"
            raise HTTPException(status_code=502, detail=detail)
    else:
        text = payload.text
        platform = None
        source_url = None

    # 4. Try LLM extraction (Groq); fall back to regex/spaCy if unavailable
    fields = extract_fields_llm(text) or extract_fields(text)
    fields["platform"] = fields.get("platform") or platform
    fields["source_url"] = source_url

    return ExtractResponse(**fields)
