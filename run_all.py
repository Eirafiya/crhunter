#!/usr/bin/env python3
"""
CRHunter — property alert monitor
Scans configured providers, detects changes, sends email alerts.
"""
import argparse
import json
import logging
import time
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
from core.detector import normalise_status

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

SENT_LOG = os.path.join(os.path.dirname(__file__), "data", "sent_notifications.json")


def load_sent() -> set:
    """Load set of listing IDs already notified about."""
    if not os.path.exists(SENT_LOG):
        return set()
    with open(SENT_LOG) as f:
        return set(json.load(f))


def save_sent(sent: set) -> None:
    os.makedirs(os.path.dirname(SENT_LOG), exist_ok=True)
    with open(SENT_LOG, "w") as f:
        json.dump(sorted(sent), f, indent=2)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run(config_path: str) -> dict:
    config = load_config(config_path)
    providers_cfg = config.get("providers", {})
    notify_cfg = config.get("notifications", {})
    filters = config.get("filters", {})
    keywords = [k.lower() for k in filters.get("keywords", [])]

    sent_ids = load_sent()
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
        except Exception as exc:
            logger.error(f"{name}: scrape failed — {exc}")
            results[name] = {"error": str(exc), "listings": 0, "changes": 0}
            time.sleep(2)
            continue

        if not listings:
            logger.warning(f"{name}: returned 0 listings — possible scraper issue")

        # Prune closed listings from state — we don't need them anymore
        old_state = store.load(name)
        pruned = {lid: lst for lid, lst in old_state.items()
                  if normalise_status(lst.raw_status or lst.status) != "closed"}
        if len(pruned) < len(old_state):
            logger.info(f"{name}: pruned {len(old_state) - len(pruned)} closed listings from state")

        changes = detector.diff(pruned, listings)

        # Keyword match: also notify for open listings matching keywords not yet seen
        for listing in listings:
            status = normalise_status(listing.raw_status or listing.status)
            if status not in ("open", "coming_soon", "unknown"):
                continue
            haystack = f"{listing.name} {listing.location}".lower()
            if any(kw in haystack for kw in keywords):
                if not any(c.listing.id == listing.id for c in changes):
                    if listing.id not in old_state:
                        from core.detector import Change
                        changes.append(Change(change_type="new", listing=listing))

        # Deduplicate — skip any listing already notified about
        new_changes = [c for c in changes if c.listing.id not in sent_ids]
        skipped = len(changes) - len(new_changes)
        if skipped:
            logger.info(f"{name}: skipped {skipped} already-notified listings")

        emails_sent = 0
        if notify_cfg.get("email") and new_changes:
            emails_sent = notifier.send_batch(new_changes)
            # Record sent IDs
            for change in new_changes:
                sent_ids.add(change.listing.id)

        # Save only open/coming_soon/unknown listings — drop closed
        open_listings = [lst for lst in listings
                         if normalise_status(lst.raw_status or lst.status) != "closed"]
        store.save(name, open_listings)

        total_changes += len(new_changes)
        total_emails += emails_sent
        results[name] = {
            "listings": len(listings),
            "open": len(open_listings),
            "changes": len(new_changes),
            "emails_sent": emails_sent,
        }
        logger.info(
            f"{name}: {len(listings)} listings ({len(open_listings)} open), "
            f"{len(new_changes)} changes, {emails_sent} emails sent"
        )
        time.sleep(2)

    save_sent(sent_ids)
    logger.info(f"Scan complete: {total_changes} total changes, {total_emails} emails sent")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRHunter property monitor")
    parser.add_argument("--config", default="config.yml", help="Path to config file")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        logger.error(f"Config not found: {args.config}")
        sys.exit(1)

    run(args.config)
