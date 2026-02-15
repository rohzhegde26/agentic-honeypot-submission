"""
Local LLM Benchmark Arena - FastAPI Server
Run: python benchmark/server.py
Access: http://localhost:8080
"""
import asyncio
import json
import os
import sys
import random
import uuid
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.agent.workflow import run_agent
from app.agent.llm import get_openai_client, call_llm

app = FastAPI(title="LLM Benchmark Arena")

# --- Game State ---
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
        self.status = "waiting" # waiting, thinking, voting, results
        self.start_time = time.time()
        
        # Metrics
        self.timings = {} # {model_name: [duration_ms, ...]}

game = GameState()

# --- Load Contestants ---
def load_contestants():
    config_path = os.path.join(os.path.dirname(__file__), "benchmark_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)
            game.contestants = data.get("contestants", [])
    else:
        game.contestants = []

# --- Models ---
class JoinRequest(BaseModel):
    nickname: str
    api_key: str

class MessageRequest(BaseModel):
    message: str

class VoteRequest(BaseModel):
    voter_token: str
    agent_alias: str

# --- Helpers ---
def require_auth(x_api_key: str = Header(None)):
    settings = get_settings()
    # Check against configured secrets or the provided key in join request
    # For simplicity, we check if the key matches the one in .env UPSTASH/NVIDIA/FIREWORKS/API_SECRET
    # Actually, the user said "needs an api key to join". 
    # We'll validate against API_SECRET_KEY from config.
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

async def llm_vote_round(turn_data: Dict):
    """Ask each LLM to vote on the best response (excluding their own)."""
    settings = get_settings()
    responses = turn_data["responses"]
    message = turn_data["user_message"]
    
    votes = {} # {voter_model_name: voted_alias}
    
    for contestant in game.contestants:
        try:
            # Filter out own response
            others = [r for r in responses if r["contestant_name"] != contestant["name"]]
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
            
            # Use specific model to vote
            # Force settings for this call
            os.environ["MODEL_PRIMARY"] = contestant["model"]
            os.environ["FIREWORKS_API_KEY"] = settings.FIREWORKS_API_KEY # Use global key
            # Clear cache
            get_settings.cache_clear()
            
            # Create client directly to avoid global state issues if possible, 
            # but run_agent uses global settings. Here we use call_llm wrapper.
            # We need to ensure call_llm uses the correct model.
            
            messages = [{"role": "user", "content": prompt}]
            
            # We can't easily perform a raw LLM call with specific model using call_llm 
            # without modifying global settings because call_llm reads get_settings().
            # So we rely on the env var override we just did.
            
            reply = await asyncio.to_thread(call_llm, "persona", messages)
            
            # Parse alias
            clean_reply = reply.strip().replace('"', '').replace("'", "")
            # Find which alias matches
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

# --- API Endpoints ---

@app.get("/")
async def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))

@app.post("/api/join")
async def join_session(req: JoinRequest):
    settings = get_settings()
    if req.api_key != settings.API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    token = str(uuid.uuid4())
    game.voters[token] = Voter(req.nickname)
    
    if not game.contestants:
        load_contestants()
        
    return {"token": token, "session_id": game.session_id}

@app.get("/api/poll")
async def poll_state(token: str = Header(None)):
    if token not in game.voters:
        raise HTTPException(status_code=401, detail="Session expired")
    
    voter = game.voters[token]
    voter.last_seen = time.time()
    
    # Calculate average timings
    avg_timings = {}
    for model, times in game.timings.items():
        if times:
            avg_timings[model] = round(sum(times) / len(times), 0)
    
    response = {
        "status": game.status,
        "turn": game.current_turn,
        "voters_count": len(game.voters),
        "voters_names": [v.nickname for v in game.voters.values()],
        "avg_timings": avg_timings
    }
    
    if game.current_turn >= 0 and game.current_turn < len(game.turns):
        current = game.turns[game.current_turn]
        response["message"] = current["user_message"]
        
        # Only show responses if in voting or result phase
        response["responses"] = []
        if game.status in ["voting", "results"]:
            response["responses"] = [
                {"alias": r["alias"], "reply": r["reply"], "model_name": r["contestant_name"] if game.status == "results" else None} 
                for r in current["responses"]
            ]
        
        # Show votes
        response["human_votes"] = current["human_votes"]
        if game.status == "results":
             response["llm_votes"] = current["llm_votes"]
    
    return response

@app.post("/api/send")
async def send_turn(req: MessageRequest, token: str = Header(None)):
    if token not in game.voters:
        raise HTTPException(status_code=401)
    
    if game.status == "thinking":
        raise HTTPException(status_code=400, detail="Busy thinking")
        
    game.status = "thinking"
    game.current_turn += 1
    
    # Add to history
    game.conversation_history.append({"role": "user", "content": req.message})
    
    responses = []
    settings = get_settings()
    
    # Generate responses
    for contestant in game.contestants:
        t_start = time.perf_counter()
        
        # Override for this specific generation
        os.environ["NVIDIA_API_KEY_PRIMARY"] = settings.FIREWORKS_API_KEY # Use Fireworks key
        os.environ["MODEL_PRIMARY"] = contestant["model"]
        os.environ["MODEL_FALLBACK"] = contestant["model"]
        if "base_url" in contestant:
            os.environ["NVIDIA_BASE_URL"] = contestant["base_url"]
            
        get_settings.cache_clear()
        
        try:
            # Generate
            result = await run_agent(
                session_id=f"bench-{game.session_id}-{game.current_turn}",
                message=req.message,
                messages_history=game.conversation_history[:-1],
                metadata={"channel": "Benchmark", "language": "en"},
                turn_count=game.current_turn + 1
            )
            reply = result.get("agent_reply", "[No Response]")
        except Exception as e:
            reply = f"[Error: {e}]"
            
        duration = (time.perf_counter() - t_start) * 1000
        
        # Track timing
        if contestant["name"] not in game.timings:
            game.timings[contestant["name"]] = []
        game.timings[contestant["name"]].append(duration)
        
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
        "user_message": req.message,
        "responses": responses,
        "human_votes": {}, # {voter_name: alias}
        "llm_votes": {}
    }
    
    # Run LLM Voting in background (or await it)
    # Await it now so it's ready for results
    turn_data["llm_votes"] = await llm_vote_round(turn_data)
    
    game.turns.append(turn_data)
    game.status = "voting"
    
    return {"status": "ok"}

@app.post("/api/vote/human")
async def vote_human(req: VoteRequest):
    if token := req.voter_token:
        if token not in game.voters: raise HTTPException(401)
        name = game.voters[token].nickname
        
        if game.current_turn >= 0:
            turn = game.turns[game.current_turn]
            turn["human_votes"][name] = req.agent_alias
            
    return {"status": "ok"}

@app.post("/api/reveal")
async def reveal_results(token: str = Header(None)):
    # Any voter can trigger reveal
    if token not in game.voters: raise HTTPException(401)
    game.status = "results"
    return {"status": "ok"}

# Mount static files
# Use absolute path to ensure it works when mounted as a sub-app
current_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_path), name="benchmark_static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
