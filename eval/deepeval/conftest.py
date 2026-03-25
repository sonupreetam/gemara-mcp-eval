import json
from pathlib import Path

import pytest
import yaml

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"


@pytest.fixture(scope="session")
def corpus():
    """Load the full scenario corpus."""
    scenarios_path = CORPUS_DIR / "scenarios.yaml"
    with open(scenarios_path) as f:
        return yaml.safe_load(f)["scenarios"]


@pytest.fixture(scope="session")
def tool_scenarios(corpus):
    """Scenarios targeting validate_gemara_artifact."""
    return [s for s in corpus if s["type"] == "tool"]


@pytest.fixture(scope="session")
def threat_scenarios(corpus):
    """Scenarios targeting threat_assessment prompt."""
    return [s for s in corpus if s["target"] == "threat_assessment"]


@pytest.fixture(scope="session")
def control_scenarios(corpus):
    """Scenarios targeting control_catalog prompt."""
    return [s for s in corpus if s["target"] == "control_catalog"]


@pytest.fixture(scope="session")
def golden_outputs():
    """Load all golden output files."""
    goldens = {}
    golden_dir = CORPUS_DIR / "golden"
    for f in golden_dir.iterdir():
        if f.suffix == ".json":
            goldens[f.stem] = json.loads(f.read_text())
        elif f.suffix in (".yaml", ".yml"):
            goldens[f.stem] = yaml.safe_load(f.read_text())
    return goldens


@pytest.fixture(scope="session")
def load_input():
    """Factory fixture to load a corpus input file."""

    def _load(filename: str) -> str:
        path = CORPUS_DIR / filename
        return path.read_text()

    return _load
