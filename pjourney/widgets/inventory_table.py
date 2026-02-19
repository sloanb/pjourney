"""Reusable data table widget for inventory screens."""

from textual.binding import Binding
from textual.widgets import DataTable


class InventoryTable(DataTable):
    """A DataTable pre-configured for inventory use."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
        Binding("ctrl+d", "page_down", "Page Down", show=False),
        Binding("ctrl+u", "page_up", "Page Up", show=False),
    ]

    DEFAULT_CSS = """
    InventoryTable {
        height: 1fr;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, cursor_type="row", zebra_stripes=True, **kwargs)

    def action_scroll_home(self) -> None:
        """Move cursor to the first row."""
        if self.row_count > 0:
            self.move_cursor(row=0)

    def action_scroll_end(self) -> None:
        """Move cursor to the last row."""
        if self.row_count > 0:
            self.move_cursor(row=self.row_count - 1)

    def action_page_down(self) -> None:
        """Move cursor down by half a page."""
        if self.row_count > 0:
            visible_rows = max(1, self.size.height - 2)
            half_page = max(1, visible_rows // 2)
            new_row = min(self.cursor_row + half_page, self.row_count - 1)
            self.move_cursor(row=new_row)

    def action_page_up(self) -> None:
        """Move cursor up by half a page."""
        if self.row_count > 0:
            visible_rows = max(1, self.size.height - 2)
            half_page = max(1, visible_rows // 2)
            new_row = max(self.cursor_row - half_page, 0)
            self.move_cursor(row=new_row)
