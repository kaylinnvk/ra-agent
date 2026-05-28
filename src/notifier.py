import smtplib
from email.message import EmailMessage
import re

from src.config import settings

EMAIL_SUBJECT = "[RA ALERT] New Research Assistant Opening Found"


def _extract_professor_name(snippet: str) -> str:
    match = re.search(r"(?:Researcher|Professor|Prof\.?):\s*([^|]+)", snippet or "", re.IGNORECASE)
    if not match:
        return ""
    return " ".join(match.group(1).split()).strip()


def _merge_professor_group(professor_group: str, snippet: str) -> str:
    professor_group = " ".join((professor_group or "").split()).strip()
    professor_name = _extract_professor_name(snippet)

    if not professor_name:
        return professor_group
    if not professor_group:
        return professor_name
    if professor_name.lower() == professor_group.lower():
        return professor_group
    return f"{professor_name} / {professor_group}"


def _plain_text_summary(snippet: str) -> str:
    text = snippet or ""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", text)
    return " ".join(text.split())


def format_message(
    title: str,
    url: str,
    snippet: str,
    score: int,
    matched_keywords: list[str],
    professor_group: str = "",
    topic_area: str = "",
    deadline: str = "",
    relevance_reason: str = "",
    classifier_source: str = "keyword",
) -> str:
    keyword_text = ", ".join(matched_keywords[:8]) if matched_keywords else "None"
    compact_snippet = _plain_text_summary(snippet)
    if len(compact_snippet) > 420:
        compact_snippet = compact_snippet[:420].rstrip() + "..."
    professor_group = _merge_professor_group(professor_group, snippet)

    lines = [
        "[RA Opportunity Monitor]",
        f"Title: {title}",
        f"Fit score: {score}",
        f"Classifier: {classifier_source}",
        f"Matched: {keyword_text}",
    ]

    if professor_group:
        lines.append(f"Professor/group: {professor_group}")
    if topic_area:
        lines.append(f"Topic area: {topic_area}")
    if deadline:
        lines.append(f"Deadline: {deadline}")
    if relevance_reason:
        lines.append(f"Why relevant: {relevance_reason}")

    lines.extend(
        [
            f"URL: {url}",
            f"Summary: {compact_snippet}",
        ]
    )
    return "\n".join(lines)

def notify(message: str) -> None:
    if has_gmail_config():
        try:
            send_gmail(message)
            return
        except Exception as exc:
            print(f"Gmail notification failed: {exc}")

    print_console(message)

def has_gmail_config() -> bool:
    return bool(
        settings.gmail_host
        and settings.gmail_port
        and settings.gmail_user
        and settings.gmail_app_password
        and settings.gmail_to
    )

def send_gmail(message: str) -> None:
    email = EmailMessage()
    email["Subject"] = EMAIL_SUBJECT
    email["From"] = settings.gmail_from or settings.gmail_user
    email["To"] = settings.gmail_to
    email["Importance"] = "high"
    email["Priority"] = "urgent"
    email["X-Priority"] = "1"
    email.set_content(message)

    with smtplib.SMTP(settings.gmail_host, settings.gmail_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.gmail_user, settings.gmail_app_password)
        smtp.send_message(email)

def print_console(message: str) -> None:
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80 + "\n")
