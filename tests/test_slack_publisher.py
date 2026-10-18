import json

import pytest
import requests

from conftest import FakeResponse
from slack_publisher import format_for_slack, publish_to_slack


def topic(i=0, summary="A summary.", n_articles=1, name=None):
    return {
        "topic": name or f"Topic {i}",
        "summary": summary,
        "articles": [{"title": f"T{i}-{j}", "link": f"http://x.test/{i}/{j}"} for j in range(n_articles)],
    }


def texts(blocks):
    return [b["text"]["text"] for b in blocks if b["type"] == "section"]


def test_format_for_slack_starts_with_header_and_divider():
    blocks = format_for_slack({"topics": []})
    assert blocks[0]["type"] == "header" and blocks[1]["type"] == "divider"
    assert len(blocks) == 2


def test_format_for_slack_one_topic_adds_four_blocks():
    assert len(format_for_slack({"topics": [topic()]})) == 2 + 4


def test_format_for_slack_escapes_title_markup():
    data = {"topics": [{"topic": "t", "summary": "s", "articles": [{"title": "A <b> & C", "link": "http://x.test"}]}]}
    assert "<http://x.test|A &lt;b&gt; &amp; C>" in texts(format_for_slack(data))[-1]


def test_format_for_slack_escapes_link_pipe_and_gt():
    data = {"topics": [{"topic": "t", "summary": "s", "articles": [{"title": "a", "link": "http://x.test/a|b>c"}]}]}
    assert "<http://x.test/a%7Cb%3Ec|a>" in texts(format_for_slack(data))[-1]


def test_format_for_slack_missing_summary_uses_default_text():
    data = {"topics": [{"topic": "t", "articles": []}]}
    assert texts(format_for_slack(data))[1] == "No summary available."


def test_format_for_slack_topic_without_articles_omits_link_block():
    assert len(format_for_slack({"topics": [topic(n_articles=0)]})) == 2 + 3


def test_format_for_slack_thirteen_topics_stay_within_block_limit():
    blocks = format_for_slack({"topics": [topic(i) for i in range(13)]})
    assert len(blocks) <= 50


def test_format_for_slack_forty_long_links_keep_sections_under_limit():
    long_topic = {
        "topic": "t",
        "summary": "s",
        "articles": [{"title": "x" * 60, "link": "http://x.test/" + "p" * 60 + str(i)} for i in range(40)],
    }
    assert all(len(t) <= 3000 for t in texts(format_for_slack({"topics": [long_topic]})))


def test_format_for_slack_empty_summary_never_emitted_empty():
    assert all(t.strip() for t in texts(format_for_slack({"topics": [topic(summary="")]})))


@pytest.mark.parametrize("payload", ["<!channel> wake up", "<http://evil.test|click>"])
def test_format_for_slack_summary_markup_is_escaped(payload):
    out = texts(format_for_slack({"topics": [topic(summary=payload)]}))
    assert payload not in "\n".join(out)


def test_format_for_slack_topic_name_markup_is_escaped():
    out = texts(format_for_slack({"topics": [topic(name="<!channel>")]}))
    assert "<!channel>" not in "\n".join(out)


def test_publish_to_slack_success_posts_blocks_and_returns_true(fake_http):
    fake_http.add("http://hooks.test/w", FakeResponse(200, "ok"))
    assert publish_to_slack({"topics": [topic()]}, "http://hooks.test/w") is True
    method, url, kw = fake_http.calls[0]
    assert method == "POST" and url == "http://hooks.test/w"
    assert kw["json"]["blocks"][0]["type"] == "header"
    json.dumps(kw["json"])


def test_publish_to_slack_non_200_returns_false(fake_http):
    fake_http.add("http://hooks.test/w", FakeResponse(500, "err"))
    assert publish_to_slack({"topics": []}, "http://hooks.test/w") is False


def test_publish_to_slack_exception_returns_false(fake_http):
    fake_http.add("http://hooks.test/w", requests.ConnectionError("down"))
    assert publish_to_slack({"topics": []}, "http://hooks.test/w") is False


# ---- message splitting and partial delivery --------------------------------------
from slack_publisher import MAX_BLOCKS, MAX_SECTION_LEN, format_for_slack_messages


def all_links(messages):
    return [l for _, links in messages for l in links]


def test_many_topics_split_into_messages_within_limits():
    topics = [topic(i, n_articles=3) for i in range(30)]
    messages = format_for_slack_messages({"topics": topics})
    assert len(messages) > 1
    for blocks, _ in messages:
        assert len(blocks) <= MAX_BLOCKS
        assert all(0 < len(t) <= MAX_SECTION_LEN for t in texts(blocks))
        assert blocks[0]["type"] == "header"
    assert "continued" in messages[1][0][0]["text"]["text"]
    expected = [a["link"] for t in topics for a in t["articles"]]
    assert all_links(messages) == expected  # every article delivered exactly once


def test_publish_to_slack_sets_a_timeout(fake_http):
    fake_http.add("http://hooks.test/w", FakeResponse(200, "ok"))
    publish_to_slack({"topics": [topic()]}, "http://hooks.test/w")
    assert fake_http.calls[0][2]["timeout"] > 0


def test_publish_to_slack_partial_failure_reports_delivered_links(fake_http):
    topics = [topic(i, n_articles=3) for i in range(30)]
    first_links = format_for_slack_messages({"topics": topics})[0][1]
    responses = iter([FakeResponse(200, "ok"), FakeResponse(500, "err")])
    fake_http.add("http://hooks.test/w", lambda url, kw: next(responses))
    delivered = set()
    assert publish_to_slack({"topics": topics}, "http://hooks.test/w", delivered_links=delivered) is False
    assert delivered == set(first_links)
