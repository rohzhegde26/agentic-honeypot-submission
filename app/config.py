"""
Centralized configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""
from functools import lru_cache
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Upstash Redis
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    
    # OpenRouter API (Alternative LLM)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_REFERER: str = "https://honeypot.local"
    
    # API Security
    API_SECRET_KEY: str = Field(
        ...,
        validation_alias=AliasChoices("API_SECRET_KEY", "API_KEY"),
    )
    
    # NVIDIA API Keys
    NVIDIA_API_KEY_PRIMARY: str = ""
    NVIDIA_API_KEY_FALLBACK: str = ""
    NVIDIA_API_KEY: str = ""  # Legacy key
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    # Fireworks AI
    FIREWORKS_API_KEY: str = ""
    FIREWORKS_BASE_URL: str = "https://api.fireworks.ai/inference/v1"
    
    # Model Configuration - Mistral Large 3 as Primary for stability and speed
    MODEL_PRIMARY: str = "mistralai/mistral-large-3-675b-instruct-2512"
    MODEL_FALLBACK: str = "accounts/fireworks/models/minimax-m2p5"
    
    # Debug Mode
    DEBUG: bool = False
    
    # Feature Flags (toggleable at runtime via /admin/config)
    FLAG_LLM_EXTRACTION: bool = True    # Enable LLM-reinforced extraction (disable to save latency)
    FLAG_STALLING: bool = True           # Enable random stalling behavior in persona
    FLAG_VERBOSE_LOGGING: bool = False   # Enable detailed per-node debug logs
    FLAG_THINKING: bool = True           # Enable thinking mode for Kimi models (disable for faster responses)
    FLAG_GUARDRAIL: bool = False         # Enable Guardrail LLM check (NVIDIA NIM)
    FLAG_ACCELERATED_TESTING: bool = False # Simulate interaction delays to speed up evaluation

    # Prompt Strategy: "default", "aggressive", "defensive"
    PROMPT_STRATEGY: str = "default"
    
    # Guardrail Configuration
    GUARDRAIL_MODEL: str = "ibm/granite-guardian-3.0-8b"
    
    # Session Configuration
    SESSION_TTL_SECONDS: int = 3600  # 1 hour as per requirements
    SESSION_KEY_PREFIX: str = "honeypot:session:"
    
    # LRU Cache Fallback Size
    MEMORY_CACHE_MAX_SIZE: int = 1000
    
    # Persona Configuration
    PERSONA_NAME: str = "Ramesh Kumar"
    PERSONA_AGE: int = 67
    PERSONA_BACKGROUND: str = "retired government employee"
    PERSONA_LOCATION: str = "Pune"
    
    # Predefined Persona Templates
    PERSONA_TEMPLATES: list = [
        {
            "name": "Ramesh Kumar",
            "age": 67,
            "background": "regular savings account holder at SBI",
            "location": "Pune",
            "occupation": "Ex-Government Clerk",
            "trait": "anxious and very polite"
        },
        {
            "name": "Sunita Deshpande",
            "age": 62,
            "background": " housewife with some FD in HDFC",
            "location": "Mumbai",
            "occupation": "Retired Teacher",
            "trait": "gentle but slightly confused about tech"
        },
        {
            "name": "Prof. S. R. Iyer",
            "age": 71,
            "background": "retired physics professor with small investments",
            "location": "Chennai",
            "occupation": "Academician",
            "trait": "meticulous, asks many questions, slightly stubborn"
        },
        {
            "name": "Harprit Singh",
            "age": 65,
            "background": "retired local grocery shop owner",
            "location": "Amritsar",
            "occupation": "Shop Owner",
            "trait": "trusting but cautious about his savings"
        }
    ]
    
    # Callback Configuration (GUVI Evaluation Endpoint)
    CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    CALLBACK_TIMEOUT: int = 5  # seconds per competition spec
    CALLBACK_MAX_RETRIES: int = 3


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
