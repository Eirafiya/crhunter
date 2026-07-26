#!/usr/bin/env python3
"""
CRHunter — property alert monitor
Scans configured providers, detects changes, sends email alerts.
"""
import argparse
import logging
import os
import sys
import yaml

from scrapers.affordablehomes import AffordableHomesScraper
from scrapers.cluid import CluidScraper
from scrapers.lda import LDAScraper
from scrapers.respond import RespondScraper
from scrapers.tuath import TuathScraper
from scrapers.circle_vha import CircleVHAScraper
from core import store, detector, notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crhunter")

SCRAPERS = {
    "affordablehomes": AffordableHomesScraper,
    "cluid": CluidScraper,
    "lda": LDAScraper,
    "respond": RespondScraper,
    "tuath": TuathScraper,
    "circle_vha": CircleVHAScraper,
}


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def matches_filters(listing, filters: dict) -> bool:
    """Return True if listing passes user-configured filters."""
    counties = [c.lower() for c in filters.get("counties", [])]
    if counties and listing.county.lower() not in counties:
        return False

    bedrooms = [str(b) for b in filters.get("bedrooms", [])]
    if bedrooms and listing.bedrooms:
        if not any(str(b) in " ".join(listing.bedrooms) for b in bedrooms):
            return False

    keywords = [k.lower() for k in filters.get("keywords", [])]
    if keywords:
        # Keywords are OR — match if any keyword present, or if no keywords configured
        # Always pass through if no keywords set
        pass  # keywords are additive alerts, not filters — notify on keywords too

    return True


def run(config_path: str) -> dict:
    config = load_config(config_path)
    filters = config.get("filters", {})
    providers_cfg = config.get("providers", {})
    notify_cfg = config.get("notifications", {})

    total_changes = 0
    total_emails = 0
    results = {}

    for name, ScraperClass in SCRAPERS.items():
        if not providers_cfg.get(name, True):
            logger.info(f"Skipping {name} (disabled in config)")
            continue

        logger.info(f"Scanning {name}...")
        scraper = ScraperClass()

        try:
            listings = scraper.fetch()
        except Exception as e:
            logger.error(f"{name}: scrape failed — {e}")
            results[name] = {"error": str(e), "listings": 0, "changes": 0}
            continue

        if not listings:
            logger.warning(f"{name}: returned 0 listings — possible scraper issue")

        old_state = store.load(name)
        changes = detector.diff(old_state, listings)

        # Apply keyword-based extra notifications
        keyword_changes = _keyword_matches(listings, filters.get("keywords", []), old_state)
        all_changes = changes + [c for c in keyword_changes if c not in changes]

        emails_sent = 0
        if notify_cfg.get("email") and all_changes:
            emails_sent = notifier.send_batch(all_changes)

        store.save(name, listings)

        total_changes += len(all_changes)
        total_emails += emails_sent
        results[name] = {
            "listings": len(listings),
            "changes": len(all_changes),
            "emails_sent": emails_sent,
        }
        logger.info(f"{name}: {len(listings)} listings, {len(all_changes)} changes, {emails_sent} emails sent")

    store.commit_and_push(f"state: scan complete — {total_changes} changes detected")
    logger.info(f"Scan complete: {total_changes} total changes, {total_emails} emails sent")
    return results


def _keyword_matches(listings, keywords: list[str], old_state: dict):
    """Generate extra change objects for listings matching user keywords."""
    from core.detector import Change
    matches = []
    for listing in listings:
        haystack = f"{listing.name} {listing.location}".lower()
        for kw in keywords:
            if kw.lower() in haystack and listing.id not in old_state:
                matches.append(Change(change_type="new", listing=listing))
                break
    return matches


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRHunter property monitor")
    parser.add_argument("--config", default="config.yml", help="Path to config file")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        logger.error(f"Config not found: {args.config}")
        sys.exit(1)

    run(args.config)
