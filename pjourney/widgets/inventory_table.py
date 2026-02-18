"""Reusable data table widget for inventory screens."""

from textual.widgets import DataTable


class InventoryTable(DataTable):
    """A DataTable pre-configured for inventory use."""

    DEFAULT_CSS = """
    InventoryTable {
        height: 1fr;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, cursor_type="row", zebra_stripes=True, **kwargs)
