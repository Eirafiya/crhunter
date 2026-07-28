import re
from urllib.parse import urljoin
import logging
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://circlevha.ie"


class CircleVHAScraper(BaseProvider):
    name = "circle_vha"
    url = f"{BASE}/cost-rental/"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        for card in soup.select(".scheme, .property-card, article"):
            try:
                listing = self._parse(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"circle_vha: failed to parse card: {e}")

        if not listings:
            listings = self._fallback_parse(soup)

        logger.info(f"circle_vha: found {len(listings)} listings")
        return listings

    def _fallback_parse(self, soup) -> list[Listing]:
        listings = []
        for badge in soup.find_all(string=re.compile(r"(open|closed) for applications", re.I)):
            try:
                raw_status = badge.strip()
                container = badge.find_parent()
                card = container.find_parent(["div", "article"]) if container else None
                if not card:
                    continue
                name_el = card.find(["h2", "h3"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                desc_el = card.find("p")
                location = desc_el.get_text(strip=True)[:80] if desc_el else name
                link_el = card.find("a", href=True)
                link = None
                if link_el:
                    href = link_el["href"]
                    link = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
                listings.append(Listing(
                    id=self._make_id(slug),
                    provider="Circle VHA",
                    name=name,
                    location=location,
                    county=self._county_from_location(location),
                    status=normalise_status(raw_status),
                    raw_status=raw_status,
                    apply_url=link,
                ))
            except Exception as e:
                logger.warning(f"circle_vha fallback error: {e}")
        return listings

    def _parse(self, card) -> Listing | None:
        name_el = card.find(["h3", "h2"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name:
            return None
        status_el = card.find(class_=re.compile(r"status|badge", re.I))
        raw_status = status_el.get_text(strip=True) if status_el else "unknown"
        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))
        location_el = card.find("p")
        location = location_el.get_text(strip=True)[:80] if location_el else name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
        return Listing(
            id=self._make_id(slug),
            provider="Circle VHA",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=link,
        )
