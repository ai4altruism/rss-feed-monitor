# src/summarizer.py

import logging
import json
import re
from utils import call_responses_api

def sanitize_json_string(json_string):
    """
    Sanitize a JSON string to fix common issues that cause parsing failures.
    """
    # Remove any markdown artifacts
    json_string = re.sub(r'^```json\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)

    # Fix common LLM JSON formatting issues
    # Handle improperly escaped quotes within JSON strings
    json_string = re.sub(r'(?<!\\)"(?=(.*?".*?":))', r'\"', json_string)

    # Fix missing quotes around keys (not standard JSON but LLMs sometimes do this)
    json_string = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', json_string)

    # Fix unterminated strings by adding a closing quote if there's an opening one
    lines = json_string.split('\n')
    for i, line in enumerate(lines):
        quotes = line.count('"')
        if quotes % 2 == 1 and not line.strip().endswith(','):
            lines[i] = line + '"'

    json_string = '\n'.join(lines)

    return json_string

def validate_json(json_string):
    """
    Attempt to validate and fix JSON if possible.

    Returns:
        (is_valid: bool, result: dict or str)
    """
    try:
        parsed = json.loads(json_string)
        return True, parsed
    except json.JSONDecodeError as e:
        logging.warning(f"Initial JSON parsing failed: {e}")

        # Try sanitizing
        sanitized = sanitize_json_string(json_string)
        try:
            parsed = json.loads(sanitized)
            logging.info("JSON sanitization resolved parsing issues")
            return True, parsed
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing still failed after sanitization: {e}")
            return False, str(e)

def unify_topics(topics_list):
    """
    Merge topics with the same name into a single topic entry.
    Deduplicate articles in the process.
    """
    unified = {}
    for topic_dict in topics_list:
        topic_name = topic_dict.get("topic", "Untitled").strip()
        if topic_name not in unified:
            unified[topic_name] = {
                "topic": topic_name,
                "articles": []
            }
        # Combine articles
        for article in topic_dict.get("articles", []):
            if article not in unified[topic_name]["articles"]:
                unified[topic_name]["articles"].append(article)
    return list(unified.values())

def group_and_summarize(articles, group_model, summarize_model, openai_api_key):
    """
    Groups articles by topic and generates summaries using OpenAI's Responses API,
    preserving hyperlinks. Unifies topic labels across chunks.
    
    Parameters:
        articles (list): List of filtered article dictionaries.
        group_model (str): Model name for grouping articles.
        summarize_model (str): Model name for summarizing groups.
        openai_api_key (str): API key for OpenAI.

    Returns:
        dict: A structured JSON-like dict with topic groups, summaries, and article links.
    """

    if not articles:
        return {"topics": []}

    def chunk_articles(articles_list, chunk_size=10):
        """Split articles into smaller chunks to avoid token limits."""
        for i in range(0, len(articles_list), chunk_size):
            yield articles_list[i:i + chunk_size]

    all_topics = []

    # ----------------------
    # GROUPING PHASE
    # ----------------------
    for chunk_index, article_chunk in enumerate(chunk_articles(articles, 10)):
        logging.info(f"Processing article chunk {chunk_index + 1} for grouping...")

        # Build the text snippet for each article in this chunk
        articles_text = "\n\n".join([
            f"Title: {json.dumps(a.get('title'))}, Link: {json.dumps(a.get('link'))}"
            for a in article_chunk
        ])

        # Prompt to get strictly valid JSON
        group_prompt = f"""
Group these articles into topics. Return ONLY valid JSON in this exact format:
{{
    "topics": [
        {{
            "topic": "Topic Name",
            "articles": [
                {{"title": "Article Title", "link": "Article Link"}}
            ]
        }}
    ]
}}

IMPORTANT:
- Return ONLY valid JSON
- Double quotes for keys/values, no trailing commas, no code blocks
- No additional explanation, just the JSON.

Articles:
{articles_text}
"""

        try:
            # Call the new Responses API for grouping
            group_raw_output = call_responses_api(
                model=group_model,
                prompt=group_prompt,
                openai_api_key=openai_api_key,
                instructions="You are a JSON formatting expert who organizes articles into topics.",
                max_output_tokens=2000,
                temperature=0.0
            )

            # Attempt direct JSON parse
            try:
                parsed = json.loads(group_raw_output)
                all_topics.extend(parsed.get("topics", []))
            except json.JSONDecodeError:
                # Attempt to fix
                is_valid, result = validate_json(group_raw_output)
                if is_valid:
                    all_topics.extend(result.get("topics", []))
                else:
                    logging.error(f"JSON validation failed on chunk {chunk_index + 1}: {result}")
                    fallback = {
                        "topic": f"Articles Group {chunk_index+1}",
                        "articles": [
                            {"title": a.get("title"), "link": a.get("link")} for a in article_chunk
                        ]
                    }
                    all_topics.append(fallback)

        except Exception as e:
            logging.error(f"LLM grouping error for chunk {chunk_index+1}: {e}")
            fallback_topic = {
                "topic": f"Articles Group {chunk_index+1}",
                "articles": [{"title": a.get("title", ""), "link": a.get("link", "")} for a in article_chunk]
            }
            all_topics.append(fallback_topic)

    # ----------------------
    # UNIFY TOPICS
    # ----------------------
    unified_topics = unify_topics(all_topics)

    # ----------------------
    # SUMMARIZATION PHASE
    # ----------------------
    for topic in unified_topics:
        articles_in_topic = topic.get("articles", [])

        if not articles_in_topic:
            topic["summary"] = "No articles available for summarization."
            continue

        # Match each short-article dict to the full article in 'articles' to retrieve summary
        relevant_articles = []
        for stub in articles_in_topic:
            match = next((a for a in articles if a.get("title") == stub.get("title")), None)
            if match:
                relevant_articles.append(match)
            else:
                relevant_articles.append({
                    "title": stub.get("title", ""),
                    "link": stub.get("link", ""),
                    "summary": "No detailed summary available."
                })

        # Build a combined prompt text from up to 5 articles
        combined_text = "\n\n".join([
            f"Title: {a.get('title')}, Summary: {a.get('summary') or ''}"
            for a in relevant_articles[:5]
        ])

        if not combined_text.strip():
            topic["summary"] = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."
            continue

        summarize_prompt = f"""
Summarize these articles about "{topic.get('topic')}" in ONE concise paragraph:

{combined_text}

RESPONSE FORMAT: Just one short paragraph.
"""

        try:
            summary_text = call_responses_api(
                model=summarize_model,
                prompt=summarize_prompt,
                openai_api_key=openai_api_key,
                instructions="You create brief, informative summaries of news articles in a single paragraph.",
                max_output_tokens=250,
                temperature=0.5
            )

            # Basic cleanup
            summary_text = re.sub(r'\s+', ' ', summary_text).strip()
            if not summary_text:
                summary_text = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."
            topic["summary"] = summary_text

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."

        # Restore the final article array with minimal keys
        topic["articles"] = [{"title": s.get("title", "Untitled"), "link": s.get("link", "#")} for s in articles_in_topic]

    return {"topics": unified_topics}
