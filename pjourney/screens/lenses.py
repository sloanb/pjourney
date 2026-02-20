"""Lens list, detail, and notes screens."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Static, TextArea

from pjourney.widgets.app_header import AppHeader
from pjourney.widgets.confirm_modal import ConfirmModal

from pjourney.db import database as db
from pjourney.db.models import Lens, LensNote
from pjourney.errors import ErrorCode, app_error
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
        fd = self.query_one("#filter_diameter", Input).value.strip()
        try:
            ln.max_aperture = float(ma) if ma else None
            ln.filter_diameter = float(fd) if fd else None
        except ValueError:
            app_error(self, ErrorCode.VAL_NUMBER, detail="Aperture and filter size must be numbers (e.g. 1.4, 52.0).")
            return
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


class LensNoteFormModal(ModalScreen[LensNote | None]):
    CSS = """
    LensNoteFormModal {
        align: center middle;
    }
    #note-form-box {
        width: 80;
        height: auto;
        max-height: 90%;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #note-form-box Label {
        margin: 1 0 0 0;
    }
    #note-content {
        height: 12;
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

    def __init__(self, note: LensNote | None = None, lens_id: int = 0):
        super().__init__()
        self.note = note or LensNote(lens_id=lens_id)

    def compose(self) -> ComposeResult:
        with Vertical(id="note-form-box"):
            yield Static("Edit Note" if self.note.id else "Add Note", markup=False)
            yield Label("Note")
            yield TextArea(self.note.content, id="note-content")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        content = self.query_one("#note-content", TextArea).text.strip()
        if not content:
            return
        self.note.content = content
        self.dismiss(self.note)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class LensesScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("enter", "notes", "Notes"),
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
            yield Button("Notes [Enter]", id="notes-btn")
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
        try:
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
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

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
                try:
                    db.save_lens(self.app.db_conn, lens)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)
        self.app.push_screen(LensFormModal(), on_result)

    @on(Button.Pressed, "#edit-btn")
    def action_edit(self) -> None:
        lens_id = self._get_selected_id()
        if lens_id is None:
            return
        lens = db.get_lens(self.app.db_conn, lens_id)
        def on_result(ln: Lens | None) -> None:
            if ln:
                try:
                    db.save_lens(self.app.db_conn, ln)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)
        self.app.push_screen(LensFormModal(lens), on_result)

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        lens_id = self._get_selected_id()
        if lens_id is None:
            return
        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                try:
                    db.delete_lens(self.app.db_conn, lens_id)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_DELETE)
        self.app.push_screen(ConfirmModal("Delete this lens? This cannot be undone."), on_confirmed)

    @on(Button.Pressed, "#notes-btn")
    def action_notes(self) -> None:
        lens_id = self._get_selected_id()
        if lens_id is None:
            return
        self.app._lens_detail_id = lens_id
        self.app.push_screen("lens_detail")

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()


class LensDetailScreen(Screen):
    BINDINGS = [
        ("a", "add_note", "Add Note"),
        ("e", "edit_note", "Edit"),
        ("d", "delete_note", "Delete"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    LensDetailScreen {
        layout: vertical;
    }
    #lens-info {
        height: auto;
        padding: 1 2;
        border-bottom: solid $accent;
    }
    #notes-section {
        height: 1fr;
        padding: 0 2;
    }
    #notes-section Static {
        padding: 1 0 0 0;
    }
    #note-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #note-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Vertical(id="lens-info")
        with Vertical(id="notes-section"):
            yield Static("Notes", markup=False)
            yield InventoryTable(id="notes-table")
        with Horizontal(id="note-actions"):
            yield Button("Add Note [a]", id="add-note-btn")
            yield Button("Edit [e]", id="edit-note-btn")
            yield Button("Delete [d]", id="del-note-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#notes-table", InventoryTable)
        table.add_columns("ID", "Note", "Created", "Updated")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            lens_id = self.app._lens_detail_id
            lens = db.get_lens(self.app.db_conn, lens_id)
            if not lens:
                self.app.pop_screen()
                return

            info = self.query_one("#lens-info", Vertical)
            info.remove_children()
            info.mount(Static(f"{lens.name}", markup=False))
            parts = []
            if lens.make:
                parts.append(f"Make: {lens.make}")
            if lens.model:
                parts.append(f"Model: {lens.model}")
            if lens.focal_length:
                parts.append(f"Focal: {lens.focal_length}")
            if lens.max_aperture:
                parts.append(f"f/{lens.max_aperture}")
            if lens.filter_diameter:
                parts.append(f"Filter: {lens.filter_diameter}mm")
            if parts:
                info.mount(Static("  ".join(parts), markup=False))
            details = []
            if lens.year_built:
                details.append(f"Built: {lens.year_built}")
            if lens.year_purchased:
                details.append(f"Purchased: {lens.year_purchased}")
            if lens.purchase_location:
                details.append(f"From: {lens.purchase_location}")
            if details:
                info.mount(Static("  ".join(details), markup=False))

            table = self.query_one("#notes-table", InventoryTable)
            table.clear()
            notes = db.get_lens_notes(self.app.db_conn, lens_id)
            for n in notes:
                preview = n.content.replace("\n", " ")
                if len(preview) > 70:
                    preview = preview[:70] + "..."
                created = str(n.created_at)[:16] if n.created_at else ""
                updated = str(n.updated_at)[:16] if n.updated_at else ""
                table.add_row(str(n.id), preview, created, updated, key=str(n.id))
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

    def _get_selected_note_id(self) -> int | None:
        table = self.query_one("#notes-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#add-note-btn")
    def action_add_note(self) -> None:
        lens_id = self.app._lens_detail_id
        def on_result(note: LensNote | None) -> None:
            if note:
                try:
                    db.save_lens_note(self.app.db_conn, note)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)
        self.app.push_screen(LensNoteFormModal(lens_id=lens_id), on_result)

    @on(Button.Pressed, "#edit-note-btn")
    def action_edit_note(self) -> None:
        note_id = self._get_selected_note_id()
        if note_id is None:
            return
        note = db.get_lens_note(self.app.db_conn, note_id)
        if not note:
            return
        def on_result(n: LensNote | None) -> None:
            if n:
                try:
                    db.save_lens_note(self.app.db_conn, n)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)
        self.app.push_screen(LensNoteFormModal(note), on_result)

    @on(Button.Pressed, "#del-note-btn")
    def action_delete_note(self) -> None:
        note_id = self._get_selected_note_id()
        if note_id is None:
            return
        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                try:
                    db.delete_lens_note(self.app.db_conn, note_id)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_DELETE)
        self.app.push_screen(ConfirmModal("Delete this note? This cannot be undone."), on_confirmed)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
