"""Tests for pjourney.errors — ErrorCode enum and app_error() helper."""
from unittest.mock import MagicMock

import pytest

from pjourney.errors import ERROR_TITLE, ErrorCode, _MESSAGES, app_error


# ---------------------------------------------------------------------------
# Sync unit tests
# ---------------------------------------------------------------------------

class TestErrorCode:
    def test_all_codes_have_pj_prefix(self):
        for code in ErrorCode:
            assert code.value.startswith("PJ-"), f"{code} missing PJ- prefix"

    def test_all_codes_have_messages(self):
        for code in ErrorCode:
            assert code in _MESSAGES, f"{code} missing from _MESSAGES"

    def test_values_are_unique(self):
        values = [c.value for c in ErrorCode]
        assert len(values) == len(set(values))

    def test_known_values(self):
        assert ErrorCode.DB_LOAD == "PJ-DB01"
        assert ErrorCode.DB_SAVE == "PJ-DB02"
        assert ErrorCode.DB_DELETE == "PJ-DB03"
        assert ErrorCode.DB_CONNECT == "PJ-DB04"
        assert ErrorCode.DB_VACUUM == "PJ-DB05"
        assert ErrorCode.IO_BACKUP == "PJ-IO01"
        assert ErrorCode.VAL_NUMBER == "PJ-VAL01"
        assert ErrorCode.VAL_DATE == "PJ-VAL02"
        assert ErrorCode.APP_UNEXPECTED == "PJ-APP01"


class TestAppError:
    def _make_widget(self):
        widget = MagicMock()
        widget.notify = MagicMock()
        return widget

    def test_calls_notify(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.DB_LOAD)
        widget.notify.assert_called_once()

    def test_title_is_error_title(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.DB_SAVE)
        _, kwargs = widget.notify.call_args
        assert kwargs["title"] == ERROR_TITLE

    def test_severity_is_error(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.DB_DELETE)
        _, kwargs = widget.notify.call_args
        assert kwargs["severity"] == "error"

    def test_timeout_is_12(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.DB_CONNECT)
        _, kwargs = widget.notify.call_args
        assert kwargs["timeout"] == 12

    def test_reference_code_in_message(self):
        for code in ErrorCode:
            widget = self._make_widget()
            app_error(widget, code)
            message = widget.notify.call_args[0][0]
            assert code.value in message, f"Code {code.value} not found in message"

    def test_detail_appended_to_message(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.VAL_NUMBER, detail="ISO must be a number.")
        message = widget.notify.call_args[0][0]
        assert "ISO must be a number." in message

    def test_no_detail_no_extra_space(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.DB_LOAD)
        message = widget.notify.call_args[0][0]
        # Should not have double spaces or leading space before \n\n
        assert "  \n" not in message

    def test_reference_section_format(self):
        widget = self._make_widget()
        app_error(widget, ErrorCode.IO_BACKUP)
        message = widget.notify.call_args[0][0]
        assert "\n\nReference: PJ-IO01" in message


# ---------------------------------------------------------------------------
# Async validation guard tests
# ---------------------------------------------------------------------------

from textual.app import App, ComposeResult
from textual.widgets import Label

from pjourney.db.models import User


class _ValidationTestApp(App):
    """Minimal host app for validation guard tests."""

    def __init__(self) -> None:
        super().__init__()
        self.current_user = User(id=1, username="test")
        self.captured_notifications: list[tuple[str, dict]] = []

    def compose(self) -> ComposeResult:
        yield Label("host")

    def notify(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self.captured_notifications.append((message, kwargs))
        super().notify(message, **kwargs)


@pytest.mark.asyncio
async def test_film_stock_iso_validation():
    """Entering non-numeric ISO keeps modal open and fires PJ-VAL01."""
    from pjourney.screens.film_stock import FilmStockFormModal

    app = _ValidationTestApp()
    async with app.run_test() as pilot:
        modal = FilmStockFormModal()
        await app.push_screen(modal)
        await pilot.pause()

        # Fill required name field and set bad ISO
        modal.query_one("#name").value = "Test Stock"
        modal.query_one("#iso").value = "abc"

        modal.query_one("#save-btn").press()
        await pilot.pause()

        # Modal should still be the active screen (not dismissed)
        assert app.screen is modal

        # PJ-VAL01 notification should have fired
        assert any("PJ-VAL01" in msg for msg, _ in app.captured_notifications)


@pytest.mark.asyncio
async def test_lens_aperture_validation():
    """Entering non-numeric aperture keeps modal open and fires PJ-VAL01."""
    from pjourney.screens.lenses import LensFormModal

    app = _ValidationTestApp()
    async with app.run_test() as pilot:
        modal = LensFormModal()
        await app.push_screen(modal)
        await pilot.pause()

        modal.query_one("#name").value = "Test Lens"
        modal.query_one("#max_aperture").value = "abc"

        modal.query_one("#save-btn").press()
        await pilot.pause()

        assert app.screen is modal
        assert any("PJ-VAL01" in msg for msg, _ in app.captured_notifications)
