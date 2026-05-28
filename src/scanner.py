from dataclasses import dataclass
import hashlib
import json
import re
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from src.config import settings

@dataclass
class WebItem:
    title: str
    url: str
    snippet: str


@dataclass
class FetchDebug:
    method: str = "requests"
    http_status: int | None = None
    response_length: int = 0
    raw_html_start: str = ""


GENERIC_HEADINGS = {
    "all positions",
    "positions",
    "people",
    "filter",
    "sort",
    "relevant",
    "date",
    "hot",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Connection": "close",
}
API_REQUEST_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json",
}

_SYSTEM_PROXY_SESSION = requests.Session()
_NO_PROXY_SESSION = requests.Session()
_NO_PROXY_SESSION.trust_env = False

def _get(url: str, **kwargs) -> requests.Response:
    session = _SYSTEM_PROXY_SESSION if settings.use_system_proxy else _NO_PROXY_SESSION
    if not settings.use_system_proxy:
        session.trust_env = False
        _NO_PROXY_SESSION.trust_env = False
    return session.get(url, **kwargs)

def _safe_preview(text: str, limit: int = 500) -> str:
    return (text or "")[:limit].replace("\r", "\\r").replace("\n", "\\n")


def _log_debug(label: str, value) -> None:
    print(f"[scanner-debug] {label}: {value}")


def fetch_html(url: str) -> str:
    html, _debug = fetch_html_with_debug(url)
    return html


