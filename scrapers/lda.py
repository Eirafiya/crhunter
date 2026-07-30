import re
import logging
from urllib.parse import urljoin
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
            except Exception as exc:
                logger.warning(f"lda: failed to parse card: {exc}")

        logger.info(f"lda: found {len(listings)} listings")
        return listings

    def _parse(self, card) -> Listing | None:
        name_el = card.find(["h2", "h3"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name or len(name) < 5:
            return None

        # Check scheme-label div first (most reliable — LDA puts status here)
        raw_status = ""
        label_el = card.find(class_="scheme-label")
        if label_el:
            raw_status = label_el.get_text(strip=True)

        # Fallback: scan bold/strong/p for status keywords
        if not raw_status:
            for el in card.find_all(["strong", "b", "p", "em", "h3"]):
                text = el.get_text(strip=True)
                if re.search(r"application|closed|open", text, re.I):
                    raw_status = text
                    break

        if not raw_status:
            raw_status = "unknown"

        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))

        location = name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider="Land Development Agency",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=link,
        )
