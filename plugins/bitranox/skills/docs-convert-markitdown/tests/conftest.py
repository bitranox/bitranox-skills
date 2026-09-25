"""Shared pytest fixtures and helpers for the markitdown skill script tests.

Two layers of test live here:

- In-process tests load a script with ``load_script`` and call its functions.
- End-to-end tests run a script as a real subprocess through ``run_script``.
  ``markitdown`` and ``openai`` are third-party edges, so the subprocess can be
  given an offline stand-in for either one: ``fake_markitdown_dir`` and
  ``fake_openai_dir`` are directories holding a fake package, put first on the
  child's PYTHONPATH so they shadow a real install. That keeps these tests
  running in CI, whose dependency set carries neither package. Tests that need
  the REAL markitdown ``pytest.importorskip`` it.

Every subprocess gets a throwaway HOME and dead proxies, so nothing can write to
the real home directory or reach the network.
"""

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

# A stand-in for markitdown with the two behaviours the scripts depend on:
# ImageConverter lets a failed LLM call propagate, PptxConverter swallows it.
# A "pptx" here is a text file; each line reading PICTURE is one picture.
FAKE_MARKITDOWN_SRC = '''
"""Offline stand-in for markitdown, used only by the skill-script tests."""
from pathlib import Path


class _Result:
    def __init__(self, text):
        self.title = None
        self.text_content = text


class MarkItDown:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def _caption(self):
        client = self._kwargs["llm_client"]
        response = client.chat.completions.create(model=self._kwargs["llm_model"], messages=[])
        return response.choices[0].message.content

    def convert(self, source):
        path = Path(source)
        text = path.read_bytes().decode("utf-8", "replace")
        if "FAIL-CONVERSION" in text:
            raise RuntimeError("fake conversion failure")
        has_llm = self._kwargs.get("llm_client") is not None and self._kwargs.get("llm_model")
        suffix = path.suffix.lower()
        if has_llm and suffix in (".png", ".jpg", ".jpeg"):
            text += "\\n# Description:\\n" + self._caption()
        elif has_llm and suffix == ".pptx":
            for line in text.splitlines():
                if line.strip() == "PICTURE":
                    try:
                        text += "\\n" + self._caption()
                    except Exception:
                        pass
        return _Result(text)
'''

# A stand-in for the openai client. FAKE_OPENAI_MODE=fail makes every call raise;
# FAKE_OPENAI_LOG names a file that gets one line per call.
FAKE_OPENAI_SRC = '''
"""Offline stand-in for openai, used only by the skill-script tests."""
import os
from types import SimpleNamespace


class _Completions:
    def create(self, **kwargs):
        log = os.environ.get("FAKE_OPENAI_LOG")
        if log:
            with open(log, "a", encoding="utf-8") as handle:
                handle.write("call\\n")
        if os.environ.get("FAKE_OPENAI_MODE") == "fail":
            raise RuntimeError("fake 401 unauthorized")
        message = SimpleNamespace(content="FAKE-CAPTION")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class OpenAI:
    def __init__(self, api_key=None, base_url=None):
        self.chat = SimpleNamespace(completions=_Completions())
'''


@dataclass(frozen=True)
class Run:
    """The outcome of one script subprocess."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """stdout and stderr together, for assertions that do not care which."""
        return self.stdout + self.stderr


def load_script(name: str) -> ModuleType:
    """Load a bundled script as a module by file path.

    Args:
        name: Script file stem, e.g. "batch_convert".

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


def _write_package(root: Path, name: str, source: str) -> Path:
    package = root / name
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(source, encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def fake_markitdown_dir(tmp_path_factory) -> Path:
    """A directory holding the offline ``markitdown`` stand-in."""
    return _write_package(tmp_path_factory.mktemp("fake_markitdown"), "markitdown", FAKE_MARKITDOWN_SRC)


@pytest.fixture(scope="session")
def fake_openai_dir(tmp_path_factory) -> Path:
    """A directory holding the offline ``openai`` stand-in."""
    return _write_package(tmp_path_factory.mktemp("fake_openai"), "openai", FAKE_OPENAI_SRC)


def _child_env(home: Path, pythonpath: list, encoding: str, extra: dict) -> dict:
    env = dict(os.environ)
    for key in ("PYTHONPATH", "OPENROUTER_API_KEY", "FAKE_OPENAI_MODE", "FAKE_OPENAI_LOG"):
        env.pop(key, None)
    if pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(str(p) for p in pythonpath)
    env["PYTHONIOENCODING"] = encoding
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    for proxy in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"):
        env[proxy] = "http://127.0.0.1:9"
    env.update(extra)
    return env


def run_script(
    name: str,
    args: list,
    *,
    cwd: Path,
    pythonpath: list | None = None,
    encoding: str = "utf-8",
    env: dict | None = None,
    prelude: str | None = None,
) -> Run:
    """Run a bundled script as a subprocess and return its decoded outcome.

    Args:
        name: Script file stem.
        args: Command-line arguments for the script.
        cwd: Working directory; also used as the child's HOME.
        pythonpath: Directories to put first on the child's import path.
        encoding: PYTHONIOENCODING for the child, e.g. "cp1252" to stand in for a Windows console.
        env: Extra environment variables for the child.
        prelude: Python code run before the script (via runpy), e.g. to block an import.

    Returns:
        The exit code and the decoded stdout/stderr.
    """
    script = SCRIPTS_DIR / (name + ".py")
    if prelude is None:
        cmd = [sys.executable, str(script), *args]
    else:
        runner = prelude + "\nimport runpy, sys\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n"
        cmd = [sys.executable, "-c", runner, str(script), *args]
    proc = subprocess.run(
        cmd, capture_output=True, cwd=cwd, timeout=180,
        env=_child_env(cwd, pythonpath or [], encoding, env or {}),
    )
    return Run(proc.returncode, proc.stdout.decode(encoding, "replace"), proc.stderr.decode(encoding, "replace"))


def block_import_prelude(*names: str) -> str:
    """A ``run_script`` prelude that makes ``import <name>`` raise ImportError, whatever is installed."""
    return "import sys\nfor _name in " + repr(list(names)) + ":\n    sys.modules[_name] = None\n"


@pytest.fixture(scope="session")
def script_runner():
    """``run_script`` as a fixture: the suite runs in importlib mode, so tests cannot import conftest."""
    return run_script


@pytest.fixture(scope="session")
def block_import():
    """``block_import_prelude`` as a fixture."""
    return block_import_prelude


@pytest.fixture(scope="session")
def scripts_dir() -> Path:
    """The skill's scripts/ directory."""
    return SCRIPTS_DIR


@pytest.fixture(scope="session")
def literature():
    """convert_literature module (markitdown is imported lazily, so no skip)."""
    return load_script("convert_literature")


@pytest.fixture(scope="session")
def with_ai():
    """convert_with_ai module (markitdown and openai are imported lazily)."""
    return load_script("convert_with_ai")


@pytest.fixture(scope="session")
def batch():
    """batch_convert module (markitdown is imported lazily)."""
    return load_script("batch_convert")
