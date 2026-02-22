"""Tests for CSV and JSON export functions."""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Frame, Lens, Roll
from pjourney.export import (
    export_frames_csv,
    export_frames_json,
    export_rolls_csv,
    export_rolls_json,
)


@pytest.fixture
def conn():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


def _read_csv(path: Path) -> list[list[str]]:
    with open(path, newline="") as f:
        return list(csv.reader(f))


class TestExportRollsCSV:
    def test_rolls_csv_header(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "rolls.csv"
        export_rolls_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert rows[0][0] == "Roll ID"
        assert "Title" in rows[0]
        assert "Film Stock" in rows[0]
        assert "Location" in rows[0]
        assert "Push/Pull" in rows[0]

    def test_rolls_csv_data(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            iso=400, format="35mm", frames_per_roll=36,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id,
            title="Vacation", notes="Great trip",
        ), 36)
        out = tmp_path / "rolls.csv"
        export_rolls_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert len(rows) == 2  # header + 1 data row
        data = rows[1]
        assert data[1] == "Vacation"
        assert data[2] == "Kodak Portra 400"

    def test_rolls_csv_location(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, location="NYC",
        ), 36)
        out = tmp_path / "rolls.csv"
        export_rolls_csv(conn, user.id, out)
        rows = _read_csv(out)
        header = rows[0]
        loc_idx = header.index("Location")
        assert rows[1][loc_idx] == "NYC"

    def test_rolls_csv_push_pull(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, push_pull_stops=2.0,
        ), 36)
        out = tmp_path / "rolls.csv"
        export_rolls_csv(conn, user.id, out)
        rows = _read_csv(out)
        header = rows[0]
        pp_idx = header.index("Push/Pull")
        assert rows[1][pp_idx] == "2.0"

    def test_rolls_csv_empty(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "rolls.csv"
        export_rolls_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert len(rows) == 1  # header only


class TestExportFramesCSV:
    def test_frames_csv_header(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert rows[0][0] == "Roll ID"
        assert "Frame #" in rows[0]
        assert "Subject" in rows[0]
        assert "Location" in rows[0]

    def test_frames_csv_data(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=3,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Test Roll",
        ), 3)
        frames = db.get_frames(conn, roll.id)
        frames[0].subject = "Portrait"
        frames[0].aperture = "f/2.8"
        db.update_frame(conn, frames[0])
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert len(rows) == 4  # header + 3 frames
        header = rows[0]
        subject_idx = header.index("Subject")
        assert rows[1][subject_idx] == "Portrait"

    def test_frames_csv_multi_roll(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra", frames_per_roll=2,
        ))
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 2)
        db.create_roll(conn, Roll(user_id=user.id, film_stock_id=stock.id), 2)
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert len(rows) == 5  # header + 4 frames (2 per roll)

    def test_frames_csv_empty(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        assert len(rows) == 1  # header only

    def test_frames_csv_includes_rating(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=2,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Rated",
        ), 2)
        frames = db.get_frames(conn, roll.id)
        frames[0].rating = 5
        db.update_frame(conn, frames[0])
        # frames[1] has no rating
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        header = rows[0]
        rating_idx = header.index("Rating")
        assert rows[1][rating_idx] == "5"
        assert rows[2][rating_idx] == ""

    def test_frames_csv_quoting(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400", frames_per_roll=1,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Roll, with comma",
        ), 1)
        frames = db.get_frames(conn, roll.id)
        frames[0].subject = 'Photo "with quotes"'
        db.update_frame(conn, frames[0])
        out = tmp_path / "frames.csv"
        export_frames_csv(conn, user.id, out)
        rows = _read_csv(out)
        header = rows[0]
        subject_idx = header.index("Subject")
        assert rows[1][subject_idx] == 'Photo "with quotes"'
        title_idx = header.index("Roll Title")
        assert rows[1][title_idx] == "Roll, with comma"


def _read_json(path: Path):
    with open(path) as f:
        return json.load(f)


