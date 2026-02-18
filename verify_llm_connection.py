
import os
import sys
from openai import OpenAI
from app.config import get_settings

def test_llm_connection():
    try:
        settings = get_settings()
        
        # Determine provider from model name
        is_fireworks = "fireworks" in settings.MODEL_PRIMARY.lower()
        
        if is_fireworks:
            api_key = settings.FIREWORKS_API_KEY
            base_url = settings.FIREWORKS_BASE_URL
        else:
            api_key = settings.NVIDIA_API_KEY_PRIMARY or settings.NVIDIA_API_KEY
            base_url = settings.NVIDIA_BASE_URL
        
        print(f"Checking configuration...")
        print(f"API Key present: {'Yes' if api_key else 'No'}")
        print(f"Base URL: {base_url}")
        print(f"Model: {settings.MODEL_PRIMARY}")
        
        if not api_key:
            print(f"❌ ERROR: API key is missing for {'Fireworks' if is_fireworks else 'NVIDIA'}.")
            return

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        print("\nSending test request to LLM...")
        completion = client.chat.completions.create(
            model=settings.MODEL_PRIMARY,
            messages=[{"role": "user", "content": "Say 'Connection successful' if you can hear me."}],
            max_tokens=20,
        )

        response = completion.choices[0].message.content
        print(f"[SUCCESS] Response: {response}")


    except Exception as e:
        print(f"[FAILED] CONNECT ERROR: {e}")

if __name__ == "__main__":
    test_llm_connection()
