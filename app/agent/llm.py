"""
LLM Wrapper Module.
NVIDIA API calls using OpenAI SDK with retry logic and fallback handling.
Fully asynchronous to prevent event loop blocking under heavy load.
"""
import logging
import asyncio
import time
import re
import random
from typing import List, Dict, Optional, Any

from openai import AsyncOpenAI
import httpx
from app.agent.utils.usage import log_token_usage

from app.config import get_settings
from app.core.rules import SAFE_FALLBACK_RESPONSE, SCRIPT_FALLBACK_RESPONSES

logger = logging.getLogger(__name__)

# Track script fallback index for cycling - Randomized start to avoid same starting message
_script_fallback_index = random.randint(0, 100)

# Regex to strip <think>...</think> blocks that some models embed in content
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# Persistent AsyncOpenAI client instances for each key
_clients_cache: Dict[str, AsyncOpenAI] = {}


def clear_client_cache():
    """Clear the cached OpenAI clients so new config takes effect."""
    _clients_cache.clear()
    logger.info("LLM client cache cleared")


def get_openai_client(api_key: Optional[str] = None, model: Optional[str] = None) -> AsyncOpenAI:
    """Get or create a persistent AsyncOpenAI client instance."""
    settings = get_settings()
    
    # Determine provider from model name
    is_fireworks = model and "fireworks" in model.lower()
    
    if is_fireworks:
        key = settings.FIREWORKS_API_KEY
        base_url = settings.FIREWORKS_BASE_URL
        timeout = 15.0
    else:
        key = api_key or settings.NVIDIA_API_KEY_PRIMARY or settings.NVIDIA_API_KEY
        base_url = settings.NVIDIA_BASE_URL
        timeout = 25.0
    
    cache_key = f"{base_url}:{key[:8]}" if key else base_url
    
    if cache_key not in _clients_cache:
        _clients_cache[cache_key] = AsyncOpenAI(
            base_url=base_url,
            api_key=key or "missing-key",
            timeout=httpx.Timeout(timeout),
        )
    return _clients_cache[cache_key]


def get_model_config():
    settings = get_settings()
    # Stable Deployment: 
    # Use Mistral 3 via NVIDIA for all tasks to ensure authentication stability.
    return {
        "persona": {
            "primary": "mistralai/mistral-large-3-675b-instruct-2512",
            "fallback": "mistralai/mistral-large-3-675b-instruct-2512",
        },
        "extract": {
            "primary": "mistralai/mistral-large-3-675b-instruct-2512",
            "fallback": "mistralai/mistral-large-3-675b-instruct-2512",
        },
        "reflection": {
            "primary": "mistralai/mistral-large-3-675b-instruct-2512",
            "fallback": "mistralai/mistral-large-3-675b-instruct-2512",
        },
        "scammer": {
            "primary": "mistralai/mistral-large-3-675b-instruct-2512",
            "fallback": "mistralai/mistral-large-3-675b-instruct-2512",
        },
    }


MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


def _strip_thinking_content(content: str) -> str:
    """Remove <think>...</think> blocks."""
    if not content:
        return content
    cleaned = _THINK_TAG_RE.sub("", content).strip()
    return cleaned if cleaned else content


