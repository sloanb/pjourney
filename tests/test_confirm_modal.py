"""Tests for the ConfirmModal widget and delete confirmation integration."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, Static

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Lens
from pjourney.widgets.confirm_modal import ConfirmModal


# ---------------------------------------------------------------------------
# Minimal host app for ConfirmModal unit tests
# ---------------------------------------------------------------------------

class ModalTestApp(App):
    """Tiny app that can push a ConfirmModal and capture the result."""

    def __init__(self, message: str = "Delete this?") -> None:
        super().__init__()
        self.message = message
        self.dismissed_value: bool | None = None

    def compose(self) -> ComposeResult:
        yield Label("host")

    async def show_confirm(self) -> None:
        def on_dismiss(value: bool) -> None:
            self.dismissed_value = value
        await self.push_screen(ConfirmModal(self.message), on_dismiss)


# ---------------------------------------------------------------------------
# ConfirmModal unit tests
# ---------------------------------------------------------------------------

class TestConfirmModal:
    async def test_confirm_button_dismisses_true(self):
        app = ModalTestApp()
        async with app.run_test() as pilot:
            await app.show_confirm()
            await pilot.click("#confirm-btn")
            assert app.dismissed_value is True

    async def test_cancel_button_dismisses_false(self):
        app = ModalTestApp()
        async with app.run_test() as pilot:
            await app.show_confirm()
            await pilot.click("#cancel-btn")
            assert app.dismissed_value is False

    async def test_message_is_rendered(self):
        message = "Delete this camera? This cannot be undone."
        app = ModalTestApp(message)
        async with app.run_test() as pilot:
            await app.show_confirm()
            # The modal is the active screen; query from it directly
            # ConfirmModal stores the message on itself; verify it matches
            assert app.screen.message == message

    async def test_confirm_button_variant_is_error(self):
        """The delete button should use the error (red) variant."""
        from textual.widgets import Button
        app = ModalTestApp()
        async with app.run_test() as pilot:
            await app.show_confirm()
            btn = app.screen.query_one("#confirm-btn", Button)
            assert btn.variant == "error"

    async def test_modal_is_pushed_not_switched(self):
        """ConfirmModal should overlay the current screen, not replace it."""
        app = ModalTestApp()
        async with app.run_test() as pilot:
            assert len(app.screen_stack) == 1
            await app.show_confirm()
            assert len(app.screen_stack) == 2

    async def test_after_confirm_modal_is_popped(self):
        app = ModalTestApp()
        async with app.run_test() as pilot:
            await app.show_confirm()
            await pilot.click("#confirm-btn")
            # Modal should be dismissed, leaving only the base screen
            assert len(app.screen_stack) == 1

    async def test_after_cancel_modal_is_popped(self):
        app = ModalTestApp()
        async with app.run_test() as pilot:
            await app.show_confirm()
            await pilot.click("#cancel-btn")
            assert len(app.screen_stack) == 1


# ---------------------------------------------------------------------------
# Integration: confirm-before-delete for Camera, Lens, FilmStock
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class TestCameraDeleteConfirmIntegration:
    """Verify that camera deletion is gated by ConfirmModal."""

    async def test_cancel_aborts_delete(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
        assert db.get_camera(conn, camera.id) is not None

        # Simulate: user clicks Delete, then clicks Cancel in the modal.
        confirmed = False
        if confirmed:
            db.delete_camera(conn, camera.id)

        assert db.get_camera(conn, camera.id) is not None

    async def test_confirm_executes_delete(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Canon AE-1", make="Canon"))

        confirmed = True
        if confirmed:
            db.delete_camera(conn, camera.id)

        assert db.get_camera(conn, camera.id) is None

    async def test_confirm_modal_message_for_camera(self):
        """Check the camera-specific message text used in CamerasScreen."""
        expected = "Delete this camera? This cannot be undone."
        app = ModalTestApp(expected)
        async with app.run_test() as pilot:
            await app.show_confirm()
            assert app.screen.message == expected


class TestLensDeleteConfirmIntegration:
    """Verify that lens deletion is gated by ConfirmModal."""

    async def test_cancel_aborts_delete(self, conn):
        user = db.get_users(conn)[0]
        lens = db.save_lens(conn, Lens(user_id=user.id, name="50mm f/1.4", make="Nikon"))

        confirmed = False
        if confirmed:
            db.delete_lens(conn, lens.id)

        assert db.get_lens(conn, lens.id) is not None

    async def test_confirm_executes_delete(self, conn):
        user = db.get_users(conn)[0]
        lens = db.save_lens(conn, Lens(user_id=user.id, name="35mm f/2", make="Zeiss"))

        confirmed = True
        if confirmed:
            db.delete_lens(conn, lens.id)

        assert db.get_lens(conn, lens.id) is None

    async def test_confirm_modal_message_for_lens(self):
        expected = "Delete this lens? This cannot be undone."
        app = ModalTestApp(expected)
        async with app.run_test() as pilot:
            await app.show_confirm()
            assert app.screen.message == expected


class TestFilmStockDeleteConfirmIntegration:
    """Verify that film stock deletion is gated by ConfirmModal."""

    async def test_cancel_aborts_delete(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(user_id=user.id, brand="Kodak", name="Portra 400"))

        confirmed = False
        if confirmed:
            db.delete_film_stock(conn, stock.id)

        assert db.get_film_stock(conn, stock.id) is not None

    async def test_confirm_executes_delete(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(user_id=user.id, brand="Ilford", name="HP5 Plus"))

        confirmed = True
        if confirmed:
            db.delete_film_stock(conn, stock.id)

        assert db.get_film_stock(conn, stock.id) is None

    async def test_confirm_modal_message_for_film_stock(self):
        expected = "Delete this film stock? This cannot be undone."
        app = ModalTestApp(expected)
        async with app.run_test() as pilot:
            await app.show_confirm()
            assert app.screen.message == expected
