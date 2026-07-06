"""
Spider Alibaba / 1688 : extraction des données produit (B2B, fournisseurs en gros).
1688.com cible le marché domestique chinois (B2B), alibaba.com cible l'international.
Les deux partagent une structure DOM proche, d'où une seule spider paramétrable.
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from scraper.spiders.base_spider import BaseSpider, ScrapedProduct, ScrapedReview

logger = logging.getLogger(__name__)


class AlibabaSpider(BaseSpider):
    platform_name = "alibaba"

    def matches(self, url: str) -> bool:
        return "alibaba.com" in url or "1688.com" in url

    def extract_product(self, page: Page, url: str) -> ScrapedProduct:
        if "1688.com" in url:
            self.platform_name = "1688"

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        name = self._safe_text(
            soup.select_one("h1, [class*='product-title'], [class*='title-text']")
        )
        price_text = self._safe_text(soup.select_one("[class*='price']"))
        price_value = self._parse_price(price_text)

        description = self._safe_text(
            soup.select_one("[class*='detail-desc'], [class*='description-content']")
        )

        images = [
            img.get("src") or img.get("data-src")
            for img in soup.select("[class*='thumb'] img, [class*='gallery'] img, [class*='image-list'] img")
            if img.get("src") or img.get("data-src")
        ]
        images = [self._normalize_image_url(src) for src in images if src]

        # En B2B, "stock" correspond souvent à la quantité disponible / MOQ
        stock_text = self._safe_text(soup.select_one("[class*='stock'], [class*='quantity']"))
        stock = self._parse_int(stock_text)

        supplier_name = self._safe_text(
            soup.select_one("[class*='company-name'], [class*='supplier-name']")
        )
        supplier_years_text = self._safe_text(soup.select_one("[class*='year']"))
        supplier_years_active = self._parse_years(supplier_years_text)

        variants = self._extract_variants(soup)

        return ScrapedProduct(
            name=name or "Produit Alibaba/1688 (nom non détecté)",
            price_value=price_value,
            price_currency="CNY",
            description=description,
            images=images[:10],
            variants=variants,
            stock=stock,
            sales_count=None,
            rating=None,
            supplier_name=supplier_name,
            supplier_years_active=supplier_years_active,
        )

    def extract_reviews(self, page: Page, max_reviews: int = 20) -> list[ScrapedReview]:
        # Les plateformes B2B exposent rarement des avis clients classiques ;
        # on retourne une liste vide par défaut (peut être enrichi plus tard
        # avec les évaluations de transactions si disponibles).
        return []

    # ---------- Helpers ----------

    @staticmethod
    def _safe_text(node) -> str | None:
        if node is None:
            return None
        text = node.get_text(strip=True)
        return text or None

    @staticmethod
    def _parse_price(text: str | None) -> float | None:
        if not text:
            return None
        match = re.search(r"[\d]+\.?[\d]*", text.replace(",", ""))
        return float(match.group()) if match else None

    @staticmethod
    def _parse_int(text: str | None) -> int | None:
        if not text:
            return None
        match = re.search(r"[\d]+", text.replace(",", ""))
        return int(match.group()) if match else None

    @staticmethod
    def _parse_years(text: str | None) -> float | None:
        if not text:
            return None
        match = re.search(r"[\d]+\.?[\d]*", text)
        return float(match.group()) if match else None

    @staticmethod
    def _normalize_image_url(src: str) -> str:
        if src.startswith("//"):
            return "https:" + src
        return src

    def _extract_variants(self, soup: BeautifulSoup) -> list[dict]:
        variants: list[dict] = []
        for group in soup.select("[class*='sku-prop'], [class*='attribute-group']"):
            label = self._safe_text(group.select_one("[class*='prop-title']")) or "Option"
            options = [
                self._safe_text(opt)
                for opt in group.select("[class*='prop-item'], li")
                if self._safe_text(opt)
            ]
            if options:
                variants.append({"name": label, "options": options})
        return variants
