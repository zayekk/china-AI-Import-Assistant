"""
Tests unitaires : chargement de la configuration (backend/app/core/config.py).

Couvre la régression diagnostiquée où toute analyse IA basculait silencieusement sur le
repli local ("Analyse IA indisponible") sans qu'aucune requête réseau n'ait jamais été
tentée : `env_file=".env"` était un chemin RELATIF, résolu par pydantic-settings par
rapport au répertoire de travail du process au moment de l'instanciation — lancé depuis
un dossier autre que `backend/` (config IDE, service, terminal différent), aucun .env
n'était trouvé et MISTRAL_API_KEY retombait silencieusement sur son défaut vide "".
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import Settings, _ENV_FILE


def test_env_file_path_is_absolute():
    """Un chemin relatif ré-introduirait la dépendance au répertoire de travail du process."""
    assert _ENV_FILE.is_absolute()


def test_env_file_path_points_to_backend_dot_env():
    assert _ENV_FILE.name == ".env"
    assert _ENV_FILE.parent.name == "backend"


def test_settings_loads_real_env_regardless_of_current_working_directory(monkeypatch, tmp_path):
    """Reproduit exactement le bug diagnostiqué : construire Settings() alors que le
    répertoire de travail courant n'est PAS backend/ ne doit plus vider MISTRAL_API_KEY."""
    monkeypatch.chdir(tmp_path)  # simule un lancement depuis un dossier quelconque

    settings = Settings()

    # Le contenu réel de backend/.env n'est pas garanti en CI, mais l'important est que la
    # RÉSOLUTION DU CHEMIN ne dépende plus du cwd : si backend/.env existe et contient une
    # clé (cas de cet environnement de dev), elle doit être chargée même après un chdir.
    if _ENV_FILE.exists() and "MISTRAL_API_KEY" in _ENV_FILE.read_text(encoding="utf-8"):
        assert settings.MISTRAL_API_KEY != ""
