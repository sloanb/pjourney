"""Tests for RecipeFormModal, RecipePickerModal, and SelfDevelop Load Recipe."""

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label, Select

from pjourney.db import database as db
from pjourney.db.models import DevRecipe, DevRecipeStep, DevelopmentStep, FilmStock, Roll, RollDevelopment
from pjourney.screens.admin import RecipeFormModal
from pjourney.screens.rolls import RecipePickerModal, SelfDevelopModal


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class ModalTestApp(App):
    """Test app for recipe modals."""

    def __init__(self, connection):
        super().__init__()
        self.db_conn = connection
        self.current_user = None
        self.dismissed_value = "UNSET"

    def compose(self) -> ComposeResult:
        yield Label("host")


# ---------------------------------------------------------------------------
# RecipeFormModal tests
# ---------------------------------------------------------------------------

class TestRecipeFormModal:
    async def test_creates_without_crash(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal())
            await pilot.pause()
            assert isinstance(app.screen, RecipeFormModal)

    async def test_shows_create_title(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal())
            await pilot.pause()
            from textual.widgets import Static
            statics = app.screen.query(Static)
            titles = []
            for s in statics:
                rendered = s.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                titles.append(text)
            assert "Create Recipe" in titles

    async def test_shows_edit_title_when_editing(self, conn):
        user = db.get_users(conn)[0]
        recipe = DevRecipe(id=1, user_id=user.id, name="Test")
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal(recipe=recipe))
            await pilot.pause()
            from textual.widgets import Static
            statics = app.screen.query(Static)
            titles = []
            for s in statics:
                rendered = s.render()
                text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
                titles.append(text)
            assert "Edit Recipe" in titles

    async def test_cancel_dismisses_none(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            cancel_btn = app.screen.query_one("#cancel-btn", Button)
            cancel_btn.press()
            await pilot.pause()
        assert dismissed == [None]

    async def test_save_with_name_and_step(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            app.screen.query_one("#recipe-name", Input).value = "My Recipe"
            app.screen.query_one("#step-0-chemical", Input).value = "D-76"
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
        assert len(dismissed) == 1
        recipe, steps = dismissed[0]
        assert recipe.name == "My Recipe"
        assert len(steps) == 1
        assert steps[0].chemical_name == "D-76"

    async def test_save_without_name_does_nothing(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipeFormModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            # Don't set recipe name
            save_btn = app.screen.query_one("#save-btn", Button)
            save_btn.press()
            await pilot.pause()
        # Should not have dismissed
        assert len(dismissed) == 0


# ---------------------------------------------------------------------------
# RecipePickerModal tests
# ---------------------------------------------------------------------------

class TestRecipePickerModal:
    async def test_opens_without_crash(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(RecipePickerModal())
            await pilot.pause()
            assert isinstance(app.screen, RecipePickerModal)

    async def test_shows_recipes_in_table(self, conn):
        user = db.get_users(conn)[0]
        db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Standard B&W", process_type="B&W",
        ), [DevRecipeStep(chemical_name="D-76")])
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(RecipePickerModal())
            await pilot.pause()
            from pjourney.widgets.inventory_table import InventoryTable
            table = app.screen.query_one("#picker-table", InventoryTable)
            assert table.row_count == 1

    async def test_cancel_dismisses_none(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipePickerModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            cancel_btn = app.screen.query_one("#cancel-btn", Button)
            cancel_btn.press()
            await pilot.pause()
        assert dismissed == [None]

    async def test_select_returns_recipe_id(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="C-41 Home", process_type="C-41",
        ), [])
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipePickerModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            select_btn = app.screen.query_one("#select-btn", Button)
            select_btn.press()
            await pilot.pause()
        assert len(dismissed) == 1
        assert dismissed[0] == saved.id

    async def test_empty_table_select_does_nothing(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        dismissed = []
        async with app.run_test() as pilot:
            await app.push_screen(RecipePickerModal(), callback=lambda r: dismissed.append(r))
            await pilot.pause()
            select_btn = app.screen.query_one("#select-btn", Button)
            select_btn.press()
            await pilot.pause()
        # With empty table, select should not dismiss
        assert len(dismissed) == 0


# ---------------------------------------------------------------------------
# SelfDevelopModal Load Recipe integration tests
# ---------------------------------------------------------------------------

class TestSelfDevelopLoadRecipe:
    async def test_load_recipe_button_exists(self, conn):
        user = db.get_users(conn)[0]
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            await pilot.pause()
            btn = app.screen.query_one("#load-recipe-btn", Button)
            rendered = btn.render()
            text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            assert "Load Recipe" in text

    async def test_load_recipe_opens_picker(self, conn):
        user = db.get_users(conn)[0]
        db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="B&W Standard", process_type="B&W",
        ), [DevRecipeStep(chemical_name="D-76", temperature="20C")])
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            await pilot.pause()
            load_btn = app.screen.query_one("#load-recipe-btn", Button)
            load_btn.press()
            await pilot.pause()
            assert isinstance(app.screen, RecipePickerModal)

    async def test_load_recipe_fills_steps(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Full B&W", process_type="B&W",
            notes="Test notes",
        ), [
            DevRecipeStep(chemical_name="Developer", temperature="20C", duration_seconds=480),
            DevRecipeStep(chemical_name="Fixer", temperature="20C", duration_seconds=300),
        ])
        app = ModalTestApp(conn)
        app.current_user = user
        async with app.run_test() as pilot:
            await app.push_screen(SelfDevelopModal())
            await pilot.pause()
            # Open picker
            load_btn = app.screen.query_one("#load-recipe-btn", Button)
            load_btn.press()
            await pilot.pause()
            # Select recipe from picker
            assert isinstance(app.screen, RecipePickerModal)
            select_btn = app.screen.query_one("#select-btn", Button)
            select_btn.press()
            await pilot.pause()
            # Back in SelfDevelopModal — check steps are filled
            # Step IDs continue from on_mount's initial step (step-0),
            # so loaded recipe steps are step-1 and step-2
            assert isinstance(app.screen, SelfDevelopModal)
            chem0 = app.screen.query_one("#step-1-chemical", Input)
            assert chem0.value == "Developer"
            chem1 = app.screen.query_one("#step-2-chemical", Input)
            assert chem1.value == "Fixer"
            # Check notes
            notes_input = app.screen.query_one("#dev-notes", Input)
            assert notes_input.value == "Test notes"
