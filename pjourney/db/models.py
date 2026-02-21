"""Dataclasses for all database entities."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class User:
    id: int | None = None
    username: str = ""
    password_hash: str = ""
    created_at: datetime | None = None


@dataclass
class Camera:
    id: int | None = None
    user_id: int = 0
    name: str = ""
    make: str = ""
    model: str = ""
    serial_number: str = ""
    year_built: int | None = None
    year_purchased: int | None = None
    purchased_from: str | None = None
    description: str = ""
    notes: str = ""
    camera_type: str = "film"          # "film" or "digital"
    sensor_size: str | None = None     # Only for digital cameras
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class CameraIssue:
    id: int | None = None
    camera_id: int = 0
    description: str = ""
    date_noted: date | None = None
    resolved: bool = False
    resolved_date: date | None = None
    notes: str = ""


@dataclass
class Lens:
    id: int | None = None
    user_id: int = 0
    name: str = ""
    make: str = ""
    model: str = ""
    focal_length: str = ""
    max_aperture: float | None = None
    filter_diameter: float | None = None
    year_built: int | None = None
    year_purchased: int | None = None
    purchase_location: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class LensNote:
    id: int | None = None
    lens_id: int = 0
    content: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class FilmStock:
    id: int | None = None
    user_id: int = 0
    brand: str = ""
    name: str = ""
    type: str = "color"  # "color" or "black_and_white"
    media_type: str = "analog"  # "analog" or "digital"
    iso: int = 400
    format: str = "35mm"
    frames_per_roll: int = 36
    quantity_on_hand: int = 0
    notes: str = ""
    created_at: datetime | None = None


ROLL_STATUSES = ["fresh", "loaded", "shooting", "finished", "developing", "developed"]


@dataclass
class Roll:
    id: int | None = None
    user_id: int = 0
    film_stock_id: int = 0
    camera_id: int | None = None
    lens_id: int | None = None
    status: str = "fresh"
    loaded_date: date | None = None
    finished_date: date | None = None
    sent_for_dev_date: date | None = None
    developed_date: date | None = None
    notes: str = ""
    title: str = ""
    push_pull_stops: float = 0.0
    scan_date: date | None = None
    scan_notes: str = ""
    location: str = ""
    created_at: datetime | None = None


@dataclass
class Frame:
    id: int | None = None
    roll_id: int = 0
    frame_number: int = 0
    subject: str = ""
    aperture: str = ""
    shutter_speed: str = ""
    lens_id: int | None = None
    date_taken: date | None = None
    location: str = ""
    notes: str = ""


DEVELOPMENT_TYPES = ["self", "lab"]
PROCESS_TYPES = ["C-41", "E-6", "B&W", "ECN-2", "Other"]


@dataclass
class RollDevelopment:
    id: int | None = None
    roll_id: int = 0
    dev_type: str = "self"           # "self" or "lab"
    process_type: str | None = None  # self only
    lab_name: str | None = None      # lab only (required for lab)
    lab_contact: str | None = None   # lab only
    cost_amount: float | None = None # lab only
    notes: str = ""
    created_at: datetime | None = None


@dataclass
class CloudSettings:
    id: int | None = None
    user_id: int = 0
    provider: str = ""
    remote_folder: str = ""
    last_sync_at: str | None = None
    account_display_name: str = ""
    account_email: str = ""
    enabled: bool = False
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class DevelopmentStep:
    id: int | None = None
    development_id: int = 0
    step_order: int = 0
    chemical_name: str = ""
    temperature: str = ""       # stored as text, e.g. "20°C", "68°F"
    duration_seconds: int | None = None
    agitation: str = ""
    notes: str = ""


@dataclass
class DevRecipe:
    id: int | None = None
    user_id: int = 0
    name: str = ""
    process_type: str = "B&W"
    notes: str = ""
    created_at: datetime | None = None


@dataclass
class DevRecipeStep:
    id: int | None = None
    recipe_id: int = 0
    step_order: int = 0
    chemical_name: str = ""
    temperature: str = ""
    duration_seconds: int | None = None
    agitation: str = ""
    notes: str = ""
