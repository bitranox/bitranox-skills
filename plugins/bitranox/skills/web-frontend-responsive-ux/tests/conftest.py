"""Put the skill directory on sys.path so tests can import the scripts by module name, and
this tests directory so they can import the shared ``responsive_fake_browser`` double (the
repo runs pytest in importlib mode, which does not add a test file's own directory)."""
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)
