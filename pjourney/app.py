"""Main Textual App class with screen routing."""

from textual.app import App

from pjourney.db import database as db
from pjourney.db.models import User
from pjourney.screens.admin import AdminScreen
from pjourney.screens.cameras import CameraDetailScreen, CamerasScreen
from pjourney.screens.dashboard import DashboardScreen
from pjourney.screens.film_stock import FilmStockScreen
from pjourney.screens.frames import FramesScreen
from pjourney.screens.lenses import LensesScreen
from pjourney.screens.login import LoginScreen
from pjourney.screens.rolls import RollsScreen


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
        "film_stock": FilmStockScreen,
        "rolls": RollsScreen,
        "frames": FramesScreen,
        "admin": AdminScreen,
    }

    current_user: User | None = None

    def __init__(self):
        super().__init__()
        self.db_conn = db.get_connection()
        db.init_db(self.db_conn)

    def on_mount(self) -> None:
        self.push_screen("login")
