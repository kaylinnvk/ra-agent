from dataclasses import dataclass
import json
from typing import Any

import requests

from src.config import settings

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_LLM_DISABLED_FOR_RUN = False

@dataclass
class ClassificationResult:
    score: int
    matched_keywords: list[str]
    is_relevant: bool
    is_ra_opening: bool = False
    professor_group: str = ""
    topic_area: str = ""
    deadline: str = ""
    relevance_reason: str = ""
    source: str = "keyword"
    raw_llm_response: dict[str, Any] | None = None


_SYSTEM_PROXY_SESSION = requests.Session()
_NO_PROXY_SESSION = requests.Session()
_NO_PROXY_SESSION.trust_env = False


def _post(url: str, **kwargs) -> requests.Response:
    use_system_proxy = getattr(settings, "use_system_proxy", False)
    session = _SYSTEM_PROXY_SESSION if use_system_proxy else _NO_PROXY_SESSION
    if not use_system_proxy:
        session.trust_env = False
        _NO_PROXY_SESSION.trust_env = False
    return session.post(url, **kwargs)


def reset_llm_runtime_state() -> None:
    global _LLM_DISABLED_FOR_RUN
    _LLM_DISABLED_FOR_RUN = False


def _disable_llm_for_run(reason: str) -> None:
    global _LLM_DISABLED_FOR_RUN
    _LLM_DISABLED_FOR_RUN = True
    print(f"LLM classification disabled for the rest of this run: {reason}")


def _log_llm_attempt(
    *,
    run_id: int | None,
    title: str,
    url: str,
    status: str,
    response_json: Any | None = None,
    parsed_json: Any | None = None,
    error_message: str = "",
) -> None:
    try:
        from src.db import log_llm_response

        log_llm_response(
            run_id=run_id,
            title=title,
            url=url,
            provider="gemini",
            model=settings.gemini_model or "gemini-2.0-flash",
            status=status,
            response_json=response_json,
            parsed_json=parsed_json,
            error_message=error_message,
        )
    except Exception as exc:
        print(f"LLM response logging failed: {exc}")


def _error_details(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)

    details = {
        "type": type(exc).__name__,
        "message": str(exc),
        "status_code": getattr(response, "status_code", None),
        "response_body": getattr(response, "text", ""),
    }
    return json.dumps(details, ensure_ascii=False)


