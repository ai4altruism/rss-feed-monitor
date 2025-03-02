# 📰 RSS Feed Monitor

RSS Feed Monitor is an AI-powered news aggregator that fetches, filters, groups, and summarizes articles from various RSS feeds. It leverages OpenAI's GPT models to curate relevant news topics and provide concise summaries, including hyperlinks to the original articles.

## 🚀 Features

- **Fetches** news articles from multiple RSS feeds with efficient caching
- **Filters** articles based on a user-defined prompt using OpenAI's API
- **Groups** similar articles into meaningful topics with AI categorization
- **Generates concise summaries** for each topic group
- **Includes hyperlinks** to the original sources
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
        {"title": "New AI breakthrough...", "link": "https://example.com/article1"}
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
│   └── cache.json           # RSS feed cache
│   └── latest_summary.json  # Latest summary data
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

## 🛠 Troubleshooting

### Common Issues

#### OpenAI API Errors
- **Error**: Authentication or token limit issues
- **Fix**: Check your API key and adjust the prompts if reaching token limits

#### Web Dashboard Not Showing Data
- **Error**: "No summaries available yet" message
- **Fix**: Run the application with `--output web` to generate summaries

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

## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

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