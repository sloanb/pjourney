"""Tests for the DashboardScreen."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from pjourney.db import database as db
from pjourney.db.models import FilmStock
from pjourney.screens.dashboard import DashboardScreen


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class DashboardTestApp(App):
    """Test app hosting DashboardScreen."""

    def __init__(self, connection, user):
        super().__init__()
        self.db_conn = connection
        self.current_user = user

    def compose(self) -> ComposeResult:
        yield Label("host")


class TestDashboardLowStockSection:
    async def test_dashboard_no_alerts_does_not_crash(self, conn):
        """Mounting DashboardScreen with no low-stock alerts must not raise.

        Regression test: low_stock_section.display was set to [] instead of
        False, causing a Textual error that surfaced as PJ-DB01.
        """
        user = db.get_users(conn)[0]
        app = DashboardTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(DashboardScreen())
            await pilot.pause()
            # Screen should mount successfully — no PJ-DB01 error
            assert isinstance(app.screen, DashboardScreen)

    async def test_dashboard_with_low_stock_does_not_crash(self, conn):
        """Mounting DashboardScreen with low-stock items must not raise."""
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            media_type="analog", quantity_on_hand=1,
        ))
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5",
            media_type="analog", quantity_on_hand=0,
        ))
        app = DashboardTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(DashboardScreen())
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
