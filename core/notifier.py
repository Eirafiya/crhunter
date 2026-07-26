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
    l = change.listing
    lines = [
        f"<h2>{l.name}</h2>",
        f"<p><strong>Provider:</strong> {l.provider}</p>",
        f"<p><strong>Location:</strong> {l.location}</p>",
    ]

    if l.bedrooms:
        lines.append(f"<p><strong>Bedrooms:</strong> {', '.join(l.bedrooms)}</p>")
    if l.price_from:
        lines.append(f"<p><strong>From:</strong> {l.price_from}/month</p>")
    if l.units_available:
        lines.append(f"<p><strong>Units:</strong> {l.units_available}</p>")

    lines.append(f"<p><strong>Status:</strong> {l.raw_status or l.status}</p>")

    if l.applications_open:
        lines.append(f"<p><strong>Opens:</strong> {l.applications_open}</p>")
    if l.applications_close:
        lines.append(f"<p><strong>Closes:</strong> {l.applications_close}</p>")

    # Show what changed
    if change.old_listing and change.diff:
        lines.append("<hr><h3>What changed</h3><ul>")
        for field, (old_val, new_val) in change.diff.items():
            lines.append(f"<li><strong>{field}:</strong> {old_val} → {new_val}</li>")
        lines.append("</ul>")

    if l.apply_url:
        lines.append(f'<p><a href="{l.apply_url}">Apply now →</a></p>')

    import datetime
    lines.append(f"<p><small>Detected: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</small></p>")

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
