"""Admin screen — DB maintenance, cloud sync, and user management."""

import asyncio
import shutil
import sqlite3
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.cloud.credentials import CredentialStore
from pjourney.cloud.dropbox_provider import DropboxProvider
from pjourney.cloud.provider import CloudProvider, CloudProviderError
from pjourney.db import database as db
from pjourney.db.models import CloudSettings
from pjourney.errors import ErrorCode, app_error
from pjourney.widgets.confirm_modal import ConfirmModal
from pjourney.widgets.inventory_table import InventoryTable


# ---------------------------------------------------------------------------
# Modals
# ---------------------------------------------------------------------------

class CreateUserModal(ModalScreen[tuple[str, str] | None]):
    CSS = """
    CreateUserModal {
        align: center middle;
    }
    #form-box {
        width: 50;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #form-box Label {
        margin: 1 0 0 0;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="form-box"):
            yield Static("Create User", markup=False)
            yield Label("Username")
            yield Input(id="username")
            yield Label("Password")
            yield Input(id="password", password=True)
            with Horizontal(classes="form-buttons"):
                yield Button("Create", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if username and password:
            self.dismiss((username, password))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class CloudAuthModal(ModalScreen[str | None]):
    """Prompt user to paste the Dropbox authorization code."""

    CSS = """
    CloudAuthModal {
        align: center middle;
    }
    #auth-box {
        width: 64;
        height: auto;
        max-height: 100%;
        border: heavy $accent;
        padding: 0 2;
        background: $surface;
    }
    #auth-box Label {
        width: 100%;
        margin: 1 0 0 0;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-box"):
            yield Static("Link Cloud Account", markup=False)
            yield Label(
                "A browser window has been opened. "
                "Sign in and authorize pjourney, then paste the code below."
            )
            yield Label("Authorization Code")
            yield Input(id="auth-code", placeholder="Paste code here")
            with Horizontal(classes="form-buttons"):
                yield Button("Submit", id="submit-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#submit-btn")
    def submit(self) -> None:
        code = self.query_one("#auth-code", Input).value.strip()
        if code:
            self.dismiss(code)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class NewFolderModal(ModalScreen[str | None]):
    """Simple modal to get a folder name from the user."""

    CSS = """
    NewFolderModal {
        align: center middle;
    }
    #newfolder-box {
        width: 50;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #newfolder-box Label {
        margin: 1 0 0 0;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="newfolder-box"):
            yield Static("New Folder", markup=False)
            yield Label("Folder Name")
            yield Input(id="folder-name", placeholder="Enter folder name")
            with Horizontal(classes="form-buttons"):
                yield Button("Create", id="create-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#create-btn")
    def create(self) -> None:
        name = self.query_one("#folder-name", Input).value.strip()
        if name:
            self.dismiss(name)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class CloudFolderBrowserModal(ModalScreen[str | None]):
    """Browse remote folders and select one for backup storage."""

    CSS = """
    CloudFolderBrowserModal {
        align: center middle;
    }
    #browser-box {
        width: 70;
        height: 24;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #path-label {
        margin: 0 0 1 0;
    }
    #folder-table {
        height: 1fr;
    }
    #browser-actions {
        height: auto;
        margin: 1 0 0 0;
    }
    #browser-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, provider: CloudProvider) -> None:
        super().__init__()
        self._provider = provider
        self._current_path = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="browser-box"):
            yield Static("Select Folder", markup=False)
            yield Label("/", id="path-label")
            yield InventoryTable(id="folder-table")
            with Horizontal(id="browser-actions"):
                yield Button("Open", id="open-btn")
                yield Button("Up", id="up-btn")
                yield Button("New Folder", id="new-folder-btn")
                yield Button("Select", id="select-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        table = self.query_one("#folder-table", InventoryTable)
        table.add_columns("Name", "Path")
        self._load_folder(path="")

    @work(exclusive=True)
    async def _load_folder(self, path: str) -> None:
        self._current_path = path
        display_path = path or "/"
        self.query_one("#path-label", Label).update(f"{display_path}  (loading...)")
        table = self.query_one("#folder-table", InventoryTable)
        table.clear()
        try:
            folders = await asyncio.to_thread(self._provider.list_folder, path)
            for f in folders:
                table.add_row(f.name, f.path, key=f.path)
            if folders:
                self.query_one("#path-label", Label).update(display_path)
            else:
                self.query_one("#path-label", Label).update(f"{display_path}  (empty)")
        except Exception as exc:
            self.query_one("#path-label", Label).update(f"{display_path}  (error: {exc})")

    @on(Button.Pressed, "#open-btn")
    def open_folder(self) -> None:
        table = self.query_one("#folder-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            self._load_folder(path=row_key.value)

    @on(Button.Pressed, "#up-btn")
    def go_up(self) -> None:
        if self._current_path:
            parent = "/".join(self._current_path.rstrip("/").split("/")[:-1])
            self._load_folder(path=parent)

    @on(Button.Pressed, "#new-folder-btn")
    def new_folder(self) -> None:
        def on_result(name: str | None) -> None:
            if name:
                new_path = f"{self._current_path}/{name}" if self._current_path else f"/{name}"
                self._create_and_refresh(new_path)
        self.app.push_screen(NewFolderModal(), on_result)

    @work(exclusive=True, group="create_folder")
    async def _create_and_refresh(self, new_path: str) -> None:
        try:
            await asyncio.to_thread(self._provider.create_folder, new_path)
        except Exception as exc:
            self.query_one("#path-label", Label).update(f"Error creating folder: {exc}")
            return
        self._load_folder(path=self._current_path)

    @on(Button.Pressed, "#select-btn")
    def select_folder(self) -> None:
        self.dismiss(self._current_path)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class CloudRestoreModal(ModalScreen[str | None]):
    """List .db files from the remote folder and let the user pick one."""

    CSS = """
    CloudRestoreModal {
        align: center middle;
    }
    #restore-box {
        width: 70;
        height: 24;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #file-table {
        height: 1fr;
    }
    #restore-actions {
        height: auto;
        margin: 1 0 0 0;
    }
    #restore-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, provider: CloudProvider, remote_folder: str) -> None:
        super().__init__()
        self._provider = provider
        self._remote_folder = remote_folder

    def compose(self) -> ComposeResult:
        with Vertical(id="restore-box"):
            yield Static("Restore from Cloud", markup=False)
            yield InventoryTable(id="file-table")
            with Horizontal(id="restore-actions"):
                yield Button("Select", id="select-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        table = self.query_one("#file-table", InventoryTable)
        table.add_columns("Name", "Size", "Modified")
        try:
            files = self._provider.list_files(self._remote_folder)
            for f in files:
                size_kb = f"{f.size / 1024:.1f} KB" if f.size else ""
                table.add_row(f.name, size_kb, f.modified, key=f.path)
        except CloudProviderError:
            pass

    @on(Button.Pressed, "#select-btn")
    def select_file(self) -> None:
        table = self.query_one("#file-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            self.dismiss(row_key.value)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Admin Screen
# ---------------------------------------------------------------------------

class AdminScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    AdminScreen {
        layout: vertical;
    }
    #admin-sections {
        height: 1fr;
        padding: 0 2;
        overflow-y: auto;
    }
    #db-section {
        height: auto;
        border: solid $accent;
        padding: 0 1;
        margin: 0;
    }
    #db-section Button {
        margin: 0 1;
    }
    #cloud-section {
        height: auto;
        border: solid $accent;
        padding: 0 1;
        margin: 0;
    }
    #cloud-status-label {
        margin: 0;
    }
    #cloud-actions Button {
        margin: 0 1;
    }
    #cloud-actions {
        height: auto;
    }
    #user-section {
        height: 1fr;
        border: solid $accent;
        padding: 0 1;
    }
    #user-actions {
        height: auto;
        margin: 0;
    }
    #user-actions Button {
        margin: 0 1;
    }
    #status-label {
        margin: 0;
        color: $success;
    }
    #admin-back {
        height: 3;
        padding: 0 2;
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with Vertical(id="admin-sections"):
            with Vertical(id="db-section"):
                yield Static("Database Maintenance", markup=False)
                yield Label("", id="status-label")
                with Horizontal():
                    yield Button("Backup Database", id="backup-btn")
                    yield Button("Vacuum Database", id="vacuum-btn")
            with Vertical(id="cloud-section"):
                yield Static("Cloud Sync", markup=False)
                yield Label("Not connected", id="cloud-status-label")
                with Horizontal(id="cloud-actions"):
                    yield Button("Link Account", id="link-btn")
                    yield Button("Select Folder", id="folder-btn", disabled=True)
                    yield Button("Sync Now", id="sync-btn", disabled=True)
                    yield Button("Restore", id="restore-btn", disabled=True)
                    yield Button("Disconnect", id="disconnect-btn", disabled=True)
            with Vertical(id="user-section"):
                yield Static("User Management", markup=False)
                yield InventoryTable(id="user-table")
                with Horizontal(id="user-actions"):
                    yield Button("Create User", id="create-user-btn")
                    yield Button("Delete User", id="del-user-btn", variant="error")
        with Horizontal(id="admin-back"):
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#user-table", InventoryTable)
        table.add_columns("ID", "Username", "Created")
        self._refresh_users()
        self._refresh_cloud_status()

    # --- Cloud helpers ---

    def _get_cloud_provider(self) -> CloudProvider:
        if not hasattr(self.app, "_cloud_provider"):
            self.app._cloud_provider = DropboxProvider(CredentialStore())
        return self.app._cloud_provider

    def _refresh_cloud_status(self) -> None:
        provider = self._get_cloud_provider()
        connected = provider.is_authenticated()
        settings = db.get_cloud_settings(self.app.db_conn, self.app.current_user.id)

        label = self.query_one("#cloud-status-label", Label)
        self.query_one("#link-btn", Button).disabled = connected
        self.query_one("#folder-btn", Button).disabled = not connected
        self.query_one("#sync-btn", Button).disabled = not connected
        self.query_one("#restore-btn", Button).disabled = not connected
        self.query_one("#disconnect-btn", Button).disabled = not connected

        if connected and settings:
            parts = [f"Connected: {provider.provider_name()}"]
            if settings.account_display_name:
                parts.append(f"({settings.account_display_name})")
            if settings.remote_folder:
                parts.append(f"| Folder: {settings.remote_folder}")
            if settings.last_sync_at:
                parts.append(f"| Last sync: {settings.last_sync_at}")
            label.update(" ".join(parts))
        elif connected:
            label.update(f"Connected: {provider.provider_name()}")
        else:
            label.update("Not connected")

    # --- Cloud button handlers ---

    @on(Button.Pressed, "#link-btn")
    def link_account(self) -> None:
        provider = self._get_cloud_provider()
        try:
            url, state = provider.get_auth_url()
            webbrowser.open(url)
        except CloudProviderError:
            app_error(self, ErrorCode.CLOUD_AUTH)
            return

        def on_code(code: str | None) -> None:
            if code is None:
                return
            try:
                info = provider.finish_auth(code, state)
                settings = CloudSettings(
                    user_id=self.app.current_user.id,
                    provider=provider.provider_name(),
                    account_display_name=info.display_name,
                    account_email=info.email,
                    enabled=True,
                )
                db.save_cloud_settings(self.app.db_conn, settings)
                self._set_status("Cloud account linked successfully")
            except (CloudProviderError, Exception):
                app_error(self, ErrorCode.CLOUD_AUTH)
            self._refresh_cloud_status()

        self.app.push_screen(CloudAuthModal(), on_code)

    @on(Button.Pressed, "#folder-btn")
    def select_folder(self) -> None:
        provider = self._get_cloud_provider()

        def on_folder(path: str | None) -> None:
            if path is None:
                return
            settings = db.get_cloud_settings(self.app.db_conn, self.app.current_user.id)
            if settings:
                settings.remote_folder = path
                db.save_cloud_settings(self.app.db_conn, settings)
            else:
                settings = CloudSettings(
                    user_id=self.app.current_user.id,
                    provider=provider.provider_name(),
                    remote_folder=path,
                    enabled=True,
                )
                db.save_cloud_settings(self.app.db_conn, settings)
            self._set_status(f"Cloud folder set to: {path or '/'}")
            self._refresh_cloud_status()

        self.app.push_screen(CloudFolderBrowserModal(provider), on_folder)

    @on(Button.Pressed, "#sync-btn")
    async def sync_now(self) -> None:
        provider = self._get_cloud_provider()
        settings = db.get_cloud_settings(self.app.db_conn, self.app.current_user.id)
        if not settings or not settings.remote_folder:
            self._set_status("Please select a cloud folder first")
            return

        src = db.DB_PATH
        if not src.exists():
            self._set_status("No database file found")
            return

        self._set_cloud_status("Uploading...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_path = f"{settings.remote_folder}/pjourney_{timestamp}.db"

        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            shutil.copy2(str(src), tmp_path)
            await asyncio.to_thread(provider.upload_file, tmp_path, remote_path)
            Path(tmp_path).unlink(missing_ok=True)
            settings.last_sync_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.save_cloud_settings(self.app.db_conn, settings)
            self._set_status(f"Backup uploaded: pjourney_{timestamp}.db")
        except CloudProviderError:
            app_error(self, ErrorCode.CLOUD_UPLOAD)
        except Exception:
            app_error(self, ErrorCode.CLOUD_UPLOAD)
        self._refresh_cloud_status()

    @on(Button.Pressed, "#restore-btn")
    def restore_backup(self) -> None:
        provider = self._get_cloud_provider()
        settings = db.get_cloud_settings(self.app.db_conn, self.app.current_user.id)
        if not settings or not settings.remote_folder:
            self._set_status("Please select a cloud folder first")
            return

        def on_file(remote_path: str | None) -> None:
            if remote_path is None:
                return

            def on_confirm(confirmed: bool) -> None:
                if not confirmed:
                    return
                self._do_restore(provider, remote_path)

            self.app.push_screen(
                ConfirmModal("This will replace your current database. Continue?"),
                on_confirm,
            )

        self.app.push_screen(
            CloudRestoreModal(provider, settings.remote_folder), on_file
        )

    async def _do_restore(self, provider: CloudProvider, remote_path: str) -> None:
        self._set_cloud_status("Downloading...")
        try:
            # Safety backup
            src = db.DB_PATH
            if src.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safety = src.parent / f"pjourney_pre_restore_{timestamp}.db"
                shutil.copy2(str(src), str(safety))

            # Download to temp
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            await asyncio.to_thread(provider.download_file, remote_path, tmp_path)

            # Verify downloaded DB is valid
            try:
                verify_conn = sqlite3.connect(tmp_path)
                result = verify_conn.execute("PRAGMA integrity_check").fetchone()
                verify_conn.close()
                if result[0] != "ok":
                    Path(tmp_path).unlink(missing_ok=True)
                    self._set_status("Downloaded file failed integrity check")
                    return
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                self._set_status("Downloaded file is not a valid database")
                return

            # Replace DB
            self.app.db_conn.close()
            shutil.move(tmp_path, str(src))
            self._set_status("Database restored. Please restart pjourney.")
        except CloudProviderError:
            app_error(self, ErrorCode.CLOUD_DOWNLOAD)
        except Exception:
            app_error(self, ErrorCode.CLOUD_DOWNLOAD)

    @on(Button.Pressed, "#disconnect-btn")
    def disconnect(self) -> None:
        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            provider = self._get_cloud_provider()
            provider.disconnect()
            db.delete_cloud_settings(self.app.db_conn, self.app.current_user.id)
            if hasattr(self.app, "_cloud_provider"):
                del self.app._cloud_provider
            self._set_status("Cloud account disconnected")
            self._refresh_cloud_status()

        self.app.push_screen(
            ConfirmModal("Disconnect cloud account? Your cloud backups will not be deleted."),
            on_confirm,
        )

    def _set_cloud_status(self, msg: str) -> None:
        self.query_one("#cloud-status-label", Label).update(msg)

    # --- User/DB handlers ---

    def _refresh_users(self) -> None:
        try:
            table = self.query_one("#user-table", InventoryTable)
            table.clear()
            users = db.get_users(self.app.db_conn)
            for u in users:
                table.add_row(
                    str(u.id), u.username, str(u.created_at or ""),
                    key=str(u.id),
                )
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-label", Label).update(msg)

    @on(Button.Pressed, "#backup-btn")
    def do_backup(self) -> None:
        src = db.DB_PATH
        if not src.exists():
            self._set_status("No database file found")
            return
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = src.parent / f"pjourney_backup_{timestamp}.db"
            shutil.copy2(str(src), str(dest))
            self._set_status(f"Backup saved: {dest.name}")
        except Exception:
            app_error(self, ErrorCode.IO_BACKUP)

    @on(Button.Pressed, "#vacuum-btn")
    def do_vacuum(self) -> None:
        try:
            db.vacuum_db(self.app.db_conn)
            self._set_status("Database vacuumed successfully")
        except Exception:
            app_error(self, ErrorCode.DB_VACUUM)

    @on(Button.Pressed, "#create-user-btn")
    def create_user(self) -> None:
        def on_result(result: tuple[str, str] | None) -> None:
            if result:
                username, password = result
                try:
                    db.create_user(self.app.db_conn, username, password)
                    self._set_status(f"User '{username}' created")
                    self._refresh_users()
                except Exception:
                    self._set_status(f"Failed to create user (name may exist)")
        self.app.push_screen(CreateUserModal(), on_result)

    @on(Button.Pressed, "#del-user-btn")
    def delete_user(self) -> None:
        table = self.query_one("#user-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            user_id = int(row_key.value)
            if user_id == self.app.current_user.id:
                self._set_status("Cannot delete current user")
                return
            user = db.get_user(self.app.db_conn, user_id)
            if user:
                try:
                    db.delete_user(self.app.db_conn, user_id)
                    self._set_status(f"User '{user.username}' deleted")
                    self._refresh_users()
                except Exception:
                    app_error(self, ErrorCode.DB_DELETE)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
