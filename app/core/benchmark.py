"""
Benchmark Arena Logic
Integrated backend for the multi-user benchmark system.
"""
import asyncio
import json
import os
import sys
import uuid
import time
import random
from typing import Dict, List, Any
from pydantic import BaseModel

from app.config import get_settings
from app.agent.workflow import run_agent
from app.agent.llm import call_llm

# --- State ---
class Voter:
    def __init__(self, nickname: str):
        self.id = str(uuid.uuid4())
        self.nickname = nickname
        self.joined_at = time.time()
        self.last_seen = time.time()

class GameState:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.contestants = []  # List of {name, model, base_url}
        self.turns = []        # List of turn data
        self.current_turn = -1
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self.voters: Dict[str, Voter] = {} # token -> Voter
        self.status = "waiting" # waiting, input, thinking, voting, results
        self.start_time = time.time()
        self.timings = {} # {model_name: [duration_ms, ...]}
        self.expected_voters = 1

# Global singleton
benchmark_state = GameState()

# --- Helpers ---
def load_contestants():
    # Path relative to project root (assuming run.py is at root)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(base_dir, "benchmark", "benchmark_config.json")
    
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)
            benchmark_state.contestants = data.get("contestants", [])
    else:
        benchmark_state.contestants = []

async def llm_vote_round(turn_data: Dict):
    """Ask each LLM to vote on the best response (excluding their own)."""
    settings = get_settings()
    responses = turn_data["responses"]
    message = turn_data["user_message"]
    
    votes = {} # {voter_model_name: voted_alias}
    
    for contestant in benchmark_state.contestants:
        try:
            # Filter out own response
            others = [r for r in responses if r["contestant_name"] != contestant["name"]]
            if not others: continue
            
            random.shuffle(others)
            
            options_text = "\n".join([f"[{r['alias']}] {r['reply'][:200]}..." for r in others])
            
            prompt = f"""
            User Message: "{message}"
            
            Rank the following AI responses to the user message. 
            Select the single best response based on helpfulness, accuracy, and safety.
            
            Options:
            {options_text}
            
            Return ONLY the alias of the best response (e.g., "Agent A"). Do not explain.
            """
            
            # Using call_llm with overridden env vars is tricky because call_llm reads 
            # settings() which are cached. We need to handle this carefully.
            # Ideally we'd pass model params to call_llm, but existing signature is fixed.
            # We will use the same env-var-patching trick as before, ensuring we lock 
            # or handle concurrency if possible (though FastAPI async is single-thread mostly).
            
            os.environ["MODEL_PRIMARY"] = contestant["model"]
            os.environ["FIREWORKS_API_KEY"] = settings.FIREWORKS_API_KEY # Use global key
            # Force primary key override if present
            # We assume FIREWORKS_API_KEY is what we want for these models.
            # But the user might have passed a specific "benchmark key" for joining?
            # We used that purely for Auth.
            
            get_settings.cache_clear()
            
            messages = [{"role": "user", "content": prompt}]
            
            # Use 'persona' trait for simple generation
            reply = await asyncio.to_thread(call_llm, "persona", messages)
            
            # Parse alias
            clean_reply = reply.strip().replace('"', '').replace("'", "")
            voted_alias = None
            for r in others:
                if r["alias"] in clean_reply:
                    voted_alias = r["alias"]
                    break
            
            if voted_alias:
                votes[contestant["name"]] = voted_alias
                
        except Exception as e:
            print(f"Voting error for {contestant['name']}: {e}")
            
    return votes

