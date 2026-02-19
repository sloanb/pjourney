"""Splash screen with Leica M3 ASCII art."""

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Static

LEICA_M3_OPEN = """\
  ┌─────────────────────────────────────────────────────────┐
  │  [S]   ERNST LEITZ WETZLAR GMBH       [RF]  [VF]   ▶  │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │      ╭──────────────╮                                   │
  │     ╱  ╭──────────╮  ╲      ┌───────────────────────┐   │
  │    │   │  ╭────╮  │   │     │                       │   │
  │    │   │  │  ◎ │  │   │     │                       │   │
  │    │   │  ╰────╯  │   │     └───────────────────────┘   │
  │     ╲  ╰──────────╯  ╱                                  │
  │      ╰──────────────╯        L E I C A   M 3            │
  │                                                         │
  └─────────────────────────────────────────────────────────┘"""

LEICA_M3_CLICKED = """\
  ┌─────────────────────────────────────────────────────────┐
  │  [S]   ERNST LEITZ WETZLAR GMBH       [RF]  [VF]   ▶  │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │      ╭──────────────╮                                   │
  │     ╱  ╭──────────╮  ╲      ┌───────────────────────┐   │
  │    │   │  ╭────╮  │   │     │                       │   │
  │    │   │  │ ▓▓ │  │   │     │                       │   │
  │    │   │  ╰────╯  │   │     └───────────────────────┘   │
  │     ╲  ╰──────────╯  ╱                                  │
  │      ╰──────────────╯        L E I C A   M 3            │
  │                                                         │
  └─────────────────────────────────────────────────────────┘"""


class SplashScreen(Screen):
    CSS = """
    SplashScreen {
        align: center middle;
        background: $surface;
    }
    #camera {
        text-align: center;
    }
    #status {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
        height: 1;
    }
    SplashScreen.flash {
        background: white;
    }
    SplashScreen.flash #camera {
        color: black;
    }
    SplashScreen.flash #status {
        color: black;
    }
    """

    def __init__(self, goodbye: bool = False) -> None:
        super().__init__()
        self._goodbye = goodbye

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical():
                yield Static(LEICA_M3_OPEN, id="camera", markup=False)
                msg = "Goodbye, Mr. Photographer Friend." if self._goodbye else ""
                yield Static(msg, id="status", markup=False)

    def on_mount(self) -> None:
        if self._goodbye:
            self.set_timer(0.8, self._shutter_click)
            self.set_timer(2.5, self.app.exit)
        else:
            self.set_timer(1.2, self._shutter_click)
            self.set_timer(2.0, self._go_to_login)

    def _shutter_click(self) -> None:
        self.query_one("#camera", Static).update(LEICA_M3_CLICKED)
        self.add_class("flash")
        self.query_one("#status", Static).update("~ click ~")
        self.set_timer(0.12, self._restore_after_flash)

    def _restore_after_flash(self) -> None:
        self.remove_class("flash")
        self.query_one("#camera", Static).update(LEICA_M3_OPEN)

    def _go_to_login(self) -> None:
        self.app.switch_screen("login")
