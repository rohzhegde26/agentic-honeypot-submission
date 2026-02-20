# 🍯 Agentic Honeypot: Evaluation & Developer Guide

This guide describes how to evaluate the system, use the tuning dashboard, and extend the agent's capabilities.

---

## 🏗️ 1. Evaluation & Benchmarking

The system is designed to be evaluated using two primary methods.

### 🏆 Methodology A: The Hackathon Submission Script
This is the definitive verification tool. It starts a local server and runs three high-impact scenarios: Bank Fraud, UPI Fraud, and Phishing.

```bash
python verify_hackathon_submission.py
```
**What to look for:**
- **Final Score**: The script will output a 90/10 split score. Aiming for **98.0+**.
- **Extraction Reports**: See which financial details were mined.
- **Callback Status**: Confirms successful reporting to the GUVI endpoint.

### 📊 Methodology B: Comprehensive Evaluation
For a deeper analysis across 15+ scenarios, use the internal evaluator:

```bash
# Set UTF-8 for Windows consistency
$env:PYTHONUTF8=1; python -m evaluation
```
This generates a detailed report in `evaluation_report/evaluation_report.md`.

---

## 🎮 2. Tuning Dashboard (GUI)

Access the interactive control panel at `http://localhost:8000/gui` while the server is running.

### Key Tuning Parameters:
1. **Thinking Mode**:
   - **ON**: Uses Chain-of-Thought (CoT) reasoning for more realistic, nuanced personas.
   - **OFF**: Faster responses, direct dialogue. Recommended for high-load latency testing.

2. **Prompt Strategies**:
   - **Default**: Balanced stall/hook logic.
   - **Defensive**: Maxes out "technical confusion" to waste scammer time (highest duration).
   - **Aggressive**: Prioritizes leaking fake bait data to extract scammer info faster.

3. **Node Feature Flags**:
   - **LLM Extraction**: Toggle the deep-scanning LLM pass for faster/slower processing.
   - **Guardrails**: Enable NVIDIA NIM security checks for output sanitization.

---

## 🛠️ 3. Developer Guide (Extending Capabilities)

### Adding a New Persona
The system uses pre-defined templates in `app/config.py`. To add a new character:
1. Open `app/config.py`.
2. Add a new dictionary to `PERSONA_TEMPLATES`.
3. Example:
   ```python
   {
       "name": "Devi Prasad",
       "age": 58,
       "background": "Small business owner in Goa",
       "trait": "Impatient and uses many local idioms"
   }
   ```

### Modifying Discovery Rules
The "brain" of the extraction logic lives in `app/core/rules.py`. 
- **Keywords**: Add new scam detection triggers to `CONFIRMED_SCAM_KEYWORDS`.
- **Patterns**: Update regex for new financial instruments in the constants section.

---

## 📁 4. Project Structure
- `app/agent/nodes`: The LangGraph state machine logic.
- `app/agent/utils`: Sanitizers, generators (fake data), and formatting.
- `app/core`: API routes, security, and rule-sets.
- `benchmark/`: Tools for model A/B testing and Arena dashboard.

---
*Maintained by Team Rohith Hegde.*
