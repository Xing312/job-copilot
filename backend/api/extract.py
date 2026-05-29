from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.extractor import fetch_jsonld, fetch_text_from_url, detect_platform, extract_fields

router = APIRouter()


class ExtractRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None


class ExtractResponse(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    work_type: Optional[str] = None
    platform: Optional[str] = None
    source_url: Optional[str] = None


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

    fields = extract_fields(text)
    fields["platform"] = fields.get("platform") or platform
    fields["source_url"] = source_url

    return ExtractResponse(**fields)
