from dataclasses import dataclass
from typing import Optional
from core.models import Listing


@dataclass
class Change:
    change_type: str        # new | opened | closed | updated | deadline_updated
    listing: Listing
    old_listing: Optional[Listing] = None
    diff: Optional[dict] = None


STATUS_OPEN = {"open", "applications open", "apply now", "accepting applications"}
STATUS_CLOSED = {"closed", "applications closed", "now closed"}
STATUS_COMING = {"coming soon", "register interest"}


def normalise_status(raw: str) -> str:
    s = raw.lower().strip().strip("*").strip()
    if any(k in s for k in STATUS_OPEN):
        return "open"
    if any(k in s for k in STATUS_CLOSED):
        return "closed"
    if any(k in s for k in STATUS_COMING):
        return "coming_soon"
    return "unknown"


def diff(
    old: dict[str, Listing],
    new: list[Listing]
) -> list[Change]:
    """Compare old state to new listings and return list of meaningful changes.

    Only emits changes worth notifying about:
    - New listing that is open or coming soon (not closed)
    - Status changed TO open
    - Deadline or bedroom update on an open listing
    """
    changes = []

    for listing in new:
        status = normalise_status(listing.raw_status or listing.status)

        if listing.id not in old:
            # Only notify for new listings that are open, coming soon, or unknown status
            if status in ("open", "coming_soon", "unknown"):
                changes.append(Change(change_type="new", listing=listing))
            continue

        prev = old[listing.id]
        prev_status = normalise_status(prev.raw_status or prev.status)
        field_changes = {}

        # Status change — only notify when transitioning TO open
        if status != prev_status:
            if status == "open":
                changes.append(Change(change_type="opened", listing=listing, old_listing=prev))
            field_changes["status"] = (prev.status, listing.status)

        # Only track field changes on open listings
        if status == "open":
            # Bedroom change
            if sorted(listing.bedrooms) != sorted(prev.bedrooms) and listing.bedrooms:
                field_changes["bedrooms"] = (prev.bedrooms, listing.bedrooms)

            # Deadline change
            if listing.applications_close and listing.applications_close != prev.applications_close:
                field_changes["applications_close"] = (prev.applications_close, listing.applications_close)
                changes.append(Change(
                    change_type="deadline_updated",
                    listing=listing,
                    old_listing=prev,
                    diff=field_changes,
                ))

            # Generic content update (bedrooms, price) — not status
            elif field_changes and "status" not in field_changes:
                changes.append(Change(
                    change_type="updated",
                    listing=listing,
                    old_listing=prev,
                    diff=field_changes,
                ))

    return changes
