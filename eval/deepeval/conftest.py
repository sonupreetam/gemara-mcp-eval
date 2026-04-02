import asyncio
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.mcp_client import GemaraMCPClient

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


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mcp_client(event_loop):
    """Session-scoped MCP client connected to gemara-mcp."""
    client = GemaraMCPClient()

    async def setup():
        await client.__aenter__()
        return client

    c = event_loop.run_until_complete(setup())
    yield c

    async def teardown():
        await client.__aexit__(None, None, None)

    event_loop.run_until_complete(teardown())