async def _call_with_retry(
    client: AsyncOpenAI,
    model: str,
    messages: List[Dict],
    task: Optional[str] = None
) -> Optional[str]:
    """Call model asynchronously with retry logic."""
    settings = get_settings()
    is_fireworks = "fireworks" in model.lower() or "accounts/fireworks" in model.lower()
    
    # FORCE DISABLE: Kimi K2.5 on Fireworks rejects 'chat_template_kwargs'.
    # Forcing extra_body to None for all Fireworks tasks to ensure 100% stability.
    if is_fireworks:
        extra_body = None
        is_thinking = False
    else:
        extra_body = {}
        is_thinking = False

    for attempt in range(MAX_RETRIES + 1):
        try:
            if is_fireworks:
                max_tok = 800 if is_thinking else 400
            else:
                max_tok = 400
            
            res_format = None
            if is_fireworks and (task == "extract" or task == "reflection"):
                res_format = {"type": "json_object"}

            if extra_body:
                logger.debug(f"DEBUG: Calling {model} for task {task} with extra_body={extra_body}")
            
            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0 if (task == "extract" or task == "reflection") else 0.6,
                top_p=1.0 if is_fireworks else 0.9,
                max_tokens=max_tok,
                stream=False,
                extra_body=extra_body if extra_body else None,
                response_format=res_format
            )
            
            if completion.choices and completion.choices[0].message:
                msg = completion.choices[0].message
                
                if completion.usage:
                    log_token_usage(model, task, {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    })
                
                content = msg.content or ""
                if is_thinking and content:
                    content = _strip_thinking_content(content)
                
                return content if content else None
            
            return None
            
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "deadline" in error_str:
                logger.warning(f"Timeout on model {model}.")
                return None

            if "429" in error_str or "rate" in error_str:
                logger.warning(f"Rate limited on model {model}, attempt {attempt + 1}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_SECONDS[attempt])
                    continue
                return None
            
            logger.warning(f"Error calling model {model}: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_SECONDS[attempt])
                continue
            return None
    
    return None


async def call_llm(task: str, messages: List[Dict]) -> str:
    """Async entry point for LLM calls with routing."""
    global _script_fallback_index
    settings = get_settings()
    
    config = get_model_config().get(task)
    if not config:
        return SAFE_FALLBACK_RESPONSE
    
    primary_model = config["primary"]
    fallback_model = config["fallback"]
    
    # Attempt 1: Primary
    t0 = time.perf_counter()
    result = None
    if not ("fireworks" in primary_model.lower() and not settings.FIREWORKS_API_KEY):
        client_primary = get_openai_client(settings.NVIDIA_API_KEY_PRIMARY, model=primary_model)
        result = await _call_with_retry(client_primary, primary_model, messages, task=task)
    
    if result:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(f"LLM SUCCESS: task={task} model={primary_model} dur={ms}ms")
        return result.strip()
    
    # Attempt 2: Fallback
    if fallback_model and fallback_model != primary_model:
        t1 = time.perf_counter()
        logger.info(f"LLM FALLBACK: Switching to {fallback_model} for {task}")
        client_fallback = get_openai_client(settings.NVIDIA_API_KEY_FALLBACK, model=fallback_model)
        result = await _call_with_retry(client_fallback, fallback_model, messages, task=task)
        
        if result:
            ms = round((time.perf_counter() - t1) * 1000, 1)
            logger.info(f"LLM SUCCESS (Fallback): model={fallback_model} dur={ms}ms")
            return result.strip()
    
    # Final Fallback: Scripted
    if task == "persona" and SCRIPT_FALLBACK_RESPONSES:
        logger.warning(f"LLM FAILURE: task={task} - Triggering scripted fallback")
        last_msg = messages[-1]["content"].lower() if messages else ""
        if "you" in last_msg and ("are" in last_msg or "who" in last_msg):
            response = "I am a retired person sir, who is this calling me?"
        elif "bot" in last_msg or "ai" in last_msg or "machine" in last_msg:
            response = "I am not understanding what you are saying... I am Ramesh. Why are you talking like this?"
        else:
            response = SCRIPT_FALLBACK_RESPONSES[_script_fallback_index % len(SCRIPT_FALLBACK_RESPONSES)]
            _script_fallback_index += 1
            
        logger.info(f"LLM SCRIPT FALLBACK: task={task} response='{response[:20]}...'")
        return response
    
    logger.error(f"LLM CRITICAL FAILURE: task={task} - No fallback available, using SAFE_FALLBACK_RESPONSE")
    return SAFE_FALLBACK_RESPONSE


async def check_guardrail(text: str) -> Dict[str, Any]:
    """Check input text against Guardrail LLM (Async)."""
    settings = get_settings()
    if not settings.FLAG_GUARDRAIL:
        return {"safe": True, "risk": "disabled", "latency": 0.0}
    
    t_start = time.perf_counter()
    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=settings.NVIDIA_API_KEY_PRIMARY
    ) if settings.NVIDIA_API_KEY_PRIMARY else None
    
    if not client:
        return {"safe": True, "risk": "missing_key", "latency": 0.0}

    try:
        response = await client.chat.completions.create(
            model=settings.GUARDRAIL_MODEL,
            messages=[{"role": "user", "content": text}],
            extra_body={"guardian_config": {"risk_name": "jailbreak"}},
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip().lower()
        is_safe = "no" in content
        elapsed = round((time.perf_counter() - t_start) * 1000, 1)
        return {"safe": is_safe, "risk": content if not is_safe else "none", "latency": elapsed}
    except Exception as e:
        logger.error(f"Guardrail check failed: {e}")
        return {"safe": True, "risk": "error_bypass", "latency": 0.0}
