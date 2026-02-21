"""Tests for database schema creation and CRUD operations."""

import sqlite3
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from pjourney.db import database as db
from pjourney.db.models import Camera, CameraIssue, CloudSettings, DevRecipe, DevRecipeStep, DevelopmentStep, FilmStock, Frame, Lens, LensNote, Roll, RollDevelopment


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

    def test_verify_password_nonexistent_user_returns_none(self, conn):
        result = db.verify_password(conn, "no_such_user", "anypassword")
        assert result is None

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


class TestRollDecrementsQuantity:
    def test_create_roll_decrements_quantity(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            frames_per_roll=36, quantity_on_hand=5,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        updated = db.get_film_stock(conn, stock.id)
        assert updated.quantity_on_hand == 4

    def test_quantity_never_goes_below_zero(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5",
            frames_per_roll=36, quantity_on_hand=0,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        updated = db.get_film_stock(conn, stock.id)
        assert updated.quantity_on_hand == 0


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


# ---------------------------------------------------------------------------
# Migration success-path tests
# ---------------------------------------------------------------------------

# Minimal DDL blocks shared by migration tests — each test builds only the
# tables it needs so that _migrate_db can attempt the ALTER TABLE statements
# without hitting "no such table" errors.

_ROLLS_NO_LENS_ID = """
    CREATE TABLE rolls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        film_stock_id INTEGER NOT NULL,
        camera_id INTEGER,
        status TEXT NOT NULL DEFAULT 'fresh',
        loaded_date DATE,
        finished_date DATE,
        sent_for_dev_date DATE,
        developed_date DATE,
        notes TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""

_CAMERAS_NO_TYPE = """
    CREATE TABLE cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        make TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        serial_number TEXT NOT NULL DEFAULT '',
        year_built INTEGER,
        year_purchased INTEGER,
        purchased_from TEXT,
        description TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""

_FILM_STOCKS_NO_MEDIA_TYPE = """
    CREATE TABLE film_stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        brand TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'color',
        iso INTEGER NOT NULL DEFAULT 400,
        format TEXT NOT NULL DEFAULT '35mm',
        frames_per_roll INTEGER NOT NULL DEFAULT 36,
        notes TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""


class TestMigrateDbSuccessPaths:
    """Verify that _migrate_db applies ALTER TABLE successfully on a DB that
    was created without the migrated columns (simulating an older schema)."""

    def test_migrate_adds_lens_id_to_rolls(self):
        """A DB created without lens_id on rolls gets it added by _migrate_db."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.db"
            conn = db.get_connection(path)
            # Build minimal schema: rolls without lens_id, plus supporting tables
            # that _migrate_db touches (cameras, film_stocks).
            conn.executescript(
                _ROLLS_NO_LENS_ID
                + _CAMERAS_NO_TYPE
                + _FILM_STOCKS_NO_MEDIA_TYPE
            )
            conn.commit()
            # Should succeed and add lens_id column to rolls
            db._migrate_db(conn)
            # Verify via PRAGMA — safe even when foreign-key tables are absent
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(rolls)").fetchall()
            }
            assert "lens_id" in columns
            conn.close()

    def test_migrate_adds_camera_type_and_sensor_size_to_cameras(self):
        """A DB created without camera_type/sensor_size gets both columns added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.db"
            conn = db.get_connection(path)
            # rolls already has lens_id; cameras is missing camera_type/sensor_size
            conn.executescript("""
                CREATE TABLE rolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    film_stock_id INTEGER NOT NULL,
                    lens_id INTEGER,
                    camera_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'fresh',
                    loaded_date DATE,
                    finished_date DATE,
                    sent_for_dev_date DATE,
                    developed_date DATE,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            + _CAMERAS_NO_TYPE
            + _FILM_STOCKS_NO_MEDIA_TYPE)
            conn.commit()
            db._migrate_db(conn)
            # Verify both columns now exist via PRAGMA
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(cameras)").fetchall()
            }
            assert "camera_type" in columns
            assert "sensor_size" in columns
            conn.close()

    def test_migrate_adds_media_type_to_film_stocks(self):
        """A DB without media_type on film_stocks gets it added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.db"
            conn = db.get_connection(path)
            # rolls already has lens_id; cameras already has type columns;
            # film_stocks is missing media_type
            conn.executescript("""
                CREATE TABLE rolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    film_stock_id INTEGER NOT NULL,
                    lens_id INTEGER,
                    camera_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'fresh',
                    loaded_date DATE,
                    finished_date DATE,
                    sent_for_dev_date DATE,
                    developed_date DATE,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    camera_type TEXT NOT NULL DEFAULT 'film',
                    sensor_size TEXT
                );
            """
            + _FILM_STOCKS_NO_MEDIA_TYPE)
            conn.commit()
            db._migrate_db(conn)
            # Verify media_type column now exists via PRAGMA
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(film_stocks)").fetchall()
            }
            assert "media_type" in columns
            conn.close()

    def test_migrate_adds_scan_date_and_scan_notes_to_rolls(self):
        """A DB without scan_date/scan_notes on rolls gets both columns added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.db"
            conn = db.get_connection(path)
            # rolls has title/push_pull_stops but not scan_date/scan_notes
            conn.executescript("""
                CREATE TABLE rolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    film_stock_id INTEGER NOT NULL,
                    lens_id INTEGER,
                    camera_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'fresh',
                    loaded_date DATE,
                    finished_date DATE,
                    sent_for_dev_date DATE,
                    developed_date DATE,
                    notes TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    push_pull_stops REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    camera_type TEXT NOT NULL DEFAULT 'film',
                    sensor_size TEXT
                );
            """
            + _FILM_STOCKS_NO_MEDIA_TYPE)
            conn.commit()
            db._migrate_db(conn)
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(rolls)").fetchall()
            }
            assert "scan_date" in columns
            assert "scan_notes" in columns
            conn.close()


