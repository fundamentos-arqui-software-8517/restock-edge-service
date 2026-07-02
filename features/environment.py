# restock-edge-service – environment.py
# Behave environment hooks: configure sys.path so that all project packages
# are importable when running BDD scenarios.
import sys
import os

def before_all(context):
    """Add the project root to sys.path before any feature is executed."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
