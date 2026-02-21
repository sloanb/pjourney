"""CSV export functions for rolls and frames data."""

import csv
import sqlite3
from pathlib import Path

from pjourney.db import database as db


def export_rolls_csv(conn: sqlite3.Connection, user_id: int, output_path: Path) -> None:
    """Write all rolls for a user to a CSV file."""
    rolls = db.get_rolls(conn, user_id)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Roll ID", "Title", "Film Stock", "Format", "ISO", "Camera", "Lens",
            "Status", "Location", "Push/Pull", "Loaded Date", "Finished Date",
            "Developed Date", "Scan Date", "Scan Notes", "Notes",
        ])
        for r in rolls:
            stock = db.get_film_stock(conn, r.film_stock_id)
            stock_name = f"{stock.brand} {stock.name}" if stock else ""
            stock_format = stock.format if stock else ""
            stock_iso = stock.iso if stock else ""
            camera = db.get_camera(conn, r.camera_id) if r.camera_id else None
            camera_name = camera.name if camera else ""
            lens = db.get_lens(conn, r.lens_id) if r.lens_id else None
            lens_name = lens.name if lens else ""
            pp = r.push_pull_stops if r.push_pull_stops != 0.0 else ""
            writer.writerow([
                r.id, r.title, stock_name, stock_format, stock_iso,
                camera_name, lens_name, r.status, r.location, pp,
                r.loaded_date or "", r.finished_date or "",
                r.developed_date or "", r.scan_date or "",
                r.scan_notes, r.notes,
            ])


def export_frames_csv(conn: sqlite3.Connection, user_id: int, output_path: Path) -> None:
    """Write all frames for a user's rolls to a CSV file."""
    rolls = db.get_rolls(conn, user_id)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Roll ID", "Roll Title", "Frame #", "Subject", "Aperture",
            "Shutter Speed", "Lens", "Date Taken", "Location", "Notes",
        ])
        for r in rolls:
            frames = db.get_frames(conn, r.id)
            for frame in frames:
                lens = db.get_lens(conn, frame.lens_id) if frame.lens_id else None
                lens_name = lens.name if lens else ""
                writer.writerow([
                    r.id, r.title, frame.frame_number, frame.subject,
                    frame.aperture, frame.shutter_speed, lens_name,
                    frame.date_taken or "", frame.location, frame.notes,
                ])
