"""Custom application header widget with ASCII camera art."""

from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from pjourney import __version__

CAMERA_ART = ".-----.\n| (o) |)\n'-----'"


class AppHeader(Widget):
    """App-wide header showing camera art, app name, and version."""

    DEFAULT_CSS = """
    AppHeader {
        height: 3;
        background: $primary;
        color: $text;
        dock: top;
        padding: 0 1;
    }
    """

    def render(self) -> Table:
        grid = Table.grid(expand=True)
        grid.add_column(width=9, no_wrap=True)
        grid.add_column(ratio=1)
        grid.add_column(width=10, no_wrap=True)

        camera = Text(CAMERA_ART, style="bold")
        title = Text("\nPhoto Journey", style="bold", justify="center")
        version = Text(f"\nv{__version__}", justify="right")

        grid.add_row(camera, title, version)
        return grid
