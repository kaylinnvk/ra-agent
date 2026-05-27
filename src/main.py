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
from src.classifier import classify_text
from src.notifier import notify, format_message

def run_scan() -> None:
    if not settings.ra_website_url:
        raise ValueError("RA_WEBSITE_URL is missing. Please set it in your .env file.")

    print(f"Scanning: {settings.ra_website_url}")

    init_db()
    items = scan_basic_links(settings.ra_website_url)

    print(f"Found {len(items)} links/items on page.")

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
            source=settings.ra_website_url,
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
        "Scan summary: "
        f"new_relevant={new_relevant_count}, "
        f"already_seen={skipped_seen_count}, "
        f"non_relevant={filtered_non_relevant_count}"
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
