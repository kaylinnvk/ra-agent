import argparse
from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.db import (
    init_db,
    test_connection,
    start_agent_run,
    mark_stale_running_runs,
    finish_agent_run,
    log_source_check,
    save_seen_post,
    save_finding,
    mark_notified,
    compute_content_hash,
    db_backend,
    normalize_url,
    seen_post_diagnostics,
)
from src.scanner import scan_basic_links
from src.classifier import classify_text, reset_llm_runtime_state
from src.notifier import notify, format_message, send_gmail

def process_items(
    source: str,
    items,
    run_id: int | None = None,
    send_notifications: bool = True,
    persist: bool = True,
) -> tuple[int, int, int, int]:
    skipped_seen_count = 0
    filtered_non_relevant_count = 0
    new_posts_count = 0
    new_relevant_count = 0
    notifications_sent = 0

    for item in items:
        content_hash = compute_content_hash(item.title, item.snippet)
        normalized_url = normalize_url(item.url)
        diagnostics = (
            seen_post_diagnostics(item.url, content_hash)
            if persist
            else {
                "already_seen": False,
                "already_seen_by_url": False,
                "already_seen_by_hash": False,
            }
        )

        print(
            "[dedup-debug] "
            f"title={item.title!r} "
            f"normalized_url={normalized_url} "
            f"content_hash={content_hash} "
            f"already_seen_by_url={diagnostics['already_seen_by_url']} "
            f"already_seen_by_hash={diagnostics['already_seen_by_hash']}"
        )

        if persist and diagnostics["already_seen"]:
            print(
                "[dedup-debug] "
                f"title={item.title!r} inserted_into_seen_posts=False reason=already_seen"
            )
            skipped_seen_count += 1
            continue

        new_posts_count += 1
        inserted_into_seen_posts = False
        if persist:
            inserted_into_seen_posts = save_seen_post(
                source_name=source,
                title=item.title,
                url=item.url,
                content_hash=content_hash,
                notified=False,
            )
        print(
            "[dedup-debug] "
            f"title={item.title!r} inserted_into_seen_posts={inserted_into_seen_posts}"
        )

        result = classify_text(
            title=item.title,
            snippet=item.snippet,
            min_score=settings.min_score,
            run_id=run_id,
            url=item.url,
        )

        if not result.is_relevant:
            if persist:
                save_finding(
                    run_id=run_id,
                    title=item.title,
                    url=item.url,
                    source_name=source,
                    content_hash=content_hash,
                    is_relevant=False,
                    relevance_score=result.score,
                    reason=result.relevance_reason,
                    notified=False,
                )
            filtered_non_relevant_count += 1
            continue

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

        if send_notifications:
            notify(message)
            notifications_sent += 1
            if persist:
                mark_notified(item.url, content_hash)
        else:
            print(
                "Dry run notification skipped for "
                f"{item.title}: {item.url}"
            )

        if persist:
            save_finding(
                run_id=run_id,
                title=item.title,
                url=item.url,
                source_name=source,
                content_hash=content_hash,
                is_relevant=True,
                relevance_score=result.score,
                reason=result.relevance_reason,
                notified=send_notifications,
            )
        new_relevant_count += 1

    print(f"[scanner-debug] posts_after_gemini_filtering: {new_relevant_count}")
    print(
        f"Source summary ({source}): "
        f"new_posts={new_posts_count}, "
        f"new_relevant={new_relevant_count}, "
        f"already_seen={skipped_seen_count}, "
        f"non_relevant={filtered_non_relevant_count}, "
        f"notifications_sent={notifications_sent}"
    )
    return new_relevant_count, skipped_seen_count, filtered_non_relevant_count, notifications_sent


