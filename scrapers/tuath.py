import re
import logging
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://tuathhousing.ie"


class TuathScraper(BaseProvider):
    name = "tuath"
    url = f"{BASE}/cost-rental/"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        # Tuath: thumbnail cards with status badge (CLOSED / OPEN) + h3 name + location
        for card in soup.select(".property-card, .scheme-card, .listing"):
            try:
                listing = self._parse(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"tuath: failed to parse card: {e}")

        if not listings:
            listings = self._fallback_parse(soup)

        logger.info(f"tuath: found {len(listings)} listings")
        return listings

    def _fallback_parse(self, soup) -> list[Listing]:
        listings = []
        # Find all status badges: CLOSED, OPEN, DÚNTA / CLOSED
        for badge in soup.find_all(string=re.compile(r"^(CLOSED|OPEN|DÚNTA)", re.I)):
            try:
                raw_status = badge.strip()
                container = badge.find_parent()
                card = container.find_parent(["div", "article"]) if container else None
                if not card:
                    continue
                name_el = card.find(["h3", "h2"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                location_el = name_el.find_next_sibling(["p", "span"]) or card.find("p")
                location = location_el.get_text(strip=True) if location_el else name
                link_el = card.find("a", href=True)
                link = None
                if link_el:
                    href = link_el["href"]
                    link = href if href.startswith("http") else BASE + href
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
                listings.append(Listing(
                    id=self._make_id(slug),
                    provider="Tuath Housing",
                    name=name,
                    location=location,
                    county=self._county_from_location(location),
                    status=normalise_status(raw_status),
                    raw_status=raw_status,
                    apply_url=link,
                ))
            except Exception as e:
                logger.warning(f"tuath fallback parse error: {e}")
        return listings

    def _parse(self, card) -> Listing | None:
        name_el = card.find(["h3", "h2"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        status_el = card.find(class_=re.compile(r"status|badge|tag", re.I))
        raw_status = status_el.get_text(strip=True) if status_el else "unknown"
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
            provider="Tuath Housing",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=link,
        )
