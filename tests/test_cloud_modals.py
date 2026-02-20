"""Tests for cloud-related modals in the admin screen."""

from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from pjourney.cloud.provider import CloudFileEntry, CloudFolderEntry, CloudProvider
from pjourney.screens.admin import (
    CloudAuthModal,
    CloudFolderBrowserModal,
    CloudRestoreModal,
    NewFolderModal,
)


class SimpleModalTestApp(App):
    """Test app for modals that don't need db_conn."""

    def __init__(self):
        super().__init__()
        self.dismissed_value = "UNSET"

    def compose(self) -> ComposeResult:
        yield Label("host")


# ---------------------------------------------------------------------------
# CloudAuthModal tests
# ---------------------------------------------------------------------------

class TestCloudAuthModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CloudAuthModal())
            assert len(app.screen_stack) == 2

    async def test_submit_with_code_dismisses(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudAuthModal(), on_dismiss)
            app.screen.query_one("#auth-code", Input).value = "abc123"
            app.screen.query_one("#submit-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == "abc123"

    async def test_submit_empty_does_not_dismiss(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudAuthModal(), on_dismiss)
            app.screen.query_one("#submit-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudAuthModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None

    async def test_cancel_button_not_clipped(self):
        """Cancel button must be fully visible on an 80x24 terminal."""
        app = SimpleModalTestApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await app.push_screen(CloudAuthModal())
            await pilot.pause()
            cancel = app.screen.query_one("#cancel-btn", Button)
            cancel_bottom = cancel.region.y + cancel.region.height
            assert cancel_bottom <= 24

    async def test_instruction_label_wraps(self):
        """Long instruction label must wrap within the auth-box width."""
        app = SimpleModalTestApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await app.push_screen(CloudAuthModal())
            await pilot.pause()
            box = app.screen.query_one("#auth-box")
            labels = app.screen.query("Label")
            instruction_label = labels[0]
            assert instruction_label.size.width <= box.size.width


# ---------------------------------------------------------------------------
# NewFolderModal tests
# ---------------------------------------------------------------------------

class TestNewFolderModal:
    async def test_opens_without_crash(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(NewFolderModal())
            assert len(app.screen_stack) == 2

    async def test_create_with_name_dismisses(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(NewFolderModal(), on_dismiss)
            app.screen.query_one("#folder-name", Input).value = "my-folder"
            app.screen.query_one("#create-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == "my-folder"

    async def test_create_empty_does_not_dismiss(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(NewFolderModal(), on_dismiss)
            app.screen.query_one("#create-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_cancel_dismisses_none(self):
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(NewFolderModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# CloudFolderBrowserModal tests
# ---------------------------------------------------------------------------

def _make_mock_provider(folders=None):
    provider = MagicMock(spec=CloudProvider)
    provider.list_folder.return_value = folders or []
    provider.list_files.return_value = []
    return provider


class TestCloudFolderBrowserModal:
    async def test_opens_without_crash(self):
        provider = _make_mock_provider()
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CloudFolderBrowserModal(provider))
            assert len(app.screen_stack) == 2

    async def test_lists_folders(self):
        folders = [
            CloudFolderEntry(name="backups", path="/backups", is_folder=True),
            CloudFolderEntry(name="photos", path="/photos", is_folder=True),
        ]
        provider = _make_mock_provider(folders)
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CloudFolderBrowserModal(provider))
            from pjourney.widgets.inventory_table import InventoryTable
            table = app.screen.query_one("#folder-table", InventoryTable)
            assert table.row_count == 2

    async def test_select_dismisses_with_path(self):
        provider = _make_mock_provider()
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudFolderBrowserModal(provider), on_dismiss)
            app.screen.query_one("#select-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == ""  # root path

    async def test_cancel_dismisses_none(self):
        provider = _make_mock_provider()
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudFolderBrowserModal(provider), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# CloudRestoreModal tests
# ---------------------------------------------------------------------------

class TestCloudRestoreModal:
    async def test_opens_without_crash(self):
        provider = MagicMock(spec=CloudProvider)
        provider.list_files.return_value = []
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CloudRestoreModal(provider, "/backups"))
            assert len(app.screen_stack) == 2

    async def test_lists_files(self):
        provider = MagicMock(spec=CloudProvider)
        provider.list_files.return_value = [
            CloudFileEntry(name="pjourney_20250101.db", path="/backups/pjourney_20250101.db", size=2048, modified="2025-01-01"),
            CloudFileEntry(name="pjourney_20250102.db", path="/backups/pjourney_20250102.db", size=4096, modified="2025-01-02"),
        ]
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CloudRestoreModal(provider, "/backups"))
            from pjourney.widgets.inventory_table import InventoryTable
            table = app.screen.query_one("#file-table", InventoryTable)
            assert table.row_count == 2

    async def test_cancel_dismisses_none(self):
        provider = MagicMock(spec=CloudProvider)
        provider.list_files.return_value = []
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CloudRestoreModal(provider, "/backups"), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None


# ---------------------------------------------------------------------------
# CreateUserModal tests
# ---------------------------------------------------------------------------

class TestCreateUserModal:
    async def test_opens_without_crash(self):
        from pjourney.screens.admin import CreateUserModal
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            await app.push_screen(CreateUserModal())
            assert len(app.screen_stack) == 2

    async def test_create_with_username_and_password_dismisses_tuple(self):
        from pjourney.screens.admin import CreateUserModal
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CreateUserModal(), on_dismiss)
            app.screen.query_one("#username", Input).value = "newuser"
            app.screen.query_one("#password", Input).value = "secret"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value == ("newuser", "secret")

    async def test_create_with_empty_username_does_not_dismiss(self):
        from pjourney.screens.admin import CreateUserModal
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CreateUserModal(), on_dismiss)
            app.screen.query_one("#password", Input).value = "secret"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_create_with_empty_password_does_not_dismiss(self):
        from pjourney.screens.admin import CreateUserModal
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CreateUserModal(), on_dismiss)
            app.screen.query_one("#username", Input).value = "newuser"
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
            assert len(app.screen_stack) == 2
            assert app.dismissed_value == "UNSET"

    async def test_cancel_dismisses_none(self):
        from pjourney.screens.admin import CreateUserModal
        app = SimpleModalTestApp()
        async with app.run_test() as pilot:
            def on_dismiss(val):
                app.dismissed_value = val
            await app.push_screen(CreateUserModal(), on_dismiss)
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
            assert app.dismissed_value is None
