"""
AGENT_CONTEXT.md Generator.
Generates a machine-readable shared context file for AI coding agents.
Reads project config, recent git history, and key file metadata.

Usage: python scripts/update_context.py
"""
import os
import sys
import subprocess
import re
from datetime import datetime, timezone

# Project root (one level up from scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cmd(cmd: str, cwd: str = PROJECT_ROOT) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return "(unavailable)"


def get_config_values() -> dict:
    """Extract key config values from app/config.py."""
    config_path = os.path.join(PROJECT_ROOT, "app", "config.py")
    values = {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract model names
        m = re.search(r'MODEL_PRIMARY.*?=\s*"([^"]+)"', content)
        values["model_primary"] = m.group(1) if m else "unknown"
        
        m = re.search(r'MODEL_FALLBACK.*?=\s*"([^"]+)"', content)
        values["model_fallback"] = m.group(1) if m else "unknown"
        
        # Extract timeout
        m = re.search(r'AGENT_TIMEOUT.*?=\s*(\d+)', content)
        values["agent_timeout"] = m.group(1) if m else "28"
        
    except FileNotFoundError:
        values = {"model_primary": "unknown", "model_fallback": "unknown", "agent_timeout": "28"}
    
    return values


def get_recent_commits(n: int = 10) -> str:
    """Get last N commits as formatted list."""
    log = run_cmd(f"git log --oneline -n {n}")
    if not log or log == "(unavailable)":
        return "- (no git history available)"
    
    lines = []
    for line in log.split("\n"):
        if line.strip():
            lines.append(f"- `{line.strip()}`")
    return "\n".join(lines)


def get_remotes() -> str:
    """Get git remote URLs (with credentials sanitized)."""
    remotes = run_cmd("git remote -v")
    if not remotes or remotes == "(unavailable)":
        return "- (no remotes configured)"
    
    lines = []
    seen = set()
    for line in remotes.split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            url = parts[1]
            # Sanitize credentials from URLs (e.g., hf_xxx tokens)
            url = re.sub(r'://[^@]+@', '://', url)
            key = f"{parts[0]}:{url}"
            if key not in seen:
                seen.add(key)
                lines.append(f"- **{parts[0]}**: `{url}`")
    return "\n".join(lines)


def get_env_keys() -> str:
    """Check which env keys are set (not values)."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    keys_status = []
    
    important_keys = [
        "API_SECRET_KEY",
        "NVIDIA_API_KEY_PRIMARY",
        "NVIDIA_API_KEY_FALLBACK",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
        "OPENROUTER_API_KEY",
    ]
    
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    val = line.split("=", 1)[1].strip()
                    env_vars[key] = val
    
    for key in important_keys:
        is_set = key in env_vars and env_vars[key] and env_vars[key] not in ('""', "''", "")
        status = "✅ Set" if is_set else "❌ Not set"
        keys_status.append(f"| `{key}` | {status} |")
    
    return "\n".join(keys_status)


def get_persona_count() -> int:
    """Count configured personas in rules.py."""
    rules_path = os.path.join(PROJECT_ROOT, "app", "core", "rules.py")
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content.count('"persona_name"') or content.count("'persona_name'") or 4
    except FileNotFoundError:
        return 4


def preserve_known_issues(existing_content: str) -> str:
    """Preserve the manually-maintained Known Issues section."""
    marker = "## Known Issues / Notes"
    if marker in existing_content:
        idx = existing_content.index(marker)
        return existing_content[idx:]
    return """## Known Issues / Notes

<!-- Manually maintained section — will be preserved across regenerations -->
- None currently documented
"""


def generate_context() -> str:
    """Generate the full AGENT_CONTEXT.md content."""
    config = get_config_values()
    commits = get_recent_commits()
    remotes = get_remotes()
    env_keys = get_env_keys()
    persona_count = get_persona_count()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Try to preserve existing Known Issues section
    existing_path = os.path.join(PROJECT_ROOT, "AGENT_CONTEXT.md")
    existing_content = ""
    if os.path.exists(existing_path):
        with open(existing_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
    
    known_issues = preserve_known_issues(existing_content)
    
    context = f"""# 🤖 Agent Context

> Auto-generated on **{now}** by `scripts/update_context.py`.  
> Read this file to instantly understand the project's current state.

## Current Configuration

| Setting | Value |
|---|---|
| Primary Model | `{config['model_primary']}` |
| Fallback Model | `{config['model_fallback']}` |
| Agent Timeout | `{config['agent_timeout']}s` |
| Persona Count | `{persona_count}` |
| Platform | Hugging Face Spaces (Docker SDK) |

## Environment Keys

| Key | Status |
|---|---|
{env_keys}

## Deployment Targets

{remotes}

## Recent Changes

{commits}

## Key Files Reference

| File | Purpose | Quick Edit |
|---|---|---|
| `app/config.py` | Models, timeouts, persona templates | Lines 35-50 |
| `app/agent/workflow.py` | LangGraph node wiring | Lines 1-50 |
| `app/agent/nodes/persona.py` | Persona prompt + OWASP defenses | Lines 24-42 |
| `app/agent/nodes/detector.py` | Keyword heuristic classification | Lines 32-54 |
| `app/agent/nodes/extractor.py` | Regex + LLM intel extraction | Lines 122-240 |
| `app/agent/nodes/output.py` | Turn counter + termination logic | Lines 51-126 |
| `app/core/routes.py` | API endpoints (webhook, admin) | Lines 69-300 |
| `app/agent/llm.py` | LLM call routing + retry + fallback | Lines 60-165 |
| `app/core/rules.py` | Keywords, regex patterns, prompts | Full file |

## Admin Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/admin/timing` | GET | Recent session timing data |
| `/admin/config` | GET | View current runtime config |
| `/admin/config` | POST | Hot-swap model config (requires API key) |
| `/health/diag` | GET | Environment diagnostic |

{known_issues}"""
    
    return context


def main():
    """Generate and write AGENT_CONTEXT.md."""
    content = generate_context()
    output_path = os.path.join(PROJECT_ROOT, "AGENT_CONTEXT.md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ AGENT_CONTEXT.md updated ({len(content)} bytes)")


if __name__ == "__main__":
    main()
