"""Roll lifecycle management screen."""

from datetime import date

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.db.models import ROLL_STATUSES, Roll
from pjourney.widgets.inventory_table import InventoryTable


class CreateRollModal(ModalScreen[tuple[int, str] | None]):
    """Select a film stock and create a new roll."""

    CSS = """
    CreateRollModal {
        align: center middle;
    }
    #form-box {
        width: 60;
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
        stocks = db.get_film_stocks(self.app.db_conn, self.app.current_user.id)
        options = [(f"{s.brand} {s.name} ({s.format}, ISO {s.iso})", s.id) for s in stocks]
        with Vertical(id="form-box"):
            yield Static("Create New Roll", markup=False)
            yield Label("Film Stock")
            if options:
                yield Select(options, id="stock-select")
            else:
                yield Static("No film stocks available. Add one first.", markup=False)
            yield Label("Notes")
            yield Input(id="notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Create", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        try:
            stock_id = self.query_one("#stock-select", Select).value
            if stock_id is Select.BLANK:
                return
        except Exception:
            return
        notes = self.query_one("#notes", Input).value.strip()
        self.dismiss((stock_id, notes))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class LoadRollModal(ModalScreen[tuple[int, int | None] | None]):
    """Select a camera and optional lens to load a roll into."""

    CSS = """
    LoadRollModal {
        align: center middle;
    }
    #form-box {
        width: 60;
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
        cameras = db.get_cameras(self.app.db_conn, self.app.current_user.id)
        camera_options = [(f"{c.name} ({c.make} {c.model})", c.id) for c in cameras]
        lenses = db.get_lenses(self.app.db_conn, self.app.current_user.id)
        lens_options = [("None", 0)] + [(f"{l.name} ({l.focal_length})", l.id) for l in lenses]
        with Vertical(id="form-box"):
            yield Static("Load Roll into Camera", markup=False)
            yield Label("Camera")
            if camera_options:
                yield Select(camera_options, id="camera-select")
            else:
                yield Static("No cameras available. Add one first.", markup=False)
            yield Label("Lens (installed on camera)")
            yield Select(lens_options, value=0, id="lens-select")
            with Horizontal(classes="form-buttons"):
                yield Button("Load", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        try:
            camera_id = self.query_one("#camera-select", Select).value
            if camera_id is Select.BLANK:
                return
        except Exception:
            return
        lens_val = self.query_one("#lens-select", Select).value
        lens_id = lens_val if lens_val and lens_val != 0 else None
        self.dismiss((camera_id, lens_id))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class RollsScreen(Screen):
    BINDINGS = [
        ("n", "new_roll", "New Roll"),
        ("l", "load", "Load"),
        ("s", "advance_status", "Advance Status"),
        ("f", "view_frames", "Frames"),
        ("d", "delete", "Delete"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    RollsScreen {
        layout: vertical;
    }
    #filter-row {
        height: auto;
        padding: 1 2;
    }
    #filter-row Button {
        margin: 0 1;
    }
    #roll-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #roll-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._filter_status: str | None = None

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with Horizontal(id="filter-row"):
            yield Button("All", id="filter-all", variant="primary")
            for status in ROLL_STATUSES:
                yield Button(status.capitalize(), id=f"filter-{status}")
        yield InventoryTable(id="roll-table")
        with Horizontal(id="roll-actions"):
            yield Button("New Roll [n]", id="new-btn")
            yield Button("Load [l]", id="load-btn")
            yield Button("Advance Status [s]", id="advance-btn")
            yield Button("Frames [f]", id="frames-btn")
            yield Button("Delete [d]", id="del-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#roll-table", InventoryTable)
        table.add_columns("ID", "Film Stock", "Camera", "Status", "Loaded", "Notes")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#roll-table", InventoryTable)
        table.clear()
        conn = self.app.db_conn
        user_id = self.app.current_user.id
        rolls = db.get_rolls(conn, user_id, self._filter_status)
        for r in rolls:
            stock = db.get_film_stock(conn, r.film_stock_id)
            stock_name = f"{stock.brand} {stock.name}" if stock else "?"
            camera = db.get_camera(conn, r.camera_id) if r.camera_id else None
            camera_name = camera.name if camera else ""
            table.add_row(
                str(r.id), stock_name, camera_name, r.status,
                str(r.loaded_date or ""), r.notes,
                key=str(r.id),
            )

    def _get_selected_id(self) -> int | None:
        table = self.query_one("#roll-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#filter-all")
    def filter_all(self) -> None:
        self._filter_status = None
        self._refresh()

    @on(Button.Pressed, "#filter-fresh")
    def filter_fresh(self) -> None:
        self._filter_status = "fresh"
        self._refresh()

    @on(Button.Pressed, "#filter-loaded")
    def filter_loaded(self) -> None:
        self._filter_status = "loaded"
        self._refresh()

    @on(Button.Pressed, "#filter-shooting")
    def filter_shooting(self) -> None:
        self._filter_status = "shooting"
        self._refresh()

    @on(Button.Pressed, "#filter-finished")
    def filter_finished(self) -> None:
        self._filter_status = "finished"
        self._refresh()

    @on(Button.Pressed, "#filter-developing")
    def filter_developing(self) -> None:
        self._filter_status = "developing"
        self._refresh()

    @on(Button.Pressed, "#filter-developed")
    def filter_developed(self) -> None:
        self._filter_status = "developed"
        self._refresh()

    @on(Button.Pressed, "#new-btn")
    def action_new_roll(self) -> None:
        def on_result(result: tuple[int, str] | None) -> None:
            if result is None:
                return
            stock_id, notes = result
            stock = db.get_film_stock(self.app.db_conn, stock_id)
            if not stock:
                return
            roll = Roll(
                user_id=self.app.current_user.id,
                film_stock_id=stock_id,
                notes=notes,
            )
            db.create_roll(self.app.db_conn, roll, stock.frames_per_roll)
            self._refresh()
        self.app.push_screen(CreateRollModal(), on_result)

    @on(Button.Pressed, "#load-btn")
    def action_load(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        roll = db.get_roll(self.app.db_conn, roll_id)
        if not roll or roll.status != "fresh":
            return

        def on_result(result: tuple[int, int | None] | None) -> None:
            if result is None:
                return
            camera_id, lens_id = result
            roll.camera_id = camera_id
            roll.lens_id = lens_id
            roll.status = "loaded"
            roll.loaded_date = date.today()
            db.update_roll(self.app.db_conn, roll)
            db.set_roll_frames_lens(self.app.db_conn, roll_id, lens_id)
            self._refresh()
        self.app.push_screen(LoadRollModal(), on_result)

    @on(Button.Pressed, "#advance-btn")
    def action_advance_status(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        roll = db.get_roll(self.app.db_conn, roll_id)
        if not roll:
            return
        idx = ROLL_STATUSES.index(roll.status)
        if idx >= len(ROLL_STATUSES) - 1:
            return
        roll.status = ROLL_STATUSES[idx + 1]
        today = date.today()
        if roll.status == "finished":
            roll.finished_date = today
        elif roll.status == "developing":
            roll.sent_for_dev_date = today
        elif roll.status == "developed":
            roll.developed_date = today
        db.update_roll(self.app.db_conn, roll)
        self._refresh()

    @on(Button.Pressed, "#frames-btn")
    def action_view_frames(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        self.app._frames_roll_id = roll_id
        self.app.push_screen("frames")

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        db.delete_roll(self.app.db_conn, roll_id)
        self._refresh()

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
