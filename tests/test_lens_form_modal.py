"""Tests for LensFormModal.

Covers the two-column layout, button visibility on small terminals,
save paths (valid data, all fields, empty name guard, invalid aperture,
empty optional fields), and cancel.
"""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from pjourney.db.models import Lens, User
from pjourney.screens.lenses import LensFormModal


# ---------------------------------------------------------------------------
# Minimal host app
# ---------------------------------------------------------------------------

class LensFormTestApp(App):
    """Minimal host that carries current_user and can push LensFormModal."""

    def __init__(self, lens: Lens | None = None) -> None:
        super().__init__()
        self._lens = lens
        self.dismissed_lens: Lens | None = None
        self.dismissed_called: bool = False
        self.current_user = User(id=1, username="test")

    def compose(self) -> ComposeResult:
        yield Label("host")

    async def show_form(self) -> None:
        def on_dismiss(lens: Lens | None) -> None:
            self.dismissed_called = True
            self.dismissed_lens = lens

        await self.push_screen(LensFormModal(self._lens), on_dismiss)


# ---------------------------------------------------------------------------
# TestLensFormModalOpens
# ---------------------------------------------------------------------------

class TestLensFormModalOpens:
    """Verify the modal renders without crashing."""

    async def test_new_lens_form_does_not_crash(self):
        """Opening add-lens form (no existing lens) must not raise."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_existing_lens_form_does_not_crash(self):
        """Editing a fully populated lens must not raise."""
        lens = Lens(
            id=1, user_id=1, name="Summicron 50mm", make="Leica",
            model="Summicron", focal_length="50mm", max_aperture=2.0,
            filter_diameter=39.0, year_built=1969, year_purchased=2023,
            purchase_location="KEH",
        )
        app = LensFormTestApp(lens)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_buttons_visible_on_small_terminal(self):
        """Save/Cancel buttons must be in the DOM and pressable on a 24-line terminal."""
        app = LensFormTestApp(None)
        async with app.run_test(size=(80, 24)) as pilot:
            await app.show_form()
            save_btn = app.screen.query_one("#save-btn", Button)
            cancel_btn = app.screen.query_one("#cancel-btn", Button)
            assert save_btn is not None
            assert cancel_btn is not None
            # Pressing cancel should dismiss without error
            cancel_btn.press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_lens is None


# ---------------------------------------------------------------------------
# TestLensFormModalSave
# ---------------------------------------------------------------------------

class TestLensFormModalSave:
    """Verify save and cancel paths."""

    async def test_cancel_dismisses_none(self):
        """Cancel must dismiss with None."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_lens is None

    async def test_save_with_valid_data_dismisses_lens(self):
        """Saving with a name must dismiss with a Lens."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#name", Input).value = "Planar 50mm"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_lens is not None
        assert app.dismissed_lens.name == "Planar 50mm"

    async def test_save_preserves_all_fields(self):
        """All fields must round-trip through save."""
        lens = Lens(
            id=1, user_id=1, name="Summicron 50mm", make="Leica",
            model="Summicron", focal_length="50mm", max_aperture=2.0,
            filter_diameter=39.0, year_built=1969, year_purchased=2023,
            purchase_location="KEH",
        )
        app = LensFormTestApp(lens)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_lens is not None
        ln = app.dismissed_lens
        assert ln.name == "Summicron 50mm"
        assert ln.make == "Leica"
        assert ln.model == "Summicron"
        assert ln.focal_length == "50mm"
        assert ln.max_aperture == 2.0
        assert ln.filter_diameter == 39.0
        assert ln.year_built == 1969
        assert ln.year_purchased == 2023
        assert ln.purchase_location == "KEH"

    async def test_save_with_empty_name_does_not_dismiss(self):
        """Saving with an empty name must not dismiss the modal."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#name", Input).value = ""
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert not app.dismissed_called

    async def test_save_with_invalid_aperture_does_not_dismiss(self):
        """Non-numeric max_aperture must trigger error and not dismiss."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#name", Input).value = "Test Lens"
            app.screen.query_one("#max_aperture", Input).value = "not-a-number"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert not app.dismissed_called

    async def test_save_with_empty_optional_fields_sets_none(self):
        """Empty aperture/filter/year/location fields must default to None."""
        app = LensFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#name", Input).value = "Bare Lens"
            app.screen.query_one("#max_aperture", Input).value = ""
            app.screen.query_one("#filter_diameter", Input).value = ""
            app.screen.query_one("#year_built", Input).value = ""
            app.screen.query_one("#year_purchased", Input).value = ""
            app.screen.query_one("#purchase_location", Input).value = ""
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_lens is not None
        assert app.dismissed_lens.max_aperture is None
        assert app.dismissed_lens.filter_diameter is None
        assert app.dismissed_lens.year_built is None
        assert app.dismissed_lens.year_purchased is None
        assert app.dismissed_lens.purchase_location is None
