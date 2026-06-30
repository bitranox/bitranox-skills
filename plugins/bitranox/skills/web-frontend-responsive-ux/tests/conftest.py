"""Put the skill directory on sys.path so tests can import the scripts by module name."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
