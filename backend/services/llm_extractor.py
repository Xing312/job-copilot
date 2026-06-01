import json
import os

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """\
You are a job posting parser. Extract structured fields from the job posting text provided.
Return ONLY a valid JSON object with these keys (omit any field you cannot determine):
  - title        (string) job title
  - company      (string) hiring company name
  - location     (string) city/state or region, e.g. "San Francisco, CA" or "Remote"
  - salary_min   (integer) annual salary lower bound in USD, no commas
  - salary_max   (integer) annual salary upper bound in USD, no commas
  - work_type    (string) one of: Remote, Hybrid, Onsite

Rules:
- Do NOT include markdown fences or any text outside the JSON object.
- If a salary range is hourly, convert to annual (multiply by 2080).
- If only one salary figure is present, put it in salary_min.
- For work_type, prefer the most specific label (Hybrid > Remote > Onsite).
"""


def extract_fields_llm(text: str) -> dict | None:
    """Call Groq LLM to extract job fields. Returns None if unavailable or on any error."""
    if not _GROQ_API_KEY:
        return None

    try:
        from groq import Groq
    except ImportError:
        return None

    try:
        client = Groq(api_key=_GROQ_API_KEY)
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[:8000]},
            ],
            temperature=0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"LLM extraction failed ({e}), falling back to regex/NER")
        return None

    result = {}
    if title := data.get("title"):
        result["title"] = str(title).strip()
    if company := data.get("company"):
        result["company"] = str(company).strip()
    if location := data.get("location"):
        result["location"] = str(location).strip()
    if work_type := data.get("work_type"):
        if work_type in ("Remote", "Hybrid", "Onsite"):
            result["work_type"] = work_type
    for key in ("salary_min", "salary_max"):
        val = data.get(key)
        if val is not None:
            try:
                result[key] = int(val)
            except (TypeError, ValueError):
                pass

    return result if result.get("title") else None
