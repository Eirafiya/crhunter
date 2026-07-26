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
        import time
        for attempt in range(3):
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 403 and attempt < 2:
                time.sleep(3 + attempt * 2)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")

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