def _is_rate_limited(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 429


KEYWORDS = {
    # English
    "ra": 2,
    "research assistant": 4,
    "student helper": 3,
    "research intern": 4,
    "research internship": 4,
    "recruitment": 2,
    "opening": 2,
    "hiring": 2,
    "llm": 4,
    "large language model": 4,
    "ai agent": 4,
    "ai agents": 4,
    "agentic": 3,
    "agentic ai": 4,
    "reinforcement learning": 4,
    "rl": 3,
    "machine learning": 3,
    "ml": 2,
    "data science": 3,
    "ai systems": 4,
    "computer vision": 4,
    "cv": 2,
    "natural language processing": 4,
    "nlp": 3,
    "deep learning": 4,
    "deepfake": 5,
    "deep fake": 5,

    # Chinese
    "研究助理": 4,
    "科研助理": 4,
    "学生助理": 3,
    "招募": 2,
    "招聘": 2,
    "大模型": 4,
    "大语言模型": 4,
    "llm": 4,
    "ai智能体": 4,
    "智能体": 4,
    "智能体式": 3,
    "强化学习": 4,
    "机器学习": 3,
    "人工智能": 3,
    "人工智能系统": 4,
    "数据科学": 3,
    "计算机视觉": 4,
    "自然语言处理": 4,
    "深度学习": 4,
    "深度伪造": 5,
}

FOCUS_KEYWORDS = {
    "llm",
    "large language model",
    "ai agent",
    "ai agents",
    "agentic",
    "agentic ai",
    "reinforcement learning",
    "rl",
    "machine learning",
    "ml",
    "computer vision",
    "cv",
    "natural language processing",
    "nlp",
    "deep learning",
    "deepfake",
    "deep fake",
    "ai systems",
    "大模型",
    "大语言模型",
    "ai智能体",
    "智能体",
    "智能体式",
    "强化学习",
    "机器学习",
    "人工智能",
    "人工智能系统",
    "计算机视觉",
    "自然语言处理",
    "深度学习",
    "深度伪造",
}

def classify_text(
    title: str,
    snippet: str = "",
    min_score: int = 2,
    run_id: int | None = None,
    url: str = "",
) -> ClassificationResult:
    keyword_result = classify_with_keywords(title=title, snippet=snippet, min_score=min_score)

    if settings.use_llm_classifier and settings.gemini_api_key:
        if not keyword_result.is_relevant:
            print(
                "LLM classification skipped; keyword prefilter did not mark item relevant: "
                f"{title}"
            )
            return keyword_result

        if _LLM_DISABLED_FOR_RUN:
            print(
                "LLM classification skipped; Gemini is disabled for this run after a prior rate-limit/error: "
                f"{title}"
            )
            return keyword_result

        try:
            result = classify_with_llm(
                title=title,
                snippet=snippet,
                min_score=min_score,
                keyword_result=keyword_result,
            )
            raw_response = (result.raw_llm_response or {}).get("provider_response")
            parsed_json = (result.raw_llm_response or {}).get("parsed_json")
            _log_llm_attempt(
                run_id=run_id,
                title=title,
                url=url,
                status="success",
                response_json=raw_response,
                parsed_json=parsed_json,
            )
            return result
        except Exception as exc:
            _log_llm_attempt(
                run_id=run_id,
                title=title,
                url=url,
                status="failed",
                error_message=_error_details(exc),
            )
            print(f"LLM classification failed; using keyword result: {exc}")
            if _is_rate_limited(exc):
                _disable_llm_for_run("Gemini returned HTTP 429 rate limit/quota error.")

    return keyword_result

def classify_with_keywords(title: str, snippet: str = "", min_score: int = 2) -> ClassificationResult:
    text = f"{title} {snippet}".lower()
    matched = []
    score = 0

    for keyword, weight in KEYWORDS.items():
        if keyword.lower() in text:
            matched.append(keyword)
            score += weight

    has_focus_keyword = any(keyword.lower() in FOCUS_KEYWORDS for keyword in matched)

    return ClassificationResult(
        score=score,
        matched_keywords=matched,
        is_relevant=(score >= min_score) and has_focus_keyword,
        is_ra_opening=any(
            keyword in matched
            for keyword in (
                "ra",
                "research assistant",
                "student helper",
                "research intern",
                "research internship",
                "ç ”ç©¶åŠ©ç†",
                "ç§‘ç ”åŠ©ç†",
                "å­¦ç”ŸåŠ©ç†",
            )
        ),
        relevance_reason="Matched keyword filter.",
    )

def classify_with_llm(
    title: str,
    snippet: str,
    min_score: int,
    keyword_result: ClassificationResult,
) -> ClassificationResult:
    prompt = (
        "Classify this webpage item for a student looking for AI/ML-related "
        "research assistant opportunities. Return only valid JSON with these keys: "
        "is_ra_opening boolean, professor_group string, topic_area string, "
        "deadline string, fit_score integer from 0 to 10, "
        "why_relevant string, matched_keywords array of strings.\n\n"
        f"Title: {title}\n"
        f"Snippet: {snippet[:2500]}"
    )

    gemini_base_url = (settings.gemini_base_url or DEFAULT_GEMINI_BASE_URL).rstrip("/")
    gemini_model = settings.gemini_model or "gemini-2.0-flash"

    response = _post(
        f"{gemini_base_url}/models/{gemini_model}:generateContent",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key,
        },
        json={
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "You are a precise RA opportunity classifier. "
                            "Be conservative: only mark is_ra_opening true when the item "
                            "appears to be a research assistant, research intern, student "
                            "helper, lab/group recruitment, or similar research opening."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        },
        timeout=30,
    )
    response.raise_for_status()

    raw_response = response.json()
    content = raw_response["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(content)

    fit_score = int(data.get("fit_score") or 0)
    matched_keywords = data.get("matched_keywords")
    if not isinstance(matched_keywords, list):
        matched_keywords = []

    normalized_keywords = [
        str(keyword).strip()
        for keyword in matched_keywords
        if str(keyword).strip()
    ]

    if not normalized_keywords:
        normalized_keywords = keyword_result.matched_keywords

    is_ra_opening = bool(data.get("is_ra_opening"))

    return ClassificationResult(
        score=fit_score,
        matched_keywords=normalized_keywords,
        is_relevant=is_ra_opening and fit_score >= min_score,
        is_ra_opening=is_ra_opening,
        professor_group=str(data.get("professor_group") or "").strip(),
        topic_area=str(data.get("topic_area") or "").strip(),
        deadline=str(data.get("deadline") or "").strip(),
        relevance_reason=str(data.get("why_relevant") or "").strip(),
        source="llm",
        raw_llm_response={
            "provider_response": raw_response,
            "parsed_json": data,
        },
    )
