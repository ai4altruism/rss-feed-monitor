import json
import os
from datetime import datetime, timedelta

import pytest

import article_history
from article_history import ArticleHistory

NOW = datetime(2026, 1, 31, 12, 0, 0)


@pytest.fixture
def frozen_now(monkeypatch):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(article_history, "datetime", Frozen)
    return NOW


def art(link, title="t"):
    return {"link": link, "title": title}


def test_new_history_starts_empty(history_file):
    assert ArticleHistory(history_file).history["articles"] == {}


def test_mark_as_published_persists_and_reloads(history_file):
    ArticleHistory(history_file).mark_as_published([art("http://x.test/1", "One")])

    reloaded = ArticleHistory(history_file)
    assert reloaded.is_published(art("http://x.test/1"))
    assert reloaded.history["articles"]["http://x.test/1"]["title"] == "One"


def test_filter_published_removes_only_known_links(history_file):
    h = ArticleHistory(history_file)
    h.mark_as_published([art("http://x.test/1")])

    out = h.filter_published([art("http://x.test/1"), art("http://x.test/2")])

    assert [a["link"] for a in out] == ["http://x.test/2"]


def test_filter_published_empty_input_returns_empty_list(history_file):
    assert ArticleHistory(history_file).filter_published([]) == []


def _seed(history_file, last_cleaned, entries):
    with open(history_file, "w") as f:
        json.dump({"last_cleaned": last_cleaned.isoformat(),
                   "articles": {k: {"title": "t", "timestamp": v.isoformat()} for k, v in entries.items()}}, f)


def test_retention_prune_keeps_entry_exactly_at_cutoff_and_drops_older(history_file, frozen_now):
    cutoff = NOW - timedelta(days=30)
    _seed(history_file, NOW - timedelta(days=2), {
        "at": cutoff, "older": cutoff - timedelta(seconds=1), "newer": NOW - timedelta(days=1)})
    h = ArticleHistory(history_file, retention_days=30)

    h.mark_as_published([art("http://x.test/new")])

    assert set(h.history["articles"]) == {"at", "newer", "http://x.test/new"}


def test_retention_prune_runs_at_most_once_per_day(history_file, frozen_now):
    _seed(history_file, NOW - timedelta(hours=23), {"old": NOW - timedelta(days=90)})
    h = ArticleHistory(history_file, retention_days=30)

    h.mark_as_published([art("http://x.test/new")])

    assert "old" in h.history["articles"]


@pytest.mark.xfail(strict=True, reason="BUG: a corrupt or truncated history file loads as empty history silently (no raise, no backup)")
def test_corrupt_history_file_raises_or_is_backed_up(history_file, workdir):
    with open(history_file, "w") as f:
        f.write('{"last_cleaned": "2026-01-01T00:00:00", "articles": {"http://x')
    try:
        ArticleHistory(history_file)
    except Exception:
        return
    siblings = [n for n in os.listdir(workdir / "data") if n != "article_history.json"]
    assert siblings, "corrupt file was silently replaced by an empty history"


@pytest.mark.xfail(strict=True, reason="BUG: _save_history writes in place, so a failed write truncates the existing history")
def test_failed_save_leaves_previous_history_intact(history_file, monkeypatch):
    h = ArticleHistory(history_file)
    h.mark_as_published([art("http://x.test/1")])
    before = open(history_file).read()

    def partial_dump(obj, f, *a, **k):
        f.write('{"last_cle')
        raise OSError("disk full")

    monkeypatch.setattr(article_history.json, "dump", partial_dump)
    h.mark_as_published([art("http://x.test/2")])

    assert open(history_file).read() == before


@pytest.mark.xfail(strict=True, reason="BUG: an empty link is never marked published, so a linkless article repeats every run")
def test_linkless_article_is_not_republished_after_marking(history_file):
    h = ArticleHistory(history_file)
    linkless = {"link": "", "title": "No link"}
    h.mark_as_published([linkless])
    assert h.filter_published([linkless]) == []
