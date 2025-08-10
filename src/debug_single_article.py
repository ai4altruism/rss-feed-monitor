#!/usr/bin/env python3
# src/debug_single_article.py

import json
from dotenv import dotenv_values
from llm_filter import filter_stories
from utils import setup_logger

def debug_single_article():
    """Debug a single test article to see GPT's detailed reasoning."""
    logger = setup_logger()
    
    # Load environment variables
    env_vars = dotenv_values(".env")
    openai_api_key = env_vars.get("OPENAI_API_KEY")
    filter_prompt = env_vars.get("FILTER_PROMPT", "")
    filter_model = env_vars.get("FILTER_MODEL", "gpt-4-turbo")
    
    # Use a clear disaster example
    test_article = {
        "title": "7.2 Magnitude Earthquake Strikes Turkey-Syria Border, Thousands Dead",
        "summary": "A devastating 7.2 magnitude earthquake struck the Turkey-Syria border region early Monday, killing over 5,000 people and leaving tens of thousands homeless. Emergency teams are conducting search and rescue operations across multiple cities including Gaziantep, Kahramanmaras, and Aleppo.",
        "link": "https://example.com/turkey-syria-earthquake",
        "published": "2024-01-15T08:30:00Z"
    }
    
    print("DEBUGGING SINGLE ARTICLE")
    print("="*60)
    print(f"Title: {test_article['title']}")
    print(f"Summary: {test_article['summary']}")
    print()
    print("CURRENT FILTER PROMPT:")
    print("-" * 40)
    print(filter_prompt)
    print("-" * 40)
    print()
    
    # Test with verbose logging
    filtered = filter_stories([test_article], filter_prompt, filter_model, openai_api_key, verbose=True)
    
    print(f"\nRESULT: {'PASSED' if len(filtered) > 0 else 'REJECTED'}")
    
    if len(filtered) == 0:
        print("\n💡 TROUBLESHOOTING SUGGESTIONS:")
        print("1. The filter prompt might be too restrictive")
        print("2. GPT-5-mini might be interpreting the criteria too strictly")
        print("3. Try simplifying the prompt or using gpt-4 instead")
        print("4. Check if the location requirement is causing issues")

if __name__ == "__main__":
    debug_single_article()