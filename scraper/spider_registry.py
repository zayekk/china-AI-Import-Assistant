"""
Registry des spiders disponibles : point d'entrée unique et modulaire du scraper.

Pour ajouter une nouvelle plateforme :
1. Créer une nouvelle classe héritant de BaseSpider dans scraper/spiders/
2. L'enregistrer dans SPIDER_REGISTRY ci-dessous
Aucune autre modification n'est nécessaire ailleurs dans le code.
"""
from __future__ import annotations

import logging

from app.core.config import settings
from scraper.spiders.alibaba_spider import AlibabaSpider
from scraper.spiders.base_spider import BaseSpider, ScrapedProduct, SpiderError
from scraper.spiders.pinduoduo_spider import PinduoduoSpider
from scraper.spiders.taobao_spider import TaobaoSpider

logger = logging.getLogger(__name__)

SPIDER_REGISTRY: list[type[BaseSpider]] = [
    TaobaoSpider,
    PinduoduoSpider,
    AlibabaSpider,
]


def get_spider_for_url(url: str) -> BaseSpider:
    """Retourne l'instance de spider capable de traiter l'URL donnée."""
    for spider_cls in SPIDER_REGISTRY:
        instance = spider_cls(
            headless=settings.SCRAPER_HEADLESS,
            timeout_ms=settings.SCRAPER_TIMEOUT_MS,
            user_agent=settings.SCRAPER_USER_AGENT,
            proxy=settings.SCRAPER_PROXY,
        )
        if instance.matches(url):
            return instance

    raise SpiderError(
        f"Aucun spider disponible pour cette URL : {url}. "
        f"Plateformes supportées : taobao.com, pinduoduo.com, alibaba.com, 1688.com"
    )


def scrape_product_url(
    url: str, fetch_reviews: bool = True, max_reviews: int = 20
) -> ScrapedProduct:
    """Point d'entrée haut niveau : détecte la plateforme et lance le scraping."""
    spider = get_spider_for_url(url)
    logger.info("Scraping démarré via %s pour %s", spider.platform_name, url)
    return spider.scrape(url, fetch_reviews=fetch_reviews, max_reviews=max_reviews)
