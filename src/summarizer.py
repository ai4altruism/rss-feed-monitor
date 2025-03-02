# src/summarizer.py

from openai import OpenAI
import logging
import json
import re

def sanitize_json_string(json_string):
    """
    Sanitize a JSON string to fix common issues that cause parsing failures.
    
    Parameters:
        json_string (str): Potentially malformed JSON string
        
    Returns:
        str: Sanitized JSON string
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
        # Count quotes in this line
        quotes = line.count('"')
        # If odd number of quotes, add one at the end
        if quotes % 2 == 1 and not line.strip().endswith(','):
            lines[i] = line + '"'
    
    json_string = '\n'.join(lines)
    
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

    # Ensure each article includes its hyperlink
    articles_text = "\n\n".join([
        f"Title: {json.dumps(a.get('title'))}, Summary: {json.dumps(a.get('summary'))}, Link: {json.dumps(a.get('link'))}" 
        for a in articles
    ])

    # Request OpenAI to group articles into topics with properly formatted JSON
    group_prompt = f"""
You will be given a set of news articles. Group them into topics based on similarity, and provide a JSON response strictly in the following format:

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

RESPONSE REQUIREMENTS:
1. The response must contain ONLY valid JSON. 
2. No code block formatting (no triple backticks).
3. No additional text or explanations.
4. Use only double quotes ("") for all JSON keys and values, never single quotes.
5. Properly escape any quotes within string values using a backslash.
6. Do not leave any string values unterminated.

Articles:
{articles_text}
"""

    try:
        group_response = client.chat.completions.create(
            model=group_model,
            messages=[
                {"role": "system", "content": "You are an AI that groups news articles into related topics and returns strictly valid JSON. Your output must be parseable by Python's json.loads() function. No trailing commas, no single quotes, all strings properly escaped."},
                {"role": "user", "content": group_prompt}
            ],
            max_tokens=1500,
            temperature=0.1  # Lower temperature for more deterministic JSON formatting
        )

        # Extract and clean the raw output
        group_raw_output = group_response.choices[0].message.content.strip()
        
        # Remove any code block markers and language identifiers
        group_raw_output = re.sub(r'^```(?:json)?\s*', '', group_raw_output)
        group_raw_output = re.sub(r'\s*```$', '', group_raw_output)
        
        logging.info(f"Raw Grouping Response (cleaned): {repr(group_raw_output[:200])}...")

        # Validate and parse the JSON
        is_valid, result = validate_json(group_raw_output)
        if is_valid:
            groups = result
        else:
            logging.error(f"JSON validation failed: {result}")
            logging.error(f"Full malformed response: {repr(group_raw_output)}")
            groups = {"topics": []}

    except Exception as e:
        logging.error(f"LLM grouping error: {e}")
        return {"topics": []}

    # Process each topic and generate a summary
    for topic in groups.get("topics", []):
        articles_in_topic = topic.get("articles", [])
        relevant_articles = [
            next((a for a in articles if a.get("title") == article.get("title")), None) for article in articles_in_topic
        ]
        relevant_articles = [a for a in relevant_articles if a]

        combined_text = "\n\n".join([
            f"Title: {json.dumps(a.get('title'))}, Summary: {json.dumps(a.get('summary'))}" for a in relevant_articles
        ])

        summarize_prompt = f"""
Summarize the following articles that belong to the topic "{topic.get('topic')}" in a concise paragraph.

{combined_text}

Ensure:
- The response is a **single paragraph**.
- No extra explanations.
"""

        try:
            summarize_response = client.chat.completions.create(
                model=summarize_model,
                messages=[
                    {"role": "system", "content": "You are an AI that summarizes news articles into a single paragraph."},
                    {"role": "user", "content": summarize_prompt}
                ],
                max_tokens=200,
                temperature=0.7  # Allow some creativity in summaries
            )

            summary_text = summarize_response.choices[0].message.content.strip() if summarize_response.choices else ""
            
            if not summary_text:
                logging.error(f"Summarization API returned an empty response for topic: {topic.get('topic')}")
                summary_text = "No summary available."

            topic["summary"] = summary_text
            topic["articles"] = [{"title": a.get("title"), "link": a.get("link")} for a in relevant_articles]

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = "Error generating summary."

    return groups