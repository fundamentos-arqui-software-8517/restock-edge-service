"""conftest.py – pytest configuration for restock-edge-service tests.

Adds the project root to sys.path so that all bounded-context packages
(tracking, iam, devices, shared) are importable without installation.
"""
import sys
import os

# Insert project root so all packages are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
