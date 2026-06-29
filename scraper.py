"""
scraper.py — searches Korean cosmetics websites for products
Supports: YesStyle, StyleKorean, Jolse, Stylevana, Soko Glam
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get(url: str, params: dict = None, timeout: int = 10) -> requests.Response | None:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        logger.warning("Request failed [%s]: %s", url, e)
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_usd(text: str) -> float | None:
    """Extract a USD float from strings like '$12.99' or 'USD 12.99'."""
    m = re.search(r"[\$USD\s]*([\d,]+\.?\d*)", text.replace(",", ""))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


# ── YesStyle ──────────────────────────────────────────────────────────────────

def search_yesstyle(query: str, max_results: int = 3) -> list[dict]:
    """Search YesStyle using their public search page."""
    url = "https://www.yesstyle.com/en/search.html"
    params = {"keyword": query, "list_type": "11", "bt": "495"}
    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select(".product-info")[:max_results]:
        try:
            name_tag = item.select_one(".product-name a") or item.select_one("a[title]")
            price_tag = item.select_one(".price") or item.select_one("[class*='price']")
            link_tag = item.select_one("a[href*='/en/']")

            name = _clean(name_tag.get_text()) if name_tag else None
            price_text = _clean(price_tag.get_text()) if price_tag else ""
            price_usd = _parse_usd(price_text)
            link = "https://www.yesstyle.com" + link_tag["href"] if link_tag and link_tag.get("href", "").startswith("/") else None

            if name and price_usd:
                results.append({
                    "source": "YesStyle",
                    "name": name,
                    "price_usd": price_usd,
                    "link": link or f"https://www.yesstyle.com/en/search.html?keyword={query.replace(' ', '+')}",
                })
        except Exception:
            continue

    return results


# ── StyleKorean ───────────────────────────────────────────────────────────────

def search_stylekorean(query: str, max_results: int = 3) -> list[dict]:
    url = "https://www.stylekorean.com/search/"
    params = {"q": query}
    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select(".product-item, .product-block, [class*='product']")[:max_results * 2]:
        try:
            name_tag = item.select_one(".product-name, .item-name, h3, h4, a[title]")
            price_tag = item.select_one(".price, .product-price, [class*='price']")
            link_tag = item.select_one("a[href*='/product']") or item.select_one("a")

            name = _clean(name_tag.get_text()) if name_tag else None
            price_text = _clean(price_tag.get_text()) if price_tag else ""
            price_usd = _parse_usd(price_text)
            href = link_tag["href"] if link_tag and link_tag.get("href") else ""
            link = ("https://www.stylekorean.com" + href) if href.startswith("/") else href

            if name and price_usd and len(name) > 5:
                results.append({
                    "source": "StyleKorean",
                    "name": name,
                    "price_usd": price_usd,
                    "link": link or f"https://www.stylekorean.com/search/?q={query.replace(' ', '+')}",
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


# ── Jolse ─────────────────────────────────────────────────────────────────────

def search_jolse(query: str, max_results: int = 3) -> list[dict]:
    url = "https://jolse.com/product/search.php"
    params = {"keyword": query}
    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select(".prdList li, .xans-product-listnormal li")[:max_results * 2]:
        try:
            name_tag = item.select_one(".prdName, .name, strong")
            price_tag = item.select_one(".price, .prdPrice, [class*='price']")
            link_tag = item.select_one("a[href*='product']")

            name = _clean(name_tag.get_text()) if name_tag else None
            price_text = _clean(price_tag.get_text()) if price_tag else ""
            price_usd = _parse_usd(price_text)
            href = link_tag["href"] if link_tag and link_tag.get("href") else ""
            link = ("https://jolse.com" + href) if href.startswith("/") else href

            if name and price_usd and len(name) > 5:
                results.append({
                    "source": "Jolse",
                    "name": name,
                    "price_usd": price_usd,
                    "link": link or f"https://jolse.com/product/search.php?keyword={query.replace(' ', '+')}",
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


# ── Stylevana ─────────────────────────────────────────────────────────────────

def search_stylevana(query: str, max_results: int = 3) -> list[dict]:
    url = "https://www.stylevana.com/en_US/catalogsearch/result/"
    params = {"q": query}
    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select(".product-item-info, .product-item, [class*='product-item']")[:max_results * 2]:
        try:
            name_tag = item.select_one(".product-item-name, .product-name, a[title]")
            price_tag = item.select_one(".price, [class*='price']")
            link_tag = item.select_one("a.product-item-link") or item.select_one("a[href*='stylevana']")

            name = _clean(name_tag.get_text()) if name_tag else None
            price_text = _clean(price_tag.get_text()) if price_tag else ""
            price_usd = _parse_usd(price_text)
            link = link_tag["href"] if link_tag and link_tag.get("href") else \
                f"https://www.stylevana.com/en_US/catalogsearch/result/?q={query.replace(' ', '+')}"

            if name and price_usd and len(name) > 5:
                results.append({
                    "source": "Stylevana",
                    "name": name,
                    "price_usd": price_usd,
                    "link": link,
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


# ── Soko Glam ─────────────────────────────────────────────────────────────────

def search_sokoglam(query: str, max_results: int = 3) -> list[dict]:
    url = "https://sokoglam.com/search"
    params = {"q": query, "type": "product"}
    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for item in soup.select(".product-card, .product-item, [class*='product-card']")[:max_results * 2]:
        try:
            name_tag = item.select_one(".product-card__title, .product-title, h3, h4")
            price_tag = item.select_one(".product-card__price, .price, [class*='price']")
            link_tag = item.select_one("a[href*='/products/']")

            name = _clean(name_tag.get_text()) if name_tag else None
            price_text = _clean(price_tag.get_text()) if price_tag else ""
            price_usd = _parse_usd(price_text)
            href = link_tag["href"] if link_tag and link_tag.get("href") else ""
            link = ("https://sokoglam.com" + href) if href.startswith("/") else href

            if name and price_usd and len(name) > 5:
                results.append({
                    "source": "Soko Glam",
                    "name": name,
                    "price_usd": price_usd,
                    "link": link or f"https://sokoglam.com/search?q={query.replace(' ', '+')}",
                })
                if len(results) >= max_results:
                    break
        except Exception:
            continue

    return results


# ── Main search function ───────────────────────────────────────────────────────

CONCERN_KEYWORDS = {
    "acne":       "acne pimple COSRX Korean skincare",
    "dark_spots": "dark spots niacinamide brightening Korean serum",
    "aging":      "anti aging wrinkle ginseng Korean cream",
    "hydration":  "hydrating moisturizer Korean skincare dry skin",
    "brightening":"brightening glow vitamin C Korean serum",
    "sensitive":  "sensitive skin calming cica Korean skincare",
}

SKIN_KEYWORDS = {
    "oily":      "oily skin pore control",
    "dry":       "dry skin hydrating",
    "combo":     "combination skin balancing",
    "sensitive": "sensitive skin gentle",
}


def build_query(skin: str, concern: str) -> str:
    concern_kw = CONCERN_KEYWORDS.get(concern, "Korean skincare")
    skin_kw = SKIN_KEYWORDS.get(skin, "")
    return f"{concern_kw} {skin_kw}".strip()


def search_all_sites(skin: str, concern: str, max_per_site: int = 2) -> list[dict]:
    """
    Search all supported Korean cosmetics websites and return combined results.
    Each result has: source, name, price_usd, link
    """
    query = build_query(skin, concern)
    logger.info("Searching all sites for: %s", query)

    all_results = []
    searchers = [
        search_yesstyle,
        search_stylekorean,
        search_jolse,
        search_stylevana,
        search_sokoglam,
    ]

    for fn in searchers:
        try:
            results = fn(query, max_results=max_per_site)
            all_results.extend(results)
            logger.info("%s → %d results", fn.__name__, len(results))
        except Exception as e:
            logger.warning("Searcher %s failed: %s", fn.__name__, e)

    return all_results
