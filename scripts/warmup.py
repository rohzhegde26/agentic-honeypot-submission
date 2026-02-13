"""
Warmup Script.
Fires test messages at the local server to warm up LLM connections.
Run after deploy to avoid cold-start latency on first evaluation hit.

Usage: python scripts/warmup.py [--url http://localhost:7860]
"""
import argparse
import time
import json

try:
    import httpx
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


def warmup(base_url: str, api_key: str):
    """Send 2 test messages to warm up the LLM pipeline."""
    endpoint = f"{base_url}/webhook"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
    }
    
    test_messages = [
        {
            "sessionId": "warmup-001",
            "message": {
                "sender": "test",
                "text": "Hello, is this the bank?",
                "timestamp": "2025-01-01T00:00:00Z",
            },
        },
        {
            "sessionId": "warmup-002",
            "message": {
                "sender": "test",
                "text": "Sir your KYC is expired, please verify immediately",
                "timestamp": "2025-01-01T00:00:01Z",
            },
        },
    ]
    
    client = httpx.Client(timeout=30.0)
    
    for i, msg in enumerate(test_messages, 1):
        print(f"  [{i}/{len(test_messages)}] Sending: {msg['message']['text'][:50]}...")
        t0 = time.perf_counter()
        
        try:
            resp = client.post(endpoint, json=msg, headers=headers)
            elapsed = round((time.perf_counter() - t0) * 1000)
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("reply", "")[:60]
                print(f"    OK ({elapsed}ms) → {reply}")
            else:
                print(f"    HTTP {resp.status_code} ({elapsed}ms)")
        except Exception as e:
            elapsed = round((time.perf_counter() - t0) * 1000)
            print(f"    ERROR ({elapsed}ms): {e}")
    
    client.close()
    print("  Warmup complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Warm up the honeypot server")
    parser.add_argument("--url", default="http://localhost:7860", help="Base URL of the server")
    parser.add_argument("--key", default="test-key", help="API key for authentication")
    args = parser.parse_args()
    
    print(f"\n=== WARMUP: {args.url} ===")
    warmup(args.url, args.key)
