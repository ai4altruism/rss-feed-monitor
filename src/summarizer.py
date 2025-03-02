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
                    {"role": "system", "content": "You are a JSON formatting expert that groups news articles into topics. Return ONLY valid, well-formatted JSON with no explanations."},
                    {"role": "user", "content": group_prompt}
                ],
                max_tokens=2000,  # Increased token limit
                temperature=0.0,  # Zero temperature for maximum determinism
                response_format={"type": "json_object"}  # Enforce JSON response format if available
            )

            # Extract the raw output
            group_raw_output = group_response.choices[0].message.content.strip()
            
            # Try to parse the JSON response
            try:
                chunk_result = json.loads(group_raw_output)
                # If successful, add topics to our collection
                all_topics.extend(chunk_result.get("topics", []))
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing failed for chunk {chunk_index+1}: {e}")
                # Try our repair function
                is_valid, result = validate_json(group_raw_output)
                if is_valid:
                    all_topics.extend(result.get("topics", []))
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
    
    # Combine all topics into one structure
    groups = {"topics": all_topics}

    # Process each topic and generate a summary
    for topic in groups.get("topics", []):
        articles_in_topic = topic.get("articles", [])
        
        # Match articles in the topic with full article data
        relevant_articles = []
        for article in articles_in_topic:
            # Try to find the matching article with full data
            matching_article = next((a for a in articles if a.get("title") == article.get("title")), None)
            if matching_article:
                relevant_articles.append(matching_article)
            else:
                # Use the limited data we have
                relevant_articles.append({
                    "title": article.get("title", ""),
                    "link": article.get("link", ""),
                    "summary": "No detailed summary available."
                })
        
        # If no articles with full data were found, skip summarization
        if not relevant_articles:
            topic["summary"] = "No articles available for summarization."
            continue

        # Create a combined text for summarization
        combined_text = "\n\n".join([
            f"Title: {a.get('title')}" + (f", Summary: {a.get('summary')}" if a.get('summary') else "") 
            for a in relevant_articles[:5]  # Limit to 5 articles to avoid token limits
        ])

        summarize_prompt = f"""
Summarize these articles about "{topic.get('topic')}" in ONE concise paragraph:

{combined_text}

RESPONSE FORMAT: Just the summary paragraph with no introduction or explanation.
"""

        try:
            summarize_response = client.chat.completions.create(
                model=summarize_model,
                messages=[
                    {"role": "system", "content": "You create brief, informative summaries of news articles in a single paragraph."},
                    {"role": "user", "content": summarize_prompt}
                ],
                max_tokens=250,
                temperature=0.5  # Balanced between creativity and consistency
            )

            summary_text = summarize_response.choices[0].message.content.strip() if summarize_response.choices else ""
            
            if not summary_text:
                logging.error(f"Summarization API returned an empty response for topic: {topic.get('topic')}")
                summary_text = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."

            # Clean up summary to remove any markdown formatting
            summary_text = re.sub(r'^[#*"\s]*(Summary:|Topic:|Articles:)\s*', '', summary_text)
            summary_text = re.sub(r'\n+', ' ', summary_text)
            
            topic["summary"] = summary_text
            topic["articles"] = [{"title": a.get("title", "Untitled"), "link": a.get("link", "#")} for a in articles_in_topic]

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."

    return groups