# 🤖 Agent Context

> Auto-generated on **2026-02-15 12:00 UTC** by `scripts/update_context.py`.  
> Read this file to instantly understand the project's current state.

## Current Configuration

| Setting | Value |
|---|---|
| Primary Model | `accounts/fireworks/models/kimi-k2p5` |
| Fallback Model | `mistralai/mistral-large-3-675b-instruct-2512` |
| Agent Timeout | `28s` |
| Persona Count | `4` |
| Prompt Strategy | `default` |
| Platform | Hugging Face Spaces (Docker SDK) |

## Feature Flags

| Flag | Default | Purpose |
|---|---|---|
| `FLAG_LLM_EXTRACTION` | `True` | Gate LLM call in extractor (disable to save 2-5s) |
| `FLAG_STALLING` | `True` | Gate random stalling in persona node |
| `FLAG_VERBOSE_LOGGING` | `False` | Enable detailed per-node debug logs |

## Prompt Strategies

| Strategy | Hook Style | Stall % | Leak Style |
|---|---|---|---|
| `default` | Curious, polite | 20% | Ask for their details first |
| `aggressive` | Worried, urgent | 5% | Share fake data proactively |
| `defensive` | Suspicious, cautious | 40% | 2+ verification questions |

## Environment Keys

| Key | Status |
|---|---|
| `API_SECRET_KEY` | ✅ Set |
| `NVIDIA_API_KEY_PRIMARY` | ✅ Set |
| `NVIDIA_API_KEY_FALLBACK` | ✅ Set |
| `UPSTASH_REDIS_REST_URL` | ✅ Set |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ Set |
| `OPENROUTER_API_KEY` | ❌ Not set |

## Deployment Targets

- **origin**: `https://github.com/RohitBharadwaj-rvu/agentic-honeypot.git`
- **space**: `https://huggingface.co/spaces/rohithhegde26/agentic-honeypot`

## Recent Changes

- `85d690a feat: expanded scam rules and tactical reporting for live finals`
- `5a21211 fix: environment pollution and context-aware persona rejections`
- `a0731c6 fix: add missing os import in persona_node`
- `df6b38a fix: bypass semantic cache in benchmark to prevent duplicate replies`
- `ae4417b fix: benchmark coordination and session id visibility`
- `b425b50 feat: enable 3-person multi-user benchmark and fix CI failure`
- `ae3d80b fix: robust api key validation and forced deployment update`
- `1a6edd7 fix: remove legacy benchmark routes and fix sub-app asset paths`
- `6e6036d feat: integrate benchmark arena and results viewer into main GUI`
- `83c4166 feat: finalize benchmark solo mode and add deep research bundle`

## Key Files Reference

| File | Purpose | Quick Edit |
|---|---|---|
| `app/config.py` | Models, timeouts, flags, persona templates | Lines 35-60 |
| `app/agent/workflow.py` | LangGraph node wiring | Lines 1-50 |
| `app/agent/nodes/persona.py` | Persona prompt + strategies + OWASP | Lines 24-65 |
| `app/agent/nodes/detector.py` | Keyword heuristic classification | Lines 32-54 |
| `app/agent/nodes/extractor.py` | Regex + LLM intel extraction | Lines 122-260 |
| `app/agent/nodes/output.py` | Turn counter + termination logic | Lines 51-126 |
| `app/core/routes.py` | API endpoints (webhook, admin, dashboard) | Lines 69-420 |
| `app/agent/llm.py` | LLM call routing + retry + fallback | Lines 60-165 |
| `app/core/rules.py` | Keywords, regex patterns, prompts | Full file |

## Admin Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/admin/timing` | GET | Recent session timing data |
| `/admin/config` | GET | View current runtime config + flags |
| `/admin/config` | POST | Hot-swap models, flags, strategy (requires API key) |
| `/admin/dashboard` | GET | Live performance dashboard (HTML) |
| `/health/diag` | GET | Environment diagnostic |

## Known Issues / Notes

<!-- Manually maintained section — will be preserved across regenerations -->
- None currently documented
