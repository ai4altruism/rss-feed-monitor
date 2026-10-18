import json

import requests

from conftest import FakeResponse, rss_xml
from rss_reader import fetch_feeds, load_cache

A = "http://feeds.test/a"
B = "http://feeds.test/b"


def test_fetch_feeds_200_returns_entries_and_writes_cache(fake_http, workdir):
    fake_http.add(A, FakeResponse(200, rss_xml([("T1", "http://x.test/1", "S1")]), {"ETag": "e1"}))

    arts = fetch_feeds([A])

    assert arts == [{"title": "T1", "link": "http://x.test/1", "summary": "S1", "published": ""}]
    assert load_cache()[A]["etag"] == "e1"


def test_fetch_feeds_sends_user_agent_and_timeout(fake_http, workdir):
    fake_http.add(A, FakeResponse(200, rss_xml([])))
    fetch_feeds([A])
    kw = fake_http.calls[0][2]
    assert "User-Agent" in kw["headers"] and kw["timeout"] == 10


def test_fetch_feeds_304_uses_cached_content_and_sends_validators(fake_http, workdir):
    (workdir / "data" / "cache.json").write_text(json.dumps({
        A: {"etag": "e1", "last_modified": "Mon", "content": rss_xml([("Cached", "http://x.test/c", "s")])}
    }))
    fake_http.add(A, FakeResponse(304))

    arts = fetch_feeds([A])

    hdrs = fake_http.calls[0][2]["headers"]
    assert hdrs["If-None-Match"] == "e1" and hdrs["If-Modified-Since"] == "Mon"
    assert [a["title"] for a in arts] == ["Cached"]


def test_fetch_feeds_non_200_is_skipped(fake_http, workdir):
    fake_http.add(A, FakeResponse(503))
    assert fetch_feeds([A]) == []


def test_fetch_feeds_exception_in_one_feed_does_not_stop_others(fake_http, workdir):
    fake_http.add(A, requests.ConnectionError("down"))
    fake_http.add(B, FakeResponse(200, rss_xml([("TB", "http://x.test/b", "s")])))
    assert [a["title"] for a in fetch_feeds([A, B])] == ["TB"]


def test_fetch_feeds_strips_whitespace_from_urls(fake_http, workdir):
    fake_http.add(A, FakeResponse(200, rss_xml([])))
    fetch_feeds(["  " + A + " "])
    assert fake_http.calls[0][1] == A


def test_fetch_feeds_missing_fields_default_to_empty_strings(fake_http, workdir):
    fake_http.add(A, FakeResponse(200, '<rss version="2.0"><channel><item><title>Only</title></item></channel></rss>'))
    assert fetch_feeds([A]) == [{"title": "Only", "link": "", "summary": "", "published": ""}]


import pytest


def test_fetch_feeds_recoverable_bozo_keeps_parsed_entries(fake_http, workdir):
    truncated = rss_xml([("T1", "http://x.test/1", "S1")]).replace("</channel></rss>", "")
    fake_http.add(A, FakeResponse(200, truncated))
    import feedparser
    assert feedparser.parse(truncated).bozo and feedparser.parse(truncated).entries  # precondition

    assert [a["title"] for a in fetch_feeds([A])] == ["T1"]
