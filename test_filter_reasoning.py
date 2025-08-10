#!/usr/bin/env python3

import json
import os
import sys
import logging
from dotenv import dotenv_values

# Add src directory to path
sys.path.append('src')

from llm_filter import filter_stories
from utils import setup_logger

def test_with_reasoning():
    """Test a single obvious disaster article to see GPT's reasoning."""
    logger = setup_logger()
    
    # Load environment
    env_vars = dotenv_values(".env")
    openai_api_key = env_vars.get("OPENAI_API_KEY")
    filter_prompt = env_vars.get("FILTER_PROMPT", "")
    filter_model = env_vars.get("FILTER_MODEL", "gpt-4-turbo")
    
    # Clear disaster example
    test_article = {
        "title": "7.2 Magnitude Earthquake Strikes Turkey-Syria Border, Thousands Dead",
        "summary": "A devastating 7.2 magnitude earthquake struck the Turkey-Syria border region early Monday, killing over 5,000 people and leaving tens of thousands homeless. Emergency teams are conducting search and rescue operations across multiple cities including Gaziantep, Kahramanmaras, and Aleppo.",
        "link": "https://example.com/turkey-syria-earthquake"
    }
    
    print("TESTING WITH VERBOSE REASONING")
    print("="*70)
    print(f"Model: {filter_model}")
    print(f"Title: {test_article['title']}")
    print(f"Summary: {test_article['summary'][:100]}...")
    print("\nCurrent Filter Prompt:")
    print("-" * 50)
    print(filter_prompt)
    print("-" * 50)
    
    # Test with verbose mode to see reasoning
    filtered = filter_stories([test_article], filter_prompt, filter_model, openai_api_key, verbose=True)
    
    result = "PASSED" if len(filtered) > 0 else "REJECTED"
    print(f"\n🎯 FINAL RESULT: {result}")
    
    if len(filtered) == 0:
        print("\n💡 RECOMMENDED FIXES:")
        print("1. Simplify the filter prompt - remove subjective words like 'SIGNIFICANT'")
        print("2. Try: 'Include major natural disasters: earthquakes 6.0+, hurricanes, floods, wildfires, volcanic eruptions.'")
        print("3. Consider switching to gpt-4 model instead of gpt-5-mini")
        print("4. Remove the strict location requirement")

if __name__ == "__main__":
    test_with_reasoning()