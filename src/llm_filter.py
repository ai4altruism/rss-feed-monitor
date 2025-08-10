# src/llm_filter.py

from openai import OpenAI
import logging
import time


def filter_stories(articles, filter_prompt, filter_model, openai_api_key, verbose=False):
    """
    Filters articles using an LLM based on a user-specified prompt.

    Parameters:
        articles (list): List of article dictionaries.
        filter_prompt (str): Plain language prompt for filtering.
        filter_model (str): Model name to be used for filtering.
        openai_api_key (str): API key for OpenAI.
        verbose (bool): If True, log detailed information about each decision.

    Returns:
        filtered_articles (list): List of articles that meet the filter criteria.
    """
    client = OpenAI(api_key=openai_api_key)
    filtered_articles = []
    
    if verbose:
        logging.info(f"Starting filter with model: {filter_model}")
        logging.info(f"Filter prompt: {filter_prompt}")
        logging.info(f"Processing {len(articles)} articles...")

    for i, article in enumerate(articles, 1):
        if verbose:
            logging.info(f"Processing article {i}/{len(articles)}: {article.get('title', 'No title')[:50]}...")
        
        # For verbose mode, request reasoning
        if verbose:
            prompt = f"""
            Determine if the following article is relevant based on this criteria:
            "{filter_prompt}"

            Article Title: {article.get('title')}
            Article Summary: {article.get('summary')}

            First, briefly explain your reasoning (1-2 sentences).
            Then, answer with "DECISION: Yes" or "DECISION: No".
            """
            max_tokens = 100
        else:
            prompt = f"""
            Determine if the following article is relevant based on this criteria:
            "{filter_prompt}"

            Article Title: {article.get('title')}
            Article Summary: {article.get('summary')}

            Answer with a single word: "Yes" or "No".
            """
            max_tokens = 5

        try:
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=filter_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Evaluate whether this article is relevant to the given criteria.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=max_tokens,
            )

            response_time = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            
            # Extract decision from response
            if verbose:
                # Look for "DECISION: Yes/No" pattern
                decision_lower = answer.lower()
                if "decision: yes" in decision_lower:
                    decision = "yes"
                elif "decision: no" in decision_lower:
                    decision = "no"
                else:
                    # Fallback to looking for yes/no anywhere
                    decision = "yes" if "yes" in decision_lower else "no"
                
                # Log detailed information
                reasoning = answer.split("DECISION:")[0].strip() if "DECISION:" in answer else answer
                logging.info(f"  → Decision: {decision.upper()}")
                logging.info(f"  → Reasoning: {reasoning}")
                logging.info(f"  → Response time: {response_time:.2f}s")
                logging.info(f"  → Tokens used: ~{len(answer.split())}")
            else:
                decision = answer.lower()
            
            if "yes" in decision:
                filtered_articles.append(article)
                if verbose:
                    logging.info(f"  ✅ INCLUDED")
            else:
                if verbose:
                    logging.info(f"  ❌ EXCLUDED")

        except Exception as e:
            logging.error(
                f"LLM filtering error for article '{article.get('title')}': {e}"
            )
            if verbose:
                logging.error(f"  💥 ERROR - article skipped")

    if verbose:
        logging.info(f"Filter complete: {len(filtered_articles)}/{len(articles)} articles passed")
    
    return filtered_articles


def filter_stories_with_reasoning(articles, filter_prompt, filter_model, openai_api_key):
    """
    Filters articles and returns both results and reasoning.
    
    Returns:
        tuple: (filtered_articles, all_decisions) where all_decisions contains
               reasoning for each article.
    """
    return filter_stories(articles, filter_prompt, filter_model, openai_api_key, verbose=True)
