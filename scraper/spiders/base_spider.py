"""
Classe de base abstraite pour tous les spiders (scrapers par plateforme).
Toute nouvelle plateforme (Taobao, Pinduoduo, Alibaba, 1688, etc.)
doit hériter de BaseSpider et implémenter ses méthodes abstraites.

Cela garantit que le scraper reste modulaire et facilement extensible.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

logger = logging.getLogger(__name__)


@dataclass
class ScrapedReview:
    author: str | None = None
    rating: float | None = None
    content: str | None = None
    images: list[str] = field(default_factory=list)
    variant_purchased: str | None = None


@dataclass
class ScrapedProduct:
    name: str
    price_value: float | None = None
    price_currency: str = "CNY"
    description: str | None = None
    images: list[str] = field(default_factory=list)
    variants: list[dict] = field(default_factory=list)
    stock: int | None = None
    sales_count: int | None = None
    rating: float | None = None
    source_url: str | None = None
    platform: str | None = None

    # Données fournisseur
    supplier_name: str | None = None
    supplier_shop_url: str | None = None
    supplier_years_active: float | None = None
    supplier_rating: float | None = None
    supplier_total_reviews: int | None = None
    supplier_total_sales: int | None = None

    reviews: list[ScrapedReview] = field(default_factory=list)


class SpiderError(Exception):
    """Erreur levée en cas d'échec du scraping."""


class BaseSpider(ABC):
    """
    Interface commune à tous les scrapers de plateforme.
    Gère le cycle de vie Playwright (browser/context/page) et délègue
    l'extraction spécifique à chaque sous-classe.
    """

    platform_name: str = "generic"

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30000,
        user_agent: str | None = None,
        proxy: str | None = None,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent
        self.proxy = proxy

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Retourne True si cette spider sait traiter l'URL donnée."""
        raise NotImplementedError

    @abstractmethod
    def extract_product(self, page: Page, url: str) -> ScrapedProduct:
        """Extrait les données produit depuis une page déjà chargée."""
        raise NotImplementedError

    def extract_reviews(self, page: Page, max_reviews: int = 20) -> list[ScrapedReview]:
        """
        Extraction des avis clients. Implémentation par défaut vide ;
        à surcharger dans les sous-classes qui supportent les avis.
        """
        return []

    def scrape(self, url: str, fetch_reviews: bool = True, max_reviews: int = 20) -> ScrapedProduct:
        """
        Point d'entrée principal : ouvre un navigateur headless, charge l'URL,
        et délègue l'extraction aux méthodes spécifiques à la plateforme.
        """
        with sync_playwright() as p:
            browser: Browser = self._launch_browser(p)
            context: BrowserContext = browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1366, "height": 900},
            )
            page: Page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)  # laisser le temps au JS de s'exécuter

                product = self.extract_product(page, url)
                product.platform = self.platform_name
                product.source_url = url

                if fetch_reviews:
                    try:
                        product.reviews = self.extract_reviews(page, max_reviews=max_reviews)
                    except Exception as exc:  # ne bloque pas le scraping produit si les avis échouent
                        logger.warning("Échec extraction avis (%s): %s", self.platform_name, exc)

                return product

            except Exception as exc:
                logger.error("Échec du scraping (%s) sur %s: %s", self.platform_name, url, exc)
                raise SpiderError(f"Échec du scraping {self.platform_name}: {exc}") from exc

            finally:
                context.close()
                browser.close()

    def _launch_browser(self, playwright_instance) -> Browser:
        launch_kwargs: dict = {"headless": self.headless}
        if self.proxy:
            launch_kwargs["proxy"] = {"server": self.proxy}
        return playwright_instance.chromium.launch(**launch_kwargs)
