# 🤖 Agent Context

> Auto-generated on **2026-02-13 07:23 UTC** by `scripts/update_context.py`.  
> Read this file to instantly understand the project's current state.

## Current Configuration

| Setting | Value |
|---|---|
| Primary Model | `mistralai/mistral-large-3-675b-instruct-2512` |
| Fallback Model | `moonshotai/kimi-k2.5` |
| Agent Timeout | `28s` |
| Persona Count | `4` |
| Platform | Hugging Face Spaces (Docker SDK) |

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

- `2a935fa feat: add competition readiness features - session timing, hot-swap config, deploy script, agent context`
- `57bc4e3 docs: ensure authors are correct and LLM tech stack reflects project reality`
- `039679f docs: update authors and fix clone URL in README.md`
- `9939392 docs: update authors to Rohit P Hegde, Rohit Bharadwaj & S Sachitanandan; remove team name`
- `623e366 Remove promotional message from README`
- `e054c6e Update README to remove metadata`
- `0941fdb docs: rewrite README â€” production-ready with architecture, credits, benchmarks, and API reference`
- `219b2b2 fix: enforce language consistency and expand fallback variety`
- `ee4393e fix: resolve fallback stalling loop with resilience improvements and diversified responses`
- `630b83f feat: improve agent flow with randomized stalling and reinforced text-based communication`

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

## Known Issues / Notes

<!-- Manually maintained section — will be preserved across regenerations -->
- None currently documented
