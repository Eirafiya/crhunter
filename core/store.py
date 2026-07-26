import json
import os
import logging

from core.models import Listing

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load(provider: str) -> dict[str, Listing]:
    """Load previous state for a provider. Returns dict keyed by listing id."""
    path = os.path.join(DATA_DIR, f"{provider}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            raw = json.load(f)
        return {k: Listing.from_dict(v) for k, v in raw.items()}
    except Exception as e:
        logger.error(f"Failed to load state for {provider}: {e}")
        return {}


def save(provider: str, listings: list[Listing]) -> None:
    """Save current state for a provider."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{provider}.json")
    data = {listing.id: listing.to_dict() for listing in listings}
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Saved {len(listings)} listings for {provider}")


def commit_and_push(message: str = "state: update listings") -> None:
    """No-op when run inside CI — the calling workflow handles git state."""
    logger.info(f"State save complete ({message}) — git commit handled by workflow")
