import re
from urllib.parse import urljoin
import logging
from scrapers.base import BaseProvider
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

BASE = "https://www.cluid.ie"


class CluidScraper(BaseProvider):
    name = "cluid"
    url = f"{BASE}/cost-rental/"

    def fetch(self) -> list[Listing]:
        soup = self._get(self.url)
        listings = []

        for article in soup.select(".property-listing, article.listing, .listing-item"):
            try:
                listings.append(self._parse(article))
            except Exception as exc:
                logger.warning(f"cluid: failed to parse listing: {exc}")

        if not listings:
            listings = self._fallback_parse(soup)

        logger.info(f"cluid: found {len(listings)} listings")
        return listings

    def _fallback_parse(self, soup) -> list[Listing]:
        listings = []
        for section in soup.find_all(string=re.compile(r"Applications (open|closed)", re.I)):
            try:
                container = section.find_parent()
                if not container:
                    continue
                card = container.find_parent(["div", "article", "section"])
                if not card:
                    continue
                raw_status = section.strip()
                name_el = card.find(["h3", "h2"])
                name = name_el.get_text(strip=True) if name_el else "Unknown"
                link_el = card.find("a", href=True)
                link = None
                if link_el:
                    href = link_el["href"]
                    link = urljoin(BASE + "/", href.lstrip("/")) if not href.startswith("http") else href
                location = ""
                if name_el:
                    sib = name_el.find_next_sibling(["p", "span"])
                    if sib:
                        location = sib.get_text(strip=True)
                if not location:
                    location = name
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                listings.append(Listing(
                    id=self._make_id(slug),
                    provider="Clúid Housing",
                    name=name,
                    location=location,
                    county=self._county_from_location(location),
                    status=normalise_status(raw_status),
                    raw_status=raw_status,
                    apply_url=link,
                ))
            except Exception as exc:
                logger.warning(f"cluid fallback parse error: {exc}")
        return listings

    def _parse(self, card) -> Listing:
        name_el = card.find(["h3", "h2"])
        name = name_el.get_text(strip=True) if name_el else "Unknown"
        status_el = card.find(class_=re.compile(r"status|badge", re.I))
        raw_status = status_el.get_text(strip=True) if status_el else "unknown"
        link_el = card.find("a", href=True)
        link = None
        if link_el:
            href = link_el["href"]
            link = urljoin(BASE + "/", href.lstrip("/")) if not href.startswith("http") else href
        location_el = card.find("p")
        location = location_el.get_text(strip=True) if location_el else name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return Listing(
            id=self._make_id(slug),
            provider="Clúid Housing",
            name=name,
            location=location,
            county=self._county_from_location(location),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=link,
        )
