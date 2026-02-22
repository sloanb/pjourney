"""Per-frame detail entry screen."""

from datetime import date

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.containers import VerticalScroll
from textual.widgets import Button, Footer, Input, Label, Select, Static, TextArea

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.db.models import Frame
from pjourney.errors import ErrorCode, app_error
from pjourney.widgets.inventory_table import InventoryTable


class FrameEditModal(ModalScreen[Frame | None]):
    CSS = """
    FrameEditModal {
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
    #form-scroll {
        height: auto;
        max-height: 80%;
    }
    #form-box Label {
        margin: 1 0 0 0;
    }
    #notes {
        height: 4;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, frame: Frame):
        super().__init__()
        self.frame = frame

    def compose(self) -> ComposeResult:
        f = self.frame
        lenses = db.get_lenses(self.app.db_conn, self.app.current_user.id)
        lens_options = [("None", 0)] + [(f"{l.name} ({l.focal_length})", l.id) for l in lenses]
        rating_options = [
            ("Unrated", -1), ("Reject", 0),
            ("1 star", 1), ("2 stars", 2), ("3 stars", 3),
            ("4 stars", 4), ("5 stars", 5),
        ]
        current_rating = f.rating if f.rating is not None else -1

        with Vertical(id="form-box"):
            yield Static(f"Frame #{f.frame_number}", markup=False)
            with VerticalScroll(id="form-scroll"):
                yield Label("Subject")
                yield Input(value=f.subject, id="subject")
                yield Label("Aperture (e.g. f/2.8)")
                yield Input(value=f.aperture, id="aperture")
                yield Label("Shutter Speed (e.g. 1/125)")
                yield Input(value=f.shutter_speed, id="shutter_speed")
                yield Label("Lens")
                yield Select(
                    lens_options,
                    value=f.lens_id or 0,
                    id="lens",
                )
                yield Label("Date Taken (YYYY-MM-DD)")
                yield Input(value=str(f.date_taken or ""), id="date_taken")
                yield Label("Location")
                yield Input(value=f.location, id="location")
                yield Label("Rating")
                yield Select(rating_options, value=current_rating, id="rating")
                yield Label("Notes")
                yield TextArea(f.notes, id="notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        f = self.frame
        f.subject = self.query_one("#subject", Input).value.strip()
        f.aperture = self.query_one("#aperture", Input).value.strip()
        f.shutter_speed = self.query_one("#shutter_speed", Input).value.strip()
        lens_val = self.query_one("#lens", Select).value
        f.lens_id = lens_val if lens_val and lens_val != 0 else None
        date_str = self.query_one("#date_taken", Input).value.strip()
        try:
            f.date_taken = date.fromisoformat(date_str) if date_str else None
        except ValueError:
            app_error(self, ErrorCode.VAL_DATE)
            return
        f.location = self.query_one("#location", Input).value.strip()
        rating_val = self.query_one("#rating", Select).value
        f.rating = rating_val if rating_val is not None and rating_val != -1 else None
        f.notes = self.query_one("#notes", TextArea).text.strip()
        self.dismiss(f)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class FramesScreen(Screen):
    BINDINGS = [
        ("e", "edit_frame", "Edit Frame"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    FramesScreen {
        layout: vertical;
    }
    #roll-info {
        height: auto;
        padding: 1 2;
        border-bottom: solid $accent;
    }
    #frame-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #frame-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Vertical(id="roll-info")
        yield InventoryTable(id="frame-table")
        with Horizontal(id="frame-actions"):
            yield Button("Edit Frame [e]", id="edit-btn")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#frame-table", InventoryTable)
        table.add_columns("#", "Subject", "Aperture", "Shutter", "Lens", "Date", "Location", "Rating")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            roll_id = self.app._frames_roll_id
            conn = self.app.db_conn
            roll = db.get_roll(conn, roll_id)
            if not roll:
                self.app.pop_screen()
                return

            stock = db.get_film_stock(conn, roll.film_stock_id)
            stock_name = f"{stock.brand} {stock.name}" if stock else "?"
            camera = db.get_camera(conn, roll.camera_id) if roll.camera_id else None
            camera_name = camera.name if camera else "Not loaded"

            title = roll.title if roll.title else f"Roll #{roll.id}"
            frames = db.get_frames(conn, roll_id)
            logged_count = sum(1 for f in frames if f.subject)
            total_count = len(frames)
            line2 = f"Camera: {camera_name}  Status: {roll.status}  [{logged_count}/{total_count} logged]"
            if roll.push_pull_stops > 0:
                line2 += f"  Push +{roll.push_pull_stops:g}"
            elif roll.push_pull_stops < 0:
                line2 += f"  Pull {roll.push_pull_stops:g}"

            info = self.query_one("#roll-info", Vertical)
            info.remove_children()
            info.mount(Static(f"{title} — {stock_name}", markup=False))
            info.mount(Static(line2, markup=False))

            table = self.query_one("#frame-table", InventoryTable)
            table.clear()
            for f in frames:
                lens_name = ""
                if f.lens_id:
                    lens = db.get_lens(conn, f.lens_id)
                    lens_name = lens.name if lens else ""
                if f.rating is None:
                    rating_display = "—"
                elif f.rating == 0:
                    rating_display = "✗"
                else:
                    rating_display = "★" * f.rating
                table.add_row(
                    str(f.frame_number), f.subject, f.aperture,
                    f.shutter_speed, lens_name,
                    str(f.date_taken or ""), f.location, rating_display,
                    key=str(f.id),
                )
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

    def _get_selected_frame_id(self) -> int | None:
        table = self.query_one("#frame-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#edit-btn")
    def action_edit_frame(self) -> None:
        frame_id = self._get_selected_frame_id()
        if frame_id is None:
            return
        frame = db.get_frame(self.app.db_conn, frame_id)
        if not frame:
            return

        def on_result(f: Frame | None) -> None:
            if f:
                try:
                    db.update_frame(self.app.db_conn, f)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)
        self.app.push_screen(FrameEditModal(frame), on_result)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
