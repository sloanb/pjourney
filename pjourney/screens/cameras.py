"""Camera list, detail, and issue tracking screens."""

from datetime import date

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static, TextArea

from pjourney.widgets.app_header import AppHeader
from pjourney.widgets.confirm_modal import ConfirmModal

from pjourney.db import database as db
from pjourney.db.models import Camera, CameraIssue
from pjourney.widgets.inventory_table import InventoryTable

CAMERA_TYPES = [("Film", "film"), ("Digital", "digital")]

SENSOR_SIZES = [
    ("Full Frame (35mm)", "full_frame"),
    ("APS-C", "aps_c"),
    ("APS-H", "aps_h"),
    ("Micro Four Thirds", "mft"),
    ("1-inch", "1_inch"),
    ("Medium Format", "medium_format"),
    ("Large Format", "large_format"),
]

_SENSOR_LABEL = {v: k for k, v in SENSOR_SIZES}


class CameraFormModal(ModalScreen[Camera | None]):
    CSS = """
    CameraFormModal {
        align: center middle;
    }
    #form-box {
        width: 130;
        max-width: 95%;
        height: auto;
        max-height: 90%;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #form-columns {
        height: auto;
    }
    #col-left, #col-right {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    #form-box Label {
        margin: 1 0 0 0;
    }
    #form-box Input {
        margin: 0 0 0 0;
    }
    #form-box Select {
        margin: 0 0 0 0;
    }
    #sensor-size-container {
        display: none;
        height: auto;
    }
    .form-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    .form-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, camera: Camera | None = None):
        super().__init__()
        self.camera = camera or Camera()

    def compose(self) -> ComposeResult:
        c = self.camera
        with Vertical(id="form-box"):
            yield Static("Edit Camera" if c.id else "Add Camera", markup=False)
            with Horizontal(id="form-columns"):
                with Vertical(id="col-left"):
                    yield Label("Name")
                    yield Input(value=c.name, id="name")
                    yield Label("Make")
                    yield Input(value=c.make, id="make")
                    yield Label("Model")
                    yield Input(value=c.model, id="model")
                    yield Label("Serial Number")
                    yield Input(value=c.serial_number, id="serial")
                    yield Label("Year Built")
                    yield Input(value=str(c.year_built or ""), id="year_built")
                    yield Label("Year Purchased")
                    yield Input(value=str(c.year_purchased or ""), id="year_purchased")
                with Vertical(id="col-right"):
                    yield Label("Purchased From")
                    yield Input(value=c.purchased_from or "", id="purchased_from")
                    yield Label("Description")
                    yield Input(value=c.description, id="description")
                    yield Label("Notes")
                    yield Input(value=c.notes, id="notes")
                    yield Label("Camera Type")
                    yield Select(CAMERA_TYPES, value=c.camera_type or "film", id="camera_type")
                    with Vertical(id="sensor-size-container"):
                        yield Label("Sensor Size")
                        yield Select(SENSOR_SIZES, value=c.sensor_size if c.sensor_size else Select.NULL,
                                     allow_blank=True, id="sensor_size")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        container = self.query_one("#sensor-size-container")
        container.display = (self.camera.camera_type == "digital")

    @on(Select.Changed, "#camera_type")
    def on_camera_type_changed(self, event: Select.Changed) -> None:
        container = self.query_one("#sensor-size-container")
        container.display = (event.value == "digital")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        c = self.camera
        c.name = self.query_one("#name", Input).value.strip()
        c.make = self.query_one("#make", Input).value.strip()
        c.model = self.query_one("#model", Input).value.strip()
        c.serial_number = self.query_one("#serial", Input).value.strip()
        yb = self.query_one("#year_built", Input).value.strip()
        c.year_built = int(yb) if yb else None
        yp = self.query_one("#year_purchased", Input).value.strip()
        c.year_purchased = int(yp) if yp else None
        c.purchased_from = self.query_one("#purchased_from", Input).value.strip() or None
        c.description = self.query_one("#description", Input).value.strip()
        c.notes = self.query_one("#notes", Input).value.strip()
        c.camera_type = self.query_one("#camera_type", Select).value or "film"
        sensor_val = self.query_one("#sensor_size", Select).value
        c.sensor_size = sensor_val if sensor_val is not Select.NULL else None
        if not c.name:
            return
        c.user_id = self.app.current_user.id
        self.dismiss(c)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class IssueFormModal(ModalScreen[CameraIssue | None]):
    CSS = """
    IssueFormModal {
        align: center middle;
    }
    #issue-form-box {
        width: 60;
        height: auto;
        border: heavy $accent;
        padding: 1 2;
        background: $surface;
    }
    #issue-form-box Label {
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

    def __init__(self, issue: CameraIssue | None = None, camera_id: int = 0):
        super().__init__()
        self.issue = issue or CameraIssue(camera_id=camera_id, date_noted=date.today())

    def compose(self) -> ComposeResult:
        i = self.issue
        with Vertical(id="issue-form-box"):
            yield Static("Edit Issue" if i.id else "Add Issue", markup=False)
            yield Label("Description")
            yield Input(value=i.description, id="issue-desc")
            yield Label("Date Noted (YYYY-MM-DD)")
            yield Input(value=str(i.date_noted or date.today()), id="issue-date")
            yield Label("Notes")
            yield Input(value=i.notes, id="issue-notes")
            with Horizontal(classes="form-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def save(self) -> None:
        i = self.issue
        i.description = self.query_one("#issue-desc", Input).value.strip()
        date_str = self.query_one("#issue-date", Input).value.strip()
        try:
            i.date_noted = date.fromisoformat(date_str)
        except ValueError:
            i.date_noted = date.today()
        i.notes = self.query_one("#issue-notes", Input).value.strip()
        if not i.description:
            return
        self.dismiss(i)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(None)


class CamerasScreen(Screen):
    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("enter", "detail", "Detail"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    CamerasScreen {
        layout: vertical;
    }
    #camera-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #camera-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield InventoryTable(id="camera-table")
        with Horizontal(id="camera-actions"):
            yield Button("Add [a]", id="add-btn")
            yield Button("Edit [e]", id="edit-btn")
            yield Button("Detail [Enter]", id="detail-btn")
            yield Button("Delete [d]", id="del-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#camera-table", InventoryTable)
        table.add_columns("ID", "Name", "Make", "Model", "Serial #", "Year", "Type", "Sensor")
        self._refresh()

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#camera-table", InventoryTable)
        table.clear()
        cameras = db.get_cameras(self.app.db_conn, self.app.current_user.id)
        for c in cameras:
            if c.camera_type == "digital":
                type_label = "Digital"
                sensor_label = _SENSOR_LABEL.get(c.sensor_size, c.sensor_size) if c.sensor_size else "N/A"
            else:
                type_label = "Film"
                sensor_label = "N/A"
            table.add_row(
                str(c.id), c.name, c.make, c.model,
                c.serial_number, str(c.year_built or ""),
                type_label, sensor_label,
                key=str(c.id),
            )

    def _get_selected_id(self) -> int | None:
        table = self.query_one("#camera-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#add-btn")
    def action_add(self) -> None:
        def on_result(camera: Camera | None) -> None:
            if camera:
                db.save_camera(self.app.db_conn, camera)
                self._refresh()
        self.app.push_screen(CameraFormModal(), on_result)

    @on(Button.Pressed, "#edit-btn")
    def action_edit(self) -> None:
        cam_id = self._get_selected_id()
        if cam_id is None:
            return
        camera = db.get_camera(self.app.db_conn, cam_id)
        def on_result(c: Camera | None) -> None:
            if c:
                db.save_camera(self.app.db_conn, c)
                self._refresh()
        self.app.push_screen(CameraFormModal(camera), on_result)

    @on(Button.Pressed, "#del-btn")
    def action_delete(self) -> None:
        cam_id = self._get_selected_id()
        if cam_id is None:
            return
        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                db.delete_camera(self.app.db_conn, cam_id)
                self._refresh()
        self.app.push_screen(ConfirmModal("Delete this camera? This cannot be undone."), on_confirmed)

    @on(Button.Pressed, "#detail-btn")
    def action_detail(self) -> None:
        cam_id = self._get_selected_id()
        if cam_id is None:
            return
        self.app._camera_detail_id = cam_id
        self.app.push_screen("camera_detail")

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()


class CameraDetailScreen(Screen):
    BINDINGS = [
        ("a", "add_issue", "Add Issue"),
        ("r", "resolve_issue", "Resolve"),
        ("escape", "go_back", "Back"),
    ]

    CSS = """
    CameraDetailScreen {
        layout: vertical;
    }
    #camera-info {
        height: auto;
        padding: 1 2;
        border-bottom: solid $accent;
    }
    #issue-section {
        height: 1fr;
        padding: 1 2;
    }
    #issue-actions {
        height: auto;
        padding: 0 2;
        dock: bottom;
    }
    #issue-actions Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Vertical(id="camera-info")
        with Vertical(id="issue-section"):
            yield Static("Issues", markup=False)
            yield InventoryTable(id="issue-table")
        with Horizontal(id="issue-actions"):
            yield Button("Add Issue [a]", id="add-issue-btn")
            yield Button("Resolve [r]", id="resolve-btn")
            yield Button("Delete Issue", id="del-issue-btn", variant="error")
            yield Button("Back [Esc]", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#issue-table", InventoryTable)
        table.add_columns("ID", "Description", "Date Noted", "Resolved", "Notes")
        self._refresh()

    def _refresh(self) -> None:
        cam_id = self.app._camera_detail_id
        camera = db.get_camera(self.app.db_conn, cam_id)
        if not camera:
            self.app.pop_screen()
            return

        info = self.query_one("#camera-info", Vertical)
        info.remove_children()
        info.mount(Static(f"{camera.name}", markup=False))
        info.mount(Static(f"Make: {camera.make}  Model: {camera.model}", markup=False))
        info.mount(Static(f"Serial: {camera.serial_number}", markup=False))
        details = []
        if camera.year_built:
            details.append(f"Built: {camera.year_built}")
        if camera.year_purchased:
            details.append(f"Purchased: {camera.year_purchased}")
        if camera.purchased_from:
            details.append(f"From: {camera.purchased_from}")
        if details:
            info.mount(Static("  ".join(details), markup=False))
        if camera.description:
            info.mount(Static(f"Description: {camera.description}", markup=False))
        if camera.notes:
            info.mount(Static(f"Notes: {camera.notes}", markup=False))
        type_label = "Digital" if camera.camera_type == "digital" else "Film"
        if camera.camera_type == "digital" and camera.sensor_size:
            sensor_label = _SENSOR_LABEL.get(camera.sensor_size, camera.sensor_size)
            info.mount(Static(f"Type: {type_label}  Sensor: {sensor_label}", markup=False))
        else:
            info.mount(Static(f"Type: {type_label}", markup=False))

        table = self.query_one("#issue-table", InventoryTable)
        table.clear()
        issues = db.get_camera_issues(self.app.db_conn, cam_id)
        for i in issues:
            table.add_row(
                str(i.id), i.description, str(i.date_noted),
                "Yes" if i.resolved else "No", i.notes,
                key=str(i.id),
            )

    def _get_selected_issue_id(self) -> int | None:
        table = self.query_one("#issue-table", InventoryTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return int(row_key.value)
        return None

    @on(Button.Pressed, "#add-issue-btn")
    def action_add_issue(self) -> None:
        cam_id = self.app._camera_detail_id
        def on_result(issue: CameraIssue | None) -> None:
            if issue:
                db.save_camera_issue(self.app.db_conn, issue)
                self._refresh()
        self.app.push_screen(IssueFormModal(camera_id=cam_id), on_result)

    @on(Button.Pressed, "#resolve-btn")
    def action_resolve_issue(self) -> None:
        issue_id = self._get_selected_issue_id()
        if issue_id is None:
            return
        row = self.app.db_conn.execute(
            "SELECT * FROM camera_issues WHERE id = ?", (issue_id,)
        ).fetchone()
        if row:
            issue = CameraIssue(**dict(row))
            issue.resolved = True
            issue.resolved_date = date.today()
            db.save_camera_issue(self.app.db_conn, issue)
            self._refresh()

    @on(Button.Pressed, "#del-issue-btn")
    def delete_issue(self) -> None:
        issue_id = self._get_selected_issue_id()
        if issue_id is None:
            return
        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                db.delete_camera_issue(self.app.db_conn, issue_id)
                self._refresh()
        self.app.push_screen(ConfirmModal("Delete this issue? This cannot be undone."), on_confirmed)

    @on(Button.Pressed, "#back-btn")
    def action_go_back(self) -> None:
        self.app.pop_screen()
