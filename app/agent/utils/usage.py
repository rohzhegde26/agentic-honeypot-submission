import os
import csv
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# CSV structure: timestamp, model, task, prompt_tokens, completion_tokens, total_tokens
USAGE_FILE = os.path.join("data", "token_usage.csv")

def log_token_usage(model: str, task: str, usage: Dict[str, Any]):
    """
    Logs LLM token usage to a local CSV file for tracking.
    """
    try:
        # Ensure data directory exists (just in case)
        os.makedirs("data", exist_ok=True)

        file_exists = os.path.isfile(USAGE_FILE)
        
        with open(USAGE_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            # Write header if new file
            if not file_exists:
                writer.writerow(["timestamp", "model", "task", "prompt_tokens", "completion_tokens", "total_tokens"])
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                model,
                task,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                usage.get("total_tokens", 0)
            ])
        
        logger.debug(f"Logged token usage for {model} to {USAGE_FILE}")
    except Exception as e:
        logger.error(f"Failed to log token usage: {e}")
