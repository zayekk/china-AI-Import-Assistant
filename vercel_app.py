"""
Point d'entrée serverless pour Vercel : réexpose l'application FastAPI existante
(backend/app/main.py) sous /api/* — voir docs/vercel_deployment.md pour le détail
de l'architecture et de ses limites.

Ce fichier vit délibérément à la racine du repo (et non dans un dossier api/,
app/ ou src/) : ces noms sont réservés par Vercel pour son ancien mécanisme de
détection automatique de fonctions par système de fichiers, qui entre en
conflit avec la configuration "services" utilisée ici (voir vercel.json et
docs/vercel_deployment.md, section "Notes techniques").

Limites connues de cet environnement serverless (déjà gérées gracieusement par le
code existant, aucune modification métier nécessaire) :
- /api/v1/scrape et /api/v1/analyze-url nécessitent un navigateur Playwright, non
  disponible sur Vercel : ils échouent proprement en 502 (SpiderError déjà géré
  dans scrape.py / analysis.py).
- /api/v1/analyze-image et /api/v1/analyze-images nécessitent le binaire système
  Tesseract, absent sur Vercel : ils échouent proprement en 422 (OCRError déjà géré
  dans analysis.py).
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
