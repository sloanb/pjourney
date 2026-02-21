"""Tests for FilmStockFormModal.

Covers the modal compose, on_mount analog-field visibility,
media-type toggle, save paths (analog, digital, empty-name guard,
invalid-number error path), and cancel.
"""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label, Select

from pjourney.db import database as db
from pjourney.db.models import FilmStock, User
from pjourney.screens.film_stock import FilmStockFormModal


# ---------------------------------------------------------------------------
# Minimal host app
# ---------------------------------------------------------------------------

class FilmStockFormTestApp(App):
    """Minimal host that carries current_user and can push FilmStockFormModal."""

    def __init__(self, stock: FilmStock | None = None) -> None:
        super().__init__()
        self._stock = stock
        self.dismissed_stock: FilmStock | None = None
        self.dismissed_called: bool = False
        self.current_user = User(id=1, username="test")

    def compose(self) -> ComposeResult:
        yield Label("host")

    async def show_form(self) -> None:
        def on_dismiss(stock: FilmStock | None) -> None:
            self.dismissed_called = True
            self.dismissed_stock = stock

        await self.push_screen(FilmStockFormModal(self._stock), on_dismiss)


# ---------------------------------------------------------------------------
# TestFilmStockFormModalOpens
# ---------------------------------------------------------------------------

class TestFilmStockFormModalOpens:
    """Verify the modal renders without crashing for all stock configurations."""

    async def test_new_stock_form_does_not_crash(self):
        """Opening add-stock form (no existing stock) must not raise."""
        app = FilmStockFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_analog_stock_form_does_not_crash(self):
        """Editing an existing analog stock must not raise."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="Portra 400",
            media_type="analog", type="color", iso=400,
            format="35mm", frames_per_roll=36, quantity_on_hand=3,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_digital_stock_form_does_not_crash(self):
        """Editing a digital stock must not raise.

        Digital stocks store format="35mm" (the model default) since the
        #format Select widget validates its initial value at mount time.
        """
        stock = FilmStock(
            id=2, user_id=1, brand="SanDisk", name="Primary Card",
            media_type="digital", type="color", iso=0,
            format="35mm", frames_per_roll=0, quantity_on_hand=0,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running


# ---------------------------------------------------------------------------
# TestFilmStockFormModalAnalogFieldVisibility
# ---------------------------------------------------------------------------

class TestFilmStockFormModalAnalogFieldVisibility:
    """Verify analog-fields section shows/hides based on media type."""

    async def test_analog_stock_shows_analog_fields_on_mount(self):
        """Analog stock: #analog-fields must be visible after mount."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="Portra 400",
            media_type="analog",
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            analog_fields = app.screen.query_one("#analog-fields")
            assert bool(analog_fields.display) is True

    async def test_digital_stock_hides_analog_fields_on_mount(self):
        """Digital stock: #analog-fields must be hidden after mount."""
        stock = FilmStock(
            id=2, user_id=1, brand="SanDisk", name="Primary Card",
            media_type="digital",
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            analog_fields = app.screen.query_one("#analog-fields")
            assert bool(analog_fields.display) is False

    async def test_new_stock_shows_analog_fields_by_default(self):
        """New stock defaults to analog media_type, so analog-fields should be visible."""
        app = FilmStockFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            analog_fields = app.screen.query_one("#analog-fields")
            # FilmStock() defaults media_type to "analog"
            assert bool(analog_fields.display) is True

    async def test_media_type_change_to_digital_hides_analog_fields(self):
        """Changing media type Select to 'digital' must hide #analog-fields."""
        app = FilmStockFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            media_select = app.screen.query_one("#media_type", Select)
            media_select.value = "digital"
            await pilot.pause()
            analog_fields = app.screen.query_one("#analog-fields")
            assert bool(analog_fields.display) is False

    async def test_media_type_change_to_analog_shows_analog_fields(self):
        """Changing from digital back to analog must re-show #analog-fields."""
        stock = FilmStock(id=2, user_id=1, brand="SanDisk", name="Card", media_type="digital")
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            media_select = app.screen.query_one("#media_type", Select)
            media_select.value = "analog"
            await pilot.pause()
            analog_fields = app.screen.query_one("#analog-fields")
            assert bool(analog_fields.display) is True


# ---------------------------------------------------------------------------
# TestFilmStockFormModalSave
# ---------------------------------------------------------------------------

class TestFilmStockFormModalSave:
    """Verify the save paths for analog stock, digital stock, and guard conditions."""

    async def test_cancel_dismisses_none(self):
        """Cancel must dismiss with None."""
        app = FilmStockFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_stock is None

    async def test_save_analog_stock_dismisses_with_stock(self):
        """Saving an analog stock with a name must dismiss with a FilmStock."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="Portra 400",
            media_type="analog", type="color", iso=400,
            format="35mm", frames_per_roll=36, quantity_on_hand=3,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_stock is not None
        assert app.dismissed_stock.name == "Portra 400"
        assert app.dismissed_stock.media_type == "analog"

    async def test_save_analog_stock_preserves_iso_and_format(self):
        """Analog stock save must preserve ISO, format, and frames_per_roll."""
        stock = FilmStock(
            id=1, user_id=1, brand="Ilford", name="HP5 Plus",
            media_type="analog", type="black_and_white", iso=400,
            format="120", frames_per_roll=12, quantity_on_hand=5,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_stock is not None
        assert app.dismissed_stock.iso == 400
        assert app.dismissed_stock.format == "120"
        assert app.dismissed_stock.frames_per_roll == 12

    async def test_save_digital_stock_zeros_analog_fields(self):
        """Saving a digital stock must set iso=0, frames_per_roll=0, quantity=0, format='35mm'."""
        stock = FilmStock(
            id=2, user_id=1, brand="SanDisk", name="Primary Card",
            media_type="digital",
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_stock is not None
        assert app.dismissed_stock.media_type == "digital"
        assert app.dismissed_stock.iso == 0
        assert app.dismissed_stock.frames_per_roll == 0
        assert app.dismissed_stock.quantity_on_hand == 0
        assert app.dismissed_stock.format == "35mm"
        assert app.dismissed_stock.type == "color"

    async def test_save_with_empty_name_does_not_dismiss(self):
        """Saving with an empty name must not dismiss the modal."""
        app = FilmStockFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#name", Input).value = ""
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert not app.dismissed_called

    async def test_save_with_invalid_iso_does_not_dismiss(self):
        """Saving with a non-numeric ISO must trigger app_error and not dismiss."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="Portra 400",
            media_type="analog",
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#iso", Input).value = "not-a-number"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert not app.dismissed_called

    async def test_save_with_empty_iso_defaults_to_400(self):
        """Empty ISO field should default to 400, not raise ValueError."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="Tri-X 400",
            media_type="analog", type="black_and_white", iso=400,
            format="35mm", frames_per_roll=36, quantity_on_hand=1,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#iso", Input).value = ""
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_stock is not None
        assert app.dismissed_stock.iso == 400

    async def test_save_with_empty_frames_per_roll_defaults_to_36(self):
        """Empty frames_per_roll field should default to 36."""
        stock = FilmStock(
            id=1, user_id=1, brand="Kodak", name="ColorPlus 200",
            media_type="analog", type="color", iso=200,
            format="35mm", frames_per_roll=36, quantity_on_hand=2,
        )
        app = FilmStockFormTestApp(stock)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#frames_per_roll", Input).value = ""
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_stock is not None
        assert app.dismissed_stock.frames_per_roll == 36
