#!/usr/bin/env python3
# src/analyze_feeds.py

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from dotenv import dotenv_values
from rss_reader import fetch_feeds
from utils import setup_logger

class FeedAnalyzer:
    """Tool for analyzing RSS feed content and identifying disaster-related patterns."""
    
    def __init__(self):
        self.logger = setup_logger()
        self.env_vars = dotenv_values(".env")
        
        # Disaster-related keywords to look for
        self.disaster_keywords = {
            'earthquake': ['earthquake', 'quake', 'seismic', 'tremor', 'magnitude'],
            'hurricane': ['hurricane', 'typhoon', 'cyclone', 'tropical storm'],
            'flooding': ['flood', 'flooding', 'inundated', 'submerged', 'deluge'],
            'wildfire': ['wildfire', 'bushfire', 'forest fire', 'blaze', 'inferno'],
            'volcano': ['volcano', 'volcanic', 'eruption', 'lava', 'ash cloud'],
            'tornado': ['tornado', 'twister', 'funnel cloud'],
            'tsunami': ['tsunami', 'tidal wave'],
            'landslide': ['landslide', 'mudslide', 'rockslide', 'avalanche'],
            'severe_weather': ['blizzard', 'ice storm', 'hail storm', 'severe weather'],
            'general_disaster': ['disaster', 'catastrophe', 'emergency', 'evacuation', 'casualties', 'devastation']
        }
    
    def fetch_and_analyze_feeds(self):
        """Fetch articles from RSS feeds and analyze them."""
        # Parse RSS feeds from .env
        rss_feeds = self.env_vars.get("RSS_FEEDS", "")
        
        if "\n" in rss_feeds:
            rss_feed_list = [url.strip() for url in rss_feeds.split("\n") if url.strip()]
        else:
            rss_feed_list = [url.strip() for url in rss_feeds.split(",") if url.strip()]
        
        self.logger.info(f"Analyzing {len(rss_feed_list)} RSS feeds...")
        
        # Fetch articles
        articles = fetch_feeds(rss_feed_list)
        self.logger.info(f"Fetched {len(articles)} articles total")
        
        return articles, rss_feed_list
    
    def analyze_keywords(self, articles):
        """Analyze articles for disaster-related keywords."""
        keyword_matches = defaultdict(list)
        category_counts = Counter()
        
        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            text = f"{title} {summary}"
            
            article_keywords = []
            
            for category, keywords in self.disaster_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        keyword_matches[keyword].append(article)
                        article_keywords.append(category)
            
            # Count categories (avoiding double-counting)
            for category in set(article_keywords):
                category_counts[category] += 1
        
        return keyword_matches, category_counts
    
    def identify_potential_disasters(self, articles):
        """Identify articles that might be disaster-related based on content analysis."""
        potential_disasters = []
        
        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            text = f"{title} {summary}"
            
            # Look for disaster indicators
            disaster_score = 0
            matched_categories = []
            matched_keywords = []
            
            for category, keywords in self.disaster_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        disaster_score += 1
                        if category not in matched_categories:
                            matched_categories.append(category)
                        matched_keywords.append(keyword)
            
            # Also look for numbers that might indicate scale
            magnitude_pattern = r'\b\d+\.\d+\s*(magnitude|richter)\b'
            death_pattern = r'\b\d+\s*(dead|killed|deaths|casualties)\b'
            evacuation_pattern = r'\b\d+\s*(evacuated|displaced|homeless)\b'
            
            if re.search(magnitude_pattern, text, re.IGNORECASE):
                disaster_score += 2
                matched_keywords.append('magnitude_mentioned')
            
            if re.search(death_pattern, text, re.IGNORECASE):
                disaster_score += 2
                matched_keywords.append('casualties_mentioned')
            
            if re.search(evacuation_pattern, text, re.IGNORECASE):
                disaster_score += 1
                matched_keywords.append('evacuation_mentioned')
            
            if disaster_score > 0:
                potential_disasters.append({
                    'article': article,
                    'disaster_score': disaster_score,
                    'categories': matched_categories,
                    'keywords': matched_keywords
                })
        
        # Sort by disaster score (highest first)
        potential_disasters.sort(key=lambda x: x['disaster_score'], reverse=True)
        
        return potential_disasters
    
    def generate_feed_statistics(self, articles, rss_feed_list):
        """Generate statistics about the RSS feeds."""
        # Count articles by domain
        domain_counts = Counter()
        
        for article in articles:
            link = article.get('link', '')
            if link:
                try:
                    # Extract domain from URL
                    domain = link.split('/')[2] if len(link.split('/')) > 2 else 'unknown'
                    domain_counts[domain] += 1
                except:
                    domain_counts['unknown'] += 1
        
        return domain_counts
    
    def print_analysis_report(self, articles, rss_feed_list):
        """Print a comprehensive analysis report."""
        print("\n" + "="*80)
        print("RSS FEED ANALYSIS REPORT")
        print("="*80)
        
        # Basic statistics
        print(f"Total RSS feeds configured: {len(rss_feed_list)}")
        print(f"Total articles fetched: {len(articles)}")
        print(f"Analysis timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Feed sources
        print("\nCONFIGURED RSS FEEDS:")
        print("-" * 40)
        for i, feed in enumerate(rss_feed_list, 1):
            print(f"{i}. {feed}")
        
        # Domain statistics
        domain_counts = self.generate_feed_statistics(articles, rss_feed_list)
        print(f"\nARTICLES BY SOURCE:")
        print("-" * 40)
        for domain, count in domain_counts.most_common(10):
            print(f"{domain}: {count} articles")
        
        # Keyword analysis
        keyword_matches, category_counts = self.analyze_keywords(articles)
        
        print(f"\nDISASTER KEYWORD ANALYSIS:")
        print("-" * 40)
        print(f"Articles with disaster keywords: {sum(len(matches) for matches in keyword_matches.values())}")
        
        if category_counts:
            print("Keywords found by category:")
            for category, count in category_counts.most_common():
                print(f"  {category.replace('_', ' ').title()}: {count} articles")
        else:
            print("❌ No disaster-related keywords found in any articles!")
        
        # Potential disaster articles
        potential_disasters = self.identify_potential_disasters(articles)
        
        print(f"\nPOTENTIAL DISASTER ARTICLES:")
        print("-" * 40)
        
        if potential_disasters:
            print(f"Found {len(potential_disasters)} articles with disaster indicators:")
            
            # Show top 10 most likely disaster articles
            for i, item in enumerate(potential_disasters[:10], 1):
                article = item['article']
                score = item['disaster_score']
                categories = item['categories']
                
                print(f"\n{i}. SCORE: {score} | CATEGORIES: {', '.join(categories)}")
                print(f"   TITLE: {article.get('title', 'No title')}")
                print(f"   SUMMARY: {article.get('summary', 'No summary')[:200]}...")
                print(f"   LINK: {article.get('link', 'No link')}")
            
            if len(potential_disasters) > 10:
                print(f"\n... and {len(potential_disasters) - 10} more articles with lower scores.")
        
        else:
            print("❌ No articles found with disaster-related content!")
            print("\nThis could mean:")
            print("1. Your RSS feeds don't currently have disaster news")
            print("2. The articles are there but use different terminology")
            print("3. The feeds focus on other topics (politics, sports, etc.)")
        
        # Current filter prompt analysis
        filter_prompt = self.env_vars.get("FILTER_PROMPT", "")
        print(f"\nCURRENT FILTER PROMPT ANALYSIS:")
        print("-" * 40)
        print("Your current filter prompt:")
        print(f'"{filter_prompt}"')
        
        # Suggestions based on analysis
        self.provide_recommendations(potential_disasters, category_counts, filter_prompt)
    
    def provide_recommendations(self, potential_disasters, category_counts, filter_prompt):
        """Provide recommendations based on the analysis."""
        print(f"\nRECOMMENDATIONS:")
        print("-" * 40)
        
        if not potential_disasters:
            print("🔍 IMMEDIATE ACTIONS:")
            print("1. Run the test filter to see if your criteria work on known disaster articles:")
            print("   python src/test_filter.py --verbose")
            print("2. Check if your RSS feeds are working:")
            print("   python src/main.py --ignore-history")
            print("3. Consider adding more disaster-focused RSS feeds like:")
            print("   - https://feeds.reuters.com/reuters/environment")
            print("   - https://www.usgs.gov/natural-hazards/feeds")
        
        elif len(potential_disasters) < 3:
            print("📰 LIMITED DISASTER CONTENT:")
            print(f"Only {len(potential_disasters)} potential disaster articles found.")
            print("1. Your feeds may not have current disaster news")
            print("2. Consider testing with --ignore-history to see older articles")
            print("3. The filter might be working correctly if no disasters are happening")
        
        else:
            print("✅ GOOD NEWS:")
            print(f"Found {len(potential_disasters)} potential disaster articles!")
            print("1. Test your filter against these articles:")
            print("   python src/review_articles.py --auto-fetch")
            print("2. If the filter rejects these articles, consider adjusting your prompt")
        
        # Specific suggestions based on content
        if 'earthquake' in category_counts:
            print("3. Earthquake articles detected - your magnitude threshold (6.0+) might be filtering some")
        
        if 'severe_weather' in category_counts:
            print("4. Severe weather articles found - check if your criteria are too restrictive")
        
        print("\n💡 TESTING WORKFLOW:")
        print("1. python src/test_filter.py --verbose  # Test against known examples")
        print("2. python src/review_articles.py --auto-fetch  # Review current articles")
        print("3. python src/analyze_feeds.py  # Re-run this analysis")

def main():
    """Main function for feed analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze RSS feeds for disaster content")
    parser.add_argument("--export", action="store_true",
                       help="Export detailed results to JSON file")
    parser.add_argument("--keywords-only", action="store_true",
                       help="Show only keyword analysis")
    
    args = parser.parse_args()
    
    try:
        analyzer = FeedAnalyzer()
        
        print("RSS Feed Monitor - Feed Analyzer")
        print("="*50)
        
        # Fetch and analyze
        articles, rss_feed_list = analyzer.fetch_and_analyze_feeds()
        
        if not articles:
            print("❌ No articles fetched!")
            print("Check your RSS_FEEDS configuration in .env file")
            return 1
        
        # Print report
        analyzer.print_analysis_report(articles, rss_feed_list)
        
        # Export if requested
        if args.export:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/feed_analysis_{timestamp}.json"
            
            potential_disasters = analyzer.identify_potential_disasters(articles)
            keyword_matches, category_counts = analyzer.analyze_keywords(articles)
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "total_articles": len(articles),
                "total_feeds": len(rss_feed_list),
                "feeds": rss_feed_list,
                "potential_disasters": len(potential_disasters),
                "category_counts": dict(category_counts),
                "articles": articles,
                "disaster_analysis": [
                    {
                        "title": item['article'].get('title'),
                        "score": item['disaster_score'],
                        "categories": item['categories'],
                        "keywords": item['keywords'],
                        "link": item['article'].get('link')
                    }
                    for item in potential_disasters
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            print(f"\n📁 Detailed analysis exported to: {filename}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return 1

if __name__ == "__main__":
    exit(main())