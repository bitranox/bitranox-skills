"""Put the skill directory on sys.path, the convention every skill's tests dir follows.

render-graphs.js is driven as a subprocess, so nothing here imports it; the path entry keeps this
directory shaped like its siblings for any Python helper the skill ships later."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
