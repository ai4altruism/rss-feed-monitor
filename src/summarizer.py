# src/summarizer.py

from openai import OpenAI
import logging
import json

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
        f"Title: {json.dumps(a.get('title'))}, Summary: {json.dumps(a.get('summary'))}, Link: {json.dumps(a.get('link'))}" for a in articles
    ])

    # Request OpenAI to group articles into topics with properly formatted JSON
    group_prompt = f"""
You will be given a set of news articles. Group them into topics based on similarity, and provide a JSON response strictly in the following format:

{{
    "topics": [
        {{
            "topic": "Topic Name",
            "articles": [
                {{"title": "Article Title", "link": "Article Link"}},
                ...
            ]
        }},
        ...
    ]
}}

Ensure:
- The response is **always** valid JSON.
- Each "title" and "link" is properly enclosed in **double quotes ("")**.
- **No extra comments or explanations** in the response.

Articles:
{articles_text}
"""

    try:
        group_response = client.chat.completions.create(
            model=group_model,
            messages=[
                {"role": "system", "content": "You are an AI that groups news articles into related topics and provides strictly valid JSON."},
                {"role": "user", "content": group_prompt}
            ],
            max_tokens=800
        )

        group_raw_output = group_response.choices[0].message.content.strip()
        logging.info(f"Raw Grouping Response: {repr(group_raw_output)}")  # Debugging log

        # Debugging: Print raw output before parsing
        try:
            groups = json.loads(group_raw_output)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            logging.error(f"Malformed JSON Response: {repr(group_raw_output)}")
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
                max_tokens=150
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
