"""
LLM Wrapper Module.
NVIDIA API calls using OpenAI SDK with retry logic and fallback handling.
"""
import logging
import time
from typing import List, Dict, Optional

from openai import OpenAI
import httpx
from app.agent.utils.usage import log_token_usage

from app.config import get_settings
from app.core.rules import SAFE_FALLBACK_RESPONSE, SCRIPT_FALLBACK_RESPONSES

logger = logging.getLogger(__name__)

# Track script fallback index for cycling - Randomized start to avoid same starting message
import re
import random
_script_fallback_index = random.randint(0, 100)

# Regex to strip <think>...</think> blocks that some models embed in content
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# Persistent OpenAI client instances for each key
_clients_cache: Dict[str, OpenAI] = {}


def clear_client_cache():
    """Clear the cached OpenAI clients so new config takes effect."""
    _clients_cache.clear()
    logger.info("LLM client cache cleared")


def get_openai_client(api_key: Optional[str] = None, model: Optional[str] = None) -> OpenAI:
    """Get or create a persistent OpenAI client instance.
    Selects Fireworks or NVIDIA backend based on model name."""
    settings = get_settings()
    
    # Determine provider from model name
    is_fireworks = model and "fireworks" in model.lower()
    
    if is_fireworks:
        key = settings.FIREWORKS_API_KEY
        base_url = settings.FIREWORKS_BASE_URL
        # Reduce timeout for primary to 12s so fallback has room within 30s
        timeout = 12.0
    else:
        key = api_key or settings.NVIDIA_API_KEY_PRIMARY or settings.NVIDIA_API_KEY
        base_url = settings.NVIDIA_BASE_URL
        timeout = 25.0
    
    cache_key = f"{base_url}:{key[:8]}" if key else base_url
    
    if cache_key not in _clients_cache:
        _clients_cache[cache_key] = OpenAI(
            base_url=base_url,
            api_key=key or "missing-key", # Pass something to avoid OpenAI validation error if key is None
            timeout=httpx.Timeout(timeout),
        )
    return _clients_cache[cache_key]


# Model configuration - Routing based on settings
def get_model_config():
    settings = get_settings()
    # Default to Kimi as primary and Mistral as fallback as per user request
    return {
        "persona": {
            "primary": settings.MODEL_PRIMARY,
            "fallback": settings.MODEL_FALLBACK,
        },
        "extract": {
            "primary": settings.MODEL_PRIMARY,
            "fallback": settings.MODEL_FALLBACK,
        },
    }


# Retry configuration - set to 1 to handle transient 429s
MAX_RETRIES = 1
BACKOFF_SECONDS = [1, 2]


def _strip_thinking_content(content: str) -> str:
    """Remove <think>...</think> blocks that may leak into the response.
    
    Some Kimi model variants embed chain-of-thought reasoning inside
    <think> tags in the content field instead of (or in addition to)
    the separate reasoning_content field. This strips them out.
    """
    if not content:
        return content
    cleaned = _THINK_TAG_RE.sub("", content).strip()
    return cleaned if cleaned else content  # never return empty


