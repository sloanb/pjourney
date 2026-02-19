"""Lens list and management screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.db.models import Lens
from pjourney.widgets.inventory_table import InventoryTable


class LensFormModal(ModalScreen[Lens | None]):
    CSS = """
    LensFormModal {
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

    def __init__(self, lens: Lens | None = None):
        super().__init__()
        self.lens = lens or Lens()

    def compose(self) -> ComposeResult:
        ln = self.lens
        with Vertical(id="form-box"):
            yield Static("Edit Lens" if ln.id else "Add Lens", markup=False)
            yield Label("Name")
            yield Input(value=ln.name, id="name")
            yield Label("Make")
            yield Input(value=ln.make, id="make")
            yield Label("Model")
            yield Input(value=ln.model, id="model")
            yield Label("Focal Length (e.g. 50mm)")
            yield Input(value=ln.focal_length, id="focal_length")
            yield Label("Max Aperture (e.g. 1.4)")
            yield Input(value=str(ln.max_aperture or ""), id="max_aperture")
            yield Label("Filter Diameter (mm)")
            yield Input(value=str(ln.filter_diameter or ""), id="filter_diameter")
            yield Label("Year Built")
            yield Input(value=str(ln.year_built or ""), id="year_built")
            yield Label("Year Purchased")
            yield Input(value=str(ln.year_purchased or ""), id="year_purchased")
            yield Label("Purchase Location")
            yield Input(value=ln.purchase_location or "", id="purchase_location")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        ln = self.lens
        ln.name = self.query_one("#name", Input).value.strip()
        ln.make = self.query_one("#make", Input).value.strip()
        ln.model = self.query_one("#model", Input).value.strip()
        ln.focal_length = self.query_one("#focal_length", Input).value.strip()
        ma = self.query_one("#max_aperture", Input).value.strip()
        ln.max_aperture = float(ma) if ma else None
        fd = self.query_one("#filter_diameter", Input).value.strip()
        ln.filter_diameter = float(fd) if fd else None
        yb = self.query_one("#year_built", Input).value.strip()
        ln.year_built = int(yb) if yb else None
        yp = self.query_one("#year_purchased", Input).value.strip()
        ln.year_purchased = int(yp) if yp else None
        ln.purchase_location = self.query_one("#purchase_location", Input).value.strip() or None
        if not ln.name:
            return
        ln.user_id = self.app.current_user.id
        self.dismiss(ln)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class LensesScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    LensesScreen {
        layout: vertical;
    }
    #lens-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #lens-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield InventoryTable(id="lens-table")
        with Horizontal(id="lens-actions"):
            yield Button("Add [a]", id="add-btn")
            yield Button("Edit [e]", id="edit-btn")
            yield Button("Delete [d]", id="del-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#lens-table", InventoryTable)
        table.add_columns("ID", "Name", "Make", "Focal Length", "Aperture", "Filter")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#lens-table", InventoryTable)
        table.clear()
        lenses = db.get_lenses(self.app.db_conn, self.app.current_user.id)
        for ln in lenses:
            table.add_row(
                str(ln.id), ln.name, ln.make, ln.focal_length,
                f"f/{ln.max_aperture}" if ln.max_aperture else "",
                f"{ln.filter_diameter}mm" if ln.filter_diameter else "",
                key=str(ln.id),
            )

    def _get_selected_id(self) -> int | None:
        table = self.query_one("#lens-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#add-btn")
    def action_add(self) -> None:
        def on_result(lens: Lens | None) -> None:
            if lens:
                db.save_lens(self.app.db_conn, lens)
                self._refresh()
        self.app.push_screen(LensFormModal(), on_result)

    @on(Button.Pressed, "#edit-btn")
    def action_edit(self) -> None:
        lens_id = self._get_selected_id()
        if lens_id is None:
            return
        lens = db.get_lens(self.app.db_conn, lens_id)
        def on_result(ln: Lens | None) -> None:
            if ln:
                db.save_lens(self.app.db_conn, ln)
                self._refresh()
        self.app.push_screen(LensFormModal(lens), on_result)

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        lens_id = self._get_selected_id()
        if lens_id is None:
            return
        db.delete_lens(self.app.db_conn, lens_id)
        self._refresh()

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
