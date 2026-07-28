import re
from urllib.parse import urljoin
import logging
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://lda.ie"


class LDAScraper(BaseProvider):
    name = "lda"
    url = f"{BASE}/affordable-homes/lda-cost-rental"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        for card in soup.select(".card, .scheme-card, article"):
            try:
                listing = self._parse(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"lda: failed to parse card: {e}")

        logger.info(f"lda: found {len(listings)} listings")
        return listings

    def _parse(self, card) -> Listing | None:
        name_el = card.find(["h2", "h3"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name or len(name) < 5:
            return None

        # Status is in bold/strong text — "APPLICATIONS NOW CLOSED" or similar
        status_text = ""
        for el in card.find_all(["strong", "p", "em"]):
            text = el.get_text(strip=True).upper()
            if "APPLICATION" in text or "CLOSED" in text or "OPEN" in text:
                status_text = el.get_text(strip=True)
                break
        if not status_text:
            status_text = "unknown"

        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))

        # Extract location from name (LDA includes location in the title)
        location = name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider="Land Development Agency",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(status_text),
            raw_status=status_text,
            apply_url=link,
        )
