"""Tests for model dataclasses."""

from datetime import date, datetime

from pjourney.db.models import (
    DEVELOPMENT_TYPES,
    PROCESS_TYPES,
    ROLL_STATUSES,
    Camera,
    CameraIssue,
    CloudSettings,
    DevelopmentStep,
    FilmStock,
    Frame,
    Lens,
    Roll,
    RollDevelopment,
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
        assert stock.quantity_on_hand == 0

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


class TestRollDevelopmentModel:
    def test_defaults(self):
        dev = RollDevelopment()
        assert dev.id is None
        assert dev.roll_id == 0
        assert dev.dev_type == "self"
        assert dev.process_type is None
        assert dev.lab_name is None
        assert dev.lab_contact is None
        assert dev.cost_amount is None
        assert dev.notes == ""
        assert dev.created_at is None

    def test_lab_development(self):
        dev = RollDevelopment(
            roll_id=2, dev_type="lab", lab_name="DwayneLab",
            lab_contact="info@dwayne.com", cost_amount=12.50,
        )
        assert dev.dev_type == "lab"
        assert dev.lab_name == "DwayneLab"
        assert dev.cost_amount == 12.50

    def test_development_types_constant(self):
        assert "self" in DEVELOPMENT_TYPES
        assert "lab" in DEVELOPMENT_TYPES
        assert len(DEVELOPMENT_TYPES) == 2

    def test_process_types_constant(self):
        assert "C-41" in PROCESS_TYPES
        assert "E-6" in PROCESS_TYPES
        assert "B&W" in PROCESS_TYPES
        assert "ECN-2" in PROCESS_TYPES
        assert "Other" in PROCESS_TYPES


class TestDevelopmentStepModel:
    def test_defaults(self):
        step = DevelopmentStep()
        assert step.id is None
        assert step.development_id == 0
        assert step.step_order == 0
        assert step.chemical_name == ""
        assert step.temperature == ""
        assert step.duration_seconds is None
        assert step.agitation == ""
        assert step.notes == ""

    def test_with_values(self):
        step = DevelopmentStep(
            development_id=1, step_order=0,
            chemical_name="Kodak D-76", temperature="20C",
            duration_seconds=480, agitation="30s initial, 5s/min",
        )
        assert step.chemical_name == "Kodak D-76"
        assert step.duration_seconds == 480


class TestCloudSettingsModel:
    def test_defaults(self):
        settings = CloudSettings()
        assert settings.id is None
        assert settings.user_id == 0
        assert settings.provider == ""
        assert settings.remote_folder == ""
        assert settings.last_sync_at is None
        assert settings.account_display_name == ""
        assert settings.account_email == ""
        assert settings.enabled is False
        assert settings.created_at is None
        assert settings.updated_at is None

    def test_with_values(self):
        settings = CloudSettings(
            user_id=1, provider="Dropbox",
            remote_folder="/pjourney-backups",
            account_display_name="Jane Doe",
            account_email="jane@example.com",
            enabled=True,
        )
        assert settings.provider == "Dropbox"
        assert settings.remote_folder == "/pjourney-backups"
        assert settings.enabled is True
