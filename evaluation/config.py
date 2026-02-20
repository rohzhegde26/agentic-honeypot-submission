"""
Evaluation configuration and scenario loading.
Pure black-box config — no internal project knowledge.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class FakeData:
    """Planted intelligence data that the scammer will 'leak' during conversation."""
    phoneNumbers: List[str] = field(default_factory=list)
    bankAccounts: List[str] = field(default_factory=list)
    upiIds: List[str] = field(default_factory=list)
    phishingLinks: List[str] = field(default_factory=list)
    emailAddresses: List[str] = field(default_factory=list)
    caseIds: List[str] = field(default_factory=list)
    policyNumbers: List[str] = field(default_factory=list)
    orderNumbers: List[str] = field(default_factory=list)

    def total_fields(self) -> int:
        """Count total number of planted data items."""
        count = 0
        for fld in [
            self.phoneNumbers, self.bankAccounts, self.upiIds,
            self.phishingLinks, self.emailAddresses, self.caseIds,
            self.policyNumbers, self.orderNumbers,
        ]:
            count += len(fld)
        return count

    def as_dict(self) -> Dict[str, List[str]]:
        """Return non-empty fields as a dictionary."""
        result = {}
        for name in [
            "phoneNumbers", "bankAccounts", "upiIds", "phishingLinks",
            "emailAddresses", "caseIds", "policyNumbers", "orderNumbers",
        ]:
            vals = getattr(self, name)
            if vals:
                result[name] = vals
        return result


@dataclass
class ScenarioConfig:
    """A single test scenario configuration."""
    name: str
    scam_type: str
    weight: float  # percentage, e.g. 35 for 35%
    initial_message: str
    fake_data: FakeData
    max_turns: int = 10
    metadata: Dict[str, str] = field(default_factory=lambda: {
        "channel": "SMS",
        "language": "English",
        "locale": "IN",
    })
    # Scammer persona instructions for the LLM simulator
    scammer_persona: str = ""


@dataclass
class EvalConfig:
    """Top-level evaluation configuration."""
    target_url: str = "http://localhost:8000/webhook"
    api_key: str = ""
    max_turns: int = 10
    timeout_seconds: int = 30
    output_dir: str = "evaluation_report"
    scenarios: List[ScenarioConfig] = field(default_factory=list)
    use_llm_scammer: bool = True
    # Delay between turns (seconds) to simulate realistic timing
    turn_delay: float = 1.0
    accelerated: bool = False
    concurrency: int = 1


def load_scenario_from_dict(data: Dict[str, Any]) -> ScenarioConfig:
    """Load a single scenario from a dictionary."""
    fake = FakeData(**data.get("fake_data", {}))
    return ScenarioConfig(
        name=data["name"],
        scam_type=data["scam_type"],
        weight=data["weight"],
        initial_message=data["initial_message"],
        fake_data=fake,
        max_turns=data.get("max_turns", 10),
        metadata=data.get("metadata", {"channel": "SMS", "language": "English", "locale": "IN"}),
        scammer_persona=data.get("scammer_persona", ""),
    )


def load_scenarios(path: str) -> List[ScenarioConfig]:
    """
    Load scenario configurations from a directory of JSON files
    or a single JSON file.
    """
    scenarios = []

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                scenarios.append(load_scenario_from_dict(item))
        else:
            scenarios.append(load_scenario_from_dict(data))
    elif os.path.isdir(path):
        for filename in sorted(os.listdir(path)):
            if filename.endswith(".json"):
                filepath = os.path.join(path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                scenarios.append(load_scenario_from_dict(data))
    else:
        raise FileNotFoundError(f"Scenario path not found: {path}")

    # Validate weights sum to ~100
    total_weight = sum(s.weight for s in scenarios)
    if abs(total_weight - 100.0) > 1.0:
        print(f"⚠️  WARNING: Scenario weights sum to {total_weight}%, expected 100%")

    return scenarios
