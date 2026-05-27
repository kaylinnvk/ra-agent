import smtplib
from email.message import EmailMessage

from src.config import settings

EMAIL_SUBJECT = "[RA ALERT] New Research Assistant Opening Found"

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
    compact_snippet = " ".join((snippet or "").split())
    if len(compact_snippet) > 420:
        compact_snippet = compact_snippet[:420].rstrip() + "..."

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
