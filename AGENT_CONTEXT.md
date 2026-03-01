# 🤖 Agent Context

> Auto-generated on **2026-03-01 17:06 UTC** by `scripts/update_context.py`.  
> Read this file to instantly understand the project's current state.

## Current Configuration

| Setting | Value |
|---|---|
| Primary Model | `mistralai/mistral-large-3-675b-instruct-2512` |
| Fallback Model | `accounts/fireworks/models/minimax-m2p5` |
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
- **submission**: `https://github.com/rohzhegde26/agentic-honeypot-submission.git`

## Recent Changes

- `4be743a perf: use dedicated fast LLM for scammer agent to fix auto-pilot timeout`
- `6ad0967 feat: overhaul scammer agent with phase-based escalation and anti-repetition`
- `f070024 feat: add context-aware Scammer Agent and Auto-Pilot showcase`
- `9898e37 final: branding update to Team Gate Keepers and pre-submission audit cleanup`
- `3da4674 chore: re-sanitize repository (removed evaluation reports accidentally pulled from remote)`
- `2c244b0 Merge branch 'main' of https://github.com/RohitBharadwaj-rvu/agentic-honeypot`
- `5cffcd7 feat: finalize score improvements and hackathon schema compliance`
- `a95b6d8 chore: final repository sanitization - removed residual logs and temp scripts`
- `68f0ff6 chore: clean up repository for final submission (removed debug scripts and temp logs)`
- `e6f1096 docs: finalize submission documentation with 98.7/100 score and technical deep dives`

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
