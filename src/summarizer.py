# src/summarizer.py

from openai import OpenAI
import logging
import json
import re

from utils import is_reasoning_model

def sanitize_json_string(json_string):
    """
    Strip markdown code fences (```json ... ```) that LLMs sometimes wrap
    around JSON output.

    Deliberately does nothing else: the grouping call already enforces
    response_format json_object, and the caller falls back to listing the
    raw articles when parsing fails. Heavier regex "repairs" (re-escaping
    quotes, appending quotes to odd-quote lines) risk corrupting valid
    output that legitimately contains quotes.

    Parameters:
        json_string (str): Potentially fence-wrapped JSON string

    Returns:
        str: JSON string without markdown fences
    """
    json_string = json_string.strip()
    json_string = re.sub(r'^```(?:json)?\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)
    return json_string

def validate_json(json_string):
    """
    Attempt to validate and fix JSON if possible.
    
    Parameters:
        json_string (str): JSON string to validate
        
    Returns:
        tuple: (is_valid, fixed_json or error_message)
    """
    try:
        # Try parsing as is
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

def _topics_from(result):
    """The topic dicts in a grouping response, whatever its shape."""
    topics = result.get("topics") if isinstance(result, dict) else result
    if not isinstance(topics, list):
        return []
    return [t for t in topics if isinstance(t, dict)]


def group_and_summarize(articles, group_model, summarize_model, openai_api_key):
    """
    Groups articles by topic and generates summaries using OpenAI's Chat API, preserving hyperlinks.

    Parameters:
        articles (list): List of filtered article dictionaries.
        group_model (str): Model name for grouping articles.
        summarize_model (str): Model name for summarizing groups.
        openai_api_key (str): API key for OpenAI.

    Returns:
        summary (dict): A structured JSON-like dict with topic groups, summaries, and article links.
    """
    client = OpenAI(api_key=openai_api_key)

    if not articles:
        return {"topics": []}
        
    # One entry per link: two feeds carrying the same story would otherwise
    # put it in a topic and again in "Additional stories".
    seen, unique = set(), []
    for a in articles:
        key = a.get("link") or id(a)
        if key not in seen:
            seen.add(key)
            unique.append(a)
    articles = unique

    # Instead of sending all articles at once, let's chunk them to avoid token limits
    def chunk_articles(articles_list, chunk_size=10):
        """Split articles into smaller chunks to avoid token limits."""
        for i in range(0, len(articles_list), chunk_size):
            yield articles_list[i:i + chunk_size]
    
    # Group articles by topic using a more resilient approach
    all_topics = []
    
    # Process articles in smaller batches
    for chunk_index, article_chunk in enumerate(chunk_articles(articles, 10)):
        logging.info(f"Processing article chunk {chunk_index+1}")
        
        # Ensure each article includes its hyperlink
        articles_text = "\n\n".join([
            f"Title: {json.dumps(a.get('title'))}, Link: {json.dumps(a.get('link'))}" 
            for a in article_chunk
        ])

        # Request OpenAI to group articles - with simpler prompt focused on correctness
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
- Return ONLY valid, parseable JSON
- Double quotes for ALL keys and values
- Properly escape quotes in strings with backslash
- No single quotes, no trailing commas
- No comments, no explanations
- No code blocks or markup

Articles:
{articles_text}
"""

        try:
            group_response = client.chat.completions.create(
                model=group_model,
                messages=[
                    {"role": "system", "content": "You are a JSON formatting expert that groups news articles into topics. Return ONLY valid JSON. Use EXACT titles and links from the input - do not modify or paraphrase them."},
                    {"role": "user", "content": group_prompt}
                ],
                # Reasoning models spend part of the cap before writing; 2000
                # left later 10-article chunks empty on gpt-5-mini.
                max_completion_tokens=16000 if is_reasoning_model(group_model) else 2000,
                response_format={"type": "json_object"}  # Enforce JSON response format if available
            )

            # Extract the raw output
            group_raw_output = group_response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            try:
                chunk_result = json.loads(group_raw_output)
                # If successful, add topics to our collection
                all_topics.extend(_topics_from(chunk_result))
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing failed for chunk {chunk_index+1}: {e}")
                # Try our repair function
                is_valid, result = validate_json(group_raw_output)
                if is_valid:
                    all_topics.extend(_topics_from(result))
                else:
                    logging.error(f"JSON validation also failed: {result}")
                    # Create a fallback topic with the raw articles
                    fallback_topic = {
                        "topic": f"Articles Group {chunk_index+1}",
                        "articles": [{"title": a.get("title"), "link": a.get("link")} for a in article_chunk]
                    }
                    all_topics.append(fallback_topic)

        except Exception as e:
            logging.error(f"LLM grouping error for chunk {chunk_index+1}: {e}")
            # Create a fallback topic with the raw articles even on API failure
            fallback_topic = {
                "topic": f"Articles Group {chunk_index+1}",
                "articles": [{"title": a.get("title"), "link": a.get("link")} for a in article_chunk]
            }
            all_topics.append(fallback_topic)
    
    # Ground every LLM-emitted article back to a source article. The LLM can
    # paraphrase titles or corrupt links when echoing them, so titles/links in
    # its output are treated as lookup keys only — the published output always
    # carries source data.
    def _normalize_title(title):
        return re.sub(r"\s+", " ", (title or "").strip().lower())

    by_link = {a.get("link"): a for a in articles if a.get("link")}
    by_title = {a.get("title"): a for a in articles if a.get("title")}
    by_norm_title = {_normalize_title(a.get("title")): a for a in articles if a.get("title")}

    grounded_topics = []
    placed_ids = set()
    for topic in all_topics:
        grounded = []
        for article in topic.get("articles") or []:
            # json_object mode enforces JSON, not this schema: a bare title
            # string is looked up as a title, anything else is skipped.
            if isinstance(article, str):
                article = {"title": article}
            elif not isinstance(article, dict):
                continue
            src = (
                by_link.get(article.get("link"))
                or by_title.get(article.get("title"))
                or by_norm_title.get(_normalize_title(article.get("title")))
            )
            if src is None:
                logging.warning(
                    f"Dropping ungroundable article from topic '{topic.get('topic')}': "
                    f"{article.get('title')!r}"
                )
                continue
            if id(src) in placed_ids:
                continue  # already placed in an earlier topic
            placed_ids.add(id(src))
            grounded.append(src)
        if grounded:
            grounded_topics.append((topic, grounded))
        else:
            logging.warning(
                f"Dropping topic with no groundable articles: '{topic.get('topic')}'"
            )

    # Articles the LLM omitted from its grouping response would otherwise be
    # marked as published without ever appearing in a report — collect them
    # into a catch-all topic instead of losing them.
    leftovers = [a for a in articles if id(a) not in placed_ids]
    if leftovers:
        logging.warning(
            f"{len(leftovers)} article(s) missing from LLM grouping; adding catch-all topic."
        )
        grounded_topics.append(({"topic": "Additional stories"}, leftovers))

    groups = {"topics": []}

    # Process each topic and generate a summary
    for topic, relevant_articles in grounded_topics:
        # Output articles come straight from source data
        topic["articles"] = [
            {"title": a.get("title", "Untitled"), "link": a.get("link", "#")}
            for a in relevant_articles
        ]

        # Create a combined text for summarization
        combined_text = "\n\n".join([
            f"Title: {a.get('title')}" + (f", Summary: {a.get('summary')}" if a.get('summary') else "") 
            for a in relevant_articles[:5]  # Limit to 5 articles to avoid token limits
        ])

        summarize_prompt = f"""
Write a single paragraph summary about {topic.get('topic')} based ONLY on these articles:

{combined_text}

CRITICAL INSTRUCTIONS:
- Use ONLY information explicitly stated in the articles above
- Do NOT add any information not present in the source material
- Do NOT invent specific numbers, dates, locations, or names
- If details are missing, use general terms like "multiple", "several", "recently" 
- Combine the facts into a flowing narrative paragraph (no lists or bullet points)
- Focus on what IS stated rather than speculating about what might be

Summary:"""

        try:
            summarize_response = client.chat.completions.create(
                model=summarize_model,
                messages=[
                    {"role": "system", "content": "You are a fact-based news summarizer. You MUST use ONLY information explicitly provided in the source articles. Never add details, numbers, or facts not present in the sources. If information is missing, use general terms rather than inventing specifics."},
                    {"role": "user", "content": summarize_prompt}
                ],
                # Reasoning models spend part of the cap before writing.
                max_completion_tokens=4000 if is_reasoning_model(summarize_model) else 400,
            )

            summary_text = (summarize_response.choices[0].message.content or "").strip() if summarize_response.choices else ""

            # Clean up before the emptiness check: a reply of just "Summary:"
            # is empty once its label is removed.
            summary_text = re.sub(r'^[#*"\s]*(Summary:|Topic:|Articles:)\s*', '', summary_text)
            summary_text = re.sub(r'\n+', ' ', summary_text).strip()

            # Debug logging
            logging.info(f"Summarization response for '{topic.get('topic')}': {len(summary_text)} chars")
            if not summary_text:
                logging.error(f"Summarization API returned an empty response for topic: {topic.get('topic')}")
                logging.error(f"Response object: {summarize_response}")
                summary_text = f"A collection of {len(relevant_articles)} articles about {topic.get('topic')}."
            else:
                logging.info(f"Summary preview: {summary_text[:100]}...")

            topic["summary"] = summary_text

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = f"A collection of {len(relevant_articles)} articles about {topic.get('topic')}."

        groups["topics"].append(topic)

    return groups