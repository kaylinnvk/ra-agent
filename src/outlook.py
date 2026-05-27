from html import unescape
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from src.config import settings
from src.scanner import WebItem


GRAPH_SCOPE = "https://graph.microsoft.com/.default"


def has_outlook_config() -> bool:
    return bool(
        settings.use_outlook_source
        and settings.microsoft_tenant_id
        and settings.microsoft_client_id
        and settings.microsoft_client_secret
        and settings.outlook_mailbox
    )


def get_graph_access_token() -> str:
    response = requests.post(
        settings.microsoft_token_url,
        data={
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "scope": GRAPH_SCOPE,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _clean_text(text: str) -> str:
    return " ".join((text or "").split())


def _clean_body(body: dict | None, body_preview: str = "") -> str:
    if not isinstance(body, dict):
        return _clean_text(body_preview)

    content = body.get("content") or ""
    content_type = str(body.get("contentType") or "").lower()
    if content_type == "html":
        text = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    else:
        text = content

    return _clean_text(unescape(text or body_preview))


def _sender_text(message: dict) -> str:
    sender = message.get("from") or message.get("sender") or {}
    email = sender.get("emailAddress") if isinstance(sender, dict) else None
    if not isinstance(email, dict):
        return ""

    name = _clean_text(str(email.get("name") or ""))
    address = _clean_text(str(email.get("address") or ""))
    if name and address:
        return f"{name} <{address}>"
    return name or address


def _message_url(message: dict) -> str:
    web_link = message.get("webLink")
    if isinstance(web_link, str) and web_link.strip():
        return web_link.strip()

    message_id = str(message.get("id") or "").strip()
    mailbox = quote(settings.outlook_mailbox, safe="")
    if message_id:
        return f"{settings.graph_base_url.rstrip('/')}/users/{mailbox}/messages/{quote(message_id, safe='')}"
    return f"{settings.graph_base_url.rstrip('/')}/users/{mailbox}/messages"


def _message_to_item(message: dict) -> WebItem | None:
    subject = _clean_text(str(message.get("subject") or ""))
    if not subject:
        return None

    sender = _sender_text(message)
    received = _clean_text(str(message.get("receivedDateTime") or ""))
    preview = _clean_body(message.get("body"), str(message.get("bodyPreview") or ""))

    snippet_parts = []
    if sender:
        snippet_parts.append(f"From: {sender}")
    if received:
        snippet_parts.append(f"Received: {received}")
    if preview:
        snippet_parts.append(f"Preview: {preview}")

    return WebItem(
        title=subject,
        url=_message_url(message),
        snippet=" | ".join(snippet_parts)[:900],
    )


def _folder_path() -> str:
    folder = settings.outlook_folder.strip().strip("/")
    mailbox = quote(settings.outlook_mailbox, safe="")
    if not folder or folder.lower() == "messages":
        return f"/users/{mailbox}/messages"
    return f"/users/{mailbox}/mailFolders/{quote(folder, safe='')}/messages"


def fetch_outlook_messages() -> list[WebItem]:
    token = get_graph_access_token()
    url = f"{settings.graph_base_url.rstrip('/')}{_folder_path()}"

    params = {
        "$top": max(1, min(settings.outlook_max_messages, 100)),
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,sender,receivedDateTime,bodyPreview,body,webLink",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'outlook.body-content-type="text"',
    }

    search_query = settings.outlook_search_query.strip()
    if search_query:
        params["$search"] = f'"{search_query.replace(chr(34), "")}"'
        params.pop("$orderby", None)

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    messages = response.json().get("value", [])
    if not isinstance(messages, list):
        return []

    items = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        item = _message_to_item(message)
        if item is not None:
            items.append(item)

    return items
