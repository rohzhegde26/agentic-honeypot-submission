# 🤖 Agent Context

> Auto-generated on **2026-02-13 07:28 UTC** by `scripts/update_context.py`.  
> Read this file to instantly understand the project's current state.

## Current Configuration

| Setting | Value |
|---|---|
| Primary Model | `mistralai/mistral-large-3-675b-instruct-2512` |
| Fallback Model | `moonshotai/kimi-k2.5` |
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
| `NVIDIA_API_KEY_FALLBACK` | ❌ Not set |
| `UPSTASH_REDIS_REST_URL` | ✅ Set |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ Set |
| `OPENROUTER_API_KEY` | ❌ Not set |

## Deployment Targets

- **hf**: `https://huggingface.co/spaces/GateKeepers1/agentic-honeypot`
- **origin**: `https://github.com/RohitBharadwaj-rvu/agentic-honeypot.git`

## Recent Changes

- `6e1ebcb feat: add feature flags, prompt strategy variants, response time dashboard`
- `2a935fa feat: add competition readiness features - session timing, hot-swap config, deploy script, agent context`
- `57bc4e3 docs: ensure authors are correct and LLM tech stack reflects project reality`
- `039679f docs: update authors and fix clone URL in README.md`
- `9939392 docs: update authors to Rohit P Hegde, Rohit Bharadwaj & S Sachitanandan; remove team name`
- `623e366 Remove promotional message from README`
- `e054c6e Update README to remove metadata`
- `0941fdb docs: rewrite README â€” production-ready with architecture, credits, benchmarks, and API reference`
- `219b2b2 fix: enforce language consistency and expand fallback variety`
- `ee4393e fix: resolve fallback stalling loop with resilience improvements and diversified responses`

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
