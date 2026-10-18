# src/main.py

import os
import json
import logging
import argparse
from dotenv import dotenv_values
from rss_reader import fetch_feeds
from llm_filter import filter_stories
from summarizer import group_and_summarize
from utils import setup_logger
from article_history import ArticleHistory

# Import optional output modules
try:
    from slack_publisher import publish_to_slack
except ImportError:
    publish_to_slack = None

try:
    from email_reporter import send_email
except ImportError:
    send_email = None

try:
    from web_dashboard import save_summary, run_dashboard
except ImportError:
    save_summary = None
    run_dashboard = None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="RSS Feed Monitor")
    parser.add_argument(
        "--output",
        choices=["console", "slack", "email", "web"],
        default="console",
        help="Output method (default: console)",
    )
    parser.add_argument(
        "--web-server", action="store_true", help="Run the web dashboard server"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Port for web dashboard (default: WEB_DASHBOARD_PORT in .env, or 5001)"
    )
    parser.add_argument(
        "--history-retention",
        type=int,
        default=None,
        help="Number of days to retain article history (default: HISTORY_RETENTION_DAYS in .env, or 30)",
    )
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Ignore article history (process all articles)",
    )
    
    # New testing and diagnostic flags
    parser.add_argument(
        "--test-filter",
        action="store_true",
        help="Run the filter test against curated test articles",
    )
    parser.add_argument(
        "--review-mode",
        action="store_true",
        help="Launch interactive article review tool",
    )
    parser.add_argument(
        "--analyze-feeds",
        action="store_true",
        help="Analyze RSS feeds for disaster content patterns",
    )
    parser.add_argument(
        "--verbose-filter",
        action="store_true",
        help="Enable detailed logging for filter decisions",
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Handle testing and diagnostic modes first
    if args.test_filter:
        from test_filter import main as test_filter_main
        logger = setup_logger()
        logger.info("Running filter test...")
        return test_filter_main()
    
    if args.review_mode:
        from review_articles import main as review_main
        logger = setup_logger() 
        logger.info("Starting interactive article review...")
        return review_main()
    
    if args.analyze_feeds:
        from analyze_feeds import main as analyze_main
        logger = setup_logger()
        logger.info("Starting feed analysis...")
        return analyze_main()

    # Load environment variables manually to properly handle multi-line values
    env_vars = dotenv_values(".env")
    openai_api_key = env_vars.get("OPENAI_API_KEY")

    # Setup logger
    logger = setup_logger()
    logger.info("Starting RSS Feed Monitor...")

    # Parse RSS feeds from .env
    rss_feeds = env_vars.get("RSS_FEEDS", "")

    if "\n" in rss_feeds:
        rss_feed_list = [url.strip() for url in rss_feeds.split("\n") if url.strip()]
    else:
        rss_feed_list = [url.strip() for url in rss_feeds.split(",") if url.strip()]

    logger.info(f"Final RSS Feed List: {rss_feed_list}")

    # Parse model configuration
    filter_prompt = env_vars.get("FILTER_PROMPT", "")
    filter_model = env_vars.get("FILTER_MODEL", "gpt-6-luna")
    group_model = env_vars.get("GROUP_MODEL", "gpt-5-mini")
    summarize_model = env_vars.get("SUMMARIZE_MODEL", "gpt-6-luna")

    # Get history retention period from args or env
    history_retention_days = (
        args.history_retention
        if args.history_retention is not None
        else int(env_vars.get("HISTORY_RETENTION_DAYS", 30))
    )

    # Get web dashboard port from args or env
    web_port = (
        args.port if args.port is not None else int(env_vars.get("WEB_DASHBOARD_PORT", 5001))
    )

    if not openai_api_key:
        logger.error("OPENAI_API_KEY is not set in the .env file")
        return

    # Check if we should run the web server only
    if args.web_server and run_dashboard:
        logger.info(f"Starting web dashboard server on port {web_port}...")
        run_dashboard(port=web_port, debug=False)
        return

    # Initialize article history
    article_history = ArticleHistory(retention_days=history_retention_days)

    # Fetch articles
    logger.info("Fetching RSS feeds...")
    articles = fetch_feeds(rss_feed_list)
    logger.info(f"Fetched {len(articles)} articles.")

    # Filter out previously published articles unless --ignore-history is specified
    if not args.ignore_history:
        unique_articles = article_history.filter_published(articles)
        logger.info(
            f"{len(unique_articles)} unique articles after filtering previously published ones."
        )

        # If no new articles, exit early with appropriate messaging
        if not unique_articles:
            logger.info("No new articles to process.")
            # Create an empty summary for outputs that expect one
            empty_summary = {
                "topics": [],
                "message": "No new articles found since last update.",
            }

            # Handle outputs that need a summary even when empty
            if args.output == "web" and save_summary:
                save_summary(empty_summary)

            if args.output == "console":
                print(json.dumps(empty_summary, indent=4))

            return
    else:
        logger.info("Article history check skipped (--ignore-history flag used).")
        unique_articles = articles

    # The same link can arrive from two feeds; filtering both copies would
    # let one copy's rejection mark the link that the other copy passed.
    seen_links, deduped = set(), []
    for a in unique_articles:
        key = a.get("link") or "title:" + (a.get("title") or "")
        if key not in seen_links:
            seen_links.add(key)
            deduped.append(a)
    if len(deduped) < len(unique_articles):
        logger.info(f"Dropped {len(unique_articles) - len(deduped)} duplicate article(s) within this run.")
    unique_articles = deduped

    # Filter articles using LLM
    logger.info("Filtering articles using LLM...")
    if args.verbose_filter:
        logger.info("Verbose filtering enabled - detailed decisions will be logged")
    
    filtered_articles, errored_articles = filter_stories(
        unique_articles,
        filter_prompt,
        filter_model,
        openai_api_key,
        verbose=args.verbose_filter,
        return_errors=True,
    )
    logger.info(
        f"{len(filtered_articles)} articles remain after filtering "
        f"({len(errored_articles)} errored and will be retried next run)."
    )

    # Record rejected articles so they are not re-filtered on every run.
    # Errored articles are deliberately left unrecorded so they get retried.
    if not args.ignore_history:
        rejected_articles = [
            a for a in unique_articles
            if a not in filtered_articles and a not in errored_articles
        ]
        if rejected_articles:
            article_history.mark_as_published(rejected_articles, status="rejected")
            logger.info(
                f"Recorded {len(rejected_articles)} rejected articles so they are not re-filtered."
            )

    # If no articles remain after filtering, exit early without sending reports
    if not filtered_articles:
        logger.info("No articles meet the filtering criteria. No reports will be sent.")
        return

    # Group and summarize
    logger.info("Grouping and summarizing articles...")
    summary = group_and_summarize(
        filtered_articles, group_model, summarize_model, openai_api_key
    )

    # Output handling based on selected method. Articles are marked as published
    # only after the selected output succeeds, so a failed delivery is retried
    # on the next run instead of being silently lost.
    delivered = False

    if args.output == "console" or args.output == "web":
        # Output the structured JSON summary to console
        output_json = json.dumps(summary, indent=4)
        logger.info("Summary generated:")
        print(output_json)
        delivered = True

        # Save for web dashboard if requested
        if args.output == "web" and save_summary:
            save_summary(summary)
            logger.info("Summary saved for web dashboard.")

    elif args.output == "slack":
        if publish_to_slack:
            # Get Slack webhook URL from environment
            slack_webhook = env_vars.get("SLACK_WEBHOOK_URL")
            if not slack_webhook:
                logger.error("SLACK_WEBHOOK_URL is not set in the .env file")
                return

            logger.info("Publishing to Slack...")
            delivered_links = set()
            delivered = publish_to_slack(summary, slack_webhook, delivered_links=delivered_links)
            if delivered:
                logger.info("Successfully published to Slack.")
            else:
                # A summary sent as several messages can fail part-way: mark
                # what Slack accepted so it is not posted twice, retry the rest.
                partial = [a for a in filtered_articles if a.get("link") in delivered_links]
                if partial and not args.ignore_history:
                    article_history.mark_as_published(partial)
                logger.error(
                    f"Failed to publish to Slack; {len(partial)} delivered article(s) marked, "
                    f"{len(filtered_articles) - len(partial)} will be retried next run."
                )
        else:
            logger.error(
                "Slack publisher module not available. Install required dependencies."
            )

    elif args.output == "email":
        if send_email:
            # Get email configuration from environment
            smtp_config = {
                "server": env_vars.get("SMTP_SERVER"),
                "port": int(env_vars.get("SMTP_PORT", 587)),
                "username": env_vars.get("SMTP_USERNAME"),
                "password": env_vars.get("SMTP_PASSWORD"),
                "use_tls": env_vars.get("SMTP_USE_TLS", "True").lower() == "true",
            }

            recipients = [
                r.strip()
                for r in env_vars.get("EMAIL_RECIPIENTS", "").split(",")
                if r.strip()
            ]

            if not all(
                [
                    smtp_config["server"],
                    smtp_config["username"],
                    smtp_config["password"],
                ]
            ):
                logger.error("Email configuration incomplete in .env file")
                return

            if not recipients:
                logger.error("No email recipients specified")
                return

            logger.info(f"Sending email to {len(recipients)} recipients...")
            delivered = send_email(summary, smtp_config, recipients)
            if delivered:
                logger.info("Email sent successfully.")
            else:
                logger.error("Failed to send email. Articles will be retried next run.")
        else:
            logger.error(
                "Email reporter module not available. Install required dependencies."
            )

    # Mark reported articles as published only after successful delivery
    if delivered and not args.ignore_history:
        article_history.mark_as_published(filtered_articles)
        logger.info(f"Marked {len(filtered_articles)} articles as published.")

    # Run web server if requested (after history bookkeeping — this call blocks)
    if args.output == "web" and delivered and run_dashboard:
        logger.info(f"Starting web dashboard server on port {web_port}...")
        run_dashboard(port=web_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
