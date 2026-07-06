"""
Spider Taobao : extraction des données produit et avis depuis taobao.com.

NOTE IMPORTANTE :
Taobao utilise une protection anti-bot agressive (login obligatoire, captchas,
chargement dynamique fort). Les sélecteurs CSS ci-dessous sont fournis à titre
de structure de référence et DOIVENT être ajustés/maintenus régulièrement,
car le DOM de Taobao change fréquemment. En production, prévoir :
- rotation de proxies résidentiels
- gestion de session/cookies persistants
- éventuellement un service de résolution de captcha tiers
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from scraper.spiders.base_spider import BaseSpider, ScrapedProduct, ScrapedReview

logger = logging.getLogger(__name__)


class TaobaoSpider(BaseSpider):
    platform_name = "taobao"

    def matches(self, url: str) -> bool:
        return "taobao.com" in url

    def extract_product(self, page: Page, url: str) -> ScrapedProduct:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        name = self._safe_text(soup.select_one(".tb-main-title, h1.tb-detail-hd"))
        price_text = self._safe_text(soup.select_one(".tb-rmb-num, .tm-price"))
        price_value = self._parse_price(price_text)

        description = self._safe_text(soup.select_one(".tb-detail-desc, #J_DivItemDesc"))

        images = [
            img.get("src") or img.get("data-src")
            for img in soup.select(".tb-thumb img, #J_UlThumb img")
            if img.get("src") or img.get("data-src")
        ]
        images = [self._normalize_image_url(src) for src in images if src]

        variants = self._extract_variants(soup)

        sales_text = self._safe_text(soup.select_one(".tb-sell-counter, .tm-ind-sellCount"))
        sales_count = self._parse_int(sales_text)

        rating_text = self._safe_text(soup.select_one(".tb-rate-counter, .tm-ind-reviewCount"))
        rating = None  # Taobao expose plutôt un nombre d'avis qu'une note moyenne directe

        supplier_name = self._safe_text(soup.select_one(".shop-name, .slogo-shopname"))
        supplier_shop_url = None
        shop_link = soup.select_one(".shop-name a, .slogo-shopname a")
        if shop_link and shop_link.get("href"):
            supplier_shop_url = self._normalize_image_url(shop_link["href"])

        return ScrapedProduct(
            name=name or "Produit Taobao (nom non détecté)",
            price_value=price_value,
            price_currency="CNY",
            description=description,
            images=images[:10],
            variants=variants,
            stock=None,
            sales_count=sales_count,
            rating=rating,
            supplier_name=supplier_name,
            supplier_shop_url=supplier_shop_url,
        )

    def extract_reviews(self, page: Page, max_reviews: int = 20) -> list[ScrapedReview]:
        reviews: list[ScrapedReview] = []
        try:
            page.wait_for_selector(".rate-grid, .comment-content", timeout=5000)
        except Exception:
            logger.info("Aucune section d'avis détectée (taobao) ou chargement trop lent.")
            return reviews

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        review_nodes = soup.select(".rate-grid .tm-rate-content, .comment-content")[:max_reviews]
        for node in review_nodes:
            content = self._safe_text(node)
            if content:
                reviews.append(ScrapedReview(content=content))

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
    def _normalize_image_url(src: str) -> str:
        if src.startswith("//"):
            return "https:" + src
        return src

    def _extract_variants(self, soup: BeautifulSoup) -> list[dict]:
        variants: list[dict] = []
        for group in soup.select(".tb-sku .tb-prop"):
            label_node = group.select_one(".tb-property-type")
            label = self._safe_text(label_node) or "Option"
            options = [
                self._safe_text(opt)
                for opt in group.select("li a, li")
                if self._safe_text(opt)
            ]
            if options:
                variants.append({"name": label, "options": options})
        return variants