# ---------------------------------------------------------------------------
# verify_password rehash path
# ---------------------------------------------------------------------------

class TestVerifyPasswordRehash:
    """Cover the check_needs_rehash == True branch in verify_password."""

    def test_rehash_updates_stored_hash(self, conn):
        """When the stored hash is flagged as outdated, verify_password
        re-hashes and persists the new hash to the database.

        argon2.PasswordHasher.check_needs_rehash is a read-only C extension
        method so we cannot patch it directly with patch.object.  Instead we
        replace the module-level ``db.ph`` with a lightweight stand-in whose
        verify() succeeds and whose check_needs_rehash() always returns True,
        then restore the original afterwards.
        """
        from unittest.mock import patch, MagicMock

        user = db.create_user(conn, "rehashuser", "correctpass")
        original_hash = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user.id,)
        ).fetchone()["password_hash"]

        # Build a fake PasswordHasher that wraps the real one but overrides
        # check_needs_rehash to return True, triggering the rehash branch.
        real_ph = db.ph
        fake_ph = MagicMock(wraps=real_ph)
        fake_ph.check_needs_rehash.return_value = True
        # hash() must produce a real verifiable hash for the UPDATE to be meaningful
        fake_ph.hash.side_effect = real_ph.hash

        with patch.object(db, "ph", fake_ph):
            result = db.verify_password(conn, "rehashuser", "correctpass")

        assert result is not None
        assert result.username == "rehashuser"
        # The stored hash must have been replaced with the new one
        new_hash = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user.id,)
        ).fetchone()["password_hash"]
        assert new_hash != original_hash


# ---------------------------------------------------------------------------
# Camera issues — list and delete
# ---------------------------------------------------------------------------

