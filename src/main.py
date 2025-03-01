# src/main.py

import os
import json
import logging
from dotenv import dotenv_values
from rss_reader import fetch_feeds
from llm_filter import filter_stories
from summarizer import group_and_summarize
from utils import setup_logger

def main():
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
    filter_model = env_vars.get("FILTER_MODEL", "gpt-4-turbo")
    group_model = env_vars.get("GROUP_MODEL", "gpt-4-turbo")
    summarize_model = env_vars.get("SUMMARIZE_MODEL", "gpt-4-turbo")

    if not openai_api_key:
        logger.error("OPENAI_API_KEY is not set in the .env file")
        return

    # Fetch articles
    logger.info("Fetching RSS feeds...")
    articles = fetch_feeds(rss_feed_list)
    logger.info(f"Fetched {len(articles)} articles.")

    # Filter articles
    logger.info("Filtering articles using LLM...")
    filtered_articles = filter_stories(articles, filter_prompt, filter_model, openai_api_key)
    logger.info(f"{len(filtered_articles)} articles remain after filtering.")

    # Group and summarize
    logger.info("Grouping and summarizing articles...")
    summary = group_and_summarize(filtered_articles, group_model, summarize_model, openai_api_key)

    # Output the structured JSON summary
    output_json = json.dumps(summary, indent=4)
    logger.info("Summary generated:")
    print(output_json)

if __name__ == "__main__":
    main()
