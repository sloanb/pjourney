"""Tests for model dataclasses."""

from datetime import date, datetime

from pjourney.db.models import (
    ROLL_STATUSES,
    Camera,
    CameraIssue,
    FilmStock,
    Frame,
    Lens,
    Roll,
    User,
)


class TestUserModel:
    def test_defaults(self):
        user = User()
        assert user.id is None
        assert user.username == ""
        assert user.password_hash == ""
        assert user.created_at is None

    def test_with_values(self):
        user = User(id=1, username="admin", password_hash="hash123")
        assert user.id == 1
        assert user.username == "admin"


class TestCameraModel:
    def test_defaults(self):
        camera = Camera()
        assert camera.id is None
        assert camera.user_id == 0
        assert camera.year_built is None
        assert camera.year_purchased is None
        assert camera.purchased_from is None

    def test_with_values(self):
        camera = Camera(
            name="Nikon F3", make="Nikon", model="F3",
            serial_number="12345", year_built=1980,
        )
        assert camera.name == "Nikon F3"
        assert camera.year_built == 1980


class TestCameraIssueModel:
    def test_defaults(self):
        issue = CameraIssue()
        assert issue.resolved is False
        assert issue.resolved_date is None

    def test_resolved(self):
        issue = CameraIssue(
            description="Light leak",
            date_noted=date(2024, 1, 1),
            resolved=True,
            resolved_date=date(2024, 2, 1),
        )
        assert issue.resolved is True


class TestLensModel:
    def test_defaults(self):
        lens = Lens()
        assert lens.max_aperture is None
        assert lens.filter_diameter is None

    def test_with_values(self):
        lens = Lens(
            name="50mm f/1.4", focal_length="50mm",
            max_aperture=1.4, filter_diameter=52.0,
        )
        assert lens.max_aperture == 1.4
        assert lens.filter_diameter == 52.0


class TestFilmStockModel:
    def test_defaults(self):
        stock = FilmStock()
        assert stock.type == "color"
        assert stock.iso == 400
        assert stock.format == "35mm"
        assert stock.frames_per_roll == 36

    def test_bw_stock(self):
        stock = FilmStock(
            brand="Ilford", name="HP5 Plus",
            type="black_and_white", iso=400,
        )
        assert stock.type == "black_and_white"


class TestRollModel:
    def test_defaults(self):
        roll = Roll()
        assert roll.status == "fresh"
        assert roll.camera_id is None
        assert roll.loaded_date is None

    def test_statuses(self):
        assert "fresh" in ROLL_STATUSES
        assert "loaded" in ROLL_STATUSES
        assert "shooting" in ROLL_STATUSES
        assert "finished" in ROLL_STATUSES
        assert "developing" in ROLL_STATUSES
        assert "developed" in ROLL_STATUSES
        assert len(ROLL_STATUSES) == 6


class TestFrameModel:
    def test_defaults(self):
        frame = Frame()
        assert frame.frame_number == 0
        assert frame.lens_id is None
        assert frame.date_taken is None

    def test_with_values(self):
        frame = Frame(
            roll_id=1, frame_number=1,
            subject="Portrait", aperture="f/2.8",
            shutter_speed="1/125", location="Studio",
        )
        assert frame.subject == "Portrait"
        assert frame.aperture == "f/2.8"
