"""Main Textual App class with screen routing."""

from textual.app import App

from pjourney.db import database as db
from pjourney.db.models import User
from pjourney.errors import ErrorCode, app_error
from pjourney.screens.admin import AdminScreen
from pjourney.screens.cameras import CameraDetailScreen, CamerasScreen
from pjourney.screens.dashboard import DashboardScreen
from pjourney.screens.film_stock import FilmStockScreen
from pjourney.screens.frames import FramesScreen
from pjourney.screens.lenses import LensDetailScreen, LensesScreen
from pjourney.screens.login import LoginScreen
from pjourney.screens.rolls import RollsScreen
from pjourney.screens.splash import SplashScreen


class PJourneyApp(App):
    TITLE = "pjourney"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen,
        "cameras": CamerasScreen,
        "camera_detail": CameraDetailScreen,
        "lenses": LensesScreen,
        "lens_detail": LensDetailScreen,
        "film_stock": FilmStockScreen,
        "rolls": RollsScreen,
        "frames": FramesScreen,
        "admin": AdminScreen,
    }

    current_user: User | None = None

    def __init__(self):
        super().__init__()
        self._startup_error = False
        try:
            self.db_conn = db.get_connection()
            db.init_db(self.db_conn)
        except Exception:
            self.db_conn = None
            self._startup_error = True

    def on_mount(self) -> None:
        self.push_screen(SplashScreen())
        if self._startup_error:
            app_error(self, ErrorCode.DB_CONNECT)

    def _handle_exception(self, error: Exception) -> None:
        """Best-effort safety net: show toast instead of crashing.

        Overrides Textual's private _handle_exception. If notify itself fails,
        falls back silently — the app may crash but nothing is worse than the
        current behaviour.
        """
        try:
            app_error(self, ErrorCode.APP_UNEXPECTED)
        except Exception:
            pass  # Last resort: do nothing, avoid making things worse