async def process_turn(message: str):
    benchmark_state.status = "thinking"
    benchmark_state.current_turn += 1
    benchmark_state.conversation_history.append({"role": "user", "content": message})
    
    responses = []
    settings = get_settings()
    
    # Generate responses
    if not benchmark_state.contestants:
        load_contestants()

    for contestant in benchmark_state.contestants:
        t_start = time.perf_counter()
        
        # Monkey patch env for this generation
        # NOTE: This is not thread-safe in a multi-threaded app, but safe in async single-loop
        os.environ["NVIDIA_API_KEY_PRIMARY"] = settings.FIREWORKS_API_KEY 
        os.environ["MODEL_PRIMARY"] = contestant["model"]
        os.environ["MODEL_FALLBACK"] = contestant["model"]
        if "base_url" in contestant:
            os.environ["NVIDIA_BASE_URL"] = contestant["base_url"]
            
        get_settings.cache_clear()
        
        try:
            result = await run_agent(
                session_id=f"bench-{benchmark_state.session_id}-{benchmark_state.current_turn}",
                message=message,
                messages_history=benchmark_state.conversation_history[:-1],
                metadata={"channel": "Benchmark", "language": "en"},
                turn_count=benchmark_state.current_turn + 1
            )
            reply = result.get("agent_reply", "[No Response]")
        except Exception as e:
            reply = f"[Error: {e}]"
            
        duration = (time.perf_counter() - t_start) * 1000
        
        # Track timing
        if contestant["name"] not in benchmark_state.timings:
            benchmark_state.timings[contestant["name"]] = []
        benchmark_state.timings[contestant["name"]].append(duration)
        
        responses.append({
            "contestant_name": contestant["name"],
            "reply": reply,
            "duration": duration
        })
    
    # Shuffle and alias
    random.shuffle(responses)
    for i, r in enumerate(responses):
        r["alias"] = f"Agent {chr(65+i)}"
        
    turn_data = {
        "user_message": message,
        "responses": responses,
        "human_votes": {}, 
        "llm_votes": {}
    }
    
    # Run LLM Voting
    turn_data["llm_votes"] = await llm_vote_round(turn_data)
    
    benchmark_state.turns.append(turn_data)
    benchmark_state.status = "voting"

def join_session(api_key: str, nickname: str, expected_voters: int = 1) -> str:
    """Join the session and return a token."""
    settings = get_settings()
    # Validate API Key
    if api_key not in [settings.API_SECRET_KEY, settings.FIREWORKS_API_KEY]:
        raise ValueError("Invalid API Key")
    
    token = str(uuid.uuid4())
    
    # Initialize state if first join
    if not benchmark_state.voters:
        benchmark_state.reset()
        benchmark_state.expected_voters = expected_voters
        load_contestants()
        
    benchmark_state.voters[token] = Voter(nickname)
    
    # Auto-start if count reached
    if len(benchmark_state.voters) >= benchmark_state.expected_voters:
        if benchmark_state.status == "waiting":
            benchmark_state.status = "input"
        
    return token

def next_turn(token: str):
    if token in benchmark_state.voters:
        benchmark_state.status = "input"

def get_poll_state(token: str) -> Dict[str, Any]:
    """Get the current state for a voter."""
    if token not in benchmark_state.voters:
        return None
    
    voter = benchmark_state.voters[token]
    voter.last_seen = time.time()
    
    # Calculate average timings
    avg_timings = {}
    for model, times in benchmark_state.timings.items():
        if times:
            avg_timings[model] = round(sum(times) / len(times), 0)
    
    response = {
        "status": benchmark_state.status,
        "turn": benchmark_state.current_turn,
        "voters_count": len(benchmark_state.voters),
        "voters_names": [v.nickname for v in benchmark_state.voters.values()],
        "avg_timings": avg_timings,
        "expected_voters": benchmark_state.expected_voters
    }
    
    if benchmark_state.current_turn >= 0 and benchmark_state.current_turn < len(benchmark_state.turns):
        current = benchmark_state.turns[benchmark_state.current_turn]
        response["message"] = current["user_message"]
        
        # Only show responses if in voting or result phase
        response["responses"] = []
        if benchmark_state.status in ["voting", "results"]:
            response["responses"] = [
                {
                    "alias": r["alias"], 
                    "reply": r["reply"], 
                    "model_name": r["contestant_name"] if benchmark_state.status == "results" else None
                } 
                for r in current["responses"]
            ]
        
        # Show votes
        response["human_votes"] = current["human_votes"]
        if benchmark_state.status == "results":
             response["llm_votes"] = current["llm_votes"]
    
    return response

def cast_vote(token: str, agent_alias: str):
    if token not in benchmark_state.voters: return
    name = benchmark_state.voters[token].nickname
    
    if benchmark_state.current_turn >= 0:
        turn = benchmark_state.turns[benchmark_state.current_turn]
        turn["human_votes"][name] = agent_alias

def reveal_results(token: str):
    if token in benchmark_state.voters:
        benchmark_state.status = "results"

