
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.extractor import (
    detect_platform,
    extract_fields,
    fetch_jsonld,
    fetch_text_from_url,
)
from services.llm_extractor import extract_fields_llm

router = APIRouter()


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

        # 1. Try JSON-LD structured data (schema.org JobPosting)
        fields = fetch_jsonld(payload.url)
        if fields:
            fields["platform"] = platform
            fields["source_url"] = source_url
            return ExtractResponse(**fields)

        # 2. Fall back to Jina + NLP
        try:
            text = fetch_text_from_url(payload.url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")
    else:
        text = payload.text
        platform = None
        source_url = None

    # 3. Try LLM extraction (Groq); fall back to regex/spaCy if unavailable
    fields = extract_fields_llm(text) or extract_fields(text)
    fields["platform"] = fields.get("platform") or platform
    fields["source_url"] = source_url

    return ExtractResponse(**fields)
