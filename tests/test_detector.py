from core.models import Listing
from core.detector import diff, normalise_status


def make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test::slug",
        provider="Test",
        name="Test Development",
        location="Dublin 18",
        county="Dublin",
        status="closed",
        raw_status="Applications closed",
    )
    defaults.update(kwargs)
    return Listing(**defaults)


class TestNormaliseStatus:
    def test_open_variants(self):
        assert normalise_status("Applications Open") == "open"
        assert normalise_status("APPLICATIONS OPEN") == "open"
        assert normalise_status("Apply Now") == "open"
        assert normalise_status("Accepting Applications") == "open"

    def test_closed_variants(self):
        assert normalise_status("Applications Closed") == "closed"
        assert normalise_status("APPLICATIONS NOW CLOSED") == "closed"
        assert normalise_status("***APPLICATIONS NOW CLOSED***") == "closed"
        assert normalise_status("CLOSED") == "closed"

    def test_coming_soon(self):
        assert normalise_status("Coming Soon") == "coming_soon"
        assert normalise_status("Register Interest") == "coming_soon"

    def test_unknown(self):
        assert normalise_status("") == "unknown"
        assert normalise_status("Some random text") == "unknown"


class TestDiff:
    def test_new_listing_detected(self):
        new = [make_listing(id="p::new-dev", name="New Development")]
        changes = diff({}, new)
        assert len(changes) == 1
        assert changes[0].change_type == "new"
        assert changes[0].listing.name == "New Development"

    def test_no_change(self):
        listing = make_listing()
        old = {listing.id: listing}
        changes = diff(old, [listing])
        assert changes == []

    def test_status_opened(self):
        old_listing = make_listing(status="closed", raw_status="Applications Closed")
        new_listing = make_listing(status="open", raw_status="Applications Open")
        changes = diff({old_listing.id: old_listing}, [new_listing])
        assert any(c.change_type == "opened" for c in changes)

    def test_status_closed(self):
        old_listing = make_listing(status="open", raw_status="Applications Open")
        new_listing = make_listing(status="closed", raw_status="Applications Closed")
        changes = diff({old_listing.id: old_listing}, [new_listing])
        assert any(c.change_type == "closed" for c in changes)

    def test_deadline_updated(self):
        old_listing = make_listing(applications_close="30 July 2026")
        new_listing = make_listing(applications_close="5 August 2026")
        changes = diff({old_listing.id: old_listing}, [new_listing])
        assert any(c.change_type == "deadline_updated" for c in changes)

    def test_bedroom_update(self):
        old_listing = make_listing(bedrooms=["1 Bed"])
        new_listing = make_listing(bedrooms=["1 Bed", "2 Bed"])
        changes = diff({old_listing.id: old_listing}, [new_listing])
        assert any(c.change_type == "updated" for c in changes)

    def test_multiple_new_listings(self):
        listings = [
            make_listing(id=f"p::dev-{i}", name=f"Dev {i}")
            for i in range(5)
        ]
        changes = diff({}, listings)
        assert len(changes) == 5
        assert all(c.change_type == "new" for c in changes)

    def test_mixed_changes(self):
        existing = make_listing(id="p::existing", status="closed", raw_status="Closed")
        new_dev = make_listing(id="p::brand-new", name="Brand New")
        updated = make_listing(id="p::existing", status="open", raw_status="Applications Open")
        old_state = {existing.id: existing}
        changes = diff(old_state, [updated, new_dev])
        change_types = {c.change_type for c in changes}
        assert "new" in change_types
        assert "opened" in change_types