def run_scan(send_notifications: bool = True, persist: bool = True) -> None:
    reset_llm_runtime_state()

    if not settings.ra_website_url:
        print("[scanner-debug] configured_sources_count: 0")
        print("[scanner-debug] RA_WEBSITE_URL is empty")
        raise ValueError(
            "No sources configured. Set RA_WEBSITE_URL. Outlook/Microsoft Graph scanning is skipped for now."
        )

    init_db()
    print(f"[scanner-debug] db_backend_effective: {db_backend()}")
    print(f"[scanner-debug] DB_BACKEND_setting: {settings.db_backend}")
    print(f"[scanner-debug] DATABASE_URL_configured: {bool(settings.database_url)}")

    configured_sources = [settings.ra_website_url] if settings.ra_website_url else []
    print(f"[scanner-debug] configured_sources_count: {len(configured_sources)}")
    for source_url in configured_sources:
        print(f"[scanner-debug] configured_source_url: {source_url}")

    if persist:
        mark_stale_running_runs(sources_checked=len(configured_sources))

    run_id = start_agent_run(sources_checked=len(configured_sources)) if persist else None
    sources_checked = 0
    posts_found = 0
    new_posts = 0
    total_new_relevant = 0
    total_seen = 0
    total_non_relevant = 0
    notifications_sent = 0
    source_errors: list[str] = []

    for source_url in configured_sources:
        source_name = source_url
        sources_checked += 1
        try:
            print(f"Scanning website: {source_url}")
            items = scan_basic_links(source_url)
            posts_found += len(items)
            print(f"Found {len(items)} links/items on page.")
            (
                new_count,
                seen_count,
                non_relevant_count,
                sent_count,
            ) = process_items(
                source_name,
                items,
                run_id=run_id,
                send_notifications=send_notifications,
                persist=persist,
            )
            total_new_relevant += new_count
            total_seen += seen_count
            total_non_relevant += non_relevant_count
            notifications_sent += sent_count
            new_posts += max(0, len(items) - seen_count)
            if persist:
                log_source_check(
                    run_id=run_id,
                    source_name=source_name,
                    source_url=source_url,
                    status="success",
                    items_found=len(items),
                )
        except Exception as exc:
            message = f"{source_name}: {exc}"
            source_errors.append(message)
            print(f"Source failed: {message}")
            if persist:
                log_source_check(
                    run_id=run_id,
                    source_name=source_name,
                    source_url=source_url,
                    status="failed",
                    error_message=str(exc),
                )

    if persist and run_id is not None:
        if source_errors and sources_checked == len(source_errors):
            status = "failed"
        elif source_errors:
            status = "partial_success"
        else:
            status = "success"
        finish_agent_run(
            run_id=run_id,
            status=status,
            sources_checked=sources_checked,
            posts_found=posts_found,
            new_posts=new_posts,
            relevant_posts=total_new_relevant,
            notifications_sent=notifications_sent,
            error_message="; ".join(source_errors),
        )

    print(
        "Scan summary: "
        f"sources_checked={sources_checked}, "
        f"posts_found={posts_found}, "
        f"new_posts={new_posts}, "
        f"new_relevant={total_new_relevant}, "
        f"already_seen={total_seen}, "
        f"non_relevant={total_non_relevant}, "
        f"notifications_sent={notifications_sent}"
    )

    if source_errors and sources_checked == len(source_errors):
        raise RuntimeError("All sources failed: " + "; ".join(source_errors))


def test_gmail_notification() -> None:
    send_gmail(
        "[RA Opportunity Monitor]\n"
        "This is a deployment smoke test for Gmail notifications."
    )
    print("Gmail notification test sent.")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--check-db", action="store_true", help="Initialize and test the configured database")
    parser.add_argument("--test-gmail", action="store_true", help="Send a Gmail notification smoke test")
    parser.add_argument("--dry-run", action="store_true", help="Run one scan without writing findings or sending notifications")
    args = parser.parse_args()

    if args.check_db:
        print(test_connection())
        return

    if args.test_gmail:
        test_gmail_notification()
        return

    if args.dry_run:
        run_scan(send_notifications=False, persist=False)
        return

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
