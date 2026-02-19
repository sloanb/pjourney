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
    iso: int = 400
    format: str = "35mm"
    frames_per_roll: int = 36
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
