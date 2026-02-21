"""Tests for development modals and _parse_duration helper."""

import tempfile
from datetime import date
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from pjourney.db import database as db
from pjourney.db.models import Camera, DevelopmentStep, FilmStock, Roll, RollDevelopment
from pjourney.screens.rolls import (
    DevelopmentInfoModal,
    DevelopmentTypeModal,
    LabDevelopModal,
    RollsScreen,
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


# ---------------------------------------------------------------------------
# Integration tests: self-develop advancement flow
# ---------------------------------------------------------------------------

class RollsFlowTestApp(App):
    """Test app hosting RollsScreen for development flow integration tests."""

    def __init__(self, connection, user):
        super().__init__()
        self.db_conn = connection
        self.current_user = user

    def compose(self) -> ComposeResult:
        yield Label("host")


class TestSelfDevelopAdvancement:
    """Tests that self-develop advances to 'developed' and lab to 'developing'."""

    def _setup_finished_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.status = "finished"
        roll.finished_date = date.today()
        roll = db.update_roll(conn, roll)
        return user, roll

    async def test_self_develop_advances_to_developed(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            # Start the developing flow
            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            # DevelopmentTypeModal: choose "Self Develop"
            app.screen.query_one("#self-btn", Button).press()
            await pilot.pause()

            # SelfDevelopModal: fill in one step and save
            app.screen.query_one("#step-0-chemical", Input).value = "D-76"
            app.screen.query_one("#step-0-temp", Input).value = "20C"
            app.screen.query_one("#step-0-duration", Input).value = "8:00"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()

            # Roll should be "developed" (skipping "developing")
            updated = db.get_roll(conn, roll.id)
            assert updated.status == "developed"
            assert updated.developed_date is not None
            assert updated.sent_for_dev_date is not None

    async def test_self_develop_saves_development_record(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            app.screen.query_one("#self-btn", Button).press()
            await pilot.pause()

            app.screen.query_one("#step-0-chemical", Input).value = "HC-110"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()

            # Development record should be saved with correct type
            dev = db.get_roll_development_by_roll(conn, roll.id)
            assert dev is not None
            assert dev.dev_type == "self"
            steps = db.get_development_steps(conn, dev.id)
            assert len(steps) == 1
            assert steps[0].chemical_name == "HC-110"

    async def test_lab_develop_advances_to_developing(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            # DevelopmentTypeModal: choose "Send to Lab"
            app.screen.query_one("#lab-btn", Button).press()
            await pilot.pause()

            # LabDevelopModal: fill in lab name and save
            app.screen.query_one("#lab-name", Input).value = "PhotoLab"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()

            # Roll should be "developing" (not "developed")
            updated = db.get_roll(conn, roll.id)
            assert updated.status == "developing"
            assert updated.sent_for_dev_date is not None
            assert updated.developed_date is None

    async def test_cancel_self_develop_stays_finished(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            # Choose "Self Develop"
            app.screen.query_one("#self-btn", Button).press()
            await pilot.pause()

            # Cancel the self-develop form
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()

            updated = db.get_roll(conn, roll.id)
            assert updated.status == "finished"
            assert updated.developed_date is None

    async def test_cancel_type_selection_stays_finished(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            # Cancel at the type selection modal
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()

            updated = db.get_roll(conn, roll.id)
            assert updated.status == "finished"
            assert updated.developed_date is None

    async def test_cancel_lab_develop_stays_finished(self, conn):
        user, roll = self._setup_finished_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._start_developing_flow(roll)
            await pilot.pause()

            # Choose "Send to Lab"
            app.screen.query_one("#lab-btn", Button).press()
            await pilot.pause()

            # Cancel the lab form
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()

            updated = db.get_roll(conn, roll.id)
            assert updated.status == "finished"
            assert updated.developed_date is None


# ---------------------------------------------------------------------------
# Advance status guard: fresh rolls must not be advanced
# ---------------------------------------------------------------------------

class TestAdvanceStatusFreshGuard:
    """Verify that advance_status does not advance fresh rolls (must use Load)."""

    def _setup_fresh_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        assert roll.status == "fresh"
        return user, roll

    async def test_advance_status_blocks_fresh_roll(self, conn):
        """Pressing advance status on a fresh roll must not change its status."""
        user, roll = self._setup_fresh_roll(conn)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            # Mock _get_selected_id to return our fresh roll
            rolls_screen._get_selected_id = lambda: roll.id
            rolls_screen.action_advance_status()
            await pilot.pause()

            updated = db.get_roll(conn, roll.id)
            assert updated.status == "fresh"

    async def test_advance_status_allows_loaded_roll(self, conn):
        """Pressing advance status on a loaded roll should advance to shooting."""
        user, roll = self._setup_fresh_roll(conn)
        cam = db.save_camera(conn, Camera(user_id=user.id, name="FM2", make="Nikon"))
        roll.camera_id = cam.id
        roll.status = "loaded"
        roll = db.update_roll(conn, roll)
        app = RollsFlowTestApp(conn, user)
        async with app.run_test() as pilot:
            rolls_screen = RollsScreen()
            await app.push_screen(rolls_screen)
            await pilot.pause()

            rolls_screen._get_selected_id = lambda: roll.id
            rolls_screen.action_advance_status()
            await pilot.pause()

            updated = db.get_roll(conn, roll.id)
            assert updated.status == "shooting"


# ---------------------------------------------------------------------------
# DevelopmentInfoModal push/pull display
# ---------------------------------------------------------------------------

class TestDevelopmentInfoModalPushPull:
    def _make_roll_with_push_pull(self, conn, push_pull_stops):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        roll = db.create_roll(
            conn,
            Roll(user_id=user.id, film_stock_id=stock.id, push_pull_stops=push_pull_stops),
            36,
        )
        return roll

    async def test_push_pull_displayed_in_dev_info(self, conn):
        roll = self._make_roll_with_push_pull(conn, 2.0)
        app = DevInfoModalTestApp(conn)
        async with app.run_test() as pilot:
            await app.push_screen(DevelopmentInfoModal(roll.id))
            from textual.widgets import Static
            statics = [_static_text(s) for s in app.screen.query(Static)]
            assert any("Push 2 stop(s)" in s for s in statics)
