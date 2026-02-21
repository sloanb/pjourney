"""Tests for CSV export functions."""

import csv
import tempfile
from pathlib import Path

import pytest

from pjourney.db import database as db
from pjourney.db.models import Camera, FilmStock, Frame, Lens, Roll
from pjourney.export import export_frames_csv, export_rolls_csv


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
