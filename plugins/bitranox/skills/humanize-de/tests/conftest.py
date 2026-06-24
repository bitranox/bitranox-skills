"""Put the skill's scripts/ dir on sys.path so tests can import the script by module name."""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_here), "scripts"))
