# src/slack_publisher.py

import requests
import logging
import json
from datetime import datetime

# Slack rejects a message with more than 50 blocks, or a section whose text
# is empty or longer than 3000 characters.
MAX_BLOCKS = 50
MAX_SECTION_LEN = 3000
WEBHOOK_TIMEOUT = 15  # seconds; a hung post must not stall the scheduler


def _escape(text):
    """Escape Slack mrkdwn control characters.

    Topic names and summaries are model output derived from untrusted feed
    text; unescaped, a summary containing <!channel> would ping the channel
    and <http://x|y> would publish a link that was never in the sources.
    """
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _section(text):
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _link_sections(articles):
    """Article-list sections, each within MAX_SECTION_LEN, split between
    whole lines. Returns [(block, [links in it])]."""
    out = []
    current, links = "*Articles:*", []
    for idx, article in enumerate(articles, 1):
        title = _escape(article.get("title", "Untitled"))
        link = article.get("link", "#").replace("|", "%7C").replace(">", "%3E")
        line = f"{idx}. <{link}|{title}>"
        if len(line) > MAX_SECTION_LEN:
            line = line[: MAX_SECTION_LEN - 1] + "…"
        if len(current) + 1 + len(line) > MAX_SECTION_LEN:
            out.append((_section(current), links))
            current, links = line, []
        else:
            current = f"{current}\n{line}"
        links.append(article.get("link"))
    out.append((_section(current), links))
    return out


def _topic_blocks(topic_group):
    """All blocks for one topic as [(block, [links it delivers])]."""
    topic_name = _escape(topic_group.get("topic") or "Uncategorized")
    summary = _escape((topic_group.get("summary") or "").strip()) or "No summary available."
    articles = topic_group.get("articles", [])
    blocks = [(_section(f"*{topic_name}*"[:MAX_SECTION_LEN]), []),
              (_section(summary[:MAX_SECTION_LEN]), [])]
    if articles:
        blocks.extend(_link_sections(articles))
    blocks.append(({"type": "divider"}, []))
    return blocks


def format_for_slack_messages(summary_data):
    """
    Format the summary into one or more Slack messages.

    Returns:
        list of (blocks, links): each message's blocks, within Slack's
        50-block limit, and the article links that message delivers.
    """
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    def header(continued):
        title = f"📰 News Summary | {stamp}" + (" (continued)" if continued else "")
        return [{"type": "header", "text": {"type": "plain_text", "text": title, "emoji": True}},
                {"type": "divider"}]

    messages = []
    blocks, links = header(False), []
    for topic_group in summary_data.get("topics", []):
        for block, block_links in _topic_blocks(topic_group):
            if len(blocks) >= MAX_BLOCKS:
                messages.append((blocks, links))
                blocks, links = header(True), []
            blocks.append(block)
            links.extend(block_links)
    messages.append((blocks, links))
    return messages


def format_for_slack(summary_data):
    """
    Format the summary data into Slack message blocks: the first message of
    format_for_slack_messages (all of it when the summary fits in one).
    """
    return format_for_slack_messages(summary_data)[0][0]


def publish_to_slack(summary_data, webhook_url, delivered_links=None):
    """
    Publish the summary data to a Slack channel using a webhook, as several
    messages when it exceeds one message's limits.

    Parameters:
        summary_data (dict): The grouped and summarized articles.
        webhook_url (str): The Slack webhook URL.
        delivered_links (set, optional): receives the link of every article
            in a message Slack accepted, so a partial failure can mark what
            was delivered and retry only the rest.

    Returns:
        bool: True only if every message was sent.
    """
    messages = format_for_slack_messages(summary_data)
    for i, (blocks, links) in enumerate(messages, 1):
        try:
            response = requests.post(
                webhook_url,
                json={"blocks": blocks},
                headers={"Content-Type": "application/json"},
                timeout=WEBHOOK_TIMEOUT,
            )
        except Exception as e:
            logging.error(f"Error publishing to Slack (message {i}/{len(messages)}): {e}")
            return False
        if response.status_code != 200:
            logging.error(
                f"Failed to publish to Slack (message {i}/{len(messages)}). "
                f"Status: {response.status_code}, Response: {response.text}"
            )
            return False
        if delivered_links is not None:
            delivered_links.update(l for l in links if l)
    logging.info(f"Successfully published summary to Slack in {len(messages)} message(s).")
    return True
