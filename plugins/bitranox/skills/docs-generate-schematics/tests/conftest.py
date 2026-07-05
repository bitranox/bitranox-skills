"""Shared pytest fixtures for the schematic-generation script tests.

The tests exercise pure, import-safe logic only; no network is touched. The AI
module needs httpx2 at import time, so it is loaded via ``pytest.importorskip``
and the suite degrades to skips when the dependency is absent.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name: str) -> ModuleType:
    """Load a bundled script as a module by file path.

    Args:
        name: Script file stem, e.g. "generate_schematic_ai".

    Returns:
        The imported module object.
    """
    path = SCRIPTS_DIR / (name + ".py")
    spec = importlib.util.spec_from_file_location("schematics_skill_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def gen_ai():
    """The generate_schematic_ai module (import-safe: only needs httpx2)."""
    pytest.importorskip("httpx2")
    return load_script("generate_schematic_ai")


@pytest.fixture(scope="session")
def gen_wrapper():
    """The generate_schematic.py wrapper module (stdlib only)."""
    return load_script("generate_schematic")


@pytest.fixture
def generator(gen_ai):
    """A generator instance built with a fake key (no network is touched)."""
    return gen_ai.ScientificSchematicGenerator(api_key="test-key-not-real")
