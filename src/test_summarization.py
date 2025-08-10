#!/usr/bin/env python3
# src/test_summarization.py

import json
from dotenv import dotenv_values
from summarizer import group_and_summarize
from utils import setup_logger

def test_summarization():
    """Test the new summarization prompt with sample articles."""
    logger = setup_logger()
    
    # Load environment variables
    env_vars = dotenv_values(".env")
    openai_api_key = env_vars.get("OPENAI_API_KEY")
    group_model = env_vars.get("GROUP_MODEL", "gpt-4-turbo")
    summarize_model = env_vars.get("SUMMARIZE_MODEL", "gpt-4-turbo")
    
    # Sample test articles (similar to your wildfire example)
    test_articles = [
        {
            "title": "Canyon fire: Evacuation zones, road closures, shelters",
            "summary": "Officials have established evacuation zones across Ventura County as the Canyon fire spreads rapidly. Multiple road closures are in effect along Highway 101 and local roads. Emergency shelters have been opened at Ventura High School and Oxnard Community Center for displaced residents.",
            "link": "https://example.com/canyon-fire-evacuations",
            "published": "2024-08-09T10:00:00Z"
        },
        {
            "title": "Fast-moving Canyon fire burns nearly 5,000 acres, spurs evacuations in Ventura and L.A. counties",
            "summary": "The Canyon fire has scorched nearly 5,000 acres since igniting yesterday afternoon, prompting mandatory evacuations across both Ventura and Los Angeles counties. Strong winds are pushing the blaze toward residential areas, with zero containment reported by fire officials.",
            "link": "https://example.com/canyon-fire-5000-acres",
            "published": "2024-08-09T14:30:00Z"
        },
        {
            "title": "California fires are burning and incoming heat wave could make things worse",
            "summary": "Multiple wildfires are burning across California as meteorologists warn of an incoming heat wave that could reach 110°F. The National Weather Service has issued red flag warnings for increased fire danger through the weekend.",
            "link": "https://example.com/california-fires-heat-wave",
            "published": "2024-08-09T16:15:00Z"
        },
        {
            "title": "California is on pace for worst wildfire year in recent memory, due mostly to SoCal blazes",
            "summary": "California has already burned over 1.2 million acres this year, marking it as potentially the worst wildfire season in recent history. Southern California fires account for 60% of the total burned acreage, driven by drought conditions and extreme heat.",
            "link": "https://example.com/worst-wildfire-year",
            "published": "2024-08-09T18:45:00Z"
        }
    ]
    
    print("TESTING NEW SUMMARIZATION")
    print("="*70)
    print(f"Group Model: {group_model}")
    print(f"Summarize Model: {summarize_model}")
    print(f"Test Articles: {len(test_articles)}")
    print()
    
    # Test the grouping and summarization
    result = group_and_summarize(test_articles, group_model, summarize_model, openai_api_key)
    
    print("RESULTS:")
    print("-" * 50)
    
    for i, topic in enumerate(result.get("topics", []), 1):
        print(f"{i}. TOPIC: {topic.get('topic', 'Unknown Topic')}")
        print(f"   ARTICLES: {len(topic.get('articles', []))}")
        print(f"   SUMMARY: {topic.get('summary', 'No summary')}")
        print()
        
        # Check if summary looks like the old list format
        summary_text = topic.get('summary', '')
        if 'A collection of' in summary_text and 'articles about' in summary_text:
            print("   ⚠️  WARNING: Still using list format instead of narrative!")
        elif 'Articles:' in summary_text or any(char in summary_text for char in ['1.', '2.', '•', '-']):
            print("   ⚠️  WARNING: Contains list-like formatting!")
        else:
            print("   ✅ Appears to be narrative format")
        print()
    
    print("ANALYSIS:")
    print("-" * 50)
    
    if len(result.get("topics", [])) == 0:
        print("❌ No topics generated - check grouping functionality")
    else:
        narrative_count = 0
        list_count = 0
        
        for topic in result.get("topics", []):
            summary_text = topic.get('summary', '')
            if ('A collection of' in summary_text or 
                'Articles:' in summary_text or 
                any(char in summary_text for char in ['1.', '2.', '•', '-'])):
                list_count += 1
            else:
                narrative_count += 1
        
        print(f"Narrative summaries: {narrative_count}")
        print(f"List-format summaries: {list_count}")
        
        if narrative_count > list_count:
            print("✅ SUCCESS: Mostly narrative format")
        else:
            print("❌ ISSUE: Still producing list-format summaries")
            print("\nRECOMMENDATIONS:")
            print("1. Try using GPT-4o-mini for SUMMARIZE_MODEL")
            print("2. Further refine the summarization prompt")
            print("3. Consider post-processing to clean up formatting")

if __name__ == "__main__":
    test_summarization()