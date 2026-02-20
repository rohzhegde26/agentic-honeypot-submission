import tkinter as tk
from tkinter import ttk
import threading
import sys

class EvaluationProgressWindow:
    def __init__(self, total_scenarios, total_turns):
        self.total_scenarios = total_scenarios
        self.total_turns = total_turns
        self.root = None
        
        if sys.platform != "win32":
            return
            
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()
        
    def _run_gui(self):
        self.root = tk.Tk()
        self.root.title("Evaluation Progress")
        self.root.geometry("450x180")
        self.root.attributes('-topmost', True)
        
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
            
        ttk.Label(self.root, text="Scenario Progress", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
        self.scenario_var = tk.DoubleVar()
        self.scenario_pb = ttk.Progressbar(self.root, variable=self.scenario_var, maximum=self.total_scenarios)
        self.scenario_pb.pack(fill=tk.X, padx=20, pady=5)
        self.scenario_lbl = ttk.Label(self.root, text=f"0 / {self.total_scenarios}")
        self.scenario_lbl.pack()
        
        ttk.Label(self.root, text="Turn Progress", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
        self.turn_var = tk.DoubleVar()
        self.turn_pb = ttk.Progressbar(self.root, variable=self.turn_var, maximum=self.total_turns)
        self.turn_pb.pack(fill=tk.X, padx=20, pady=5)
        self.turn_lbl = ttk.Label(self.root, text=f"0 / {self.total_turns}")
        self.turn_lbl.pack()
        
        self.root.mainloop()

    def update_scenario(self, current, name):
        if self.root:
            try:
                self.root.after(0, self._update_s, current, name)
            except Exception:
                pass

    def _update_s(self, current, name):
        if hasattr(self, 'scenario_var'):
            self.scenario_var.set(current)
            self.scenario_lbl.config(text=f"{current} / {self.total_scenarios} - {name}")

    def update_turn(self, current, maximum):
        if self.root:
            try:
                self.root.after(0, self._update_t, current, maximum)
            except Exception:
                pass

    def _update_t(self, current, maximum):
        if hasattr(self, 'turn_var'):
            self.turn_pb.config(maximum=maximum)
            self.turn_var.set(current)
            self.turn_lbl.config(text=f"{current} / {maximum}")

    def close(self):
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
        self.root = None
