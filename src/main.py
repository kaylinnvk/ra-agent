import argparse
from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.db import (
    init_db,
    already_seen,
    save_opportunity,
    mark_notified,
    compute_content_hash,
)
from src.scanner import scan_basic_links
from src.outlook import fetch_outlook_messages, has_outlook_config
from src.classifier import classify_text
from src.notifier import notify, format_message

def process_items(source: str, items) -> tuple[int, int, int]:
    skipped_seen_count = 0
    filtered_non_relevant_count = 0
    new_relevant_count = 0

    for item in items:
        content_hash = compute_content_hash(item.title, item.snippet)

        if already_seen(item.url, content_hash):
            skipped_seen_count += 1
            continue

        result = classify_text(
            title=item.title,
            snippet=item.snippet,
            min_score=settings.min_score,
        )

        if not result.is_relevant:
            filtered_non_relevant_count += 1
            continue

        save_opportunity(
            source=source,
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            content_hash=content_hash,
            score=result.score,
        )

        message = format_message(
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            score=result.score,
            matched_keywords=result.matched_keywords,
            professor_group=result.professor_group,
            topic_area=result.topic_area,
            deadline=result.deadline,
            relevance_reason=result.relevance_reason,
            classifier_source=result.source,
        )

        notify(message)
        mark_notified(item.url, content_hash)
        new_relevant_count += 1

    print(
        f"Source summary ({source}): "
        f"new_relevant={new_relevant_count}, "
        f"already_seen={skipped_seen_count}, "
        f"non_relevant={filtered_non_relevant_count}"
    )
    return new_relevant_count, skipped_seen_count, filtered_non_relevant_count


def run_scan() -> None:
    if not settings.ra_website_url and not has_outlook_config():
        raise ValueError(
            "No sources configured. Set RA_WEBSITE_URL or enable USE_OUTLOOK_SOURCE with Microsoft Graph settings."
        )

    init_db()

    total_new_relevant = 0
    total_seen = 0
    total_non_relevant = 0

    if settings.ra_website_url:
        print(f"Scanning website: {settings.ra_website_url}")
        items = scan_basic_links(settings.ra_website_url)
        print(f"Found {len(items)} links/items on page.")
        new_count, seen_count, non_relevant_count = process_items(settings.ra_website_url, items)
        total_new_relevant += new_count
        total_seen += seen_count
        total_non_relevant += non_relevant_count

    if has_outlook_config():
        outlook_source = f"outlook:{settings.outlook_mailbox}/{settings.outlook_folder}"
        print(f"Scanning Outlook mailbox: {settings.outlook_mailbox}/{settings.outlook_folder}")
        items = fetch_outlook_messages()
        print(f"Found {len(items)} Outlook messages.")
        new_count, seen_count, non_relevant_count = process_items(outlook_source, items)
        total_new_relevant += new_count
        total_seen += seen_count
        total_non_relevant += non_relevant_count

    print(
        "Scan summary: "
        f"new_relevant={total_new_relevant}, "
        f"already_seen={total_seen}, "
        f"non_relevant={total_non_relevant}"
    )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    args = parser.parse_args()

    if args.once:
        run_scan()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_scan,
        "interval",
        minutes=settings.check_interval_minutes,
        next_run_time=None,
    )

    print(f"Agent started. It will scan every {settings.check_interval_minutes} minutes.")
    print("Press Ctrl+C to stop.")

    # Run once immediately
    run_scan()

    scheduler.start()

if __name__ == "__main__":
    main()