def fetch_html_with_debug(url: str) -> tuple[str, FetchDebug]:
    last_error: requests.RequestException | None = None

    for attempt in range(1, 4):
        try:
            response = _get(url, headers=REQUEST_HEADERS, timeout=20)
            response.raise_for_status()
            html = response.text
            return html, FetchDebug(
                method="requests",
                http_status=response.status_code,
                response_length=len(html),
                raw_html_start=_safe_preview(html),
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 3:
                print(f"Fetch failed on attempt {attempt}/3: {exc}")
                time.sleep(attempt * 2)

    raise RuntimeError(f"Could not fetch {url} after 3 attempts: {last_error}") from last_error


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _looks_like_generic_heading(title: str) -> bool:
    clean = _clean_text(title).lower()
    return clean in GENERIC_HEADINGS


def _make_fallback_url(page_url: str, title: str, snippet: str, index: int) -> str:
    digest = hashlib.sha1(f"{title}|{snippet}".encode("utf-8")).hexdigest()[:12]
    return f"{page_url}#item-{index}-{digest}"


def _extract_link_items(soup: BeautifulSoup, page_url: str) -> list[WebItem]:
    items: list[WebItem] = []

    for a in soup.find_all("a", href=True):
        title = _clean_text(a.get_text(" ", strip=True))
        href = a["href"].strip()

        if not title or len(title) < 4:
            continue

        full_url = urljoin(page_url, href)
        parent_text = _clean_text(a.parent.get_text(" ", strip=True)) if a.parent else ""

        items.append(
            WebItem(
                title=title,
                url=full_url,
                snippet=parent_text[:700],
            )
        )

    return items


def _extract_heading_card_items(soup: BeautifulSoup, page_url: str) -> list[WebItem]:
    items: list[WebItem] = []

    headings = soup.find_all(["h2", "h3", "h4"])
    for i, heading in enumerate(headings):
        title = _clean_text(heading.get_text(" ", strip=True))
        if len(title) < 6 or len(title) > 180 or _looks_like_generic_heading(title):
            continue

        block = heading.find_parent(["article", "li", "div", "section"]) or heading
        snippet = _clean_text(block.get_text(" ", strip=True))
        if snippet and snippet.startswith(title):
            snippet = _clean_text(snippet[len(title) :])

        anchor = block.find("a", href=True) if hasattr(block, "find") else None
        if anchor and anchor.get("href"):
            url = urljoin(page_url, anchor["href"].strip())
        else:
            url = _make_fallback_url(page_url, title=title, snippet=snippet, index=i)

        items.append(
            WebItem(
                title=title,
                url=url,
                snippet=snippet[:900],
            )
        )

    return items


def _count_candidate_card_elements(soup: BeautifulSoup) -> int:
    candidates = 0
    for heading in soup.find_all(["h2", "h3", "h4"]):
        title = _clean_text(heading.get_text(" ", strip=True))
        if len(title) >= 6 and len(title) <= 180 and not _looks_like_generic_heading(title):
            candidates += 1
    return candidates


def _walk_json(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_json(value)


def _extract_json_items(soup: BeautifulSoup, page_url: str) -> list[WebItem]:
    items: list[WebItem] = []
    scripts = soup.find_all("script")

    for script in scripts:
        script_text = (script.string or script.get_text() or "").strip()
        if not script_text:
            continue
        if script.get("id") != "__NEXT_DATA__" and "application/json" not in (script.get("type") or ""):
            continue

        try:
            payload = json.loads(script_text)
        except json.JSONDecodeError:
            continue

        for idx, obj in enumerate(_walk_json(payload)):
            title = ""
            for key in ("title", "positionTitle", "postTitle", "name"):
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    title = _clean_text(value)
                    break

            if not title or len(title) < 6 or _looks_like_generic_heading(title):
                continue

            snippet_parts: list[str] = []
            for key in ("description", "summary", "content", "professor", "professorName", "status", "deadline"):
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    snippet_parts.append(_clean_text(value))
                if isinstance(value, list):
                    snippet_parts.extend(_clean_text(str(v)) for v in value if str(v).strip())

            snippet = _clean_text(" | ".join(snippet_parts))

            url = ""
            for key in ("url", "href", "path", "slug"):
                value = obj.get(key)
                if isinstance(value, str) and value.strip():
                    url = urljoin(page_url, value.strip())
                    break

            if not url:
                url = _make_fallback_url(page_url, title=title, snippet=snippet, index=idx)

            items.append(WebItem(title=title, url=url, snippet=snippet[:900]))

    return items


def _extract_api_posts(page_url: str, max_pages: int = 3) -> list[WebItem]:
    """
    Dynamic-site fallback:
    tries a common JSON feed shape used by SPA boards (count/next/results).
    """
    parsed = urlparse(page_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    candidate_endpoints = [
        urljoin(origin, "/api/posts/"),
        urljoin(page_url, "api/posts/"),
    ]

    items: list[WebItem] = []

    for endpoint in candidate_endpoints:
        next_url = endpoint
        pages = 0
        local_items: list[WebItem] = []

        while next_url and pages < max_pages:
            pages += 1
            try:
                response = _get(next_url, headers=API_REQUEST_HEADERS, timeout=20)
                _log_debug("api_posts_endpoint", next_url)
                _log_debug("api_posts_http_status_code", getattr(response, "status_code", "unknown"))
                _log_debug("api_posts_response_length", len(getattr(response, "text", "") or ""))
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                _log_debug("api_posts_error", exc)
                local_items = []
                break

            results = data.get("results") if isinstance(data, dict) else None
            if not isinstance(results, list):
                _log_debug("api_posts_results_count", "not_a_list")
                local_items = []
                break
            _log_debug("api_posts_results_count", len(results))

            for post in results:
                if not isinstance(post, dict):
                    continue

                title = _clean_text(str(post.get("title", "")))
                if len(title) < 6:
                    continue

                post_id = str(post.get("id", "")).strip()
                post_url = urljoin(origin, f"/post/{post_id}") if post_id else endpoint

                tags = []
                raw_tags = post.get("tags", [])
                if isinstance(raw_tags, list):
                    for tag in raw_tags:
                        if isinstance(tag, dict) and tag.get("name"):
                            tags.append(str(tag["name"]))
                        elif isinstance(tag, str):
                            tags.append(tag)

                researcher_name = _clean_text(str(post.get("researcher_name", "") or ""))
                school = _clean_text(str(post.get("school", "") or ""))
                status = _clean_text(str(post.get("status", "") or ""))
                deadline = _clean_text(str(post.get("deadline", "") or ""))

                snippet_parts = [
                    str(post.get("description", "") or ""),
                    str(post.get("requirements", "") or ""),
                    f"Researcher: {researcher_name}" if researcher_name else "",
                    f"School: {school}" if school else "",
                    f"Status: {status}" if status else "",
                    f"Deadline: {deadline}" if deadline else "",
                    " ".join(tags),
                ]
                snippet = _clean_text(" | ".join(part for part in snippet_parts if part and part.strip()))

                local_items.append(WebItem(title=title, url=post_url, snippet=snippet[:900]))

            next_candidate = data.get("next") if isinstance(data, dict) else None
            next_url = next_candidate if isinstance(next_candidate, str) and next_candidate.strip() else ""

        if local_items:
            items.extend(local_items)
            break

    return items


def _deduplicate_items(items: list[WebItem]) -> list[WebItem]:
    unique: list[WebItem] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        key = (item.url, item.title.lower())
        if key in seen:
            continue

        # Ignore likely navigation/static URLs if we got no meaningful context.
        if not item.snippet and re.search(r"#(top|footer|header)$", item.url.lower()):
            continue

        seen.add(key)
        unique.append(item)

    return unique

def scan_basic_links(page_url: str) -> list[WebItem]:
    """
    Generic scanner:
    - Fetches one page
    - Looks for links
    - Treats each link as a possible opportunity item

    Later, you can customize this for a specific website's HTML structure.
    """
    _log_debug("source_url", page_url)
    _log_debug("fetch_method", "requests")
    _log_debug("use_system_proxy", settings.use_system_proxy)
    _log_debug("requests_trust_env", _SYSTEM_PROXY_SESSION.trust_env if settings.use_system_proxy else _NO_PROXY_SESSION.trust_env)
    _log_debug("playwright_used", "false")
    _log_debug("playwright_browser_launched", "not_applicable")

    try:
        html, fetch_debug = fetch_html_with_debug(page_url)
    except RuntimeError as exc:
        print(f"Scan skipped: {exc}")
        _log_debug("parsed_posts_before_deduplication", 0)
        _log_debug("posts_after_deduplication", 0)
        return []

    _log_debug("http_status_code", fetch_debug.http_status)
    _log_debug("response_length", fetch_debug.response_length)
    _log_debug("raw_html_first_500", fetch_debug.raw_html_start)

    soup = BeautifulSoup(html, "html.parser")
    page_title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    a_tag_count = len(soup.find_all("a"))
    card_candidate_count = _count_candidate_card_elements(soup)

    _log_debug("page_title", page_title or "(none)")
    _log_debug("a_tags_found", a_tag_count)
    _log_debug("candidate_post_card_elements_found", card_candidate_count)
    _log_debug("playwright_links_after_rendering", "not_applicable")
    _log_debug("playwright_cards_after_rendering", "not_applicable")

    items: list[WebItem] = []
    items.extend(_extract_link_items(soup, page_url))
    items.extend(_extract_heading_card_items(soup, page_url))
    items.extend(_extract_json_items(soup, page_url))
    items.extend(_extract_api_posts(page_url))
    deduplicated = _deduplicate_items(items)

    _log_debug("parsed_posts_before_deduplication", len(items))
    _log_debug("posts_after_deduplication", len(deduplicated))
    return deduplicated
