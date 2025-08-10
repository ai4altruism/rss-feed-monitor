#!/usr/bin/env python3
# src/review_articles.py

import json
import os
import logging
from datetime import datetime
from dotenv import dotenv_values
from rss_reader import fetch_feeds
from llm_filter import filter_stories
from utils import setup_logger

class ArticleReviewer:
    """Interactive tool for reviewing articles and filter decisions."""
    
    def __init__(self):
        self.logger = setup_logger()
        self.env_vars = dotenv_values(".env")
        self.openai_api_key = self.env_vars.get("OPENAI_API_KEY")
        self.filter_prompt = self.env_vars.get("FILTER_PROMPT", "")
        self.filter_model = self.env_vars.get("FILTER_MODEL", "gpt-4-turbo")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in the .env file")
    
    def fetch_current_articles(self):
        """Fetch articles from current RSS feeds."""
        rss_feeds = self.env_vars.get("RSS_FEEDS", "")
        
        if "\n" in rss_feeds:
            rss_feed_list = [url.strip() for url in rss_feeds.split("\n") if url.strip()]
        else:
            rss_feed_list = [url.strip() for url in rss_feeds.split(",") if url.strip()]
        
        self.logger.info(f"Fetching from {len(rss_feed_list)} RSS feeds...")
        articles = fetch_feeds(rss_feed_list)
        self.logger.info(f"Fetched {len(articles)} articles total")
        
        return articles
    
    def test_filter_on_articles(self, articles):
        """Test the filter on a list of articles and return results."""
        self.logger.info("Testing filter on articles...")
        
        # Test each article individually to get individual results
        filter_results = []
        
        for article in articles:
            # Test the single article
            filtered = filter_stories([article], self.filter_prompt, self.filter_model, self.openai_api_key)
            
            result = {
                'article': article,
                'passed_filter': len(filtered) > 0,
                'timestamp': datetime.now().isoformat()
            }
            
            filter_results.append(result)
        
        return filter_results
    
    def display_summary(self, filter_results):
        """Display a summary of filter results."""
        total = len(filter_results)
        passed = sum(1 for r in filter_results if r['passed_filter'])
        rejected = total - passed
        
        print("\n" + "="*80)
        print("FILTER RESULTS SUMMARY")
        print("="*80)
        print(f"Total articles: {total}")
        print(f"Passed filter: {passed}")
        print(f"Rejected: {rejected}")
        print(f"Pass rate: {(passed/total*100) if total > 0 else 0:.1f}%")
        print("="*80)
    
    def interactive_review(self, filter_results):
        """Interactive review of filter results."""
        passed_articles = [r for r in filter_results if r['passed_filter']]
        rejected_articles = [r for r in filter_results if not r['passed_filter']]
        
        while True:
            print("\n" + "-"*60)
            print("INTERACTIVE ARTICLE REVIEW")
            print("-"*60)
            print("1. Review articles that PASSED the filter")
            print("2. Review articles that were REJECTED")
            print("3. Search articles by keyword")
            print("4. Show filter statistics")
            print("5. Export results to JSON")
            print("6. Test current filter prompt")
            print("0. Exit")
            print("-"*60)
            
            choice = input("Select an option (0-6): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self._review_article_list(passed_articles, "PASSED")
            elif choice == "2":
                self._review_article_list(rejected_articles, "REJECTED")
            elif choice == "3":
                self._search_articles(filter_results)
            elif choice == "4":
                self.display_summary(filter_results)
            elif choice == "5":
                self._export_results(filter_results)
            elif choice == "6":
                self._show_filter_info()
            else:
                print("Invalid option. Please try again.")
    
    def _review_article_list(self, article_results, status):
        """Review a list of articles."""
        if not article_results:
            print(f"\nNo articles {status} the filter.")
            return
        
        print(f"\n{status} ARTICLES ({len(article_results)} total)")
        print("-" * 60)
        
        for i, result in enumerate(article_results, 1):
            article = result['article']
            print(f"\n[{i}] {article.get('title', 'No title')}")
            print(f"    Source: {article.get('link', 'No link')}")
            print(f"    Published: {article.get('published', 'Unknown')}")
            print(f"    Summary: {article.get('summary', 'No summary')[:150]}...")
            
            if i % 5 == 0:  # Pause every 5 articles
                response = input(f"\nShowing {i}/{len(article_results)}. Press Enter to continue, 'q' to quit: ")
                if response.lower() == 'q':
                    break
    
    def _search_articles(self, filter_results):
        """Search articles by keyword."""
        keyword = input("\nEnter keyword to search for: ").strip().lower()
        
        if not keyword:
            print("No keyword entered.")
            return
        
        matching = []
        for result in filter_results:
            article = result['article']
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            
            if keyword in title or keyword in summary:
                matching.append(result)
        
        if not matching:
            print(f"No articles found containing '{keyword}'")
            return
        
        print(f"\nFound {len(matching)} articles containing '{keyword}':")
        print("-" * 60)
        
        for i, result in enumerate(matching, 1):
            article = result['article']
            status = "PASSED" if result['passed_filter'] else "REJECTED"
            
            print(f"\n[{i}] {status} | {article.get('title', 'No title')}")
            print(f"    Summary: {article.get('summary', 'No summary')[:150]}...")
    
    def _export_results(self, filter_results):
        """Export results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/review_results_{timestamp}.json"
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "filter_prompt": self.filter_prompt,
            "filter_model": self.filter_model,
            "total_articles": len(filter_results),
            "passed_filter": sum(1 for r in filter_results if r['passed_filter']),
            "results": filter_results
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"\nResults exported to: {filename}")
        except Exception as e:
            print(f"Error exporting results: {e}")
    
    def _show_filter_info(self):
        """Show current filter configuration."""
        print("\n" + "="*80)
        print("CURRENT FILTER CONFIGURATION")
        print("="*80)
        print(f"Model: {self.filter_model}")
        print(f"Prompt:")
        print("-" * 40)
        print(self.filter_prompt)
        print("-" * 40)

def main():
    """Main function for the interactive article reviewer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive RSS Feed Article Reviewer")
    parser.add_argument("--auto-fetch", action="store_true",
                       help="Automatically fetch current articles")
    parser.add_argument("--export-only", action="store_true",
                       help="Fetch articles, run filter, and export results without interactive mode")
    
    args = parser.parse_args()
    
    try:
        reviewer = ArticleReviewer()
        
        print("RSS Feed Monitor - Article Reviewer")
        print("="*50)
        
        if args.auto_fetch:
            # Fetch current articles
            articles = reviewer.fetch_current_articles()
            
            if not articles:
                print("No articles fetched. Check your RSS feeds configuration.")
                return
            
            # Run filter test
            filter_results = reviewer.test_filter_on_articles(articles)
            
            # Show summary
            reviewer.display_summary(filter_results)
            
            if args.export_only:
                reviewer._export_results(filter_results)
                print("Results exported. Exiting.")
                return
            
            # Start interactive review
            reviewer.interactive_review(filter_results)
        else:
            print("Use --auto-fetch to fetch current articles and start review.")
            print("Example: python src/review_articles.py --auto-fetch")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())