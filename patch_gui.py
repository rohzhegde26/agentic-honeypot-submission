import sys
import re

def patch():
    with open('evaluation/runner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Import the UI class
    if "EvaluationProgressWindow" not in content:
        content = content.replace(
            "from evaluation.api_client import HoneypotAPIClient, APIResponse",
            "from evaluation.api_client import HoneypotAPIClient, APIResponse\nfrom evaluation.gui_progress import EvaluationProgressWindow"
        )

    # Revert imports and prints
    content = content.replace('from tqdm import tqdm\n', '')
    content = re.sub(r'\btqdm\.write\(', 'print(', content)

    # Add GUI init inside run()
    gui_init = """        print(f"  Max turns per scenario: {self.config.max_turns}")
        print(f"{'='*60}\\n")

        self.gui = EvaluationProgressWindow(len(self.config.scenarios), self.config.max_turns)
        
        scenario_results = []"""
    
    # Let's find a reliable anchor to insert GUI init
    anchor = """        print(f"{'='*60}\\n")

        scenario_results = []"""
    
    if "self.gui = EvaluationProgressWindow" not in content:
        content = content.replace(
            anchor,
            """        print(f"{'='*60}\\n")\n\n        self.gui = EvaluationProgressWindow(len(self.config.scenarios), self.config.max_turns)\n\n        scenario_results = []"""
        )

    # Revert outer loop
    if "scenario_pbar = tqdm" in content:
        content = re.sub(
            r'        scenario_pbar = tqdm\(.*?\)\n        for i, scenario in enumerate\(scenario_pbar\):\n            scenario_pbar\.set_description\(.*?\)',
            '        for i, scenario in enumerate(self.config.scenarios):\n            if hasattr(self, "gui"): self.gui.update_scenario(i+1, scenario.name)',
            content
        )
    else:
        # Just inject update
        content = re.sub(r'(for i, scenario in enumerate\(self\.config\.scenarios\):)', r'\1\n            if hasattr(self, "gui"): self.gui.update_scenario(i+1, scenario.name)', content)

    # Revert inner loop
    if 'desc="Turns"' in content:
        content = re.sub(
            r'        for turn_num in tqdm\(.*?\):',
            '        for turn_num in range(1, max_turns + 1):\n            if hasattr(self, "gui"): self.gui.update_turn(turn_num, max_turns)',
            content
        )
        
    # Inject GUI close at the end of run
    close_anchor = """        print(f"{'='*60}\\n")

        return eval_result"""
    
    if "self.gui.close()" not in content:
        content = content.replace(
            close_anchor,
            """        print(f"{'='*60}\\n")\n\n        if hasattr(self, "gui"): self.gui.close()\n        return eval_result"""
        )

    with open('evaluation/runner.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched for GUI successfully.")

if __name__ == "__main__":
    patch()
