# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
- `python src/main.py` - Run console output (default)
- `python src/main.py --output web` - Run with web dashboard at http://localhost:5001
- `python src/main.py --output slack` - Post to Slack (requires SLACK_WEBHOOK_URL)
- `python src/main.py --output email` - Send email report (requires SMTP config)
- `python src/main.py --ignore-history` - Process all articles, ignoring history
- `python src/main.py --history-retention 60` - Set custom retention period (days)
- `python src/scheduler.py --output slack --interval 30` - Run scheduler with 30-minute intervals

### Docker Commands
- `docker run --rm --env-file /path/to/.env -v /path/to/.env:/app/.env IMAGE_NAME --output console` - Run once with console output
- `docker run --rm --env-file /path/to/.env -v /path/to/.env:/app/.env IMAGE_NAME --output slack` - Run once with Slack output
- `docker run -d --env-file /path/to/.env -v /path/to/.env:/app/.env --name news_scheduler2 --restart unless-stopped --entrypoint python IMAGE_NAME src/scheduler.py --output slack --interval 60` - Run scheduler daemon
- `docker logs news_scheduler2 -f` - Follow logs in real-time
- `docker stop news_scheduler2 && docker rm news_scheduler2` - Stop and remove container
- `docker exec news_scheduler2 python src/check_history.py` - Check article history status

### Article History Management
- `rm -f data/article_history.json` - Clear article history
- `python src/check_history.py` - Check history status

### Testing and Diagnostics
- `python src/test_filter.py` - Test filter against curated disaster articles
- `python src/test_filter.py --verbose` - Test filter with detailed output
- `python src/review_articles.py --auto-fetch` - Interactive review of current articles  
- `python src/review_articles.py --auto-fetch --export-only` - Export filter results to JSON
- `python src/analyze_feeds.py` - Analyze RSS feeds for disaster content patterns
- `python src/analyze_feeds.py --export` - Export feed analysis to JSON
- `python src/main.py --test-filter` - Run filter test via main script
- `python src/main.py --review-mode --auto-fetch` - Launch interactive review mode
- `python src/main.py --analyze-feeds` - Analyze feeds via main script  
- `python src/main.py --verbose-filter --ignore-history` - Enable detailed filter logging
- `python src/test_summarization.py` - Test summarization output format with sample articles

## Architecture

### Core Pipeline
The application follows a linear processing pipeline:
1. **RSS Reader** (`rss_reader.py`) - Fetches articles from multiple RSS feeds with HTTP caching
2. **Article History** (`article_history.py`) - Filters out previously processed articles
3. **LLM Filter** (`llm_filter.py`) - Uses OpenAI API to filter articles based on user-defined criteria
4. **Summarizer** (`summarizer.py`) - Groups similar articles and generates topic summaries
5. **Output Modules** - Publishes to various destinations (console, Slack, email, web)

### Key Components
- `main.py` - Main entry point with argument parsing and orchestration
- `scheduler.py` - Runs main.py at regular intervals as subprocess
- `web_dashboard.py` - Flask app serving dashboard at configurable port
- `utils.py` - Shared utilities including logger setup
- `templates/dashboard.html` - Web dashboard HTML template

### Testing and Diagnostic Tools
- `test_filter.py` - Automated filter testing against curated disaster articles
- `review_articles.py` - Interactive tool for reviewing filter decisions on live articles
- `analyze_feeds.py` - RSS feed content analysis and disaster keyword detection
- `check_history.py` - Article history inspection and debugging tool
- `data/test_articles.json` - Curated test dataset with known disaster/non-disaster articles

### Data Storage
- `data/cache.json` - RSS feed HTTP caching (ETag, Last-Modified)
- `data/article_history.json` - Tracks published articles to prevent duplicates
- `data/latest_summary.json` - Stores latest summary for web dashboard
- `logs/app.log` - Application logs

### Configuration
Environment variables are loaded from `.env` file:
- `OPENAI_API_KEY` - Required for LLM filtering and summarization
- `RSS_FEEDS` - Comma-separated or multi-line list of RSS URLs
- `FILTER_PROMPT` - Plain language criteria for article filtering
- `PROCESS_INTERVAL` - Scheduler interval in minutes (default: 60)
- `HISTORY_RETENTION_DAYS` - Article history retention period (default: 30)
- OpenAI model selection: `FILTER_MODEL`, `GROUP_MODEL`, `SUMMARIZE_MODEL`
  - **Critical**: `FILTER_MODEL=gpt-4o-mini` (GPT-5-mini rejects obvious disaster articles)
  - **Optimal**: `GROUP_MODEL=gpt-5-mini` (enhanced reasoning for categorization)
  - **Summarization**: `SUMMARIZE_MODEL=gpt-4o-mini` (GPT-5-mini uses all tokens for reasoning, returns empty content)
  - **Issue**: GPT-5-mini fails in filtering (too restrictive) and summarization (reasoning tokens consume completion limit)
  - **Solution**: Use GPT-4o-mini for filtering and summarization, GPT-5-mini only for grouping
  - GPT-5 compatibility: Uses `max_completion_tokens` parameter, default temperature only
- Slack: `SLACK_WEBHOOK_URL`
- Email: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_RECIPIENTS`

### Output Formats
All outputs use the same JSON structure with `topics` array containing grouped articles and summaries. The web output additionally saves this JSON to `data/latest_summary.json` for dashboard consumption.

## Docker Deployment

The application runs as a single Docker container with different entry points:

1. **One-time execution**: Run the monitor once and exit
2. **Scheduler daemon**: Run continuously with periodic execution  
3. **Web dashboard**: Serve the dashboard interface

Use the Docker commands above with your built image name.

## Testing and Debugging Workflow

When experiencing issues with filter accuracy (e.g., 0 articles passing filter):

**Common Issue**: If test shows 0% pass rate for disaster articles, GPT-5-mini is likely being used for filtering.  
**Quick Fix**: Change `FILTER_MODEL=gpt-4o-mini` in .env file.

1. **Test Filter Logic**: `python src/test_filter.py --verbose`
   - Tests filter against 22+ curated disaster/non-disaster articles  
   - Shows accuracy percentage and specific failures
   - **Expected Results**: 80%+ accuracy with GPT-4o-mini, 0-40% with GPT-5-mini
   - Identifies if filter prompt needs adjustment

2. **Analyze Current Feeds**: `python src/analyze_feeds.py`
   - Examines RSS feeds for disaster content patterns
   - Identifies potential disaster articles by keywords
   - Shows feed statistics and content analysis

3. **Interactive Review**: `python src/review_articles.py --auto-fetch`
   - Manually review what articles are being filtered out
   - Search articles by keywords
   - Export results for detailed analysis

4. **Verbose Filtering**: `python src/main.py --verbose-filter --ignore-history`
   - See GPT's reasoning for each filter decision
   - Understand why articles are being rejected
   - Debug prompt effectiveness in real-time

5. **Test Summarization**: `python src/test_summarization.py`
   - Check if summaries are narrative paragraphs vs. article lists
   - Validate summarization model behavior
   - Switch to `SUMMARIZE_MODEL=gpt-4o-mini` if getting list format

## Development Notes
- Python 3.10+ required
- Comprehensive testing suite for filter validation
- Docker containers run as non-root user for security
- Persistent data stored in mounted volumes (`data/`, `logs/`)
- Article history prevents duplicate processing across runs
- HTTP caching reduces RSS feed requests
- Graceful error handling for missing dependencies (Slack, email modules)