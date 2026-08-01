"""Put the skill's scripts dir on sys.path so tests import them by module name. ASCII only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
