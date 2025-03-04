# src/article_history.py

import os
import json
import logging
from datetime import datetime, timedelta


class ArticleHistory:
    """
    Manages the history of published articles to prevent duplicates.
    """

    def __init__(self, history_file="data/article_history.json", retention_days=30):
        """
        Initialize the article history tracker.

        Parameters:
            history_file (str): Path to store article history
            retention_days (int): Number of days to retain article history
        """
        self.history_file = history_file
        self.retention_days = retention_days
        self.history = self._load_history()

    def _load_history(self):
        """Load article history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading article history: {e}")
        return {"last_cleaned": datetime.now().isoformat(), "articles": {}}

    def _save_history(self):
        """Save article history to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

            with open(self.history_file, "w") as f:
                json.dump(self.history, f)
        except Exception as e:
            logging.error(f"Error saving article history: {e}")

    def _clean_old_entries(self):
        """Remove entries older than retention_days."""
        now = datetime.now()
        last_cleaned = datetime.fromisoformat(
            self.history.get("last_cleaned", now.isoformat())
        )

        # Only clean once per day to avoid excessive I/O
        if (now - last_cleaned).days < 1:
            return

        cutoff_date = (now - timedelta(days=self.retention_days)).isoformat()
        cleaned_articles = {}

        for url, data in self.history["articles"].items():
            if data["timestamp"] >= cutoff_date:
                cleaned_articles[url] = data

        self.history["articles"] = cleaned_articles
        self.history["last_cleaned"] = now.isoformat()
        self._save_history()

        logging.info(
            f"Cleaned article history. Retained {len(cleaned_articles)} articles."
        )

    def is_published(self, article):
        """
        Check if an article has been published before.

        Parameters:
            article (dict): Article dictionary with at least 'link' key

        Returns:
            bool: True if article was previously published
        """
        url = article.get("link", "")
        return url in self.history["articles"]

    def mark_as_published(self, articles):
        """
        Mark articles as published.

        Parameters:
            articles (list): List of article dictionaries with at least 'link' key
        """
        now = datetime.now().isoformat()

        for article in articles:
            url = article.get("link", "")
            if url:
                self.history["articles"][url] = {
                    "title": article.get("title", ""),
                    "timestamp": now,
                }

        self._save_history()
        self._clean_old_entries()

    def filter_published(self, articles):
        """
        Filter out previously published articles.

        Parameters:
            articles (list): List of article dictionaries

        Returns:
            list: List of unpublished articles
        """
        return [article for article in articles if not self.is_published(article)]
