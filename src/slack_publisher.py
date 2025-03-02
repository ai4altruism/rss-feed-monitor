# src/slack_publisher.py

import requests
import logging
import json
from datetime import datetime

def format_for_slack(summary_data):
    """
    Format the summary data into Slack message blocks.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        
    Returns:
        list: Formatted Slack message blocks.
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 News Summary | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]
    
    for topic_group in summary_data.get("topics", []):
        topic_name = topic_group.get("topic", "Uncategorized")
        summary = topic_group.get("summary", "No summary available.")
        articles = topic_group.get("articles", [])
        
        # Add topic header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{topic_name}*"
            }
        })
        
        # Add summary
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary
            }
        })
        
        # Add article links
        if articles:
            link_text = "*Articles:*\n"
            for idx, article in enumerate(articles, 1):
                title = article.get("title", "Untitled")
                link = article.get("link", "#")
                link_text += f"{idx}. <{link}|{title}>\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": link_text
                }
            })
        
        blocks.append({
            "type": "divider"
        })
    
    return blocks

def publish_to_slack(summary_data, webhook_url):
    """
    Publish the summary data to a Slack channel using a webhook.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        webhook_url (str): The Slack webhook URL.
        
    Returns:
        bool: Whether the message was sent successfully.
    """
    blocks = format_for_slack(summary_data)
    
    payload = {
        "blocks": blocks
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logging.info("Successfully published summary to Slack.")
            return True
        else:
            logging.error(f"Failed to publish to Slack. Status: {response.status_code}, Response: {response.text}")
            return False
    
    except Exception as e:
        logging.error(f"Error publishing to Slack: {e}")
        return False