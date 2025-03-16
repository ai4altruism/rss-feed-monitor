# src/llm_filter.py

import logging
import json
import re
from utils import call_responses_api

def sanitize_json_string(json_string):
    """
    Attempts to fix common JSON issues such as code fences, partial strings, or mismatched quotes.
    You can adapt or expand this if needed.
    """
    # Remove Markdown fences
    json_string = re.sub(r'^```(\w+)?', '', json_string)
    json_string = re.sub(r'```$', '', json_string)

    # Potentially fix unescaped quotes or trailing commas
    # (Extend this logic as needed, or use your existing summarize-level approach.)
    # For example:
    # Replace single quotes around keys/values with double quotes (if you're sure it won't break legitimate text).
    # json_string = re.sub(r"(?<!\\)'", '"', json_string)

    return json_string.strip()

def filter_stories(articles, filter_prompt, filter_model, openai_api_key, batch_size=5):
    """
    Filters articles using an LLM based on a user-specified prompt, in batches.

    Steps:
      1. Chunk the articles into groups of 'batch_size'.
      2. Build a single JSON-based classification prompt for each batch.
      3. Call the LLM once per batch, instructing it to return valid JSON
         with a yes/no decision for each article.
      4. If JSON parsing fails, attempt sanitization and re-parse.
      5. Any article whose decision is 'Yes' gets appended to 'filtered_articles'.

    Parameters:
        articles (list): List of article dictionaries.
        filter_prompt (str): Plain language prompt for filtering.
        filter_model (str): Model name to be used for filtering.
        openai_api_key (str): API key for OpenAI.
        batch_size (int): Number of articles per request.

    Returns:
        filtered_articles (list): List of articles that meet the filter criteria.
    """
    filtered_articles = []

    def chunked(iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i : i + size]

    chunk_index = 0
    for batch in chunked(articles, batch_size):
        chunk_index += 1

        # Build the prompt
        article_list_text = ""
        for idx, art in enumerate(batch, start=1):
            title = art.get("title", "").replace("\n", " ")
            # Truncate summary to ~300 chars to avoid huge prompts
            summary_full = art.get("summary", "").replace("\n", " ")
            summary_short = summary_full[:300]
            if len(summary_full) > 300:
                summary_short += "..."

            article_list_text += f"{idx}. Title: {title}\n   Summary: {summary_short}\n\n"

        prompt = f"""
You are evaluating a batch of articles for relevance based on this criteria:
"{filter_prompt}"

For each article, respond with exactly "Yes" or "No". Then return them in valid JSON using this structure:
{{
  "decisions": [
    {{
      "index": 1,
      "decision": "Yes"
    }},
    ...
  ]
}}

IMPORTANT:
- Output ONLY valid JSON (no markdown, code fences, or additional keys).
- Each 'index' must match the article's number in the batch.
- If the article is relevant, answer "Yes"; otherwise "No".
- Do not include any commentary or text besides the JSON.

Here are the articles in this batch:

{article_list_text}
""".strip()

        try:
            output_text = call_responses_api(
                model=filter_model,
                prompt=prompt,
                openai_api_key=openai_api_key,
                instructions="Output only valid JSON. No extra commentary.",
                max_output_tokens=256,  # Must be >=16
                temperature=0.0
            )

            # Attempt direct JSON parse
            try:
                parsed = json.loads(output_text)
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing failed for chunk {chunk_index}: {e}")
                # Attempt to sanitize
                cleaned = sanitize_json_string(output_text)
                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as e2:
                    logging.error(f"JSON parsing still failed after sanitization for chunk {chunk_index}: {e2}")
                    parsed = {"decisions": []}

            # Process decisions
            for dec in parsed.get("decisions", []):
                idx = dec.get("index")
                decision = dec.get("decision", "").lower()
                # Validate index is in range
                if idx and 1 <= idx <= len(batch) and "yes" in decision:
                    filtered_articles.append(batch[idx - 1])

        except Exception as e:
            logging.error(f"LLM filtering error for chunk {chunk_index}: {e}")

    return filtered_articles
