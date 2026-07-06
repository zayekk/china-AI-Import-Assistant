"""
Spider Pinduoduo : extraction des données produit et avis depuis pinduoduo.com / yangkeduo.com.

NOTE : comme Taobao, Pinduoduo charge son contenu via JavaScript et peut
nécessiter une géolocalisation/IP chinoise pour un accès optimal.
Les sélecteurs sont fournis comme structure de référence à maintenir.
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from scraper.spiders.base_spider import BaseSpider, ScrapedProduct, ScrapedReview

logger = logging.getLogger(__name__)


class PinduoduoSpider(BaseSpider):
    platform_name = "pinduoduo"

    def matches(self, url: str) -> bool:
        return "pinduoduo.com" in url or "yangkeduo.com" in url

    def extract_product(self, page: Page, url: str) -> ScrapedProduct:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        name = self._safe_text(soup.select_one("h1, [class*='goods-name']"))
        price_text = self._safe_text(soup.select_one("[class*='price']"))
        price_value = self._parse_price(price_text)

        description = self._safe_text(soup.select_one("[class*='detail-desc'], [class*='description']"))

        images = [
            img.get("src") or img.get("data-src")
            for img in soup.select("[class*='thumb'] img, [class*='gallery'] img")
            if img.get("src") or img.get("data-src")
        ]
        images = [self._normalize_image_url(src) for src in images if src]

        sales_text = self._safe_text(soup.select_one("[class*='sold'], [class*='sales']"))
        sales_count = self._parse_int(sales_text)

        rating_text = self._safe_text(soup.select_one("[class*='rate'], [class*='score']"))
        rating = self._parse_rating(rating_text)

        supplier_name = self._safe_text(soup.select_one("[class*='mall-name'], [class*='shop-name']"))

        variants = self._extract_variants(soup)

        return ScrapedProduct(
            name=name or "Produit Pinduoduo (nom non détecté)",
            price_value=price_value,
            price_currency="CNY",
            description=description,
            images=images[:10],
            variants=variants,
            stock=None,
            sales_count=sales_count,
            rating=rating,
            supplier_name=supplier_name,
        )

    def extract_reviews(self, page: Page, max_reviews: int = 20) -> list[ScrapedReview]:
        reviews: list[ScrapedReview] = []
        try:
            page.wait_for_selector("[class*='review'], [class*='comment']", timeout=5000)
        except Exception:
            logger.info("Aucune section d'avis détectée (pinduoduo) ou chargement trop lent.")
            return reviews

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        review_nodes = soup.select("[class*='review-item'], [class*='comment-item']")[:max_reviews]
        for node in review_nodes:
            content = self._safe_text(node.select_one("[class*='content'], [class*='text']")) \
                or self._safe_text(node)
            author = self._safe_text(node.select_one("[class*='name'], [class*='nickname']"))
            if content:
                reviews.append(ScrapedReview(content=content, author=author))

        return reviews

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
    def _parse_rating(text: str | None) -> float | None:
        if not text:
            return None
        match = re.search(r"[\d]+\.?[\d]*", text)
        if not match:
            return None
        value = float(match.group())
        return value if value <= 5 else round(value / 20, 2)  # normalise si note /100

    @staticmethod
    def _normalize_image_url(src: str) -> str:
        if src.startswith("//"):
            return "https:" + src
        return src

    def _extract_variants(self, soup: BeautifulSoup) -> list[dict]:
        variants: list[dict] = []
        for group in soup.select("[class*='sku-group']"):
            label = self._safe_text(group.select_one("[class*='sku-title']")) or "Option"
            options = [
                self._safe_text(opt)
                for opt in group.select("[class*='sku-item']")
                if self._safe_text(opt)
            ]
            if options:
                variants.append({"name": label, "options": options})
        return variants
