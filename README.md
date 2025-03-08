# 📰 RSS Feed Monitor

RSS Feed Monitor is an AI-powered news aggregator that fetches, filters, groups, and summarizes articles from various RSS feeds. It leverages OpenAI's GPT models to curate relevant news topics and provide concise summaries, including hyperlinks to the original articles.

## 🚀 Features

- **Fetches** news articles from multiple RSS feeds with efficient caching
- **Filters** articles based on a user-defined prompt using OpenAI's API
- **Groups** similar articles into meaningful topics with AI categorization
- **Generates concise summaries** for each topic group
- **Includes hyperlinks** to the original sources
- **Eliminates duplicate articles** by tracking article history
- **Multiple output methods**:
  - Console output (JSON)
  - Web dashboard with UI
  - Slack integration
  - Email reports
- **Containerized** with Docker for easy deployment
- **Scheduled execution** with configurable intervals

## 📜 Installation

### Local Development Setup

1. **Clone the Repository**

```bash
git clone https://github.com/yourusername/rss-feed-monitor.git
cd rss-feed-monitor
```

2. **Run the Setup Script**

```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:

- Create necessary directories
- Set up an environment file from the template
- Create a Python virtual environment
- Install dependencies
- Optionally build the Docker image

3. **Configure Environment Variables**
   Edit the `.env` file that was created from `.env.example`:

```ini
# OpenAI API Key (required)
OPENAI_API_KEY=your_openai_api_key_here

# RSS feed URLs (comma-separated or multi-line)
RSS_FEEDS=https://feeds.npr.org/1001/rss.xml
https://feeds.bbci.co.uk/news/rss.xml

# Filtering prompt (modify as needed)
FILTER_PROMPT=Only include articles related to AI and technology.

# Article history settings
HISTORY_RETENTION_DAYS=30

# Optional: Slack, Email, Web Dashboard configuration
...
```

### Docker Installation (Recommended for Production)

1. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

2. **Build and Run with Docker Compose**

```bash
docker-compose up -d rss-feed-monitor
```

This will:

- Build the Docker image
- Run the container with the web dashboard
- Mount volumes for logs, data, and configuration

## ▶ Usage

### Running Locally

Use one of the following commands:

```bash
# Console output (default)
python src/main.py

# Web dashboard at http://localhost:5000
python src/main.py --output web

# Post to Slack (requires SLACK_WEBHOOK_URL in .env)
python src/main.py --output slack

# Send email report (requires email settings in .env)
python src/main.py --output email

# Ignore article history (process all articles, even if already published)
python src/main.py --output slack --ignore-history

# Set custom article history retention period (in days)
python src/main.py --output slack --history-retention 60

# Run scheduler (checks periodically)
python src/scheduler.py --output slack --interval 30
```

### Running with Docker

```bash
# Run with web dashboard
docker-compose up -d rss-feed-monitor

# Run web dashboard only (no processing)
docker-compose up -d dashboard

# Run scheduler (periodic checks with Slack output)
docker-compose up -d scheduler
```

### Web Dashboard

Access the web dashboard at http://localhost:5000

The dashboard shows:

- Grouped topics with summaries
- Links to original articles
- Auto-refresh every 30 minutes

## 🔀 Output Methods

### Console Output (Default)

Prints JSON output to the console:

```json
{
  "topics": [
    {
      "topic": "AI and Technology",
      "summary": "Recent developments in AI show...",
      "articles": [
        {
          "title": "New AI breakthrough...",
          "link": "https://example.com/article1"
        }
      ]
    }
  ]
}
```

### Web Dashboard

Displays a responsive web UI with:

- Topic cards with summaries
- Clickable article links
- Last update timestamp

### Slack Integration

Posts formatted summaries to a Slack channel with:

- Topic headers and summaries
- Article links
- Requires Slack webhook URL

### Email Reports

Sends HTML emails with:

- Formatted topic summaries
- Article links
- Configurable recipients

## 🔄 Article History

The RSS Feed Monitor tracks published articles to ensure each update contains only new content:

- **Eliminates duplicate stories**: Articles are only processed once, even across multiple runs
- **Configurable retention**: Set how long to remember published articles (default: 30 days)
- **Automatic cleanup**: Old entries are periodically removed to prevent unlimited growth
- **Override option**: Use `--ignore-history` flag when testing or to force reprocessing

Configure the retention period in `.env`:

```ini
HISTORY_RETENTION_DAYS=30
```

Or via command line:

```bash
python src/main.py --history-retention 60
```

## 📁 Project Structure

```
rss-feed-monitor/
├── .env                     # Environment variables
├── .env.example             # Template for environment variables
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Multi-container configuration
├── requirements.txt         # Python dependencies
├── setup.sh                 # Setup script
│
├── data/                    # Persistent data storage
│   ├── cache.json           # RSS feed cache
│   ├── latest_summary.json  # Latest summary data
│   └── article_history.json # Published article tracking
│
├── logs/                    # Application logs
│   └── app.log              # Log file
│
└── src/                     # Source code
    ├── main.py              # Entry point
    ├── rss_reader.py        # Feed fetching
    ├── llm_filter.py        # Article filtering
    ├── summarizer.py        # Group and summarize
    ├── utils.py             # Utilities
    ├── article_history.py   # Article history tracking
    ├── slack_publisher.py   # Slack integration
    ├── email_reporter.py    # Email reports
    ├── web_dashboard.py     # Web interface
    ├── scheduler.py         # Scheduled execution
    │
    └── templates/           # Web templates
        └── dashboard.html   # Dashboard HTML
