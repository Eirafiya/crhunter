import pytest
import responses as responses_mock
from unittest.mock import patch, MagicMock
from core.models import Listing
from core.detector import Change
from core.notifier import _format_subject, _format_body, send


def make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test::slug",
        provider="Test Provider",
        name="Lightburn, Murphystown Way",
        location="Murphystown Way, Dublin 18",
        county="Dublin",
        status="open",
        raw_status="Applications Open",
        bedrooms=["1 Bed", "2 Bed"],
        price_from="€1,200",
        apply_url="https://example.ie/apply",
    )
    defaults.update(kwargs)
    return Listing(**defaults)


class TestFormatSubject:
    def test_new(self):
        c = Change(change_type="new", listing=make_listing())
        assert "New listing" in _format_subject(c)
        assert "Lightburn" in _format_subject(c)

    def test_opened(self):
        c = Change(change_type="opened", listing=make_listing())
        assert "Applications open" in _format_subject(c)

    def test_closed(self):
        c = Change(change_type="closed", listing=make_listing())
        assert "closed" in _format_subject(c).lower()

    def test_deadline_updated(self):
        c = Change(change_type="deadline_updated", listing=make_listing())
        assert "Deadline" in _format_subject(c)

    def test_updated(self):
        c = Change(change_type="updated", listing=make_listing())
        assert "updated" in _format_subject(c).lower()


class TestFormatBody:
    def test_contains_key_fields(self):
        c = Change(change_type="opened", listing=make_listing())
        body = _format_body(c)
        assert "Lightburn" in body
        assert "Test Provider" in body
        assert "1 Bed" in body
        assert "Apply now" in body

    def test_shows_diff_when_present(self):
        old = make_listing(applications_close="30 July")
        new = make_listing(applications_close="5 August")
        c = Change(
            change_type="deadline_updated",
            listing=new,
            old_listing=old,
            diff={"applications_close": ("30 July", "5 August")},
        )
        body = _format_body(c)
        assert "30 July" in body
        assert "5 August" in body


class TestSend:
    def test_returns_false_when_no_config(self):
        c = Change(change_type="new", listing=make_listing())
        with patch.dict("os.environ", {}, clear=True):
            result = send(c)
        assert result is False

    def test_sends_email_with_valid_config(self):
        c = Change(change_type="opened", listing=make_listing())
        mock_send = MagicMock(return_value={"id": "test-id"})
        with patch.dict("os.environ", {
            "RESEND_API_KEY": "re_test_key",
            "EMAIL_SENDER": "test@example.com",
            "EMAIL_RECIPIENT": "user@example.com",
        }):
            with patch("resend.Emails.send", mock_send):
                result = send(c)
        assert result is True
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[0][0]
        assert "Applications open" in call_kwargs["subject"]
        assert call_kwargs["to"] == ["user@example.com"]
