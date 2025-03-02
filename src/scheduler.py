# src/scheduler.py

import time
import subprocess
import os
import logging
import argparse
from dotenv import dotenv_values
from utils import setup_logger

def run_scheduler(output="slack", interval=None):
    """
    Run the RSS Feed Monitor at regular intervals.
    
    Parameters:
        output (str): Output method (console, slack, email, web)
        interval (int): Interval in minutes between runs (defaults to PROCESS_INTERVAL in .env)
    """
    logger = setup_logger()
    logger.info("Starting RSS Feed Monitor Scheduler...")
    
    # Load environment variables
    env_vars = dotenv_values(".env")
    
    # Get interval from parameter, .env, or default to 60 minutes
    if interval is None:
        interval = int(env_vars.get("PROCESS_INTERVAL", 60))
    
    logger.info(f"Running with {output} output method every {interval} minutes")
    
    while True:
        logger.info(f"Running RSS Feed Monitor...")
        
        try:
            # Run the main.py script as a subprocess
            cmd = ["python", "src/main.py", f"--output", output]
            subprocess.run(cmd, check=True)
            logger.info(f"RSS Feed Monitor run completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running RSS Feed Monitor: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        # Wait for the next interval
        next_run_time = time.time() + (interval * 60)
        logger.info(f"Next run scheduled at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run_time))}")
        
        try:
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RSS Feed Monitor Scheduler')
    parser.add_argument('--output', choices=['console', 'slack', 'email', 'web'], default='slack',
                       help='Output method (default: slack)')
    parser.add_argument('--interval', type=int,
                       help='Interval in minutes between runs (defaults to PROCESS_INTERVAL in .env)')
    args = parser.parse_args()
    
    run_scheduler(output=args.output, interval=args.interval)