"""Dashboard screen — inventory summary and navigation."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.errors import ErrorCode, app_error


class DashboardScreen(Screen):
    BINDINGS = [
        ("c", "go_cameras", "Cameras"),
        ("l", "go_lenses", "Lenses"),
        ("f", "go_film_stock", "Film Stock"),
        ("r", "go_rolls", "Rolls"),
        ("a", "go_admin", "Admin"),
        ("q", "quit", "Quit"),
    ]

    CSS = """
    DashboardScreen {
        layout: vertical;
    }
    #stats-row {
        height: auto;
        padding: 1 2;
    }
    .stat-box {
        width: 1fr;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        margin: 0 1;
        text-align: center;
    }
    .stat-value {
        text-style: bold;
        text-align: center;
    }
    .stat-label {
        text-align: center;
        color: $text-muted;
    }
    #favorites-row {
        height: auto;
        padding: 0 2 1 2;
    }
    .fav-box {
        width: 1fr;
        height: auto;
        border: solid $success;
        padding: 1 2;
        margin: 0 1;
        text-align: center;
    }
    .fav-value {
        text-style: bold;
        text-align: center;
        color: $success;
    }
    .fav-label {
        text-align: center;
        color: $text-muted;
    }
    #loaded-section {
        height: auto;
        padding: 1 2;
        max-height: 50%;
    }
    #loaded-section .loaded-item {
        padding: 0 2;
    }
    #nav-row {
        height: auto;
        padding: 1 2;
        dock: bottom;
    }
    #nav-row Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with Horizontal(id="stats-row"):
            with Vertical(classes="stat-box"):
                yield Label("0", id="camera-count", classes="stat-value")
                yield Label("Cameras", classes="stat-label")
            with Vertical(classes="stat-box"):
                yield Label("0", id="lens-count", classes="stat-value")
                yield Label("Lenses", classes="stat-label")
            with Vertical(classes="stat-box"):
                yield Label("0", id="stock-count", classes="stat-value")
                yield Label("Film Stocks", classes="stat-label")
            with Vertical(classes="stat-box"):
                yield Label("0", id="roll-count", classes="stat-value")
                yield Label("Rolls", classes="stat-label")
        with Horizontal(id="favorites-row"):
            with Vertical(classes="fav-box"):
                yield Label("—", id="fav-camera", classes="fav-value")
                yield Label("Most Used Camera", classes="fav-label")
            with Vertical(classes="fav-box"):
                yield Label("—", id="fav-lens", classes="fav-value")
                yield Label("Most Used Lens", classes="fav-label")
            with Vertical(classes="fav-box"):
                yield Label("—", id="fav-film", classes="fav-value")
                yield Label("Most Used Film", classes="fav-label")
        with Vertical(id="loaded-section"):
            yield Static("Currently Loaded Cameras", markup=False)
            yield Vertical(id="loaded-list")
        with Horizontal(id="nav-row"):
            yield Button("Cameras [c]", id="btn-cameras")
            yield Button("Lenses [l]", id="btn-lenses")
            yield Button("Film Stock [f]", id="btn-film-stock")
            yield Button("Rolls [r]", id="btn-rolls")
            yield Button("Admin [a]", id="btn-admin")
        yield Footer()

    def on_screen_resume(self) -> None:
        self._refresh_data()

    def on_mount(self) -> None:
        self._refresh_data()

    def _refresh_data(self) -> None:
        try:
            user_id = self.app.current_user.id
            conn = self.app.db_conn
            counts = db.get_counts(conn, user_id)
            self.query_one("#camera-count", Label).update(str(counts["cameras"]))
            self.query_one("#lens-count", Label).update(str(counts["lenses"]))
            self.query_one("#stock-count", Label).update(str(counts["film_stocks"]))
            self.query_one("#roll-count", Label).update(str(counts["rolls"]))

            stats = db.get_usage_stats(conn, user_id)
            self.query_one("#fav-camera", Label).update(stats["camera"] or "—")
            self.query_one("#fav-lens", Label).update(stats["lens"] or "—")
            self.query_one("#fav-film", Label).update(stats["film_stock"] or "—")

            loaded = db.get_loaded_cameras(conn, user_id)
            loaded_list = self.query_one("#loaded-list", Vertical)
            loaded_list.remove_children()
            if loaded:
                for item in loaded:
                    loaded_list.mount(
                        Static(
                            f"  {item['camera_name']} — {item['film_name']} ({item['status']})",
                            classes="loaded-item",
                            markup=False,
                        )
                    )
            else:
                loaded_list.mount(Static("  No cameras currently loaded", markup=False))
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

    @on(Button.Pressed, "#btn-cameras")
    def go_cameras_btn(self) -> None:
        self.app.push_screen("cameras")

    @on(Button.Pressed, "#btn-lenses")
    def go_lenses_btn(self) -> None:
        self.app.push_screen("lenses")

    @on(Button.Pressed, "#btn-film-stock")
    def go_film_stock_btn(self) -> None:
        self.app.push_screen("film_stock")

    @on(Button.Pressed, "#btn-rolls")
    def go_rolls_btn(self) -> None:
        self.app.push_screen("rolls")

    @on(Button.Pressed, "#btn-admin")
    def go_admin_btn(self) -> None:
        self.app.push_screen("admin")

    def action_go_cameras(self) -> None:
        self.app.push_screen("cameras")

    def action_go_lenses(self) -> None:
        self.app.push_screen("lenses")

    def action_go_film_stock(self) -> None:
        self.app.push_screen("film_stock")

    def action_go_rolls(self) -> None:
        self.app.push_screen("rolls")

    def action_go_admin(self) -> None:
        self.app.push_screen("admin")

    def action_quit(self) -> None:
        from pjourney.screens.splash import SplashScreen
        self.app.push_screen(SplashScreen(goodbye=True))
