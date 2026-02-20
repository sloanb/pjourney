"""Roll lifecycle management screen."""

from datetime import date

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static

from pjourney.widgets.app_header import AppHeader

from pjourney.db import database as db
from pjourney.db.models import PROCESS_TYPES, ROLL_STATUSES, DevelopmentStep, Roll, RollDevelopment
from pjourney.errors import ErrorCode, app_error
from pjourney.widgets.inventory_table import InventoryTable


def _parse_duration(raw: str) -> int | None:
    """Parse 'MM:SS' or plain seconds string into integer seconds. Returns None if unparseable."""
    raw = raw.strip()
    if not raw:
        return None
    if ":" in raw:
        parts = raw.split(":", 1)
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except (ValueError, IndexError):
            return None
    try:
        return int(raw)
    except ValueError:
        return None


def _format_duration(seconds: int | None) -> str:
    """Format integer seconds as 'M:SS' string. Returns '' if None."""
    if seconds is None:
        return ""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


class DevelopmentTypeModal(ModalScreen[str | None]):
    """Choose self-develop or send to lab."""

    CSS = """
    DevelopmentTypeModal {
        align: center middle;
    }
    #type-box {
        width: 64;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #type-box Static {
        margin: 0 0 1 0;
    }
    .type-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .type-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="type-box"):
            yield Static("How will this roll be developed?", markup=False)
            with Horizontal(classes="type-buttons"):
                yield Button("Self Develop", id="self-btn", variant="primary")
                yield Button("Send to Lab", id="lab-btn")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#self-btn")
    def choose_self(self) -> None:
        self.dismiss("self")

    @on(Button.Pressed, "#lab-btn")
    def choose_lab(self) -> None:
        self.dismiss("lab")

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class SelfDevelopModal(ModalScreen[tuple[RollDevelopment, list[DevelopmentStep]] | None]):
    """Enter self-development process details."""

    CSS = """
    SelfDevelopModal {
        align: center middle;
    }
    #self-form-box {
        width: 70;
        height: auto;
        max-height: 40;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #self-form-box Label {
        margin: 1 0 0 0;
    }
    #steps-scroll {
        height: 12;
        border: solid $accent;
        margin: 1 0;
    }
    .step-row {
        height: auto;
        margin: 0 0 1 0;
    }
    .step-row Input {
        width: 1fr;
        margin: 0 1 0 0;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._step_count = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="self-form-box"):
            yield Static("Self Development", markup=False)
            yield Label("Process Type")
            yield Select(
                [(p, p) for p in PROCESS_TYPES],
                value="B&W",
                id="process-select",
            )
            yield Label("Development Steps")
            yield VerticalScroll(id="steps-scroll")
            yield Button("+ Add Step", id="add-step-btn")
            yield Label("Notes")
            yield Input(id="dev-notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self._add_step_row()

    def _add_step_row(self) -> None:
        n = self._step_count
        self._step_count += 1
        scroll = self.query_one("#steps-scroll", VerticalScroll)
        row = Horizontal(id=f"step-row-{n}", classes="step-row")
        scroll.mount(row)
        row.mount(Input(placeholder="Chemical", id=f"step-{n}-chemical"))
        row.mount(Input(placeholder="Temp (e.g. 20C)", id=f"step-{n}-temp"))
        row.mount(Input(placeholder="Time (MM:SS)", id=f"step-{n}-duration"))
        row.mount(Input(placeholder="Agitation", id=f"step-{n}-agitation"))

    @on(Button.Pressed, "#add-step-btn")
    def add_step(self) -> None:
        self._add_step_row()

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        steps = []
        for i in range(self._step_count):
            try:
                chemical = self.query_one(f"#step-{i}-chemical", Input).value.strip()
            except Exception:
                continue
            if not chemical:
                continue
            temp = self.query_one(f"#step-{i}-temp", Input).value.strip()
            duration_raw = self.query_one(f"#step-{i}-duration", Input).value.strip()
            agitation = self.query_one(f"#step-{i}-agitation", Input).value.strip()
            steps.append(DevelopmentStep(
                chemical_name=chemical,
                temperature=temp,
                duration_seconds=_parse_duration(duration_raw),
                agitation=agitation,
            ))
        if not steps:
            return
        process_val = self.query_one("#process-select", Select).value
        process_type = process_val if process_val is not Select.NULL else None
        notes = self.query_one("#dev-notes", Input).value.strip()
        dev = RollDevelopment(dev_type="self", process_type=process_type, notes=notes)
        self.dismiss((dev, steps))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class LabDevelopModal(ModalScreen[tuple[RollDevelopment, list[DevelopmentStep]] | None]):
    """Enter lab development details."""

    CSS = """
    LabDevelopModal {
        align: center middle;
    }
    #lab-form-box {
        width: 60;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #lab-form-box Label {
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
        with Vertical(id="lab-form-box"):
            yield Static("Send to Lab", markup=False)
            yield Label("Lab Name *")
            yield Input(id="lab-name")
            yield Label("Lab Contact (phone/email)")
            yield Input(id="lab-contact")
            yield Label("Cost")
            yield Input(id="lab-cost", placeholder="e.g. 12.50")
            yield Label("Notes")
            yield Input(id="dev-notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        lab_name = self.query_one("#lab-name", Input).value.strip()
        if not lab_name:
            return
        lab_contact = self.query_one("#lab-contact", Input).value.strip() or None
        cost_raw = self.query_one("#lab-cost", Input).value.strip()
        try:
            cost_amount = float(cost_raw) if cost_raw else None
        except ValueError:
            cost_amount = None
        notes = self.query_one("#dev-notes", Input).value.strip()
        dev = RollDevelopment(
            dev_type="lab",
            lab_name=lab_name,
            lab_contact=lab_contact,
            cost_amount=cost_amount,
            notes=notes,
        )
        self.dismiss((dev, []))

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class DevelopmentInfoModal(ModalScreen[None]):
    """Read-only view of development details for a roll."""

    CSS = """
    DevelopmentInfoModal {
        align: center middle;
    }
    #info-box {
        width: 60;
        height: auto;
        max-height: 36;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #info-box Static {
        margin: 0 0 1 0;
    }
    #info-scroll {
        max-height: 28;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    """

    def __init__(self, roll_id: int):
        super().__init__()
        self._roll_id = roll_id

    def compose(self) -> ComposeResult:
        dev = db.get_roll_development_by_roll(self.app.db_conn, self._roll_id)
        with Vertical(id="info-box"):
            yield Static("Development Info", markup=False)
            with VerticalScroll(id="info-scroll"):
                if dev is None:
                    yield Static("This film has not yet been developed.", markup=False)
                elif dev.dev_type == "lab":
                    yield Static(f"Type: Lab", markup=False)
                    yield Static(f"Lab: {dev.lab_name or ''}", markup=False)
                    if dev.lab_contact:
                        yield Static(f"Contact: {dev.lab_contact}", markup=False)
                    if dev.cost_amount is not None:
                        yield Static(f"Cost: ${dev.cost_amount:.2f}", markup=False)
                    if dev.notes:
                        yield Static(f"Notes: {dev.notes}", markup=False)
                else:
                    yield Static(f"Type: Self", markup=False)
                    if dev.process_type:
                        yield Static(f"Process: {dev.process_type}", markup=False)
                    steps = db.get_development_steps(self.app.db_conn, dev.id)
                    for i, step in enumerate(steps):
                        dur = _format_duration(step.duration_seconds)
                        parts = [f"Step {i + 1}: {step.chemical_name}"]
                        if step.temperature:
                            parts.append(f"@ {step.temperature}")
                        if dur:
                            parts.append(f"for {dur}")
                        if step.agitation:
                            parts.append(f"({step.agitation})")
                        yield Static("  ".join(parts), markup=False)
                    if dev.notes:
                        yield Static(f"Notes: {dev.notes}", markup=False)
            with Horizontal(classes="form-buttons"):
                yield Button("Close", id="close-btn", variant="primary")

    @on(Button.Pressed, "#close-btn")
    def close(self) -> None:
        self.dismiss(None)


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
        analog = [s for s in stocks if s.media_type == "analog"]
        digital = [s for s in stocks if s.media_type == "digital"]
        options = []
        if analog:
            options += [("── Analog Film ──", Select.NULL)]
            options += [(f"{s.brand} {s.name} ({s.format}, ISO {s.iso})", s.id) for s in analog]
        if digital:
            options += [("── Memory Cards ──", Select.NULL)]
            options += [(f"{s.brand} {s.name}", s.id) for s in digital]
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
            if stock_id is Select.NULL:
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
            if camera_id is Select.NULL:
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
        ("i", "view_dev_info", "Dev Info"),
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
            yield Button("Dev Info [i]", id="dev-info-btn")
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
        try:
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
        except Exception:
            app_error(self, ErrorCode.DB_LOAD)

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
            try:
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
            except Exception:
                app_error(self, ErrorCode.DB_SAVE)
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
            try:
                roll.camera_id = camera_id
                roll.lens_id = lens_id
                roll.status = "loaded"
                roll.loaded_date = date.today()
                db.update_roll(self.app.db_conn, roll)
                db.set_roll_frames_lens(self.app.db_conn, roll_id, lens_id)
                self._refresh()
            except Exception:
                app_error(self, ErrorCode.DB_SAVE)
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
        next_status = ROLL_STATUSES[idx + 1]
        if next_status == "developing":
            self._start_developing_flow(roll)
            return
        try:
            roll.status = next_status
            today = date.today()
            if roll.status == "finished":
                roll.finished_date = today
            elif roll.status == "developed":
                roll.developed_date = today
            db.update_roll(self.app.db_conn, roll)
            self._refresh()
        except Exception:
            app_error(self, ErrorCode.DB_SAVE)

    def _start_developing_flow(self, roll: Roll) -> None:
        def on_type_chosen(dev_type: str | None) -> None:
            if dev_type is None:
                return
            modal = SelfDevelopModal() if dev_type == "self" else LabDevelopModal()

            def on_dev_result(result) -> None:
                if result is None:
                    return
                dev, steps = result
                try:
                    dev.roll_id = roll.id
                    db.save_roll_development(self.app.db_conn, dev, steps)
                    roll.status = "developing"
                    roll.sent_for_dev_date = date.today()
                    db.update_roll(self.app.db_conn, roll)
                    self._refresh()
                except Exception:
                    app_error(self, ErrorCode.DB_SAVE)

            self.app.push_screen(modal, on_dev_result)

        self.app.push_screen(DevelopmentTypeModal(), on_type_chosen)

    @on(Button.Pressed, "#frames-btn")
    def action_view_frames(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        self.app._frames_roll_id = roll_id
        self.app.push_screen("frames")

    @on(Button.Pressed, "#dev-info-btn")
    def action_view_dev_info(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        self.app.push_screen(DevelopmentInfoModal(roll_id))

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        roll_id = self._get_selected_id()
        if roll_id is None:
            return
        try:
            db.delete_roll(self.app.db_conn, roll_id)
            self._refresh()
        except Exception:
            app_error(self, ErrorCode.DB_DELETE)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
