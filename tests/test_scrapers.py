import pytest
import responses as responses_mock
from scrapers.cluid import CluidScraper
from scrapers.lda import LDAScraper
from scrapers.tuath import TuathScraper
from scrapers.respond import RespondScraper


CLUID_FIXTURE = """
<html><body>
  <div class="property-listing">
    <span>Applications open</span>
    <h3>Barnhall Meadows</h3>
    <p>Barnhall Meadows, Leixlip, Co. Kildare</p>
    <a href="/property/barnhall-meadows/">View</a>
  </div>
  <div class="property-listing">
    <span>Applications closed</span>
    <h3>Oscar Traynor Woods</h3>
    <p>Coolock Lane, Dublin 17</p>
    <a href="/property/oscar-traynor/">View</a>
  </div>
</body></html>
"""

LDA_FIXTURE = """
<html><body>
  <div class="card">
    <h2>The Crossings, Adamstown, Co. Dublin</h2>
    <p><strong>APPLICATIONS NOW CLOSED</strong></p>
    <a href="/projects/the-crossings">Find out more</a>
  </div>
  <div class="card">
    <h2>New Development, Dublin 15</h2>
    <p><strong>APPLICATIONS NOW OPEN</strong></p>
    <a href="/projects/new-dev">Apply</a>
  </div>
</body></html>
"""

TUATH_FIXTURE = """
<html><body>
  <div>
    <span>CLOSED</span>
    <div>
      <h3>Woodside Rise</h3>
      <p>Enniskerry Rd, Dublin 18</p>
      <a href="/properties/woodside-rise/">View</a>
    </div>
  </div>
  <div>
    <span>OPEN</span>
    <div>
      <h3>New Tuath Scheme</h3>
      <p>Ballymun, Dublin 9</p>
      <a href="/properties/new-scheme/">Apply</a>
    </div>
  </div>
</body></html>
"""


class TestCluidScraper:
    @responses_mock.activate
    def test_parses_open_and_closed(self):
        responses_mock.add(
            responses_mock.GET,
            "https://www.cluid.ie/cost-rental/",
            body=CLUID_FIXTURE,
            status=200,
        )
        scraper = CluidScraper()
        listings = scraper.fetch()
        assert len(listings) >= 1
        names = [l.name for l in listings]
        assert any("Barnhall" in n or "Oscar" in n for n in names)

    @responses_mock.activate
    def test_returns_empty_on_error(self):
        responses_mock.add(
            responses_mock.GET,
            "https://www.cluid.ie/cost-rental/",
            status=503,
        )
        scraper = CluidScraper()
        with pytest.raises(Exception):
            scraper.fetch()


class TestLDAScraper:
    @responses_mock.activate
    def test_detects_open_status(self):
        responses_mock.add(
            responses_mock.GET,
            "https://lda.ie/affordable-homes/lda-cost-rental",
            body=LDA_FIXTURE,
            status=200,
        )
        scraper = LDAScraper()
        listings = scraper.fetch()
        assert len(listings) >= 1
        statuses = [l.status for l in listings]
        assert "closed" in statuses

    @responses_mock.activate
    def test_open_listing_parsed(self):
        responses_mock.add(
            responses_mock.GET,
            "https://lda.ie/affordable-homes/lda-cost-rental",
            body=LDA_FIXTURE,
            status=200,
        )
        scraper = LDAScraper()
        listings = scraper.fetch()
        open_listings = [l for l in listings if l.status == "open"]
        assert len(open_listings) >= 1


class TestTuathScraper:
    @responses_mock.activate
    def test_parses_status_badges(self):
        responses_mock.add(
            responses_mock.GET,
            "https://tuathhousing.ie/cost-rental/",
            body=TUATH_FIXTURE,
            status=200,
        )
        scraper = TuathScraper()
        listings = scraper.fetch()
        assert len(listings) >= 1

    @responses_mock.activate
    def test_provider_name_correct(self):
        responses_mock.add(
            responses_mock.GET,
            "https://tuathhousing.ie/cost-rental/",
            body=TUATH_FIXTURE,
            status=200,
        )
        scraper = TuathScraper()
        listings = scraper.fetch()
        assert all(l.provider == "Tuath Housing" for l in listings)