```

## ⚙ Configuration

### RSS Feeds

Add RSS feeds in `.env` using **comma-separated values**:

```ini
RSS_FEEDS=https://example.com/rss1.xml,https://example.com/rss2.xml
```

Or **multi-line format**:

```ini
RSS_FEEDS=https://example.com/rss1.xml
https://example.com/rss2.xml
```

### Filter Criteria

Modify `FILTER_PROMPT` in `.env`:

```ini
FILTER_PROMPT=Include only climate change news and environmental topics.
```

### Article History

Configure the article history retention period:

```ini
HISTORY_RETENTION_DAYS=30
```

### OpenAI Models

Choose models based on your needs:

```ini
FILTER_MODEL=gpt-4o
GROUP_MODEL=gpt-4o
SUMMARIZE_MODEL=gpt-4o
```

### Scheduler Settings

Set the checking interval (in minutes):

```ini
PROCESS_INTERVAL=60
```

### Slack Integration

Get a webhook URL from Slack API:

```ini
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Email Configuration

Configure SMTP settings for email delivery:

```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=True
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

## 🐳 Docker Deployment

The application includes three Docker services:

1. **rss-feed-monitor**: Main service with web dashboard

   ```bash
   docker-compose up -d rss-feed-monitor
   ```

2. **dashboard**: Web dashboard only (no processing)

   ```bash
   docker-compose up -d dashboard
   ```

3. **scheduler**: Periodic processing with Slack output
   ```bash
   docker-compose up -d scheduler
   ```

## 🔄 Managing Your Deployment

### Workflow for Complete Reset and Restart

Follow these steps to stop, update configuration, clear history, and restart:

```bash
# 1. Stop the container
docker-compose down

# 2. Update .env file if needed
nano .env

# 3. Remove history if desired
rm -f data/article_history.json

# 4. Start the container
docker-compose up -d

# 5. Check logs to verify it's running correctly
docker-compose logs -f
```

### Common Management Tasks

#### Starting and Stopping

```bash
# Stop containers (preserves data)
docker-compose stop

# Stop and remove containers (still preserves volume data)
docker-compose down

# Start containers
docker-compose start

# Restart with latest configuration
docker-compose up -d
```

#### Managing Article History

```bash
# Clear article history
rm -f data/article_history.json

# Run once ignoring history
docker-compose exec scheduler python src/main.py --output slack --ignore-history

# Check history status
docker-compose exec scheduler python src/check_history.py
```

#### Monitoring

```bash
# View recent logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific number of lines
docker-compose logs --tail=100
```

#### Updating the Container

```bash
# On your local machine
docker save -o rss-feed-monitor-new.tar rss-feed-monitor:latest
scp rss-feed-monitor-new.tar user@remote-server:/path/to/deployment/

# On the remote server
docker-compose down
docker load -i rss-feed-monitor-new.tar
docker-compose up -d
```

## 🛠 Troubleshooting

### Common Issues

#### OpenAI API Errors

- **Error**: Authentication or token limit issues
- **Fix**: Check your API key and adjust the prompts if reaching token limits

#### Web Dashboard Not Showing Data

- **Error**: "No summaries available yet" message
- **Fix**: Run the application with `--output web` to generate summaries

#### No New Articles Appearing

- **Error**: Updates show "No new articles found since last update"
- **Fix**: Use `--ignore-history` flag to force processing all articles, or wait for genuinely new content

#### Article History Not Working

- **Error**: Duplicate articles appearing in every update
- **Fix**: Check if `data/article_history.json` exists and has proper permissions
- **Diagnostic**: Run `docker-compose exec scheduler python src/check_history.py`

#### Slack Integration Not Working

- **Error**: Failed to publish to Slack
- **Fix**: Verify your webhook URL in `.env` and check Slack app permissions

#### Scheduling Issues

- **Error**: Scheduler not running at expected intervals
- **Fix**: Check `PROCESS_INTERVAL` in `.env` and verify logs

### Debugging Logs

Check logs for detailed error information:

```bash
# Local logs
cat logs/app.log

# Docker logs
docker-compose logs rss-feed-monitor
```

## 📊 Data Persistence

All data is stored in volume-mounted directories:

- `/data`: Contains article history, cache, and summaries
- `/logs`: Contains application logs

These directories are preserved across container restarts and updates. To completely reset:

```bash
# Remove all data (use with caution)
rm -rf data/* logs/*
```

## 📜 License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). Copyright (c) 2025 AI for Altruism Inc.

When using or distributing this software, please attribute as follows:

```
RSS Feed Monitor
Copyright (c) 2025 AI for Altruism Inc
License: GNU GPL v3.0
```

## 🎯 Contributing

Pull requests are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📩 Contact

For issues or questions, please open a GitHub issue or contact:

- **Email**: team@ai4altruism.org