class TestExportRollsJSON:
    def test_rolls_json_structure(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            iso=400, format="35mm", frames_per_roll=36,
        ))
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id,
            title="Vacation", notes="Great trip", location="NYC",
        ), 36)
        out = tmp_path / "rolls.json"
        export_rolls_json(conn, user.id, out)
        data = _read_json(out)
        assert isinstance(data, list)
        assert len(data) == 1
        roll = data[0]
        assert roll["title"] == "Vacation"
        assert roll["film_stock"] == "Kodak Portra 400"
        assert roll["format"] == "35mm"
        assert roll["iso"] == 400
        assert roll["location"] == "NYC"
        assert roll["notes"] == "Great trip"
        assert roll["status"] == "fresh"

    def test_rolls_json_field_completeness(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Ilford", name="HP5",
            frames_per_roll=36,
        ))
        camera = db.save_camera(conn, Camera(
            user_id=user.id, name="Nikon F3",
        ))
        lens = db.save_lens(conn, Lens(
            user_id=user.id, name="50mm f/1.4",
        ))
        db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id,
            camera_id=camera.id, lens_id=lens.id,
            title="Full", push_pull_stops=1.0,
        ), 36)
        out = tmp_path / "rolls.json"
        export_rolls_json(conn, user.id, out)
        data = _read_json(out)
        roll = data[0]
        expected_keys = {
            "roll_id", "title", "film_stock", "format", "iso",
            "camera", "lens", "status", "location", "push_pull",
            "loaded_date", "finished_date", "developed_date",
            "scan_date", "scan_notes", "notes",
        }
        assert set(roll.keys()) == expected_keys
        assert roll["camera"] == "Nikon F3"
        assert roll["lens"] == "50mm f/1.4"
        assert roll["push_pull"] == 1.0

    def test_rolls_json_empty(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "rolls.json"
        export_rolls_json(conn, user.id, out)
        data = _read_json(out)
        assert data == []


class TestExportFramesJSON:
    def test_frames_json_structure(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            frames_per_roll=2,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Test",
        ), 2)
        frames = db.get_frames(conn, roll.id)
        frames[0].subject = "Portrait"
        frames[0].aperture = "f/2.8"
        frames[0].shutter_speed = "1/125"
        frames[0].location = "Studio"
        db.update_frame(conn, frames[0])
        out = tmp_path / "frames.json"
        export_frames_json(conn, user.id, out)
        data = _read_json(out)
        assert isinstance(data, list)
        assert len(data) == 2
        frame = data[0]
        assert frame["subject"] == "Portrait"
        assert frame["aperture"] == "f/2.8"
        assert frame["shutter_speed"] == "1/125"
        assert frame["location"] == "Studio"
        assert frame["roll_title"] == "Test"

    def test_frames_json_rating_included(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra 400",
            frames_per_roll=2,
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Rated",
        ), 2)
        frames = db.get_frames(conn, roll.id)
        frames[0].rating = 5
        db.update_frame(conn, frames[0])
        out = tmp_path / "frames.json"
        export_frames_json(conn, user.id, out)
        data = _read_json(out)
        assert data[0]["rating"] == 5
        assert data[1]["rating"] is None

    def test_frames_json_empty(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        out = tmp_path / "frames.json"
        export_frames_json(conn, user.id, out)
        data = _read_json(out)
        assert data == []

    def test_frames_json_field_completeness(self, conn, tmp_path):
        user = db.get_users(conn)[0]
        stock = db.save_film_stock(conn, FilmStock(
            user_id=user.id, brand="Kodak", name="Portra",
            frames_per_roll=1,
        ))
        lens = db.save_lens(conn, Lens(
            user_id=user.id, name="50mm f/1.4",
        ))
        roll = db.create_roll(conn, Roll(
            user_id=user.id, film_stock_id=stock.id, title="Full",
        ), 1)
        frames = db.get_frames(conn, roll.id)
        frames[0].lens_id = lens.id
        frames[0].subject = "Test"
        frames[0].notes = "Some notes"
        db.update_frame(conn, frames[0])
        out = tmp_path / "frames.json"
        export_frames_json(conn, user.id, out)
        data = _read_json(out)
        frame = data[0]
        expected_keys = {
            "roll_id", "roll_title", "frame_number", "subject",
            "aperture", "shutter_speed", "lens", "date_taken",
            "location", "rating", "notes",
        }
        assert set(frame.keys()) == expected_keys
        assert frame["lens"] == "50mm f/1.4"
        assert frame["notes"] == "Some notes"