def _call_with_retry(
    client: OpenAI,
    model: str,
    messages: List[Dict],
    task: Optional[str] = None
) -> Optional[str]:
    """
    Call model with retry logic for errors.
    
    Thinking mode (Kimi only, persona task):
      - Enabled via extra_body chat_template_kwargs.
      - Kimi thinking is binary (on/off) — no low/high modes exist.
      - reasoning_content is checked first (separate field).
      - <think>...</think> tags are stripped from content as safety net.
      - max_tokens increased to 800 for Fireworks thinking to budget for overhead.
    """
    extra_body = {}
    is_thinking = False
    # Enable thinking mode for any Fireworks model on persona task IF thinking flag is on
    # (User confirmed all deployed models support this Fireworks feature)
    settings = get_settings()
    is_fireworks = "fireworks" in model.lower() or "accounts/fireworks" in model.lower()
    
    if is_fireworks and task == "persona" and settings.FLAG_THINKING:
        extra_body["chat_template_kwargs"] = {"thinking": True}
        is_thinking = True

    for attempt in range(MAX_RETRIES + 1):
        try:
            # Adjust parameters based on provider
            # Thinking needs a higher budget since reasoning consumes tokens
            if is_fireworks:
                max_tok = 800 if is_thinking else 400
            else:
                max_tok = 100
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6,
                top_p=1.0 if is_fireworks else 0.9,
                max_tokens=max_tok,
                stream=False,
                extra_body=extra_body if extra_body else None
            )
            
            if completion.choices and completion.choices[0].message:
                msg = completion.choices[0].message
                
                # --- Token usage logging ---
                if completion.usage:
                    logger.info(f"LLM Usage ({model}): prompt={completion.usage.prompt_tokens}, completion={completion.usage.completion_tokens}, total={completion.usage.total_tokens}")
                    log_token_usage(model, task, {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    })
                
                # --- Thinking token handling ---
                # 1. Check for reasoning_content field (Kimi/Moonshot API format)
                reasoning = getattr(msg, "reasoning_content", None)
                if reasoning:
                    logger.info(f"THINKING [{model}] reasoning_content: {len(reasoning)} chars")
                
                # 2. Get the main content
                content = msg.content or ""
                
                # 3. Strip any <think>...</think> tags that leaked into content
                if is_thinking and content:
                    stripped = _strip_thinking_content(content)
                    if stripped != content:
                        logger.info(f"THINKING [{model}] Stripped {len(content) - len(stripped)} chars of <think> tags from content")
                        content = stripped
                
                return content if content else None
            
            return None
            
        except Exception as e:
            error_str = str(e).lower()
            
            # If timeout, do NOT retry. Jump to fallback immediately to save time.
            if "timeout" in error_str or "deadline" in error_str:
                logger.warning(f"Timeout on model {model}. Skipping retries.")
                return None

            if "429" in error_str or "rate" in error_str:
                logger.warning(f"Rate limited on model {model}, attempt {attempt + 1}")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_SECONDS[attempt])
                    continue
                return None
            
            if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
                logger.error(f"Authentication error for model {model}: {e}. Skipping retries.")
                return None

            logger.warning(f"Error calling model {model}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            return None
    
    return None


def call_llm(task: str, messages: List[Dict]) -> str:
    """
    Call LLM with task-based model routing and separate keys.
    """
    global _script_fallback_index
    settings = get_settings()
    
    # Get model configuration for task
    config = get_model_config().get(task)
    if not config:
        logger.error(f"Unknown task: {task}")
        return SAFE_FALLBACK_RESPONSE
    
    primary_model = config["primary"]
    fallback_model = config["fallback"]
    
    # Try primary model ONLY if we have a key
    if "fireworks" in primary_model.lower() and not settings.FIREWORKS_API_KEY:
        logger.warning(f"Skipping primary model {primary_model} - missing FIREWORKS_API_KEY")
        result = None
    else:
        client_primary = get_openai_client(settings.NVIDIA_API_KEY_PRIMARY, model=primary_model)
        result = _call_with_retry(client_primary, primary_model, messages, task=task)
    
    if result:
        return result.strip()
    
    # Try fallback model with fallback key
    if fallback_model and fallback_model != primary_model:
        logger.info(f"Switching to fallback model: {fallback_model}")
        client_fallback = get_openai_client(settings.NVIDIA_API_KEY_FALLBACK, model=fallback_model)
        result = _call_with_retry(client_fallback, fallback_model, messages, task=task)
        
        if result:
            return result.strip()
    
    # All attempts failed - use script fallback for persona tasks
    logger.error(f"All LLM attempts failed for task: {task}")
    
    if task == "persona" and SCRIPT_FALLBACK_RESPONSES:
        response = SCRIPT_FALLBACK_RESPONSES[_script_fallback_index % len(SCRIPT_FALLBACK_RESPONSES)]
        _script_fallback_index += 1
        logger.info(f"Using script fallback: {response}")
        return response
    
    return SAFE_FALLBACK_RESPONSE
