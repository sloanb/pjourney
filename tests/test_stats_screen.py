"""Tests for the StatsScreen."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, Static

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Roll, RollDevelopment
from pjourney.screens.stats import StatsScreen


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class StatsTestApp(App):
    """Test app hosting StatsScreen."""

    def __init__(self, connection, user):
        super().__init__()
        self.db_conn = connection
        self.current_user = user

    def compose(self) -> ComposeResult:
        yield Label("host")


class TestStatsScreen:
    async def test_opens_without_crash(self, conn):
        user = db.get_users(conn)[0]
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            assert isinstance(app.screen, StatsScreen)

    async def test_shows_section_headers(self, conn):
        user = db.get_users(conn)[0]
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            headers = app.screen.query(".section-header")
            header_texts = []
            for h in headers:
                rendered = h.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                header_texts.append(text)
            assert "Roll Overview" in header_texts
            assert "Film Usage" in header_texts
            assert "Equipment Usage" in header_texts
            assert "Development" in header_texts
            assert "Activity (last 12 months)" in header_texts

    async def test_shows_zero_counts_with_empty_db(self, conn):
        user = db.get_users(conn)[0]
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            overview = app.screen.query_one("#roll-overview-content", Static)
            rendered = overview.render()
            text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            assert "Total Rolls: 0" in text

    async def test_shows_film_stock_name_when_rolls_exist(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            film_content = app.screen.query_one("#film-usage-content", Static)
            rendered = film_content.render()
            text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            assert "Kodak Portra 400" in text

    async def test_shows_dev_cost_when_lab_development_exists(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="Lab A", cost_amount=12.50)
        db.save_roll_development(conn, dev, [])
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            dev_content = app.screen.query_one("#dev-content", Static)
            rendered = dev_content.render()
            text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            assert "$12.50" in text

    async def test_back_button_pops_screen(self, conn):
        user = db.get_users(conn)[0]
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            assert isinstance(app.screen, StatsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, StatsScreen)
