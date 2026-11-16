import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(backend_dir)

for path in (backend_dir, project_root):
    if path not in sys.path:
        sys.path.insert(0, path)
