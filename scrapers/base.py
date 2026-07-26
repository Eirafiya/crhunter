import logging
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from core.detector import normalise_status

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IE,en;q=0.9",
}


class BaseProvider:
    name: str = ""
    url: str = ""

    def fetch(self) -> list[Listing]:
        raise NotImplementedError

    def _get(self, url: str) -> BeautifulSoup:
        resp = requests.get(url, headers=HEADERS, timeout=20)
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
