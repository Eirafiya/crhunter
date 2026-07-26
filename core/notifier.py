import os
import logging
import resend
from core.detector import Change

logger = logging.getLogger(__name__)


def _format_subject(change: Change) -> str:
    name = change.listing.name
    if change.change_type == "new":
        return f"🏠 New listing — {name}"
    if change.change_type == "opened":
        return f"✅ Applications open — {name}"
    if change.change_type == "closed":
        return f"🔒 Applications closed — {name}"
    if change.change_type == "deadline_updated":
        return f"📅 Deadline updated — {name}"
    return f"🔔 Listing updated — {name}"


def _format_body(change: Change) -> str:
    listing = change.listing
    lines = [
        f"<h2>{listing.name}</h2>",
        f"<p><strong>Provider:</strong> {listing.provider}</p>",
        f"<p><strong>Location:</strong> {listing.location}</p>",
    ]

    if listing.bedrooms:
        lines.append(f"<p><strong>Bedrooms:</strong> {', '.join(listing.bedrooms)}</p>")
    if listing.price_from:
        lines.append(f"<p><strong>From:</strong> {listing.price_from}/month</p>")
    if listing.units_available:
        lines.append(f"<p><strong>Units:</strong> {listing.units_available}</p>")

    lines.append(f"<p><strong>Status:</strong> {listing.raw_status or listing.status}</p>")

    if listing.applications_open:
        lines.append(f"<p><strong>Opens:</strong> {listing.applications_open}</p>")
    if listing.applications_close:
        lines.append(f"<p><strong>Closes:</strong> {listing.applications_close}</p>")

    # Show what changed
    if change.old_listing and change.diff:
        lines.append("<hr><h3>What changed</h3><ul>")
        for field, (old_val, new_val) in change.diff.items():
            lines.append(f"<li><strong>{field}:</strong> {old_val} → {new_val}</li>")
        lines.append("</ul>")

    if listing.apply_url:
        lines.append(f'<p><a href="{listing.apply_url}">Apply now →</a></p>')

    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines.append(f"<p><small>Detected: {ts}</small></p>")

    return "\n".join(lines)


def send(change: Change) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("EMAIL_SENDER", "alerts@crhunter.io")
    recipient = os.environ.get("EMAIL_RECIPIENT")

    if not api_key or not recipient:
        logger.warning("Email not configured — skipping notification")
        return False

    resend.api_key = api_key

    try:
        resend.Emails.send({
            "from": sender,
            "to": [recipient],
            "subject": _format_subject(change),
            "html": _format_body(change),
        })
        logger.info(f"Email sent: {_format_subject(change)}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_batch(changes: list[Change]) -> int:
    """Send emails for a list of changes. Returns count sent."""
    sent = 0
    for change in changes:
        if send(change):
            sent += 1
    return sent
