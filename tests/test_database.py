"""Tests for database schema creation and CRUD operations."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pjourney.db import database as db
from pjourney.db.models import Camera, CameraIssue, CloudSettings, DevelopmentStep, FilmStock, Frame, Lens, Roll, RollDevelopment


@pytest.fixture
def conn():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class TestSchema:
    def test_tables_created(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "users" in names
        assert "cameras" in names
        assert "camera_issues" in names
        assert "lenses" in names
        assert "film_stocks" in names
        assert "rolls" in names
        assert "frames" in names
        assert "roll_development" in names
        assert "development_steps" in names

    def test_default_user_created(self, conn):
        users = db.get_users(conn)
        assert len(users) >= 1
        assert users[0].username == "admin"

    def test_init_db_idempotent(self, conn):
        db.init_db(conn)
        db.init_db(conn)
        users = db.get_users(conn)
        assert len(users) == 1


class TestUserCRUD:
    def test_create_user(self, conn):
        user = db.create_user(conn, "testuser", "password123")
        assert user.id is not None
        assert user.username == "testuser"

    def test_verify_password(self, conn):
        db.create_user(conn, "testuser", "password123")
        user = db.verify_password(conn, "testuser", "password123")
        assert user is not None
        assert user.username == "testuser"

    def test_verify_wrong_password(self, conn):
        db.create_user(conn, "testuser", "password123")
        user = db.verify_password(conn, "testuser", "wrong")
        assert user is None

    def test_delete_user(self, conn):
        user = db.create_user(conn, "testuser", "password123")
        db.delete_user(conn, user.id)
        assert db.get_user(conn, user.id) is None


class TestCameraCRUD:
    def test_create_camera(self, conn):
        user = db.get_users(conn)[0]
        camera = Camera(user_id=user.id, name="Test Camera", make="Nikon", model="F3")
        saved = db.save_camera(conn, camera)
        assert saved.id is not None
        assert saved.name == "Test Camera"

    def test_update_camera(self, conn):
        user = db.get_users(conn)[0]
        camera = Camera(user_id=user.id, name="Old Name", make="Nikon", model="F3")
        saved = db.save_camera(conn, camera)
        saved.name = "New Name"
        updated = db.save_camera(conn, saved)
        assert updated.name == "New Name"

    def test_delete_camera(self, conn):
        user = db.get_users(conn)[0]
        camera = Camera(user_id=user.id, name="To Delete", make="Canon")
        saved = db.save_camera(conn, camera)
        db.delete_camera(conn, saved.id)
        assert db.get_camera(conn, saved.id) is None

    def test_list_cameras(self, conn):
        user = db.get_users(conn)[0]
        db.save_camera(conn, Camera(user_id=user.id, name="Cam1", make="Nikon"))
        db.save_camera(conn, Camera(user_id=user.id, name="Cam2", make="Canon"))
        cameras = db.get_cameras(conn, user.id)
        assert len(cameras) == 2


class TestCameraIssues:
    def test_create_issue(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Cam", make="Nikon"))
        issue = CameraIssue(camera_id=camera.id, description="Light leak", date_noted="2024-01-01")
        saved = db.save_camera_issue(conn, issue)
        assert saved.id is not None
        assert saved.description == "Light leak"

    def test_resolve_issue(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Cam", make="Nikon"))
        issue = CameraIssue(camera_id=camera.id, description="Sticky shutter", date_noted="2024-01-01")
        saved = db.save_camera_issue(conn, issue)
        saved.resolved = True
        saved.resolved_date = "2024-02-01"
        updated = db.save_camera_issue(conn, saved)
        assert updated.resolved


class TestLensCRUD:
    def test_create_lens(self, conn):
        user = db.get_users(conn)[0]
        lens = Lens(user_id=user.id, name="50mm f/1.4", make="Nikon", focal_length="50mm", max_aperture=1.4)
        saved = db.save_lens(conn, lens)
        assert saved.id is not None
        assert saved.focal_length == "50mm"

    def test_delete_lens(self, conn):
        user = db.get_users(conn)[0]
        lens = db.save_lens(conn, Lens(user_id=user.id, name="To Delete", make="Canon"))
        db.delete_lens(conn, lens.id)
        assert db.get_lens(conn, lens.id) is None


class TestFilmStockCRUD:
    def test_create_film_stock(self, conn):
        user = db.get_users(conn)[0]
        stock = FilmStock(user_id=user.id, brand="Kodak", name="Portra 400", iso=400)
        saved = db.save_film_stock(conn, stock)
        assert saved.id is not None
        assert saved.brand == "Kodak"

    def test_delete_film_stock(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(user_id=user.id, brand="Ilford", name="HP5"))
        db.delete_film_stock(conn, stock.id)
        assert db.get_film_stock(conn, stock.id) is None


class TestRollCRUD:
    def test_create_roll_with_frames(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            frames_per_roll=36,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id)
        saved = db.create_roll(conn, roll, 36)
        assert saved.id is not None
        assert saved.status == "fresh"
        frames = db.get_frames(conn, saved.id)
        assert len(frames) == 36
        assert frames[0].frame_number == 1
        assert frames[-1].frame_number == 36

    def test_roll_lifecycle(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Gold 200",
            frames_per_roll=24,
        ))
        camera = db.save_camera(conn, Camera(user_id=user.id, name="AE-1", make="Canon"))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 24)

        roll.camera_id = camera.id
        roll.status = "loaded"
        roll = db.update_roll(conn, roll)
        assert roll.status == "loaded"
        assert roll.camera_id == camera.id

        roll.status = "shooting"
        roll = db.update_roll(conn, roll)
        assert roll.status == "shooting"

    def test_delete_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Fuji", name="Superia 400",
            frames_per_roll=24,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 24)
        db.delete_roll(conn, roll.id)
        assert db.get_roll(conn, roll.id) is None
        assert len(db.get_frames(conn, roll.id)) == 0


class TestFrameCRUD:
    def test_update_frame(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Tri-X 400",
            frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        frames = db.get_frames(conn, roll.id)
        frame = frames[0]
        frame.subject = "Golden Gate Bridge"
        frame.aperture = "f/8"
        frame.shutter_speed = "1/250"
        frame.location = "San Francisco"
        updated = db.update_frame(conn, frame)
        assert updated.subject == "Golden Gate Bridge"
        assert updated.aperture == "f/8"


class TestDevelopmentCRUD:
    def _make_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        return db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)

    def test_save_self_development_with_steps(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="B&W")
        steps = [
            DevelopmentStep(chemical_name="Developer", temperature="20C", duration_seconds=480),
            DevelopmentStep(chemical_name="Fixer", temperature="20C", duration_seconds=300),
        ]
        saved = db.save_roll_development(conn, dev, steps)
        assert saved.id is not None
        assert saved.dev_type == "self"
        assert saved.process_type == "B&W"

    def test_get_development_steps(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="B&W")
        steps = [
            DevelopmentStep(chemical_name="Developer", temperature="20C", duration_seconds=480),
            DevelopmentStep(chemical_name="Fixer", temperature="20C", duration_seconds=300),
        ]
        saved = db.save_roll_development(conn, dev, steps)
        fetched_steps = db.get_development_steps(conn, saved.id)
        assert len(fetched_steps) == 2
        assert fetched_steps[0].chemical_name == "Developer"
        assert fetched_steps[0].step_order == 0
        assert fetched_steps[1].chemical_name == "Fixer"
        assert fetched_steps[1].step_order == 1

    def test_save_lab_development(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="DwayneLab", cost_amount=12.50)
        saved = db.save_roll_development(conn, dev, [])
        assert saved.lab_name == "DwayneLab"
        assert saved.cost_amount == 12.50

    def test_get_development_by_roll(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="TestLab")
        db.save_roll_development(conn, dev, [])
        found = db.get_roll_development_by_roll(conn, roll.id)
        assert found is not None
        assert found.lab_name == "TestLab"

    def test_get_development_by_roll_returns_none_when_absent(self, conn):
        roll = self._make_roll(conn)
        result = db.get_roll_development_by_roll(conn, roll.id)
        assert result is None

    def test_delete_development_cascades_steps(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="B&W")
        steps = [DevelopmentStep(chemical_name="Developer", temperature="20C")]
        saved = db.save_roll_development(conn, dev, steps)
        db.delete_roll_development(conn, roll.id)
        assert db.get_roll_development_by_roll(conn, roll.id) is None
        assert db.get_development_steps(conn, saved.id) == []

    def test_roll_delete_cascades_development(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="Lab")
        saved = db.save_roll_development(conn, dev, [])
        dev_id = saved.id
        db.delete_roll(conn, roll.id)
        assert db.get_roll_development(conn, dev_id) is None

    def test_one_development_per_roll_enforced(self, conn):
        import sqlite3 as sqlite3_module
        roll = self._make_roll(conn)
        dev1 = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="Lab1")
        db.save_roll_development(conn, dev1, [])
        dev2 = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="Lab2")
        with pytest.raises(sqlite3_module.IntegrityError):
            db.save_roll_development(conn, dev2, [])

    def test_step_order_preserved(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="C-41")
        steps = [
            DevelopmentStep(chemical_name="Developer", temperature="38C", duration_seconds=210),
            DevelopmentStep(chemical_name="Bleach", temperature="38C", duration_seconds=390),
            DevelopmentStep(chemical_name="Fixer", temperature="38C", duration_seconds=240),
        ]
        saved = db.save_roll_development(conn, dev, steps)
        fetched = db.get_development_steps(conn, saved.id)
        assert fetched[0].chemical_name == "Developer"
        assert fetched[1].chemical_name == "Bleach"
        assert fetched[2].chemical_name == "Fixer"


class TestUtility:
    def test_get_counts(self, conn):
        user = db.get_users(conn)[0]
        counts = db.get_counts(conn, user.id)
        assert counts["cameras"] == 0
        assert counts["lenses"] == 0
        assert counts["film_stocks"] == 0
        assert counts["rolls"] == 0

    def test_get_loaded_cameras(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="FM2", make="Nikon"))
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.camera_id = camera.id
        roll.status = "loaded"
        db.update_roll(conn, roll)
        loaded = db.get_loaded_cameras(conn, user.id)
        assert len(loaded) == 1
        assert loaded[0]["camera_name"] == "FM2"

    def test_vacuum(self, conn):
        db.vacuum_db(conn)


class TestSetRollFramesLens:
    def _make_roll_with_lens(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=4,
        ))
        lens = db.save_lens(conn, Lens(user_id=user.id, name="50mm", make="Nikon"))
        roll = db.create_roll(
            conn, Roll(user_id=user.id, film_stock_id=stock.id), 4
        )
        return roll, lens

    def test_set_lens_on_all_frames(self, conn):
        roll, lens = self._make_roll_with_lens(conn)
        db.set_roll_frames_lens(conn, roll.id, lens.id)
        frames = db.get_frames(conn, roll.id)
        assert all(f.lens_id == lens.id for f in frames)

    def test_clear_lens_from_all_frames(self, conn):
        roll, lens = self._make_roll_with_lens(conn)
        db.set_roll_frames_lens(conn, roll.id, lens.id)
        db.set_roll_frames_lens(conn, roll.id, None)
        frames = db.get_frames(conn, roll.id)
        assert all(f.lens_id is None for f in frames)


class TestDigitalRollCreation:
    def test_create_digital_roll_no_frames_prepopulated(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Digital", name="Memory Card",
            frames_per_roll=0,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 0)
        assert roll.id is not None
        frames = db.get_frames(conn, roll.id)
        assert len(frames) == 0


class TestSaveRollDevelopmentUpdate:
    def _make_roll(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        return db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)

    def test_update_development_replaces_steps(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="B&W")
        steps_v1 = [
            DevelopmentStep(chemical_name="Developer", temperature="20C", duration_seconds=480),
        ]
        saved = db.save_roll_development(conn, dev, steps_v1)
        saved.process_type = "C-41"
        steps_v2 = [
            DevelopmentStep(chemical_name="Color Developer", temperature="38C", duration_seconds=210),
            DevelopmentStep(chemical_name="Bleach", temperature="38C", duration_seconds=390),
        ]
        updated = db.save_roll_development(conn, saved, steps_v2)
        assert updated.process_type == "C-41"
        fetched_steps = db.get_development_steps(conn, updated.id)
        assert len(fetched_steps) == 2
        assert fetched_steps[0].chemical_name == "Color Developer"
        assert fetched_steps[1].chemical_name == "Bleach"

    def test_update_development_can_clear_steps(self, conn):
        roll = self._make_roll(conn)
        dev = RollDevelopment(roll_id=roll.id, dev_type="self", process_type="B&W")
        steps = [DevelopmentStep(chemical_name="Developer", temperature="20C")]
        saved = db.save_roll_development(conn, dev, steps)
        saved.notes = "No steps needed"
        updated = db.save_roll_development(conn, saved, [])
        fetched_steps = db.get_development_steps(conn, updated.id)
        assert len(fetched_steps) == 0


class TestGetUsageStatsPopulated:
    def test_returns_most_used_film_stock(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        for _ in range(3):
            db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        stats = db.get_usage_stats(conn, user.id)
        assert stats["film_stock"] == "Kodak Portra 400"

    def test_returns_most_used_camera(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        camera = db.save_camera(conn, Camera(user_id=user.id, name="FM2", make="Nikon"))
        for _ in range(2):
            roll = db.create_roll(
                conn, Roll(user_id=user.id, film_stock_id=stock.id), 36
            )
            roll.camera_id = camera.id
            db.update_roll(conn, roll)
        stats = db.get_usage_stats(conn, user.id)
        assert stats["camera"] == "FM2"

    def test_returns_most_used_lens(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=4,
        ))
        lens = db.save_lens(conn, Lens(user_id=user.id, name="50mm f/1.4", make="Nikon"))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 4)
        frames = db.get_frames(conn, roll.id)
        for frame in frames:
            frame.lens_id = lens.id
            db.update_frame(conn, frame)
        stats = db.get_usage_stats(conn, user.id)
        assert stats["lens"] == "50mm f/1.4"

    def test_returns_none_when_no_data(self, conn):
        user = db.get_users(conn)[0]
        stats = db.get_usage_stats(conn, user.id)
        assert stats["film_stock"] is None
        assert stats["camera"] is None
        assert stats["lens"] is None
