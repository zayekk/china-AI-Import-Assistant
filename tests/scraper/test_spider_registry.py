"""
Tests unitaires : registry de spiders (détection de plateforme par URL).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scraper.spiders.alibaba_spider import AlibabaSpider
from scraper.spiders.pinduoduo_spider import PinduoduoSpider
from scraper.spiders.taobao_spider import TaobaoSpider


def test_taobao_spider_matches():
    spider = TaobaoSpider()
    assert spider.matches("https://item.taobao.com/item.htm?id=123456")
    assert not spider.matches("https://www.pinduoduo.com/goods.html?id=123")


def test_pinduoduo_spider_matches():
    spider = PinduoduoSpider()
    assert spider.matches("https://mobile.yangkeduo.com/goods.html?id=123")
    assert spider.matches("https://www.pinduoduo.com/goods.html?id=123")
    assert not spider.matches("https://item.taobao.com/item.htm?id=123456")


def test_alibaba_spider_matches():
    spider = AlibabaSpider()
    assert spider.matches("https://www.alibaba.com/product-detail/foo_123.html")
    assert spider.matches("https://detail.1688.com/offer/123456.html")
    assert not spider.matches("https://item.taobao.com/item.htm?id=123456")
