# src/llm_filter.py

from openai import OpenAI
import logging


def filter_stories(articles, filter_prompt, filter_model, openai_api_key):
    """
    Filters articles using an LLM based on a user-specified prompt.

    Parameters:
        articles (list): List of article dictionaries.
        filter_prompt (str): Plain language prompt for filtering.
        filter_model (str): Model name to be used for filtering.
        openai_api_key (str): API key for OpenAI.

    Returns:
        filtered_articles (list): List of articles that meet the filter criteria.
    """
    client = OpenAI(api_key=openai_api_key)
    filtered_articles = []

    for article in articles:
        prompt = f"""
        Determine if the following article is relevant based on this criteria:
        "{filter_prompt}"

        Article Title: {article.get('title')}
        Article Summary: {article.get('summary')}

        Answer with a single word: "Yes" or "No".
        """

        try:
            response = client.chat.completions.create(
                model=filter_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Evaluate whether this article is relevant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=5,
                temperature=0.0,
            )

            answer = response.choices[0].message.content.strip().lower()
            if "yes" in answer:
                filtered_articles.append(article)

        except Exception as e:
            logging.error(
                f"LLM filtering error for article '{article.get('title')}': {e}"
            )

    return filtered_articles
