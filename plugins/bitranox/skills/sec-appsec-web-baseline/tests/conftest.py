"""Put the skill directory on sys.path so tests can `import audit_headers` by name."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
