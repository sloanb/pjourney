"""Film stock types list and management screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static

from pjourney.widgets.app_header import AppHeader
from pjourney.widgets.confirm_modal import ConfirmModal

from pjourney.db import database as db
from pjourney.db.models import FilmStock
from pjourney.widgets.inventory_table import InventoryTable


FILM_TYPES = [("Color", "color"), ("Black & White", "black_and_white")]
FILM_FORMATS = [
    ("35mm", "35mm"),
    ("120", "120"),
    ("4x5", "4x5"),
    ("8x10", "8x10"),
]


class FilmStockFormModal(ModalScreen[FilmStock | None]):
    CSS = """
    FilmStockFormModal {
        align: center middle;
    }
    #form-box {
        width: 70;
        height: auto;
        max-height: 90%;
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

    def __init__(self, stock: FilmStock | None = None):
        super().__init__()
        self.stock = stock or FilmStock()

    def compose(self) -> ComposeResult:
        s = self.stock
        with Vertical(id="form-box"):
            yield Static("Edit Film Stock" if s.id else "Add Film Stock", markup=False)
            yield Label("Brand (e.g. Kodak, Ilford)")
            yield Input(value=s.brand, id="brand")
            yield Label("Name (e.g. Portra 400, HP5 Plus)")
            yield Input(value=s.name, id="name")
            yield Label("Type")
            yield Select(
                FILM_TYPES,
                value=s.type,
                id="type",
            )
            yield Label("ISO")
            yield Input(value=str(s.iso), id="iso")
            yield Label("Format")
            yield Select(
                FILM_FORMATS,
                value=s.format,
                id="format",
            )
            yield Label("Frames Per Roll")
            yield Input(value=str(s.frames_per_roll), id="frames_per_roll")
            yield Label("Notes")
            yield Input(value=s.notes, id="notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        s = self.stock
        s.brand = self.query_one("#brand", Input).value.strip()
        s.name = self.query_one("#name", Input).value.strip()
        s.type = self.query_one("#type", Select).value
        iso_str = self.query_one("#iso", Input).value.strip()
        s.iso = int(iso_str) if iso_str else 400
        s.format = self.query_one("#format", Select).value
        fpr = self.query_one("#frames_per_roll", Input).value.strip()
        s.frames_per_roll = int(fpr) if fpr else 36
        s.notes = self.query_one("#notes", Input).value.strip()
        if not s.name:
            return
        s.user_id = self.app.current_user.id
        self.dismiss(s)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class FilmStockScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    FilmStockScreen {
        layout: vertical;
    }
    #stock-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #stock-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield InventoryTable(id="stock-table")
        with Horizontal(id="stock-actions"):
            yield Button("Add [a]", id="add-btn")
            yield Button("Edit [e]", id="edit-btn")
            yield Button("Delete [d]", id="del-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#stock-table", InventoryTable)
        table.add_columns("ID", "Brand", "Name", "Type", "ISO", "Format", "Frames")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#stock-table", InventoryTable)
        table.clear()
        stocks = db.get_film_stocks(self.app.db_conn, self.app.current_user.id)
        for s in stocks:
            type_display = "Color" if s.type == "color" else "B&W"
            table.add_row(
                str(s.id), s.brand, s.name, type_display,
                str(s.iso), s.format, str(s.frames_per_roll),
                key=str(s.id),
            )

    def _get_selected_id(self) -> int | None:
        table = self.query_one("#stock-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#add-btn")
    def action_add(self) -> None:
        def on_result(stock: FilmStock | None) -> None:
            if stock:
                db.save_film_stock(self.app.db_conn, stock)
                self._refresh()
        self.app.push_screen(FilmStockFormModal(), on_result)

    @on(Button.Pressed, "#edit-btn")
    def action_edit(self) -> None:
        stock_id = self._get_selected_id()
        if stock_id is None:
            return
        stock = db.get_film_stock(self.app.db_conn, stock_id)
        def on_result(s: FilmStock | None) -> None:
            if s:
                db.save_film_stock(self.app.db_conn, s)
                self._refresh()
        self.app.push_screen(FilmStockFormModal(stock), on_result)

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        stock_id = self._get_selected_id()
        if stock_id is None:
            return
        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                db.delete_film_stock(self.app.db_conn, stock_id)
                self._refresh()
        self.app.push_screen(ConfirmModal("Delete this film stock? This cannot be undone."), on_confirmed)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
