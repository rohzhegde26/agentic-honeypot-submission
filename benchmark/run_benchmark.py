import asyncio
import json
import logging
import os
import random
import uuid
import sys
from typing import List, Dict
from functools import lru_cache

# Add project root to sys.path to ensure we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.agent.workflow import run_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BENCHMARK_CONFIG_FILE = "benchmark/benchmark_config.json"
OUTPUT_FILE = "benchmark/webui/data.json"

async def run_benchmark():
    """
    Main benchmark loop.
    1. Load contestants (models/keys).
    2. Load tester scenarios (messages).
    3. Run agent for each combination.
    4. Save anonymized results.
    """
    
    # 1. Load Configuration
    if not os.path.exists(BENCHMARK_CONFIG_FILE):
        logger.error(f"Config file not found: {BENCHMARK_CONFIG_FILE}")
        print(f"Please create {BENCHMARK_CONFIG_FILE} with a list of contestants.")
        return

    with open(BENCHMARK_CONFIG_FILE, "r") as f:
        config_data = json.load(f)
    
    contestants = config_data.get("contestants", [])
    scenarios = config_data.get("scenarios", [])
    
    if not contestants:
        logger.error("No contestants found in config.")
        return

    results = []

    # 2. Iterate Scenarios
    for scenario in scenarios:
        scenario_id = str(uuid.uuid4())
        tester_message = scenario.get("message")
        logger.info(f"Processing Scenario: {tester_message[:30]}...")
        
        scenario_output = {
            "id": scenario_id,
            "message": tester_message,
            "responses": []
        }
        
        # 3. Iterate Contestants
        for contestant in contestants:
            name = contestant.get("name")
            api_key = contestant.get("api_key")
            base_url = contestant.get("base_url")
            model = contestant.get("model")
            
            logger.info(f"  Running Contestant: {name}")
            
            # --- DYNAMIC CONFIG INJECTION ---
            # We must monkey-patch the settings. 
            # get_settings is lru_cached, so we must define a new override or clear cache.
            # The easiest way for this codebase is to modify os.environ and clear cache.
            os.environ["NVIDIA_API_KEY"] = api_key
            if base_url:
                os.environ["NVIDIA_BASE_URL"] = base_url
            if model:
                os.environ["MODEL_PRIMARY"] = model
                os.environ["MODEL_FALLBACK"] = model # Use same for fallback in benchmark
            
            # Force overwrite PRIMARY key also, because llm.py prioritizes it over NVIDIA_API_KEY
            os.environ["NVIDIA_API_KEY_PRIMARY"] = api_key
            os.environ["NVIDIA_API_KEY_FALLBACK"] = ""
            
            # Clear cache to force reload from os.environ
            get_settings.cache_clear()
            
            # Verify settings loaded correctly
            current_settings = get_settings()
            # logger.info(f"    Loaded Key: {current_settings.NVIDIA_API_KEY[:4]}... Model: {current_settings.MODEL_PRIMARY}")

            try:
                # Run the agent
                # We start a new session for each request to ensure no history pollution
                session_id = f"bench-{uuid.uuid4()}"
                
                agent_result = await run_agent(
                    session_id=session_id,
                    message=tester_message,
                    messages_history=[], # Starting fresh
                    metadata={"channel": "Benchmark", "language": "en", "locale": "IN"},
                    turn_count=1
                )
                
                reply = agent_result.get("agent_reply", "")
                scam_level = agent_result.get("scam_level", "unknown")
                
                scenario_output["responses"].append({
                    "contestant_name": name, # Kept for internal debugging, remove for blind? 
                                            # Actually we need to track who won. 
                                            # The UI should hide this.
                    "reply": reply,
                    "scam_level": scam_level,
                    "model": model
                })
                
            except Exception as e:
                logger.error(f"    Failed: {e}")
                scenario_output["responses"].append({
                    "contestant_name": name,
                    "reply": f"[ERROR] Generation failed: {str(e)}",
                    "scam_level": "error"
                })

        # Shuffle responses for Blind Test if needed, but the UI can also do it.
        # Doing it here ensures the JSON order doesn't leak rank if we just dump it.
        # But we want to map back votes to contestants. 
        # So we keep them identifiable here, and the UI will randomize display.
        results.append(scenario_output)

    # 4. Save Results
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"scenarios": results}, f, indent=2)
    
    logger.info(f"Benchmark complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
