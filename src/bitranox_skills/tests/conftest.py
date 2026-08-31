"""Put `src/` on sys.path so the package imports from a plain source checkout.

Mirrors what hooks/tests/conftest.py does for the hook modules: the suite must run without
the distribution being installed, or the tests only ever exercise a wheel somebody already
built, which is the opposite of the order you want.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
