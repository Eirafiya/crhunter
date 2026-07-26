import logging
import requests
from bs4 import BeautifulSoup
from core.models import Listing

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IE,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


class BaseProvider:
    name: str = ""
    url: str = ""

    def fetch(self) -> list[Listing]:
        raise NotImplementedError

    def _get(self, url: str) -> BeautifulSoup:
        """Fetch URL, falling back to Playwright if requests is blocked."""
        import time
        session = requests.Session()
        session.headers.update(HEADERS)
        try:
            from urllib.parse import urlparse
            origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            session.get(origin, timeout=10)
            time.sleep(1)
        except Exception:
            pass

        for attempt in range(2):
            resp = session.get(url, timeout=20)
            if resp.status_code in (403, 429, 503) and attempt < 1:
                time.sleep(4)
                continue
            if resp.status_code in (403, 429, 503):
                logger.info(f"requests blocked ({resp.status_code}), trying playwright for {url}")
                return self._get_playwright(url)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        return self._get_playwright(url)

    def _get_playwright(self, url: str) -> BeautifulSoup:
        """Fetch via headless Chromium — bypasses JS-based bot detection."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright not available and requests was blocked")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="en-IE",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()

        return BeautifulSoup(html, "lxml")

    def _make_id(self, slug: str) -> str:
        return f"{self.name}::{slug}"

    def _county_from_location(self, location: str) -> str:
        location_lower = location.lower()
        counties = [
            "dublin", "kildare", "meath", "wicklow", "cork",
            "galway", "limerick", "waterford", "westmeath", "laois",
            "louth", "wexford", "kilkenny", "tipperary", "clare",
        ]
        for county in counties:
            if county in location_lower:
                return county.title()
        return "Unknown"
