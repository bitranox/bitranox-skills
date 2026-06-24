"""Shared pytest fixtures and helpers for the markitdown skill script tests.

These tests only exercise pure, import-safe logic. Scripts that import heavy
third-party libraries at module top level (markitdown, openai) are loaded via
``load_script`` guarded by ``pytest.importorskip`` so the suite degrades to
skips instead of errors when those deps are absent.
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
    spec = importlib.util.spec_from_file_location("md_skill_" + name, path)
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


@pytest.fixture(scope="session")
def literature():
    """convert_literature module; needs markitdown at import time."""
    pytest.importorskip("markitdown")
    return load_script("convert_literature")


@pytest.fixture(scope="session")
def with_ai():
    """convert_with_ai module; needs markitdown and openai at import time."""
    pytest.importorskip("markitdown")
    pytest.importorskip("openai")
    return load_script("convert_with_ai")


@pytest.fixture(scope="session")
def batch():
    """batch_convert module; needs markitdown at import time."""
    pytest.importorskip("markitdown")
    return load_script("batch_convert")


@pytest.fixture
def generator(gen_ai):
    """A generator instance built with a fake key (no network is touched)."""
    return gen_ai.ScientificSchematicGenerator(api_key="test-key-not-real")
