"""Statistics screen — aggregated photography insights."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.errors import ErrorCode, app_error


class StatsScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    StatsScreen {
        layout: vertical;
    }
    .section-header {
        color: $accent;
        text-style: bold;
        border-bottom: solid $accent;
        margin: 1 0 0 0;
        padding: 0 2;
    }
    .stat-content {
        padding: 0 2;
    }
    #actions-row {
        height: auto;
        padding: 1 2;
        dock: bottom;
    }
    #actions-row Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with VerticalScroll(id="stats-scroll"):
            yield Static("Roll Overview", classes="section-header")
            yield Static("", id="roll-overview-content", classes="stat-content")
            yield Static("Film Usage", classes="section-header")
            yield Static("", id="film-usage-content", classes="stat-content")
            yield Static("Top Shooting Locations", classes="section-header")
            yield Static("", id="locations-content", classes="stat-content")
            yield Static("Equipment Usage", classes="section-header")
            yield Static("", id="equipment-content", classes="stat-content")
            yield Static("Development", classes="section-header")
            yield Static("", id="dev-content", classes="stat-content")
            yield Static("Activity (last 12 months)", classes="section-header")
            yield Static("", id="activity-content", classes="stat-content")
        with Horizontal(id="actions-row"):
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_data()

    def on_screen_resume(self) -> None:
        self._refresh_data()

    def _refresh_data(self) -> None:
        try:
            stats = db.get_stats(self.app.db_conn, self.app.current_user.id)
            self._update_roll_overview(stats)
            self._update_film_usage(stats)
            self._update_locations(stats)
            self._update_equipment(stats)
            self._update_dev(stats)
            self._update_activity(stats)
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

    def _update_roll_overview(self, stats: dict) -> None:
        rbs = stats["rolls_by_status"]
        total = sum(rbs.values())
        lines = [f"Total Rolls: {total}"]
        for status in ["fresh", "loaded", "shooting", "finished", "developing", "developed"]:
            count = rbs.get(status, 0)
            if count:
                lines.append(f"  {status.capitalize()}: {count}")
        lines.append(f"Frames Logged: {stats['total_frames_logged']}")
        self.query_one("#roll-overview-content", Static).update("\n".join(lines))

    def _update_film_usage(self, stats: dict) -> None:
        lines = []
        if stats["top_film_stocks"]:
            lines.append("Top Film Stocks:")
            for item in stats["top_film_stocks"]:
                lines.append(f"  {item['name']} ({item['count']} rolls)")
        else:
            lines.append("No film stock data yet.")

        if stats["rolls_by_format"]:
            lines.append("By Format:")
            for item in stats["rolls_by_format"]:
                lines.append(f"  {item['format']}: {item['count']} rolls")

        if stats["rolls_by_type"]:
            lines.append("By Type:")
            for item in stats["rolls_by_type"]:
                label = "Color" if item["type"] == "color" else "B&W"
                lines.append(f"  {label}: {item['count']} rolls")

        self.query_one("#film-usage-content", Static).update("\n".join(lines))

    def _update_locations(self, stats: dict) -> None:
        locations = stats.get("top_locations", [])
        if locations:
            lines = []
            for item in locations:
                lines.append(f"  {item['location']} ({item['count']} rolls)")
            self.query_one("#locations-content", Static).update("\n".join(lines))
        else:
            self.query_one("#locations-content", Static).update("No location data yet.")

    def _update_equipment(self, stats: dict) -> None:
        lines = []
        if stats["top_cameras"]:
            lines.append("Top Cameras:")
            for item in stats["top_cameras"]:
                lines.append(f"  {item['name']} ({item['count']} rolls)")
        else:
            lines.append("No camera data yet.")

        if stats["top_lenses"]:
            lines.append("Top Lenses:")
            for item in stats["top_lenses"]:
                lines.append(f"  {item['name']} ({item['count']} frames)")
        else:
            lines.append("No lens data yet.")

        self.query_one("#equipment-content", Static).update("\n".join(lines))

    def _update_dev(self, stats: dict) -> None:
        lines = []
        if stats["dev_type_split"]:
            lines.append("Development Split:")
            for dev_type, count in stats["dev_type_split"].items():
                label = "Self" if dev_type == "self" else "Lab"
                lines.append(f"  {label}: {count}")
        else:
            lines.append("No development data yet.")

        cost = stats["total_dev_cost"]
        if cost > 0:
            lines.append(f"Total Lab Cost: ${cost:.2f}")

        self.query_one("#dev-content", Static).update("\n".join(lines))

    def _update_activity(self, stats: dict) -> None:
        months = stats["rolls_by_month"]
        if not months:
            self.query_one("#activity-content", Static).update("No activity data yet.")
            return

        max_count = max(m["count"] for m in months)
        lines = []
        for m in reversed(months):
            bar_len = int((m["count"] / max_count) * 20) if max_count > 0 else 0
            bar = "#" * bar_len
            lines.append(f"  {m['month']}  {bar} {m['count']}")

        self.query_one("#activity-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
