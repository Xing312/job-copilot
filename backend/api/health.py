import os

from fastapi import APIRouter

from services.llm_extractor import groq_available

router = APIRouter()


@router.get("/health")
def health():
    """Report which optional extraction backends are actually wired up.

    Surfaces silent degradations: if `groq_available` is false the pipeline is
    falling back to regex/spaCy (missing package or unset GROQ_API_KEY), and if
    `jina_configured` is false the Jina Reader fallback will 401 on SPA pages.
    """
    return {
        "status": "ok",
        "groq_available": groq_available(),
        "jina_configured": bool(os.getenv("JINA_API_KEY")),
    }