class TestCameraIssuesList:
    """Cover get_camera_issues (list) and delete_camera_issue."""

    def test_get_camera_issues_returns_all_for_camera(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Cam", make="Nikon"))
        db.save_camera_issue(conn, CameraIssue(
            camera_id=camera.id, description="Light leak", date_noted="2024-01-01"
        ))
        db.save_camera_issue(conn, CameraIssue(
            camera_id=camera.id, description="Sticky shutter", date_noted="2024-01-02"
        ))
        issues = db.get_camera_issues(conn, camera.id)
        assert len(issues) == 2

    def test_get_camera_issues_returns_empty_when_none(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Cam", make="Nikon"))
        issues = db.get_camera_issues(conn, camera.id)
        assert issues == []

    def test_delete_camera_issue_removes_it(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Cam", make="Canon"))
        issue = db.save_camera_issue(conn, CameraIssue(
            camera_id=camera.id, description="Fungus on glass", date_noted="2024-03-01"
        ))
        db.delete_camera_issue(conn, issue.id)
        remaining = db.get_camera_issues(conn, camera.id)
        assert remaining == []


# ---------------------------------------------------------------------------
# Lens list and update
# ---------------------------------------------------------------------------

class TestLensListAndUpdate:
    """Cover get_lenses (list all) and save_lens update branch."""

    def test_get_lenses_returns_all_for_user(self, conn):
        user = db.get_users(conn)[0]
        db.save_lens(conn, Lens(user_id=user.id, name="50mm f/1.4", make="Nikon"))
        db.save_lens(conn, Lens(user_id=user.id, name="35mm f/2", make="Canon"))
        lenses = db.get_lenses(conn, user.id)
        assert len(lenses) == 2

    def test_get_lenses_returns_empty_when_none(self, conn):
        user = db.get_users(conn)[0]
        assert db.get_lenses(conn, user.id) == []

    def test_update_lens_changes_fields(self, conn):
        user = db.get_users(conn)[0]
        lens = db.save_lens(
            conn,
            Lens(user_id=user.id, name="Old Name", make="Nikon", focal_length="50mm"),
        )
        lens.name = "Updated Name"
        lens.focal_length = "55mm"
        updated = db.save_lens(conn, lens)
        assert updated.name == "Updated Name"
        assert updated.focal_length == "55mm"


# ---------------------------------------------------------------------------
# Lens notes CRUD
# ---------------------------------------------------------------------------

class TestLensNotesCRUD:
    """Cover get_lens_notes, get_lens_note, save_lens_note (insert + update),
    and delete_lens_note."""

    def _make_lens(self, conn):
        user = db.get_users(conn)[0]
        return db.save_lens(conn, Lens(user_id=user.id, name="50mm", make="Nikon"))

    def test_save_lens_note_creates_note(self, conn):
        lens = self._make_lens(conn)
        note = LensNote(lens_id=lens.id, content="Great sharpness wide open")
        saved = db.save_lens_note(conn, note)
        assert saved.id is not None
        assert saved.content == "Great sharpness wide open"

    def test_get_lens_notes_returns_all(self, conn):
        lens = self._make_lens(conn)
        db.save_lens_note(conn, LensNote(lens_id=lens.id, content="Note 1"))
        db.save_lens_note(conn, LensNote(lens_id=lens.id, content="Note 2"))
        notes = db.get_lens_notes(conn, lens.id)
        assert len(notes) == 2

    def test_get_lens_notes_empty_when_none(self, conn):
        lens = self._make_lens(conn)
        assert db.get_lens_notes(conn, lens.id) == []

    def test_get_lens_note_by_id(self, conn):
        lens = self._make_lens(conn)
        saved = db.save_lens_note(conn, LensNote(lens_id=lens.id, content="Specific note"))
        fetched = db.get_lens_note(conn, saved.id)
        assert fetched is not None
        assert fetched.content == "Specific note"

    def test_get_lens_note_returns_none_when_missing(self, conn):
        result = db.get_lens_note(conn, 99999)
        assert result is None

    def test_update_lens_note_changes_content(self, conn):
        lens = self._make_lens(conn)
        saved = db.save_lens_note(conn, LensNote(lens_id=lens.id, content="Original"))
        saved.content = "Updated content"
        updated = db.save_lens_note(conn, saved)
        assert updated.content == "Updated content"

    def test_delete_lens_note_removes_it(self, conn):
        lens = self._make_lens(conn)
        saved = db.save_lens_note(conn, LensNote(lens_id=lens.id, content="To delete"))
        db.delete_lens_note(conn, saved.id)
        assert db.get_lens_note(conn, saved.id) is None


# ---------------------------------------------------------------------------
# Film stock list and update
# ---------------------------------------------------------------------------

class TestFilmStockListAndUpdate:
    """Cover get_film_stocks (list all) and save_film_stock update branch."""

    def test_get_film_stocks_returns_all_for_user(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(user_id=user.id, brand="Kodak", name="Portra 400"))
        db.save_film_stock(conn, FilmStock(user_id=user.id, brand="Ilford", name="HP5"))
        stocks = db.get_film_stocks(conn, user.id)
        assert len(stocks) == 2

    def test_get_film_stocks_returns_empty_when_none(self, conn):
        user = db.get_users(conn)[0]
        assert db.get_film_stocks(conn, user.id) == []

    def test_update_film_stock_changes_fields(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(
            conn,
            FilmStock(user_id=user.id, brand="Kodak", name="Gold 200", iso=200),
        )
        stock.name = "Gold 400"
        stock.iso = 400
        updated = db.save_film_stock(conn, stock)
        assert updated.name == "Gold 400"
        assert updated.iso == 400

    def test_quantity_on_hand_persists(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(
            conn,
            FilmStock(user_id=user.id, brand="Kodak", name="Portra 800", quantity_on_hand=10),
        )
        assert stock.quantity_on_hand == 10
        loaded = db.get_film_stock(conn, stock.id)
        assert loaded.quantity_on_hand == 10


# ---------------------------------------------------------------------------
# get_rolls with status filter
# ---------------------------------------------------------------------------

class TestGetRollsWithStatusFilter:
    """Cover the get_rolls(conn, user_id, status=...) filtered branch."""

    def _make_roll(self, conn, user, brand, name, status="fresh"):
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand=brand, name=name, frames_per_roll=24,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 24)
        if status != "fresh":
            roll.status = status
            roll = db.update_roll(conn, roll)
        return roll

    def test_get_rolls_with_status_filter_returns_only_matching(self, conn):
        user = db.get_users(conn)[0]
        self._make_roll(conn, user, "Kodak", "Portra 400", status="fresh")
        self._make_roll(conn, user, "Fuji", "Superia 400", status="loaded")

        fresh_rolls = db.get_rolls(conn, user.id, status="fresh")
        loaded_rolls = db.get_rolls(conn, user.id, status="loaded")

        assert len(fresh_rolls) == 1
        assert all(r.status == "fresh" for r in fresh_rolls)
        assert len(loaded_rolls) == 1
        assert all(r.status == "loaded" for r in loaded_rolls)

    def test_get_rolls_without_filter_returns_all(self, conn):
        user = db.get_users(conn)[0]
        self._make_roll(conn, user, "Kodak", "Tri-X", status="fresh")
        self._make_roll(conn, user, "Ilford", "HP5", status="shooting")

        all_rolls = db.get_rolls(conn, user.id)
        assert len(all_rolls) == 2

    def test_get_rolls_filter_returns_empty_when_no_match(self, conn):
        user = db.get_users(conn)[0]
        self._make_roll(conn, user, "Kodak", "Portra", status="fresh")

        developed_rolls = db.get_rolls(conn, user.id, status="developed")
        assert developed_rolls == []


# ---------------------------------------------------------------------------
# Roll title and push/pull CRUD
# ---------------------------------------------------------------------------

class TestRollTitleAndPushPull:
    def test_create_roll_with_title(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id, title="Vacation Roll")
        saved = db.create_roll(conn, roll, 36)
        assert saved.title == "Vacation Roll"

    def test_create_roll_with_push_pull(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id, push_pull_stops=2.0)
        saved = db.create_roll(conn, roll, 36)
        assert saved.push_pull_stops == 2.0

    def test_create_roll_defaults_title_and_push_pull(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Fuji", name="Superia 400", frames_per_roll=24,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id)
        saved = db.create_roll(conn, roll, 24)
        assert saved.title == ""
        assert saved.push_pull_stops == 0.0

    def test_update_roll_title(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Tri-X", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.title = "Street Photography"
        updated = db.update_roll(conn, roll)
        assert updated.title == "Street Photography"

    def test_update_roll_push_pull(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="Delta 3200", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.push_pull_stops = -1.0
        updated = db.update_roll(conn, roll)
        assert updated.push_pull_stops == -1.0


# ---------------------------------------------------------------------------
# get_low_stock_items
# ---------------------------------------------------------------------------

class TestGetLowStockItems:
    def test_low_stock_items_returned(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            media_type="analog", quantity_on_hand=2,
        ))
        result = db.get_low_stock_items(conn, user.id)
        assert len(result["low_stock"]) == 1
        assert result["low_stock"][0]["brand"] == "Kodak"
        assert result["low_stock"][0]["quantity"] == 2

    def test_out_of_stock_items_returned(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5",
            media_type="analog", quantity_on_hand=0,
        ))
        result = db.get_low_stock_items(conn, user.id)
        assert len(result["out_of_stock"]) == 1
        assert result["out_of_stock"][0]["brand"] == "Ilford"

    def test_well_stocked_items_excluded(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Gold 200",
            media_type="analog", quantity_on_hand=10,
        ))
        result = db.get_low_stock_items(conn, user.id)
        assert result["low_stock"] == []
        assert result["out_of_stock"] == []

    def test_digital_stocks_excluded(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="SanDisk", name="SD Card",
            media_type="digital", quantity_on_hand=1,
        ))
        result = db.get_low_stock_items(conn, user.id)
        assert result["low_stock"] == []
        assert result["out_of_stock"] == []

    def test_custom_threshold(self, conn):
        user = db.get_users(conn)[0]
        db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 800",
            media_type="analog", quantity_on_hand=5,
        ))
        result = db.get_low_stock_items(conn, user.id, threshold=5)
        assert len(result["low_stock"]) == 1
        result2 = db.get_low_stock_items(conn, user.id, threshold=2)
        assert result2["low_stock"] == []

    def test_empty_database(self, conn):
        user = db.get_users(conn)[0]
        result = db.get_low_stock_items(conn, user.id)
        assert result["low_stock"] == []
        assert result["out_of_stock"] == []


# ---------------------------------------------------------------------------
# Roll scan fields
# ---------------------------------------------------------------------------

class TestRollScanFields:
    def test_roll_defaults_scan_fields(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        assert roll.scan_date is None
        assert roll.scan_notes == ""

    def test_update_roll_sets_scan_fields(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Tri-X", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.scan_date = "2025-06-15"
        roll.scan_notes = "Scanned with Plustek 8200i"
        updated = db.update_roll(conn, roll)
        assert str(updated.scan_date) == "2025-06-15"
        assert updated.scan_notes == "Scanned with Plustek 8200i"

    def test_update_roll_preserves_scan_fields(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.scan_date = "2025-06-15"
        roll.scan_notes = "High res scan"
        db.update_roll(conn, roll)
        # Now update a different field
        roll.notes = "Updated notes"
        updated = db.update_roll(conn, roll)
        assert str(updated.scan_date) == "2025-06-15"
        assert updated.scan_notes == "High res scan"


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_returns_expected_keys(self, conn):
        user = db.get_users(conn)[0]
        stats = db.get_stats(conn, user.id)
        expected_keys = {
            "rolls_by_status", "total_frames_logged", "top_film_stocks",
            "rolls_by_format", "rolls_by_type", "top_cameras", "top_lenses",
            "dev_type_split", "total_dev_cost", "top_locations", "rolls_by_month",
        }
        assert set(stats.keys()) == expected_keys

    def test_empty_database_returns_zeros(self, conn):
        user = db.get_users(conn)[0]
        stats = db.get_stats(conn, user.id)
        assert stats["rolls_by_status"] == {}
        assert stats["total_frames_logged"] == 0
        assert stats["top_film_stocks"] == []
        assert stats["rolls_by_format"] == []
        assert stats["rolls_by_type"] == []
        assert stats["top_cameras"] == []
        assert stats["top_lenses"] == []
        assert stats["dev_type_split"] == {}
        assert stats["total_dev_cost"] == 0.0
        assert stats["rolls_by_month"] == []

    def test_rolls_by_status_counts(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        r1 = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        r2 = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        r2.status = "loaded"
        db.update_roll(conn, r2)
        stats = db.get_stats(conn, user.id)
        assert stats["rolls_by_status"]["fresh"] == 1
        assert stats["rolls_by_status"]["loaded"] == 1

    def test_total_frames_logged_counts_nonempty_subjects(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=3,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 3)
        frames = db.get_frames(conn, roll.id)
        frames[0].subject = "Portrait"
        db.update_frame(conn, frames[0])
        frames[1].subject = "Landscape"
        db.update_frame(conn, frames[1])
        # Frame 3 has empty subject — should not be counted
        stats = db.get_stats(conn, user.id)
        assert stats["total_frames_logged"] == 2

    def test_top_film_stocks_ordered_by_count(self, conn):
        user = db.get_users(conn)[0]
        stock_a = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        stock_b = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_a.id), 36)
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_b.id), 36)
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_b.id), 36)
        stats = db.get_stats(conn, user.id)
        assert stats["top_film_stocks"][0]["name"] == "Ilford HP5"
        assert stats["top_film_stocks"][0]["count"] == 2

    def test_top_film_stocks_limited_to_5(self, conn):
        user = db.get_users(conn)[0]
        for i in range(6):
            stock = db.save_film_stock(conn, FilmStock(
                user_id=user.id, brand=f"Brand{i}", name=f"Film{i}", frames_per_roll=36,
            ))
            db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        stats = db.get_stats(conn, user.id)
        assert len(stats["top_film_stocks"]) == 5

    def test_rolls_by_format(self, conn):
        user = db.get_users(conn)[0]
        stock_35 = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", format="35mm", frames_per_roll=36,
        ))
        stock_120 = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 120", format="120", frames_per_roll=12,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_35.id), 36)
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_120.id), 12)
        stats = db.get_stats(conn, user.id)
        formats = {item["format"]: item["count"] for item in stats["rolls_by_format"]}
        assert formats["35mm"] == 1
        assert formats["120"] == 1

    def test_rolls_by_type_color_vs_bw(self, conn):
        user = db.get_users(conn)[0]
        stock_c = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", type="color", frames_per_roll=36,
        ))
        stock_bw = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", type="black_and_white", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_c.id), 36)
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock_bw.id), 36)
        stats = db.get_stats(conn, user.id)
        types = {item["type"]: item["count"] for item in stats["rolls_by_type"]}
        assert types["color"] == 1
        assert types["black_and_white"] == 1

    def test_top_cameras(self, conn):
        user = db.get_users(conn)[0]
        camera = db.save_camera(conn, Camera(user_id=user.id, name="Nikon F3", make="Nikon"))
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, camera_id=camera.id,
        ), 36)
        stats = db.get_stats(conn, user.id)
        assert stats["top_cameras"][0]["name"] == "Nikon F3"
        assert stats["top_cameras"][0]["count"] == 1

    def test_top_lenses_by_frame_count(self, conn):
        user = db.get_users(conn)[0]
        lens = db.save_lens(conn, Lens(user_id=user.id, name="50mm f/1.4", make="Nikon"))
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=3,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, lens_id=lens.id,
        ), 3)
        stats = db.get_stats(conn, user.id)
        assert stats["top_lenses"][0]["name"] == "50mm f/1.4"
        assert stats["top_lenses"][0]["count"] == 3

    def test_dev_type_split_and_cost(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        dev = RollDevelopment(roll_id=roll.id, dev_type="lab", lab_name="Lab A", cost_amount=15.00)
        db.save_roll_development(conn, dev, [])
        stats = db.get_stats(conn, user.id)
        assert stats["dev_type_split"]["lab"] == 1
        assert stats["total_dev_cost"] == 15.00

    def test_dev_cost_zero_when_no_records(self, conn):
        user = db.get_users(conn)[0]
        stats = db.get_stats(conn, user.id)
        assert stats["total_dev_cost"] == 0.0

    def test_rolls_by_month_excludes_null_loaded_date(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        # Fresh roll has no loaded_date
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        stats = db.get_stats(conn, user.id)
        assert stats["rolls_by_month"] == []

    def test_rolls_by_month_includes_recent(self, conn):
        from datetime import date as d
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.loaded_date = d.today()
        db.update_roll(conn, roll)
        stats = db.get_stats(conn, user.id)
        assert len(stats["rolls_by_month"]) == 1
        assert stats["rolls_by_month"][0]["month"] == d.today().strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Date adapters
# ---------------------------------------------------------------------------

class TestDateAdapters:
    def test_date_binding_no_deprecation_warning(self, conn):
        import warnings
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            roll.loaded_date = date(2025, 6, 15)
            db.update_roll(conn, roll)

    def test_datetime_binding_no_deprecation_warning(self, conn):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            db.create_user(conn, "adaptertest", "pass123")


# ---------------------------------------------------------------------------
# Roll location
# ---------------------------------------------------------------------------

class TestRollLocation:
    def test_create_roll_with_location(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id, location="NYC")
        saved = db.create_roll(conn, roll, 36)
        assert saved.location == "NYC"

    def test_create_roll_default_location(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        roll = Roll(user_id=user.id, film_stock_id=stock.id)
        saved = db.create_roll(conn, roll, 36)
        assert saved.location == ""

    def test_update_roll_location(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Tri-X", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        roll.location = "Tokyo"
        updated = db.update_roll(conn, roll)
        assert updated.location == "Tokyo"

    def test_update_roll_preserves_location(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, location="London",
        ), 36)
        roll.notes = "Updated notes"
        updated = db.update_roll(conn, roll)
        assert updated.location == "London"

    def test_top_locations_in_stats(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, location="NYC",
        ), 36)
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, location="NYC",
        ), 36)
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, location="Tokyo",
        ), 36)
        stats = db.get_stats(conn, user.id)
        assert stats["top_locations"][0]["location"] == "NYC"
        assert stats["top_locations"][0]["count"] == 2

    def test_top_locations_excludes_empty(self, conn):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 36)
        stats = db.get_stats(conn, user.id)
        assert stats["top_locations"] == []

    def test_top_locations_empty_db(self, conn):
        user = db.get_users(conn)[0]
        stats = db.get_stats(conn, user.id)
        assert stats["top_locations"] == []


