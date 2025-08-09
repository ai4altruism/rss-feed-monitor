# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
- `python src/main.py` - Run console output (default)
- `python src/main.py --output web` - Run with web dashboard at http://localhost:5000
- `python src/main.py --output slack` - Post to Slack (requires SLACK_WEBHOOK_URL)
- `python src/main.py --output email` - Send email report (requires SMTP config)
- `python src/main.py --ignore-history` - Process all articles, ignoring history
- `python src/main.py --history-retention 60` - Set custom retention period (days)
- `python src/scheduler.py --output slack --interval 30` - Run scheduler with 30-minute intervals

### Docker Commands
- `docker run --rm --env-file .env -v $(pwd)/.env:/app/.env IMAGE_NAME --output console` - Run once with console output
- `docker run --rm --env-file .env -v $(pwd)/.env:/app/.env IMAGE_NAME --output slack` - Run once with Slack output
- `docker run -d --env-file .env -v $(pwd)/.env:/app/.env --name news_scheduler --restart unless-stopped --entrypoint python IMAGE_NAME src/scheduler.py --output slack --interval 60` - Run scheduler daemon
- `docker logs news_scheduler -f` - Follow logs in real-time
- `docker stop news_scheduler && docker rm news_scheduler` - Stop and remove container
- `docker exec news_scheduler python src/check_history.py` - Check article history status

### Article History Management
- `rm -f data/article_history.json` - Clear article history
- `python src/check_history.py` - Check history status

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
  - Default models: `gpt-5-mini` (supports GPT-5 series with enhanced reasoning)
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

## Development Notes
- Python 3.10+ required
- No test suite currently exists
- Docker containers run as non-root user for security
- Persistent data stored in mounted volumes (`data/`, `logs/`)
- Article history prevents duplicate processing across runs
- HTTP caching reduces RSS feed requests
- Graceful error handling for missing dependencies (Slack, email modules)