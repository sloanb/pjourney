"""Reusable confirmation dialog modal."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmModal(ModalScreen[bool]):
    """A simple yes/no confirmation dialog. Dismisses with True on confirm."""

    CSS = """
    ConfirmModal {
        align: center middle;
    }
    #confirm-box {
        width: 50;
        height: auto;
        border: heavy $error;
        padding: 1 2;
        background: $surface;
    }
    #confirm-message {
        margin: 0 0 1 0;
    }
    #confirm-buttons {
        height: auto;
        margin: 1 0 0 0;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str, confirm_label: str = "Delete", confirm_variant: str = "error") -> None:
        super().__init__()
        self.message = message
        self._confirm_label = confirm_label
        self._confirm_variant = confirm_variant

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(self.message, id="confirm-message", markup=False)
            with Horizontal(id="confirm-buttons"):
                yield Button(self._confirm_label, id="confirm-btn", variant=self._confirm_variant)
                yield Button("Cancel", id="cancel-btn")

    @on(Button.Pressed, "#confirm-btn")
    def confirm(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-btn")
    def cancel(self) -> None:
        self.dismiss(False)
