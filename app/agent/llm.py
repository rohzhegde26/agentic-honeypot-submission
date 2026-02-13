"""
LLM Wrapper Module.
NVIDIA API calls using OpenAI SDK with retry logic and fallback handling.
"""
import logging
import time
from typing import List, Dict, Optional

from openai import OpenAI
import httpx

from app.config import get_settings
from app.core.rules import SAFE_FALLBACK_RESPONSE, SCRIPT_FALLBACK_RESPONSES

logger = logging.getLogger(__name__)

# Track script fallback index for cycling - Randomized start to avoid same starting message
import random
_script_fallback_index = random.randint(0, 100)

# Persistent OpenAI client instances for each key
_clients_cache: Dict[str, OpenAI] = {}


def clear_client_cache():
    """Clear the cached OpenAI clients so new config takes effect."""
    _clients_cache.clear()
    logger.info("LLM client cache cleared")


def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """Get or create a persistent OpenAI client instance for a specific key."""
    settings = get_settings()
    key = api_key or settings.NVIDIA_API_KEY_PRIMARY or settings.NVIDIA_API_KEY
    
    if key not in _clients_cache:
        _clients_cache[key] = OpenAI(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=key,
            timeout=httpx.Timeout(25.0),  # Stay under 30s HuggingFace Spaces timeout
        )
    return _clients_cache[key]


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


def _call_with_retry(
    client: OpenAI,
    model: str,
    messages: List[Dict],
    task: Optional[str] = None
) -> Optional[str]:
    """
    Call model with retry logic for errors.
    Supports thinking mode for Kimi models if the task is 'persona'.
    """
    extra_body = {}
    # Disabled thinking mode for all tasks to stay under 30s platform timeout
    # if "kimi" in model.lower() and task == "persona":
    #     extra_body["chat_template_kwargs"] = {"thinking": True}

    for attempt in range(MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.6 if "kimi" not in model.lower() else 1.0, # Kimi often likes high temp
                top_p=0.9 if "kimi" not in model.lower() else 1.0,
                max_tokens=100,  # SMS replies should be very short - faster generation
                stream=False,
                extra_body=extra_body if extra_body else None
            )
            
            if completion.choices and completion.choices[0].message:
                return completion.choices[0].message.content
            
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
    
    # Try primary model with primary key
    client_primary = get_openai_client(settings.NVIDIA_API_KEY_PRIMARY)
    result = _call_with_retry(client_primary, primary_model, messages, task=task)
    
    if result:
        return result.strip()
    
    # Try fallback model with fallback key
    if fallback_model and fallback_model != primary_model:
        logger.info(f"Switching to fallback model: {fallback_model}")
        client_fallback = get_openai_client(settings.NVIDIA_API_KEY_FALLBACK)
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
