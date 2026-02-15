from app.config import get_settings
import os

# Mock env vars if needed to avoid validation errors, but get_settings should handle it
try:
    settings = get_settings()
    print(f"KEY:{settings.API_SECRET_KEY}")
    print(f"FIREWORKS:{settings.FIREWORKS_API_KEY}")
except Exception as e:
    print(f"Error: {e}")
