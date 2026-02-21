"""Tests for the StatsScreen."""

import datetime
import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, Static

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Lens, Roll, RollDevelopment
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
            assert "Top Shooting Locations" in header_texts
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

    async def test_refresh_data_calls_app_error_on_db_failure(self, conn):
        """When db.get_stats raises, _refresh_data must catch the exception and show
        an error toast without propagating — the screen must remain alive.

        Covers lines 78-79 (the except branch in _refresh_data).
        """
        from unittest.mock import patch

        user = db.get_users(conn)[0]
        app = StatsTestApp(conn, user)
        async with app.run_test() as pilot:
            await app.push_screen(StatsScreen())
            await pilot.pause()
            # Screen is up and healthy; now force get_stats to raise on the
            # next call so the except branch (lines 78-79) is exercised.
            with patch(
                "pjourney.screens.stats.db.get_stats",
                side_effect=RuntimeError("simulated db failure"),
            ):
                app.screen._refresh_data()
                await pilot.pause()
            # The screen must still be running — app_error toasts but does not
            # propagate the exception or dismiss the screen.
            assert isinstance(app.screen, StatsScreen)


class TestStatsScreenPopulatedData:
    """Tests for stats screen sections that require data to exercise non-empty branches."""

    async def test_shows_location_data_when_rolls_have_locations(self):
        """When rolls have locations set, the locations section should display them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db"
            conn = db.get_connection(path)
            db.init_db(conn)
            user = db.get_users(conn)[0]
            stock = db.save_film_stock(conn, FilmStock(
                user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
            ))
            camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
            roll = db.create_roll(conn, Roll(
                user_id=user.id, film_stock_id=stock.id, camera_id=camera.id,
                status="developed", location="Paris",
            ), 36)
            app = StatsTestApp(conn, user)
            async with app.run_test() as pilot:
                await app.push_screen(StatsScreen())
                await pilot.pause()
                content = app.screen.query_one("#locations-content", Static)
                rendered = content.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                assert "Paris" in text
            conn.close()

    async def test_shows_camera_data_in_equipment_when_rolls_exist(self):
        """When rolls are associated with cameras, top cameras section populates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db"
            conn = db.get_connection(path)
            db.init_db(conn)
            user = db.get_users(conn)[0]
            stock = db.save_film_stock(conn, FilmStock(
                user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
            ))
            camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
            db.create_roll(conn, Roll(
                user_id=user.id, film_stock_id=stock.id, camera_id=camera.id,
                status="developed",
            ), 36)
            app = StatsTestApp(conn, user)
            async with app.run_test() as pilot:
                await app.push_screen(StatsScreen())
                await pilot.pause()
                content = app.screen.query_one("#equipment-content", Static)
                rendered = content.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                assert "Nikon F3" in text
            conn.close()

    async def test_shows_lens_data_in_equipment_when_frames_logged(self):
        """When frames are logged with lens assignments, top lenses section populates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db"
            conn = db.get_connection(path)
            db.init_db(conn)
            user = db.get_users(conn)[0]
            stock = db.save_film_stock(conn, FilmStock(
                user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
            ))
            camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
            lens = db.save_lens(conn, Lens(user_id=user.id, name="50mm f/1.4", make="Nikon"))
            roll = db.create_roll(conn, Roll(
                user_id=user.id, film_stock_id=stock.id, camera_id=camera.id,
                status="developed",
            ), 36)
            # Assign the lens to all frames so get_stats picks it up for top_lenses
            db.set_roll_frames_lens(conn, roll.id, lens.id)
            app = StatsTestApp(conn, user)
            async with app.run_test() as pilot:
                await app.push_screen(StatsScreen())
                await pilot.pause()
                content = app.screen.query_one("#equipment-content", Static)
                rendered = content.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                assert "50mm f/1.4" in text
            conn.close()

    async def test_shows_activity_bar_chart_when_rolls_have_loaded_dates(self):
        """When rolls have loaded_date set, the activity bar chart renders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.db"
            conn = db.get_connection(path)
            db.init_db(conn)
            user = db.get_users(conn)[0]
            stock = db.save_film_stock(conn, FilmStock(
                user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
            ))
            camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
            roll = db.create_roll(conn, Roll(
                user_id=user.id, film_stock_id=stock.id, camera_id=camera.id,
                status="developed",
            ), 36)
            # Set loaded_date so get_stats includes this roll in rolls_by_month
            roll.loaded_date = datetime.date.today()
            db.update_roll(conn, roll)
            app = StatsTestApp(conn, user)
            async with app.run_test() as pilot:
                await app.push_screen(StatsScreen())
                await pilot.pause()
                content = app.screen.query_one("#activity-content", Static)
                rendered = content.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                # Should contain a month entry, not the "No activity" placeholder
                assert "No activity data yet." not in text
            conn.close()
