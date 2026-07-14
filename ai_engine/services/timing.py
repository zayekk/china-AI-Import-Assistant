"""
Instrumentation de performance du pipeline d'analyse IA (OCR -> fusion -> construction du
prompt -> appel Mistral -> parsing). Un log structuré par étape, pour diagnostiquer
précisément où le temps est passé — c'est ce qui a permis de confirmer que le prompt
système (65+ champs depuis la v1.3) pousse le temps de génération Mistral tout près du
timeout configuré, plutôt que de le supposer.

Toutes les étapes du pipeline (ai_engine/services/product_analysis_service.py,
multi_capture_service.py, mistral_client.py) journalisent via `log_step()` avec un format
uniforme, facilement grep-able : `[PIPELINE] step=<nom> duration=<secondes>s <clé>=<valeur>...`
"""
import logging
import time

logger = logging.getLogger("ai_engine.timing")


def estimate_tokens(text: str) -> int:
    """
    Estimation grossière du nombre de tokens (aucun tokenizer Mistral exact n'est exposé
    côté client) : ~4 caractères par token en moyenne pour du texte à dominante latine.
    Suffisant pour diagnostiquer une volumétrie de prompt, pas pour une facturation exacte.
    """
    return max(1, len(text) // 4)


def log_step(step: str, duration_seconds: float, **fields) -> None:
    """Log structuré uniforme pour une étape du pipeline (durée + métadonnées libres)."""
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("[PIPELINE] step=%s duration=%.3fs %s", step, duration_seconds, details)


class StepTimer:
    """
    Petit chronomètre manuel (pas un context manager) : certaines étapes ont besoin de
    connaître des métadonnées calculées APRÈS la fin de la mesure (ex: taille de la réponse
    Mistral, connue seulement une fois la requête terminée) — `elapsed()` peut être appelé
    à tout moment sans clore la mesure, contrairement à un `@contextmanager` classique.
    """

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._start
