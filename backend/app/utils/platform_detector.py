"""
Utilitaire : détecte la plateforme e-commerce à partir d'une URL produit.

Dérive du même registry que le scraper (scraper/spider_registry.py) pour
qu'il n'existe qu'une seule source de vérité sur les plateformes supportées :
ajouter un spider au registry suffit, aucune liste séparée à maintenir ici.
"""
from __future__ import annotations

from scraper.spider_registry import SPIDER_REGISTRY


def detect_platform(url: str) -> str:
    """Retourne le nom de la plateforme détectée, ou 'unknown'."""
    for spider_cls in SPIDER_REGISTRY:
        if spider_cls().matches(url):
            return spider_cls.platform_name
    return "unknown"
