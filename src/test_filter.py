#!/usr/bin/env python3
# src/test_filter.py

import json
import os
import logging
from dotenv import dotenv_values
from llm_filter import filter_stories
from utils import setup_logger

def load_test_articles():
    """Load test articles from the test dataset."""
    test_file = "data/test_articles.json"
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test dataset not found: {test_file}")
    
    with open(test_file, "r") as f:
        data = json.load(f)
    
    return data["test_articles"]

def run_filter_test(verbose=False):
    """Run the filter test against the test dataset."""
    logger = setup_logger()
    logger.info("Starting filter test...")
    
    # Load environment variables
    env_vars = dotenv_values(".env")
    openai_api_key = env_vars.get("OPENAI_API_KEY")
    filter_prompt = env_vars.get("FILTER_PROMPT", "")
    filter_model = env_vars.get("FILTER_MODEL", "gpt-4-turbo")
    
    if not openai_api_key:
        logger.error("OPENAI_API_KEY is not set in the .env file")
        return False
    
    # Load test articles
    try:
        test_articles = load_test_articles()
        logger.info(f"Loaded {len(test_articles)} test articles")
    except FileNotFoundError as e:
        logger.error(str(e))
        return False
    
    # Separate articles by expected result
    should_pass = [a for a in test_articles if a["expected_result"] == "pass"]
    should_reject = [a for a in test_articles if a["expected_result"] == "reject"]
    
    logger.info(f"Test dataset: {len(should_pass)} should pass, {len(should_reject)} should be rejected")
    
    # Test articles that should pass
    print("\n" + "="*80)
    print("TESTING ARTICLES THAT SHOULD PASS")
    print("="*80)
    
    passed_correctly = []
    failed_to_pass = []
    
    for article in should_pass:
        # Create a single-item list for the filter function
        test_list = [article]
        filtered = filter_stories(test_list, filter_prompt, filter_model, openai_api_key)
        
        if len(filtered) > 0:
            passed_correctly.append(article)
            result = "✅ PASS"
        else:
            failed_to_pass.append(article)
            result = "❌ FAIL"
        
        print(f"{result} | {article['category'].upper()} | {article['title']}")
        if verbose:
            print(f"    Summary: {article['summary'][:100]}...")
            print()
    
    # Test articles that should be rejected
    print("\n" + "="*80)
    print("TESTING ARTICLES THAT SHOULD BE REJECTED")
    print("="*80)
    
    rejected_correctly = []
    failed_to_reject = []
    
    for article in should_reject:
        # Create a single-item list for the filter function
        test_list = [article]
        filtered = filter_stories(test_list, filter_prompt, filter_model, openai_api_key)
        
        if len(filtered) == 0:
            rejected_correctly.append(article)
            result = "✅ REJECT"
        else:
            failed_to_reject.append(article)
            result = "❌ FAIL"
        
        print(f"{result} | {article['category'].upper()} | {article['title']}")
        if verbose:
            print(f"    Summary: {article['summary'][:100]}...")
            print()
    
    # Summary statistics
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    total_articles = len(test_articles)
    total_correct = len(passed_correctly) + len(rejected_correctly)
    accuracy = (total_correct / total_articles) * 100
    
    print(f"Total articles tested: {total_articles}")
    print(f"Correctly classified: {total_correct}")
    print(f"Overall accuracy: {accuracy:.1f}%")
    print()
    print(f"Should pass - Passed correctly: {len(passed_correctly)}/{len(should_pass)}")
    print(f"Should reject - Rejected correctly: {len(rejected_correctly)}/{len(should_reject)}")
    print()
    
    # Detailed failure analysis
    if failed_to_pass:
        print("ARTICLES THAT SHOULD HAVE PASSED BUT WERE REJECTED:")
        for article in failed_to_pass:
            print(f"  • {article['title']} ({article['category']})")
        print()
    
    if failed_to_reject:
        print("ARTICLES THAT SHOULD HAVE BEEN REJECTED BUT PASSED:")
        for article in failed_to_reject:
            print(f"  • {article['title']} ({article['category']})")
        print()
    
    # Filter prompt analysis
    print("CURRENT FILTER PROMPT:")
    print("-" * 40)
    print(filter_prompt)
    print("-" * 40)
    
    if accuracy < 80:
        print("\n⚠️  LOW ACCURACY WARNING:")
        print("Your filter accuracy is below 80%. Consider:")
        print("1. Adjusting the FILTER_PROMPT in your .env file")
        print("2. Using gpt-4o-mini for FILTER_MODEL (gpt-5-mini is too restrictive for filtering)")
        print("3. Making the criteria more specific or inclusive")
    
    return accuracy >= 80

def main():
    """Main function for running the filter test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the RSS Feed Monitor filter")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Show detailed output for each test")
    
    args = parser.parse_args()
    
    success = run_filter_test(verbose=args.verbose)
    
    if success:
        print("\n🎉 Filter test completed successfully!")
        exit(0)
    else:
        print("\n💥 Filter test failed or encountered errors!")
        exit(1)

if __name__ == "__main__":
    main()