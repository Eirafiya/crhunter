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
    """Compare old state to new listings and return list of meaningful changes."""
    changes = []

    for listing in new:
        if listing.id not in old:
            changes.append(Change(
                change_type="new",
                listing=listing,
            ))
            continue

        prev = old[listing.id]
        field_changes = {}

        # Status change
        if normalise_status(listing.raw_status or listing.status) != normalise_status(prev.raw_status or prev.status):
            old_status = normalise_status(prev.raw_status or prev.status)
            new_status = normalise_status(listing.raw_status or listing.status)
            if new_status == "open":
                changes.append(Change(change_type="opened", listing=listing, old_listing=prev))
            elif new_status == "closed" and old_status == "open":
                changes.append(Change(change_type="closed", listing=listing, old_listing=prev))
            field_changes["status"] = (prev.status, listing.status)

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

        # Generic content update (bedrooms, price, availability)
        elif field_changes and "status" not in field_changes:
            changes.append(Change(
                change_type="updated",
                listing=listing,
                old_listing=prev,
                diff=field_changes,
            ))

    return changes
