import re
import logging
from urllib.parse import urljoin
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
        seen_urls = set()

        # Parse only elements that have a /properties/ link — avoids Step1/2 and calculator
        for link_el in soup.find_all("a", href=re.compile(r"/properties/")):
            href = link_el["href"]
            full_url = href if href.startswith("http") else urljoin(BASE + "/", href.lstrip("/"))
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            try:
                listing = self._parse_from_link(soup, link_el, full_url)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.warning(f"respond: parse error: {exc}")

        logger.info(f"respond: found {len(listings)} listings")
        return listings

    def _parse_from_link(self, soup, link_el, full_url: str) -> Listing | None:
        card = link_el.find_parent(["div", "article", "section", "li"])
        if not card:
            return None

        name_el = card.find(["h3", "h2", "h4"])
        if not name_el:
            return None
        name = name_el.get_text(strip=True)
        if not name or len(name) < 3:
            return None
        # Skip non-property headings
        if re.match(r"^(Step\s*\d+|Overview)", name, re.I):
            return None

        raw_status = self._detect_status(soup, card)
        desc_el = card.find("p")
        location = desc_el.get_text(strip=True)[:80] if desc_el else name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]

        return Listing(
            id=self._make_id(slug),
            provider="Respond Housing",
            name=name,
            location=location,
            county=self._county_from_location(location or name),
            status=normalise_status(raw_status),
            raw_status=raw_status,
            apply_url=full_url,
        )

    def _detect_status(self, soup, card) -> str:
        """Walk backwards from the card to find the nearest section heading."""
        # Check card itself for status badge
        badge = card.find(class_=re.compile(r"status|badge|label", re.I))
        if badge:
            return badge.get_text(strip=True)

        # Find which named section this card falls under in the page
        # by looking at all headings in document order
        card_pos = None
        for i, el in enumerate(soup.find_all(True)):
            if el == card:
                card_pos = i
                break

        last_section = "unknown"
        if card_pos is not None:
            for el in soup.find_all(True)[:card_pos]:
                if el.name in ("h2", "h3"):
                    txt = el.get_text(strip=True).lower()
                    if "current listing" in txt:
                        last_section = "Applications Open"
                    elif "closed listing" in txt:
                        last_section = "Applications Closed"
                    elif "coming soon" in txt:
                        last_section = "Coming Soon"

        if last_section != "unknown":
            return last_section

        # Fallback: check card text
        text = card.get_text(separator=" ", strip=True).lower()
        if "apply today" in text or "applications open" in text:
            return "Applications Open"
        if "closed" in text:
            return "Applications Closed"
        return "unknown"
