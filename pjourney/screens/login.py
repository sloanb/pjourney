"""Login / user selection screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, Select, Static

from pjourney.db import database as db


class LoginScreen(Screen):
    CSS = """
    LoginScreen {
        align: center middle;
    }
    #login-box {
        width: 60;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
    }
    #login-box Label {
        margin: 1 0 0 0;
    }
    #login-box Input {
        margin: 0 0 1 0;
    }
    #login-box Button {
        margin: 1 1;
        width: 100%;
    }
    #error-label {
        color: $error;
        text-align: center;
    }
    #mode-toggle {
        text-align: center;
        margin: 1 0;
    }
    """

    def __init__(self):
        super().__init__()
        self._create_mode = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="login-box"):
                yield Static("pjourney", id="title", markup=False)
                yield Label("Username")
                yield Input(id="username", placeholder="Username")
                yield Label("Password")
                yield Input(id="password", placeholder="Password", password=True)
                yield Label("", id="error-label")
                yield Button("Login", id="login-btn", variant="primary")
                yield Button("Create Account", id="create-btn", variant="default")

    @on(Button.Pressed, "#login-btn")
    def do_login(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not username or not password:
            self.query_one("#error-label", Label).update("Please enter username and password")
            return
        user = db.verify_password(self.app.db_conn, username, password)
        if user:
            self.app.current_user = user
            self.app.push_screen("dashboard")
        else:
            self.query_one("#error-label", Label).update("Invalid credentials")

    @on(Button.Pressed, "#create-btn")
    def do_create(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not username or not password:
            self.query_one("#error-label", Label).update("Please enter username and password")
            return
        try:
            user = db.create_user(self.app.db_conn, username, password)
            self.app.current_user = user
            self.app.push_screen("dashboard")
        except Exception:
            self.query_one("#error-label", Label).update("Username already exists")
