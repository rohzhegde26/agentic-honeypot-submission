# 🍯 Agentic Honeypot: Tuning & Developer Guide

This guide is divided into two parts:
1.  **User Guide:** How to use the dashboard to tune the agent.
2.  **Developer Guide:** How to modify the code to add *new* capabilities, flags, and strategies.

---

# Part 1: User Guide (Dashboard)

Access the control panel at `http://localhost:8000/`.

## 🧠 Thinking Mode (New!)
**What it does:**  
Contols whether the AI "thinks" before speaking.
- **ON (Default):** Uses Chain-of-Thought (CoT) reasoning. Result: **More realistic, in-character responses.**
- **OFF:** Direct response. Result: **Faster speed, but less nuance.**

> **Tip:** Keep ON for the best "confused old person" simulation.

## 🤖 Model Hot-Swapping
Switch AI models instantly to balance cost vs. intelligence.

| Tier | Best Model | Use Case |
|---|---|---|
| **Top Tier** | **Kimi K2.5** | **Best Overall.** High reasoning, perfect persona. |
| **Value** | **MiniMax M2.1** | **Best Value.** Fast, cheap, capable enough. |
| **Reasoning** | **Kimi K2 Thinking**| **Deep Logic.** Slow but thorough. |

## 🎯 Prompt Strategies
Change the agent's engagement style:

- **Default:** Balanced. 20% stall chance. Honest engagement.
- **Aggressive:** fast leaks. 5% stall chance. Gives scammers what they want (fake data).
- **Defensive:** Wastes time. 40% stall chance. Asks verification questions.

---

# Part 2: Developer Guide (Extending the Honeypot)

Want to add a "Super Aggressive" mode or a "Simulate Network Lag" flag? Here is how to extend the system.

## 🛠️ How to Add a New Feature Flag

Example: Adding a `FLAG_NETWORK_LAG` to simulate slow typing.

### Step 1: Define it in `app/config.py`
Add the boolean field to the `Settings` class.

```python
class Settings(BaseSettings):
    # ... existing flags ...
    FLAG_THINKING: bool = True
    FLAG_NETWORK_LAG: bool = False  # <--- NEW
```

### Step 2: Expose it in `app/core/routes.py`
Update the API to allow changing it at runtime.

1.  Add to `ConfigUpdate` class:
    ```python
    class ConfigUpdate(BaseModel):
        flag_network_lag: Optional[bool] = None  # <--- NEW
    ```
2.  Update `admin_config_update` function:
    ```python
    if update.flag_network_lag is not None:
        settings.FLAG_NETWORK_LAG = update.flag_network_lag
        changes["FLAG_NETWORK_LAG"] = update.flag_network_lag
    ```
3.  Update `admin_config_view` function:
    ```python
    return {
        # ...
        "FLAG_NETWORK_LAG": settings.FLAG_NETWORK_LAG,
    }
    ```

### Step 3: Add to Dashboard (`app/core/gui.py`)
Add the toggle switch to the HTML.

1.  Add HTML in `flagsSection`:
    ```html
    <div class="toggle-row">
      <span class="toggle-label">Simulate Lag</span>
      <label class="toggle"><input type="checkbox" id="flagLag" onchange="updateConfig()"><span class="toggle-slider"></span></label>
    </div>
    ```
2.  Update `loadConfigState` JS function:
    ```javascript
    document.getElementById('flagLag').checked = cfg.FLAG_NETWORK_LAG;
    ```
3.  Update `updateConfig` JS function:
    ```javascript
    flag_network_lag: document.getElementById('flagLag').checked,
    ```

### Step 4: Implement Logic
Use the flag in your code (e.g., `app/agent/nodes/output.py`).

```python
from app.config import get_settings

if get_settings().FLAG_NETWORK_LAG:
    time.sleep(2)  # Simulate lag
```

---

## 🎭 How to Add a New Prompt Strategy

Example: Adding a **"Paranoid"** strategy that refuses to share anything.

### Step 1: Define Options in `app/config.py`
Update the comment (optional) but ensure `PROMPT_STRATEGY` field accepts string.

### Step 2: Define Logic in `app/agent/nodes/persona.py`
This is where the magic happens. Scroll to `STRATEGY_MAP`.

1.  **Define the Instructions:**
    ```python
    PARANOID_HOOK = "You are extremely suspicious. Accuse them of being a scammer immediately."
    PARANOID_LEAK = "Do NOT share any details. Threaten to call the police."
    ```

2.  **Add to Map:**
    ```python
    STRATEGY_MAP = {
        "default": { ... },
        "paranoid": {  # <--- NEW
            "hook": PARANOID_HOOK,
            "stall": STALL_INSTRUCTION,
            "leak": PARANOID_LEAK,
            "stall_chance": 80  # Stalls 80% of the time!
        }
    }
    ```

### Step 3: Update API Validation (`app/core/routes.py`)
Allow the new string in the API.

```python
if update.prompt_strategy in ("default", "aggressive", "defensive", "paranoid"): # <--- ADD HERE
    settings.PROMPT_STRATEGY = update.prompt_strategy
```

### Step 4: Update Dashboard (`app/core/gui.py`)
Add a radio button.

```html
<label class="strategy-option">
  <input type="radio" name="strategy" value="paranoid" onchange="updateConfig()">
  Paranoid <span class="strategy-badge" style="background:#ff000033;color:red">Blocker</span>
</label>
```

---

## 📁 How to Add New Personas

Add new targets in `app/config.py` under the `PERSONA_TEMPLATES` list.

```python
{
    "name": "Sarah Connor",
    "age": 29,
    "background": "Waitress",
    "location": "Los Angeles",
    "occupation": "Survivalist",
    "trait": "tough and distrusting of machines"
}
```

Restart the app to see them in the logs/logic (if you wire them up to the randomizer).
