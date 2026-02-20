import sys
import re

def update_runner():
    with open('evaluation/runner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    if "from tqdm import tqdm" not in content:
        content = content.replace(
            'from dataclasses import dataclass, field',
            'from dataclasses import dataclass, field\nfrom tqdm import tqdm'
        )

    # Convert print to tqdm.write
    content = re.sub(r'\bprint\(', 'tqdm.write(', content)

    # Outer loop progress
    if "scenario_pbar = tqdm" not in content:
        content = content.replace(
            'for i, scenario in enumerate(self.config.scenarios):',
            'scenario_pbar = tqdm(self.config.scenarios, desc="Scenarios", position=0, leave=True)\n        for i, scenario in enumerate(scenario_pbar):\n            scenario_pbar.set_description(f"Scenario {i+1}/{len(self.config.scenarios)}")'
        )

    # Inner loop progress
    if 'desc="Turns"' not in content:
        content = content.replace(
            'for turn_num in range(1, max_turns + 1):',
            'for turn_num in tqdm(range(1, max_turns + 1), desc="Turns", position=1, leave=False):'
        )

    with open('evaluation/runner.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated runner.py successfully.")

if __name__ == "__main__":
    update_runner()
