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
    Cards are <article class="property open|soon|closed">.
    """
    name = "affordablehomes"
    url = f"{BASE}/rent/"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        for article in soup.select("article.property"):
            try:
                listing = self._parse(article)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.warning(f"affordablehomes: parse error: {exc}")

        logger.info(f"affordablehomes: found {len(listings)} listings")
        return listings

    def _parse(self, article) -> Listing | None:
        # Name
        name_el = article.find("h3")
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        # Status — from <p class="status"> text and article CSS class
        status_el = article.find("p", class_="status")
        raw_status = status_el.get_text(strip=True) if status_el else ""
        # Also use CSS class as fallback: open / soon / closed
        if not raw_status:
            css = article.get("class", [])
            if "open" in css:
                raw_status = "Applications Open"
            elif "soon" in css:
                raw_status = "Coming Soon"
            elif "closed" in css:
                raw_status = "Applications Closed"

        # Location
        location_el = article.select_one("p.location span, p.location")
        location = location_el.get_text(strip=True) if location_el else ""

        # Price
        price_el = article.find("p", class_="price")
        price_from = price_el.get_text(strip=True) if price_el else None

        # Apply URL — from <a class="button"> or <h3><a>
        link = None
        link_el = article.select_one("a.button, h3 a")
        if link_el:
            href = link_el.get("href", "")
            link = href if href.startswith("http") else urljoin(self.url, href)

        # Listed date

        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider="Affordable Homes IE",
            name=name,
            location=location or name,
            county=self._county_from_location(location or name),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            price_from=price_from,
            apply_url=link,
        )
