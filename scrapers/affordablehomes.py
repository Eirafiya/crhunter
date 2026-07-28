import re
import logging
from urllib.parse import urljoin
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://affordablehomes.ie"


class AffordableHomesScraper(BaseProvider):
    """
    Central government portal — aggregates listings from all providers.
    Primary source: covers all approved housing bodies and state schemes.
    """
    name = "affordablehomes"
    url = f"{BASE}/rent/"

    def fetch(self) -> list[Listing]:
        try:
            return self._fetch_with_requests()
        except Exception as e:
            logger.warning(f"affordablehomes: requests failed ({e}), trying playwright")
            return self._fetch_with_playwright()

    def _fetch_with_requests(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = self._parse_soup(soup)
        if not listings:
            raise ValueError("No listings found with requests — may be blocked")
        return listings

    def _fetch_with_playwright(self) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            )
            page.goto(self.url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        return self._parse_soup(soup)

    def _parse_soup(self, soup) -> list[Listing]:
        listings = []

        # Expected structure from search snippet:
        # Each listing card has: name, price, status, applications open date,
        # location, bedrooms, availability, listed date
        for card in soup.select(".property-card, .listing-card, .scheme-card, article, .card"):
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"affordablehomes: card parse error: {e}")

        # Fallback: structured text blocks
        if not listings:
            listings = self._text_fallback(soup)

        logger.info(f"affordablehomes: found {len(listings)} listings")
        return listings

    def _parse_card(self, card) -> Listing | None:
        name_el = card.find(["h2", "h3", "h4"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name or len(name) < 3:
            return None

        # Status
        status_el = card.find(class_=re.compile(r"status|badge|state", re.I))
        raw_status = status_el.get_text(strip=True) if status_el else ""
        if not raw_status:
            for el in card.find_all(["p", "span", "div"]):
                t = el.get_text(strip=True)
                if re.search(r"applications (open|closed)|coming soon", t, re.I):
                    raw_status = t
                    break

        # Location
        location = ""
        for el in card.find_all(["p", "span", "li"]):
            t = el.get_text(strip=True)
            if re.search(r"(dublin|cork|galway|kildare|meath|wicklow|limerick)", t, re.I):
                location = t
                break

        # Bedrooms
        bedrooms = []
        for el in card.find_all(["p", "span", "li"]):
            t = el.get_text(strip=True)
            m = re.findall(r"(\d+)\s*[Bb]ed|[Ss]tudio", t)
            if m:
                bedrooms = [f"{b} Bed" if b else "Studio" for b in m]
                break

        # Price
        price_el = card.find(string=re.compile(r"€[\d,]+"))
        price_from = price_el.strip() if price_el else None

        # Apply date
        open_date = None
        close_date = None
        for el in card.find_all(["p", "span", "li"]):
            t = el.get_text(strip=True)
            if re.search(r"applications open", t, re.I):
                open_date = t
            if re.search(r"applications close|deadline", t, re.I):
                close_date = t

        # Units
        units = None
        for el in card.find_all(["p", "span", "li"]):
            t = el.get_text(strip=True)
            m = re.search(r"(\d+)\s+units?", t, re.I)
            if m:
                units = int(m.group(1))
                break

        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))

        if not location:
            location = name

        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider=self._detect_provider(card, name),
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status) if raw_status else "unknown",
            raw_status=raw_status or "unknown",
            bedrooms=bedrooms,
            price_from=price_from,
            units_available=units,
            applications_open=open_date,
            applications_close=close_date,
            apply_url=link,
        )

    def _detect_provider(self, card, name: str) -> str:
        """Try to detect which provider a listing belongs to."""
        text = card.get_text(strip=True).lower()
        if "clúid" in text or "cluid" in text:
            return "Clúid Housing"
        if "lda" in text or "land development" in text:
            return "Land Development Agency"
        if "respond" in text:
            return "Respond Housing"
        if "tuath" in text:
            return "Tuath Housing"
        if "circle" in text:
            return "Circle VHA"
        return "Affordable Homes IE"

    def _text_fallback(self, soup) -> list[Listing]:
        """Parse raw text blocks matching the search snippet structure."""
        listings = []
        text = soup.get_text(separator="\n")
        # Match blocks: Name\nPrice from €X\nCategory\nStatus\n...
        blocks = re.split(r"\n{2,}", text)
        for block in blocks:
            if "Properties to Rent" not in block:
                continue
            lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
            if len(lines) < 3:
                continue
            try:
                name = lines[0]
                raw_status = next((ln for ln in lines if re.search(r"coming soon|open|closed", ln, re.I)), "unknown")
                location = next((ln for ln in lines if re.search(r"(dublin|co\.|county)", ln, re.I)), name)
                bedrooms_str = next((ln for ln in lines if re.search(r"\d+\s*bed|studio", ln, re.I)), "")
                bedrooms = re.findall(r"(\d+\s*[Bb]ed|[Ss]tudio)", bedrooms_str)
                price_match = re.search(r"€([\d,]+)", block)
                price_from = f"€{price_match.group(1)}" if price_match else None
                open_match = re.search(r"Applications Open\s+([\d/ :A-Za-z]+)", block)
                open_date = open_match.group(1).strip() if open_match else None
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
                listings.append(Listing(
                    id=self._make_id(slug),
                    provider="Affordable Homes IE",
                    name=name,
                    location=location,
                    county=self._county_from_location(location),
                    status=normalise_status(raw_status),
                    raw_status=raw_status,
                    bedrooms=bedrooms,
                    price_from=price_from,
                    applications_open=open_date,
                ))
            except Exception as e:
                logger.warning(f"affordablehomes text fallback error: {e}")
        return listings