class TestRollLocationMigration:
    def test_migrate_adds_location_to_rolls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.db"
            conn = db.get_connection(path)
            conn.executescript("""
                CREATE TABLE rolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    film_stock_id INTEGER NOT NULL,
                    lens_id INTEGER,
                    camera_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'fresh',
                    loaded_date DATE,
                    finished_date DATE,
                    sent_for_dev_date DATE,
                    developed_date DATE,
                    notes TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    push_pull_stops REAL NOT NULL DEFAULT 0.0,
                    scan_date DATE,
                    scan_notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    camera_type TEXT NOT NULL DEFAULT 'film',
                    sensor_size TEXT
                );
                CREATE TABLE film_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'color',
                    media_type TEXT NOT NULL DEFAULT 'analog',
                    iso INTEGER NOT NULL DEFAULT 400,
                    format TEXT NOT NULL DEFAULT '35mm',
                    frames_per_roll INTEGER NOT NULL DEFAULT 36,
                    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            db._migrate_db(conn)
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(rolls)").fetchall()
            }
            assert "location" in columns
            conn.close()


# ---------------------------------------------------------------------------
# Dev recipe CRUD
# ---------------------------------------------------------------------------

class TestDevRecipeCRUD:
    def test_create_recipe(self, conn):
        user = db.get_users(conn)[0]
        recipe = DevRecipe(user_id=user.id, name="Standard B&W", process_type="B&W")
        steps = [DevRecipeStep(chemical_name="D-76", temperature="20C", duration_seconds=480)]
        saved = db.save_dev_recipe(conn, recipe, steps)
        assert saved.id is not None
        assert saved.name == "Standard B&W"

    def test_get_recipes(self, conn):
        user = db.get_users(conn)[0]
        db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="B&W Standard", process_type="B&W",
        ), [])
        db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="C-41 Home", process_type="C-41",
        ), [])
        recipes = db.get_dev_recipes(conn, user.id)
        assert len(recipes) == 2

    def test_get_recipe_by_id(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Test Recipe", process_type="E-6",
        ), [])
        fetched = db.get_dev_recipe(conn, saved.id)
        assert fetched is not None
        assert fetched.name == "Test Recipe"

    def test_get_recipe_returns_none_when_missing(self, conn):
        assert db.get_dev_recipe(conn, 99999) is None

    def test_get_recipe_steps(self, conn):
        user = db.get_users(conn)[0]
        steps = [
            DevRecipeStep(chemical_name="Developer", temperature="20C", duration_seconds=480),
            DevRecipeStep(chemical_name="Stop Bath", temperature="20C", duration_seconds=60),
            DevRecipeStep(chemical_name="Fixer", temperature="20C", duration_seconds=300),
        ]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Full B&W", process_type="B&W",
        ), steps)
        fetched_steps = db.get_dev_recipe_steps(conn, saved.id)
        assert len(fetched_steps) == 3
        assert fetched_steps[0].chemical_name == "Developer"
        assert fetched_steps[0].step_order == 0
        assert fetched_steps[2].chemical_name == "Fixer"
        assert fetched_steps[2].step_order == 2

    def test_update_recipe(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Old Name", process_type="B&W",
        ), [DevRecipeStep(chemical_name="D-76")])
        saved.name = "New Name"
        saved.process_type = "C-41"
        new_steps = [
            DevRecipeStep(chemical_name="Color Dev", temperature="38C"),
            DevRecipeStep(chemical_name="Bleach", temperature="38C"),
        ]
        updated = db.save_dev_recipe(conn, saved, new_steps)
        assert updated.name == "New Name"
        assert updated.process_type == "C-41"
        fetched_steps = db.get_dev_recipe_steps(conn, updated.id)
        assert len(fetched_steps) == 2
        assert fetched_steps[0].chemical_name == "Color Dev"

    def test_update_recipe_replaces_steps(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Test", process_type="B&W",
        ), [DevRecipeStep(chemical_name="Developer")])
        db.save_dev_recipe(conn, saved, [])
        assert db.get_dev_recipe_steps(conn, saved.id) == []

    def test_delete_recipe(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="To Delete", process_type="B&W",
        ), [DevRecipeStep(chemical_name="D-76")])
        db.delete_dev_recipe(conn, saved.id)
        assert db.get_dev_recipe(conn, saved.id) is None
        assert db.get_dev_recipe_steps(conn, saved.id) == []

    def test_delete_recipe_cascades_steps(self, conn):
        user = db.get_users(conn)[0]
        steps = [DevRecipeStep(chemical_name="Developer"), DevRecipeStep(chemical_name="Fixer")]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="Cascade Test",
        ), steps)
        recipe_id = saved.id
        db.delete_dev_recipe(conn, recipe_id)
        assert db.get_dev_recipe_steps(conn, recipe_id) == []

    def test_recipe_with_notes(self, conn):
        user = db.get_users(conn)[0]
        saved = db.save_dev_recipe(conn, DevRecipe(
            user_id=user.id, name="With Notes", process_type="B&W",
            notes="Dilution 1+1",
        ), [])
        assert saved.notes == "Dilution 1+1"


class TestDevRecipeSchema:
    def test_dev_recipes_table_exists(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "dev_recipes" in names

    def test_dev_recipe_steps_table_exists(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "dev_recipe_steps" in names
