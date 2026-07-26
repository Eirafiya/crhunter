import re
import logging
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://www.respond.ie"


class RespondScraper(BaseProvider):
    name = "respond"
    url = f"{BASE}/cost-rental/"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        # "Current Listings" section — open applications at top
        for card in soup.select(".listing-card, .property-card, .scheme"):
            try:
                listing = self._parse(card, status_hint="open")
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"respond: failed to parse card: {e}")

        # Fallback: find headings under "Current Listings" and "Closed Listings"
        if not listings:
            listings = self._fallback_parse(soup)

        logger.info(f"respond: found {len(listings)} listings")
        return listings

    def _fallback_parse(self, soup) -> list[Listing]:
        listings = []
        current_status = "unknown"

        for el in soup.find_all(["h2", "h3", "h4", "div"]):
            text = el.get_text(strip=True)
            if re.search(r"current listings", text, re.I):
                current_status = "open"
                continue
            if re.search(r"closed listings|coming soon", text, re.I):
                current_status = "closed"
                continue

            # Look for listing headings with a sibling link
            if el.name in ("h3", "h4") and len(text) > 5:
                link_el = el.find_next("a", href=True)
                location_el = el.find_next("p")
                link = None
                if link_el:
                    href = link_el["href"]
                    link = href if href.startswith("http") else BASE + href
                location = location_el.get_text(strip=True) if location_el else text
                slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]

                listings.append(Listing(
                    id=self._make_id(slug),
                    provider="Respond Housing",
                    name=text,
                    location=location,
                    county=self._county_from_location(location),
                    status=current_status,
                    raw_status=current_status,
                    apply_url=link,
                ))
        return listings

    def _parse(self, card, status_hint="unknown") -> Listing | None:
        name_el = card.find(["h3", "h2", "h4"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None

        status_el = card.find(class_=re.compile(r"status|badge", re.I))
        raw_status = status_el.get_text(strip=True) if status_el else status_hint
        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = href if href.startswith("http") else BASE + href
        location_el = card.find("p")
        location = location_el.get_text(strip=True) if location_el else name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider="Respond Housing",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=link,
        )
