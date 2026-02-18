"""Admin screen — DB maintenance and user management."""

import shutil
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from pjourney.db import database as db
from pjourney.widgets.inventory_table import InventoryTable


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
        padding: 1 2;
    }
    #db-section {
        height: auto;
        border: solid $accent;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    #db-section Button {
        margin: 0 1;
    }
    #user-section {
        height: 1fr;
        border: solid $accent;
        padding: 1 2;
    }
    #user-actions {
        height: auto;
        margin: 1 0 0 0;
    }
    #user-actions Button {
        margin: 0 1;
    }
    #status-label {
        margin: 1 0;
        color: $success;
    }
    #admin-back {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="admin-sections"):
            with Vertical(id="db-section"):
                yield Static("Database Maintenance", markup=False)
                yield Label("", id="status-label")
                with Horizontal():
                    yield Button("Backup Database", id="backup-btn")
                    yield Button("Vacuum Database", id="vacuum-btn")
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

    def _refresh_users(self) -> None:
        table = self.query_one("#user-table", InventoryTable)
        table.clear()
        users = db.get_users(self.app.db_conn)
        for u in users:
            table.add_row(
                str(u.id), u.username, str(u.created_at or ""),
                key=str(u.id),
            )

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-label", Label).update(msg)

    @on(Button.Pressed, "#backup-btn")
    def do_backup(self) -> None:
        src = db.DB_PATH
        if not src.exists():
            self._set_status("No database file found")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = src.parent / f"pjourney_backup_{timestamp}.db"
        shutil.copy2(str(src), str(dest))
        self._set_status(f"Backup saved: {dest.name}")

    @on(Button.Pressed, "#vacuum-btn")
    def do_vacuum(self) -> None:
        db.vacuum_db(self.app.db_conn)
        self._set_status("Database vacuumed successfully")

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
                db.delete_user(self.app.db_conn, user_id)
                self._set_status(f"User '{user.username}' deleted")
                self._refresh_users()

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
