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
        """
        Load article history from file, falling back to the previous save.

        An unreadable history must not load as empty: every article still in
        the feeds would be posted again. If neither the file nor its .bak
        loads, the file is set aside as .corrupt-<time> and loading raises.
        """
        if not os.path.exists(self.history_file):
            logging.info(f"Article history file {self.history_file} not found, creating new history")
            return {"last_cleaned": datetime.now().isoformat(), "articles": {}}
        for path in (self.history_file, self.history_file + ".bak"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if path != self.history_file:
                    logging.error(f"Article history {self.history_file} unreadable; using backup {path}")
                logging.info(f"Loaded article history with {len(data.get('articles', {}))} articles from {path}")
                return data
            except FileNotFoundError:
                continue
            except Exception as e:
                logging.error(f"Error loading article history from {path}: {e}")
        corrupt = f"{self.history_file}.corrupt-{datetime.now():%Y%m%dT%H%M%S}"
        os.replace(self.history_file, corrupt)
        raise RuntimeError(
            f"Article history unreadable and no usable backup; set aside as {corrupt}. "
            "Refusing to start with an empty history, which would repost every article."
        )

    def _save_history(self):
        """Save article history atomically, keeping the previous save as .bak."""
        try:
            directory = os.path.dirname(self.history_file) or "."
            os.makedirs(directory, exist_ok=True)
            tmp = f"{self.history_file}.tmp"
            with open(tmp, "w") as f:
                json.dump(self.history, f)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(self.history_file):
                os.replace(self.history_file, self.history_file + ".bak")
            os.replace(tmp, self.history_file)
            logging.info(f"Saved article history with {len(self.history.get('articles', {}))} articles to {self.history_file}")
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

    @staticmethod
    def _key(article):
        """History key: the link, or the title for an article without one."""
        return article.get("link") or "title:" + (article.get("title") or "")

    def is_published(self, article):
        """
        Check if an article was published, or rejected in its current form.

        A rejection is remembered with the title it had: when the outlet
        updates the story under the same link (a location or toll added to an
        early wire item), the changed title makes it eligible to be filtered
        again.

        Parameters:
            article (dict): Article dictionary with at least 'link' key

        Returns:
            bool: True if the article should be skipped
        """
        entry = self.history["articles"].get(self._key(article))
        if entry is None:
            return False
        if entry.get("status") == "rejected" and entry.get("title", "") != article.get("title", ""):
            logging.info(f"Rejected article changed, filtering again: {article.get('title', 'Untitled')}")
            return False
        logging.debug(f"Article already published: {article.get('title', 'Untitled')}")
        return True

    def mark_as_published(self, articles, status="published"):
        """
        Record articles as handled.

        Parameters:
            articles (list): List of article dictionaries with at least 'link' key
            status (str): "published", or "rejected" for filter rejections
        """
        now = datetime.now().isoformat()

        for article in articles:
            self.history["articles"][self._key(article)] = {
                "title": article.get("title", ""),
                "timestamp": now,
                "status": status,
            }

        logging.info(f"Marked {len(articles)} articles as published")
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
        if not articles:
            logging.info("No articles to filter")
            return []
            
        total_articles = len(articles)
        filtered_articles = [article for article in articles if not self.is_published(article)]
        filtered_count = total_articles - len(filtered_articles)
        
        logging.info(f"Filtered out {filtered_count} of {total_articles} articles as previously published")
        
        return filtered_articles