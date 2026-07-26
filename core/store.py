import json
import os
import subprocess
import logging
from typing import Optional
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
    data = {l.id: l.to_dict() for l in listings}
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Saved {len(listings)} listings for {provider}")


def commit_and_push(message: str = "state: update listings") -> None:
    """Commit updated data files and push to origin."""
    try:
        subprocess.run(["git", "add", DATA_DIR], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode == 0:
            logger.info("No state changes to commit")
            return
        subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        logger.info("State committed and pushed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
