"""Tests for ScanRollModal and scan integration."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Roll, RollDevelopment
from pjourney.screens.rolls import RollsScreen, ScanRollModal


# ---------------------------------------------------------------------------
# Minimal host apps
# ---------------------------------------------------------------------------

class SimpleModalTestApp(App):
    """Test app for modals that don't need db_conn."""

    def __init__(self):
        super().__init__()
        self.dismissed_value = "UNSET"

    def compose(self) -> ComposeResult:
        yield Label("host")


class RollsTestApp(App):
    """Test app hosting RollsScreen with a real DB connection."""

    def __init__(self, connection, user):
        super().__init__()
        self.db_conn = connection
        self.current_user = user

    def compose(self) -> ComposeResult:
        yield Label("host")


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


# ---------------------------------------------------------------------------
# ScanRollModal unit tests
# ---------------------------------------------------------------------------

class TestScanRollModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            app.push_screen(ScanRollModal())
            await pilot.pause()
            assert isinstance(app.screen, ScanRollModal)

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(result):
                app.dismissed_value = result
            app.push_screen(ScanRollModal(), on_dismiss)
            await pilot.pause()
            cancel_btn = app.screen.query_one("#cancel-btn", Button)
            cancel_btn.press()
            await pilot.pause()
            assert app.dismissed_value is None

    async def test_save_with_valid_date_dismisses_tuple(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(result):
                app.dismissed_value = result
            app.push_screen(ScanRollModal(), on_dismiss)
            await pilot.pause()
            app.screen.query_one("#scan-date", Input).value = "2025-06-15"
            app.screen.query_one("#scan-notes", Input).value = "Flatbed scan"
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
            assert app.dismissed_value == ("2025-06-15", "Flatbed scan")

    async def test_save_with_invalid_date_does_not_dismiss(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(result):
                app.dismissed_value = result
            app.push_screen(ScanRollModal(), on_dismiss)
            await pilot.pause()
            app.screen.query_one("#scan-date", Input).value = "not-a-date"
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
            # Modal should still be showing — not dismissed
            assert app.dismissed_value == "UNSET"

    async def test_save_with_empty_date_defaults_to_today(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(result):
                app.dismissed_value = result
            app.push_screen(ScanRollModal(), on_dismiss)
            await pilot.pause()
            # Leave date empty
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
            assert app.dismissed_value is not None
            assert app.dismissed_value[0] == str(date.today())

    async def test_pre_populated_values_shown(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            app.push_screen(ScanRollModal(
                current_scan_date="2025-03-10",
                current_scan_notes="Nikon Coolscan",
            ))
            await pilot.pause()
            assert app.screen.query_one("#scan-date", Input).value == "2025-03-10"
            assert app.screen.query_one("#scan-notes", Input).value == "Nikon Coolscan"


# ---------------------------------------------------------------------------
# Scan integration test
# ---------------------------------------------------------------------------

class TestScanRollIntegration:
    async def test_scan_action_saves_to_db(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, status="developed",
        ), 36)
        roll.status = "developed"
        db.update_roll(conn, roll)

        app = RollsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(RollsScreen())
            await pilot.pause()
            # Trigger scan action
            await pilot.press("c")
            await pilot.pause()
            # Should have ScanRollModal open
            assert isinstance(app.screen, ScanRollModal)
            app.screen.query_one("#scan-date", Input).value = "2025-07-01"
            app.screen.query_one("#scan-notes", Input).value = "Epson V600"
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
            # Verify DB was updated
            updated = db.get_roll(conn, roll.id)
            assert str(updated.scan_date) == "2025-07-01"
            assert updated.scan_notes == "Epson V600"
