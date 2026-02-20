"""Tests for development modals and _parse_duration helper."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from pjourney.db import database as db
from pjourney.db.models import DevelopmentStep, FilmStock, Roll, RollDevelopment
from pjourney.screens.rolls import (
    DevelopmentInfoModal,
    DevelopmentTypeModal,
    LabDevelopModal,
    SelfDevelopModal,
    _parse_duration,
)


# ---------------------------------------------------------------------------
# Unit tests for _parse_duration
# ---------------------------------------------------------------------------

class TestParseDuration:
    def test_mm_ss_format(self):
        assert _parse_duration("8:00") == 480

    def test_plain_seconds(self):
        assert _parse_duration("300") == 300

    def test_empty_string(self):
        assert _parse_duration("") is None

    def test_non_numeric(self):
        assert _parse_duration("abc") is None

    def test_short_mm_ss(self):
        assert _parse_duration("1:30") == 90


# ---------------------------------------------------------------------------
# Minimal host apps for modal tests
# ---------------------------------------------------------------------------

class SimpleModalTestApp(App):
    """Test app for modals that don't need db_conn."""

    def __init__(self):
        super().__init__()
        self.dismissed_value = "UNSET"

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


class DevInfoModalTestApp(App):
    """Test app for DevelopmentInfoModal which needs db_conn."""

    def __init__(self, connection):
        super().__init__()
        self.db_conn = connection
        self.dismissed_value = "UNSET"

    def compose(self) -> ComposeResult:
        yield Label("host")


# ---------------------------------------------------------------------------
# DevelopmentTypeModal tests
# ---------------------------------------------------------------------------

class TestDevelopmentTypeModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(DevelopmentTypeModal())
            assert len(app.screen_stack) == 2

    async def test_self_btn_dismisses_self(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(DevelopmentTypeModal(), on_dismiss)
            app.screen.query_one("#self-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == "self"

    async def test_lab_btn_dismisses_lab(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(DevelopmentTypeModal(), on_dismiss)
            app.screen.query_one("#lab-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == "lab"

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(DevelopmentTypeModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# LabDevelopModal tests
# ---------------------------------------------------------------------------

class TestLabDevelopModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(LabDevelopModal())
            assert len(app.screen_stack) == 2

    async def test_save_without_lab_name_does_not_dismiss(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(LabDevelopModal(), on_dismiss)
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            # Still on the modal (not dismissed)
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_save_with_lab_name_dismisses(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(LabDevelopModal(), on_dismiss)
            app.screen.query_one("#lab-name", Input).value = "DwayneLab"
            app.screen.query_one("#lab-cost", Input).value = "12.50"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is not None
            dev, steps = app.dismissed_value
            assert dev.lab_name == "DwayneLab"
            assert dev.dev_type == "lab"
            assert dev.cost_amount == 12.50
            assert steps == []

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(LabDevelopModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# SelfDevelopModal tests
# ---------------------------------------------------------------------------

class TestSelfDevelopModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            assert len(app.screen_stack) == 2

    async def test_one_step_row_on_mount(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            rows = app.screen.query(".step-row")
            assert len(rows) == 1

    async def test_add_step_adds_row(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            app.screen.query_one("#add-step-btn", Button).press()
            await pilot.pause()
            rows = app.screen.query(".step-row")
            assert len(rows) == 2

    async def test_save_with_empty_steps_does_not_dismiss(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(SelfDevelopModal(), on_dismiss)
            # Don't fill in any chemical name - default is empty
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(SelfDevelopModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# DevelopmentInfoModal tests
# ---------------------------------------------------------------------------

def _static_text(widget) -> str:
    """Extract plain text from a Static widget (Textual 8 compatible)."""
    rendered = widget.render()
    if hasattr(rendered, "plain"):
        return rendered.plain
    return str(rendered)


class TestDevelopmentInfoModal:
    def _make_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        return db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)

    async def test_shows_not_developed_when_no_record(self, conn):
        roll = self._make_roll(conn)
        app = DevInfoModalTestApp(conn)
        async with app.run_test() as pilot:
            await app.push_screen(DevelopmentInfoModal(roll.id))
            from textual.widgets import Static
            statics = [_static_text(s) for s in app.screen.query(Static)]
            assert any("not yet been developed" in s for s in statics)

    async def test_shows_lab_name_for_lab_dev(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="PhotoLab NYC")
        db.save_roll_development(conn, dev, [])
        app = DevInfoModalTestApp(conn)
        async with app.run_test() as pilot:
            await app.push_screen(DevelopmentInfoModal(roll.id))
            from textual.widgets import Static
            statics = [_static_text(s) for s in app.screen.query(Static)]
            assert any("PhotoLab NYC" in s for s in statics)

    async def test_close_button_dismisses(self, conn):
        roll = self._make_roll(conn)
        app = DevInfoModalTestApp(conn)
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(DevelopmentInfoModal(roll.id), on_dismiss)
            app.screen.query_one("#close-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 1
