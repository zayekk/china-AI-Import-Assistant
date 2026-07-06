"""
Configuration pytest globale : ajoute la racine du projet au PYTHONPATH
pour permettre les imports `app.*`, `ai_engine.*`, `scraper.*` dans les tests.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

for path in (ROOT_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
