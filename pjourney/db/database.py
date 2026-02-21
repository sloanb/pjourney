"""Database connection management, schema creation, and CRUD operations."""

import sqlite3
from datetime import date, datetime
from pathlib import Path

from argon2 import PasswordHasher

from .models import Camera, CameraIssue, CloudSettings, DevRecipe, DevRecipeStep, DevelopmentStep, FilmStock, Frame, Lens, LensNote, Roll, RollDevelopment, User

DB_PATH = Path.home() / ".pjourney" / "pjourney.db"

# Suppress Python 3.12+ deprecation warning for date/datetime binding
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())

ph = PasswordHasher()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            serial_number TEXT NOT NULL DEFAULT '',
            year_built INTEGER,
            year_purchased INTEGER,
            purchased_from TEXT,
            description TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            camera_type TEXT NOT NULL DEFAULT 'film',
            sensor_size TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS camera_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            date_noted DATE NOT NULL,
            resolved BOOLEAN NOT NULL DEFAULT 0,
            resolved_date DATE,
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS lenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            focal_length TEXT NOT NULL DEFAULT '',
            max_aperture REAL,
            filter_diameter REAL,
            year_built INTEGER,
            year_purchased INTEGER,
            purchase_location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lens_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lens_id INTEGER NOT NULL REFERENCES lenses(id) ON DELETE CASCADE,
            content TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS film_stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            brand TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'color',
            iso INTEGER NOT NULL DEFAULT 400,
            format TEXT NOT NULL DEFAULT '35mm',
            frames_per_roll INTEGER NOT NULL DEFAULT 36,
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            film_stock_id INTEGER NOT NULL REFERENCES film_stocks(id),
            camera_id INTEGER REFERENCES cameras(id),
            lens_id INTEGER REFERENCES lenses(id),
            status TEXT NOT NULL DEFAULT 'fresh',
            loaded_date DATE,
            finished_date DATE,
            sent_for_dev_date DATE,
            developed_date DATE,
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_id INTEGER NOT NULL REFERENCES rolls(id) ON DELETE CASCADE,
            frame_number INTEGER NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            aperture TEXT NOT NULL DEFAULT '',
            shutter_speed TEXT NOT NULL DEFAULT '',
            lens_id INTEGER REFERENCES lenses(id),
            date_taken DATE,
            location TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS roll_development (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_id INTEGER NOT NULL UNIQUE REFERENCES rolls(id) ON DELETE CASCADE,
            dev_type TEXT NOT NULL DEFAULT 'self',
            process_type TEXT,
            lab_name TEXT,
            lab_contact TEXT,
            cost_amount REAL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS development_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            development_id INTEGER NOT NULL REFERENCES roll_development(id) ON DELETE CASCADE,
            step_order INTEGER NOT NULL DEFAULT 0,
            chemical_name TEXT NOT NULL DEFAULT '',
            temperature TEXT NOT NULL DEFAULT '',
            duration_seconds INTEGER,
            agitation TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS dev_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            process_type TEXT NOT NULL DEFAULT 'B&W',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dev_recipe_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL REFERENCES dev_recipes(id) ON DELETE CASCADE,
            step_order INTEGER NOT NULL DEFAULT 0,
            chemical_name TEXT NOT NULL DEFAULT '',
            temperature TEXT NOT NULL DEFAULT '',
            duration_seconds INTEGER,
            agitation TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS cloud_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            provider TEXT NOT NULL DEFAULT '',
            remote_folder TEXT NOT NULL DEFAULT '',
            last_sync_at TEXT,
            account_display_name TEXT NOT NULL DEFAULT '',
            account_email TEXT NOT NULL DEFAULT '',
            enabled BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    _migrate_db(conn)
    _ensure_default_user(conn)


def _migrate_db(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for existing databases."""
    try:
        conn.execute("ALTER TABLE rolls ADD COLUMN lens_id INTEGER REFERENCES lenses(id)")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    for col, definition in [
        ("camera_type", "TEXT NOT NULL DEFAULT 'film'"),
        ("sensor_size", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE cameras ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    try:
        conn.execute("ALTER TABLE film_stocks ADD COLUMN media_type TEXT NOT NULL DEFAULT 'analog'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE film_stocks ADD COLUMN quantity_on_hand INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    for col, definition in [
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("push_pull_stops", "REAL NOT NULL DEFAULT 0.0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE rolls ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    for col, definition in [
        ("scan_date", "DATE"),
        ("scan_notes", "TEXT NOT NULL DEFAULT ''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE rolls ADD COLUMN {col} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    try:
        conn.execute("ALTER TABLE rolls ADD COLUMN location TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists


def _ensure_default_user(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
    if row is None:
        hashed = ph.hash("pjourney")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", hashed),
        )
        conn.commit()


# --- User CRUD ---

def get_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    return [User(**dict(r)) for r in rows]


def get_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User(**dict(row)) if row else None


def verify_password(conn: sqlite3.Connection, username: str, password: str) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        return None
    user = User(**dict(row))
    try:
        ph.verify(user.password_hash, password)
        if ph.check_needs_rehash(user.password_hash):
            new_hash = ph.hash(password)
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user.id))
            conn.commit()
        return user
    except Exception:
        return None


def create_user(conn: sqlite3.Connection, username: str, password: str) -> User:
    hashed = ph.hash(password)
    cur = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hashed),
    )
    conn.commit()
    return get_user(conn, cur.lastrowid)


def delete_user(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()


# --- Camera CRUD ---

def get_cameras(conn: sqlite3.Connection, user_id: int) -> list[Camera]:
    rows = conn.execute(
        "SELECT * FROM cameras WHERE user_id = ? ORDER BY name", (user_id,)
    ).fetchall()
    return [Camera(**dict(r)) for r in rows]


def get_camera(conn: sqlite3.Connection, camera_id: int) -> Camera | None:
    row = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    return Camera(**dict(row)) if row else None


def save_camera(conn: sqlite3.Connection, camera: Camera) -> Camera:
    now = datetime.now().isoformat()
    if camera.id is None:
        cur = conn.execute(
            """INSERT INTO cameras (user_id, name, make, model, serial_number,
               year_built, year_purchased, purchased_from, description, notes,
               camera_type, sensor_size, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (camera.user_id, camera.name, camera.make, camera.model,
             camera.serial_number, camera.year_built, camera.year_purchased,
             camera.purchased_from, camera.description, camera.notes,
             camera.camera_type, camera.sensor_size, now, now),
        )
        conn.commit()
        return get_camera(conn, cur.lastrowid)
    else:
        conn.execute(
            """UPDATE cameras SET name=?, make=?, model=?, serial_number=?,
               year_built=?, year_purchased=?, purchased_from=?, description=?,
               notes=?, camera_type=?, sensor_size=?, updated_at=? WHERE id=?""",
            (camera.name, camera.make, camera.model, camera.serial_number,
             camera.year_built, camera.year_purchased, camera.purchased_from,
             camera.description, camera.notes, camera.camera_type,
             camera.sensor_size, now, camera.id),
        )
        conn.commit()
        return get_camera(conn, camera.id)


def delete_camera(conn: sqlite3.Connection, camera_id: int) -> None:
    conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
    conn.commit()


# --- Camera Issues ---

def get_camera_issues(conn: sqlite3.Connection, camera_id: int) -> list[CameraIssue]:
    rows = conn.execute(
        "SELECT * FROM camera_issues WHERE camera_id = ? ORDER BY date_noted DESC",
        (camera_id,),
    ).fetchall()
    return [CameraIssue(**dict(r)) for r in rows]


def save_camera_issue(conn: sqlite3.Connection, issue: CameraIssue) -> CameraIssue:
    if issue.id is None:
        cur = conn.execute(
            """INSERT INTO camera_issues (camera_id, description, date_noted, resolved,
               resolved_date, notes) VALUES (?, ?, ?, ?, ?, ?)""",
            (issue.camera_id, issue.description, issue.date_noted,
             issue.resolved, issue.resolved_date, issue.notes),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM camera_issues WHERE id = ?", (cur.lastrowid,)).fetchone()
    else:
        conn.execute(
            """UPDATE camera_issues SET description=?, date_noted=?, resolved=?,
               resolved_date=?, notes=? WHERE id=?""",
            (issue.description, issue.date_noted, issue.resolved,
             issue.resolved_date, issue.notes, issue.id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM camera_issues WHERE id = ?", (issue.id,)).fetchone()
    return CameraIssue(**dict(row))


def delete_camera_issue(conn: sqlite3.Connection, issue_id: int) -> None:
    conn.execute("DELETE FROM camera_issues WHERE id = ?", (issue_id,))
    conn.commit()


# --- Lens CRUD ---

def get_lenses(conn: sqlite3.Connection, user_id: int) -> list[Lens]:
    rows = conn.execute(
        "SELECT * FROM lenses WHERE user_id = ? ORDER BY name", (user_id,)
    ).fetchall()
    return [Lens(**dict(r)) for r in rows]


def get_lens(conn: sqlite3.Connection, lens_id: int) -> Lens | None:
    row = conn.execute("SELECT * FROM lenses WHERE id = ?", (lens_id,)).fetchone()
    return Lens(**dict(row)) if row else None


def save_lens(conn: sqlite3.Connection, lens: Lens) -> Lens:
    now = datetime.now().isoformat()
    if lens.id is None:
        cur = conn.execute(
            """INSERT INTO lenses (user_id, name, make, model, focal_length,
               max_aperture, filter_diameter, year_built, year_purchased,
               purchase_location, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lens.user_id, lens.name, lens.make, lens.model, lens.focal_length,
             lens.max_aperture, lens.filter_diameter, lens.year_built,
             lens.year_purchased, lens.purchase_location, now, now),
        )
        conn.commit()
        return get_lens(conn, cur.lastrowid)
    else:
        conn.execute(
            """UPDATE lenses SET name=?, make=?, model=?, focal_length=?,
               max_aperture=?, filter_diameter=?, year_built=?, year_purchased=?,
               purchase_location=?, updated_at=? WHERE id=?""",
            (lens.name, lens.make, lens.model, lens.focal_length,
             lens.max_aperture, lens.filter_diameter, lens.year_built,
             lens.year_purchased, lens.purchase_location, now, lens.id),
        )
        conn.commit()
        return get_lens(conn, lens.id)


def delete_lens(conn: sqlite3.Connection, lens_id: int) -> None:
    conn.execute("DELETE FROM lenses WHERE id = ?", (lens_id,))
    conn.commit()


# --- Lens Notes ---

def get_lens_notes(conn: sqlite3.Connection, lens_id: int) -> list[LensNote]:
    rows = conn.execute(
        "SELECT * FROM lens_notes WHERE lens_id = ? ORDER BY created_at DESC",
        (lens_id,),
    ).fetchall()
    return [LensNote(**dict(r)) for r in rows]


def get_lens_note(conn: sqlite3.Connection, note_id: int) -> LensNote | None:
    row = conn.execute("SELECT * FROM lens_notes WHERE id = ?", (note_id,)).fetchone()
    return LensNote(**dict(row)) if row else None


def save_lens_note(conn: sqlite3.Connection, note: LensNote) -> LensNote:
    now = datetime.now().isoformat()
    if note.id is None:
        cur = conn.execute(
            "INSERT INTO lens_notes (lens_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (note.lens_id, note.content, now, now),
        )
        conn.commit()
        return get_lens_note(conn, cur.lastrowid)
    else:
        conn.execute(
            "UPDATE lens_notes SET content=?, updated_at=? WHERE id=?",
            (note.content, now, note.id),
        )
        conn.commit()
        return get_lens_note(conn, note.id)


def delete_lens_note(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM lens_notes WHERE id = ?", (note_id,))
    conn.commit()


# --- Film Stock CRUD ---

def get_film_stocks(conn: sqlite3.Connection, user_id: int) -> list[FilmStock]:
    rows = conn.execute(
        "SELECT * FROM film_stocks WHERE user_id = ? ORDER BY brand, name", (user_id,)
    ).fetchall()
    return [FilmStock(**dict(r)) for r in rows]


def get_film_stock(conn: sqlite3.Connection, stock_id: int) -> FilmStock | None:
    row = conn.execute("SELECT * FROM film_stocks WHERE id = ?", (stock_id,)).fetchone()
    return FilmStock(**dict(row)) if row else None


def save_film_stock(conn: sqlite3.Connection, stock: FilmStock) -> FilmStock:
    now = datetime.now().isoformat()
    if stock.id is None:
        cur = conn.execute(
            """INSERT INTO film_stocks (user_id, brand, name, type, media_type, iso, format,
               frames_per_roll, quantity_on_hand, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (stock.user_id, stock.brand, stock.name, stock.type, stock.media_type,
             stock.iso, stock.format, stock.frames_per_roll, stock.quantity_on_hand,
             stock.notes, now),
        )
        conn.commit()
        return get_film_stock(conn, cur.lastrowid)
    else:
        conn.execute(
            """UPDATE film_stocks SET brand=?, name=?, type=?, media_type=?, iso=?, format=?,
               frames_per_roll=?, quantity_on_hand=?, notes=? WHERE id=?""",
            (stock.brand, stock.name, stock.type, stock.media_type, stock.iso, stock.format,
             stock.frames_per_roll, stock.quantity_on_hand, stock.notes, stock.id),
        )
        conn.commit()
        return get_film_stock(conn, stock.id)


def delete_film_stock(conn: sqlite3.Connection, stock_id: int) -> None:
    conn.execute("DELETE FROM film_stocks WHERE id = ?", (stock_id,))
    conn.commit()


# --- Roll CRUD ---

def get_rolls(conn: sqlite3.Connection, user_id: int, status: str | None = None) -> list[Roll]:
    if status:
        rows = conn.execute(
            "SELECT * FROM rolls WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (user_id, status),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM rolls WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    return [Roll(**dict(r)) for r in rows]


def get_roll(conn: sqlite3.Connection, roll_id: int) -> Roll | None:
    row = conn.execute("SELECT * FROM rolls WHERE id = ?", (roll_id,)).fetchone()
    return Roll(**dict(row)) if row else None


def create_roll(conn: sqlite3.Connection, roll: Roll, frames_per_roll: int) -> Roll:
    now = datetime.now().isoformat()
    cur = conn.execute(
        """INSERT INTO rolls (user_id, film_stock_id, camera_id, lens_id, status,
           loaded_date, finished_date, sent_for_dev_date, developed_date,
           notes, title, push_pull_stops, location, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (roll.user_id, roll.film_stock_id, roll.camera_id, roll.lens_id, roll.status,
         roll.loaded_date, roll.finished_date, roll.sent_for_dev_date,
         roll.developed_date, roll.notes, roll.title, roll.push_pull_stops,
         roll.location, now),
    )
    roll_id = cur.lastrowid
    # Pre-populate frames, seeding with roll's default lens if set.
    # frames_per_roll == 0 means unlimited (digital), so skip pre-population.
    if frames_per_roll > 0:
        for i in range(1, frames_per_roll + 1):
            conn.execute(
                "INSERT INTO frames (roll_id, frame_number, lens_id) VALUES (?, ?, ?)",
                (roll_id, i, roll.lens_id),
            )
    conn.execute(
        "UPDATE film_stocks SET quantity_on_hand = MAX(quantity_on_hand - 1, 0) WHERE id = ?",
        (roll.film_stock_id,),
    )
    conn.commit()
    return get_roll(conn, roll_id)


def update_roll(conn: sqlite3.Connection, roll: Roll) -> Roll:
    conn.execute(
        """UPDATE rolls SET film_stock_id=?, camera_id=?, lens_id=?, status=?,
           loaded_date=?, finished_date=?, sent_for_dev_date=?,
           developed_date=?, notes=?, title=?, push_pull_stops=?,
           scan_date=?, scan_notes=?, location=? WHERE id=?""",
        (roll.film_stock_id, roll.camera_id, roll.lens_id, roll.status,
         roll.loaded_date, roll.finished_date, roll.sent_for_dev_date,
         roll.developed_date, roll.notes, roll.title, roll.push_pull_stops,
         roll.scan_date, roll.scan_notes, roll.location, roll.id),
    )
    conn.commit()
    return get_roll(conn, roll.id)


def set_roll_frames_lens(conn: sqlite3.Connection, roll_id: int, lens_id: int | None) -> None:
    """Set the default lens on all frames of a roll (used when loading a roll)."""
    conn.execute("UPDATE frames SET lens_id = ? WHERE roll_id = ?", (lens_id, roll_id))
    conn.commit()


def delete_roll(conn: sqlite3.Connection, roll_id: int) -> None:
    conn.execute("DELETE FROM frames WHERE roll_id = ?", (roll_id,))
    conn.execute("DELETE FROM rolls WHERE id = ?", (roll_id,))
    conn.commit()


# --- Roll Development CRUD ---

def save_roll_development(conn: sqlite3.Connection, dev: RollDevelopment, steps: list[DevelopmentStep]) -> RollDevelopment:
    """Insert or replace development record and its steps atomically."""
    if dev.id is None:
        cur = conn.execute(
            """INSERT INTO roll_development (roll_id, dev_type, process_type, lab_name,
               lab_contact, cost_amount, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dev.roll_id, dev.dev_type, dev.process_type, dev.lab_name,
             dev.lab_contact, dev.cost_amount, dev.notes),
        )
        dev_id = cur.lastrowid
    else:
        conn.execute(
            """UPDATE roll_development SET dev_type=?, process_type=?, lab_name=?,
               lab_contact=?, cost_amount=?, notes=? WHERE id=?""",
            (dev.dev_type, dev.process_type, dev.lab_name, dev.lab_contact,
             dev.cost_amount, dev.notes, dev.id),
        )
        dev_id = dev.id
        conn.execute("DELETE FROM development_steps WHERE development_id = ?", (dev_id,))
    for i, step in enumerate(steps):
        conn.execute(
            """INSERT INTO development_steps (development_id, step_order, chemical_name,
               temperature, duration_seconds, agitation, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dev_id, i, step.chemical_name, step.temperature,
             step.duration_seconds, step.agitation, step.notes),
        )
    conn.commit()
    return get_roll_development(conn, dev_id)


def get_roll_development(conn: sqlite3.Connection, dev_id: int) -> RollDevelopment | None:
    row = conn.execute("SELECT * FROM roll_development WHERE id = ?", (dev_id,)).fetchone()
    return RollDevelopment(**dict(row)) if row else None


def get_roll_development_by_roll(conn: sqlite3.Connection, roll_id: int) -> RollDevelopment | None:
    row = conn.execute("SELECT * FROM roll_development WHERE roll_id = ?", (roll_id,)).fetchone()
    return RollDevelopment(**dict(row)) if row else None


def get_development_steps(conn: sqlite3.Connection, development_id: int) -> list[DevelopmentStep]:
    rows = conn.execute(
        "SELECT * FROM development_steps WHERE development_id = ? ORDER BY step_order",
        (development_id,),
    ).fetchall()
    return [DevelopmentStep(**dict(r)) for r in rows]


def delete_roll_development(conn: sqlite3.Connection, roll_id: int) -> None:
    conn.execute("DELETE FROM roll_development WHERE roll_id = ?", (roll_id,))
    conn.commit()


# --- Frame CRUD ---

def get_frames(conn: sqlite3.Connection, roll_id: int) -> list[Frame]:
    rows = conn.execute(
        "SELECT * FROM frames WHERE roll_id = ? ORDER BY frame_number", (roll_id,)
    ).fetchall()
    return [Frame(**dict(r)) for r in rows]


def get_frame(conn: sqlite3.Connection, frame_id: int) -> Frame | None:
    row = conn.execute("SELECT * FROM frames WHERE id = ?", (frame_id,)).fetchone()
    return Frame(**dict(row)) if row else None


def update_frame(conn: sqlite3.Connection, frame: Frame) -> Frame:
    conn.execute(
        """UPDATE frames SET subject=?, aperture=?, shutter_speed=?,
           lens_id=?, date_taken=?, location=?, notes=? WHERE id=?""",
        (frame.subject, frame.aperture, frame.shutter_speed,
         frame.lens_id, frame.date_taken, frame.location, frame.notes,
         frame.id),
    )
    conn.commit()
    return get_frame(conn, frame.id)


# --- Cloud Settings CRUD ---

def get_cloud_settings(conn: sqlite3.Connection, user_id: int) -> CloudSettings | None:
    row = conn.execute("SELECT * FROM cloud_settings WHERE user_id = ?", (user_id,)).fetchone()
    return CloudSettings(**dict(row)) if row else None


def save_cloud_settings(conn: sqlite3.Connection, settings: CloudSettings) -> CloudSettings:
    now = datetime.now().isoformat()
    if settings.id is None:
        cur = conn.execute(
            """INSERT INTO cloud_settings (user_id, provider, remote_folder, last_sync_at,
               account_display_name, account_email, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (settings.user_id, settings.provider, settings.remote_folder,
             settings.last_sync_at, settings.account_display_name,
             settings.account_email, settings.enabled, now, now),
        )
        conn.commit()
        return get_cloud_settings(conn, settings.user_id)
    else:
        conn.execute(
            """UPDATE cloud_settings SET provider=?, remote_folder=?, last_sync_at=?,
               account_display_name=?, account_email=?, enabled=?, updated_at=?
               WHERE id=?""",
            (settings.provider, settings.remote_folder, settings.last_sync_at,
             settings.account_display_name, settings.account_email,
             settings.enabled, now, settings.id),
        )
        conn.commit()
        return get_cloud_settings(conn, settings.user_id)


def delete_cloud_settings(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM cloud_settings WHERE user_id = ?", (user_id,))
    conn.commit()


# --- Dev Recipe CRUD ---

def get_dev_recipes(conn: sqlite3.Connection, user_id: int) -> list[DevRecipe]:
    rows = conn.execute(
        "SELECT * FROM dev_recipes WHERE user_id = ? ORDER BY name", (user_id,)
    ).fetchall()
    return [DevRecipe(**dict(r)) for r in rows]


def get_dev_recipe(conn: sqlite3.Connection, recipe_id: int) -> DevRecipe | None:
    row = conn.execute("SELECT * FROM dev_recipes WHERE id = ?", (recipe_id,)).fetchone()
    return DevRecipe(**dict(row)) if row else None


def get_dev_recipe_steps(conn: sqlite3.Connection, recipe_id: int) -> list[DevRecipeStep]:
    rows = conn.execute(
        "SELECT * FROM dev_recipe_steps WHERE recipe_id = ? ORDER BY step_order",
        (recipe_id,),
    ).fetchall()
    return [DevRecipeStep(**dict(r)) for r in rows]


def save_dev_recipe(conn: sqlite3.Connection, recipe: DevRecipe, steps: list[DevRecipeStep]) -> DevRecipe:
    """Insert or update a recipe and its steps atomically."""
    now = datetime.now().isoformat()
    if recipe.id is None:
        cur = conn.execute(
            """INSERT INTO dev_recipes (user_id, name, process_type, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (recipe.user_id, recipe.name, recipe.process_type, recipe.notes, now),
        )
        recipe_id = cur.lastrowid
    else:
        conn.execute(
            """UPDATE dev_recipes SET name=?, process_type=?, notes=? WHERE id=?""",
            (recipe.name, recipe.process_type, recipe.notes, recipe.id),
        )
        recipe_id = recipe.id
        conn.execute("DELETE FROM dev_recipe_steps WHERE recipe_id = ?", (recipe_id,))
    for i, step in enumerate(steps):
        conn.execute(
            """INSERT INTO dev_recipe_steps (recipe_id, step_order, chemical_name,
               temperature, duration_seconds, agitation, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (recipe_id, i, step.chemical_name, step.temperature,
             step.duration_seconds, step.agitation, step.notes),
        )
    conn.commit()
    return get_dev_recipe(conn, recipe_id)


def delete_dev_recipe(conn: sqlite3.Connection, recipe_id: int) -> None:
    conn.execute("DELETE FROM dev_recipes WHERE id = ?", (recipe_id,))
    conn.commit()


# --- Film Stock Alerts ---

def get_low_stock_items(conn: sqlite3.Connection, user_id: int, threshold: int = 2) -> dict[str, list[dict]]:
    """Return analog film stocks that are low or out of stock."""
    rows = conn.execute(
        """SELECT brand, name, quantity_on_hand
           FROM film_stocks
           WHERE user_id = ? AND media_type = 'analog' AND quantity_on_hand <= ?
           ORDER BY quantity_on_hand, brand, name""",
        (user_id, threshold),
    ).fetchall()
    low_stock = []
    out_of_stock = []
    for r in rows:
        item = {"brand": r["brand"], "name": r["name"], "quantity": r["quantity_on_hand"]}
        if r["quantity_on_hand"] == 0:
            out_of_stock.append(item)
        else:
            low_stock.append(item)
    return {"low_stock": low_stock, "out_of_stock": out_of_stock}


# --- Statistics ---

def get_stats(conn: sqlite3.Connection, user_id: int) -> dict:
    """Return aggregated statistics for the user's photography data."""
    # Rolls by status
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM rolls WHERE user_id = ? GROUP BY status",
        (user_id,),
    ).fetchall()
    rolls_by_status = {r["status"]: r["cnt"] for r in rows}

    # Total frames logged (with non-empty subject)
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM frames f
           JOIN rolls r ON f.roll_id = r.id
           WHERE r.user_id = ? AND f.subject != ''""",
        (user_id,),
    ).fetchone()
    total_frames_logged = row["cnt"]

    # Top film stocks by roll count
    rows = conn.execute(
        """SELECT fs.brand || ' ' || fs.name as name, COUNT(*) as cnt
           FROM rolls r
           JOIN film_stocks fs ON r.film_stock_id = fs.id
           WHERE r.user_id = ?
           GROUP BY r.film_stock_id
           ORDER BY cnt DESC
           LIMIT 5""",
        (user_id,),
    ).fetchall()
    top_film_stocks = [{"name": r["name"], "count": r["cnt"]} for r in rows]

    # Rolls by format
    rows = conn.execute(
        """SELECT fs.format, COUNT(*) as cnt
           FROM rolls r
           JOIN film_stocks fs ON r.film_stock_id = fs.id
           WHERE r.user_id = ?
           GROUP BY fs.format""",
        (user_id,),
    ).fetchall()
    rolls_by_format = [{"format": r["format"], "count": r["cnt"]} for r in rows]

    # Rolls by type (color vs black_and_white)
    rows = conn.execute(
        """SELECT fs.type, COUNT(*) as cnt
           FROM rolls r
           JOIN film_stocks fs ON r.film_stock_id = fs.id
           WHERE r.user_id = ?
           GROUP BY fs.type""",
        (user_id,),
    ).fetchall()
    rolls_by_type = [{"type": r["type"], "count": r["cnt"]} for r in rows]

    # Top cameras by roll count
    rows = conn.execute(
        """SELECT c.name, COUNT(*) as cnt
           FROM rolls r
           JOIN cameras c ON r.camera_id = c.id
           WHERE r.user_id = ? AND r.camera_id IS NOT NULL
           GROUP BY r.camera_id
           ORDER BY cnt DESC
           LIMIT 5""",
        (user_id,),
    ).fetchall()
    top_cameras = [{"name": r["name"], "count": r["cnt"]} for r in rows]

    # Top lenses by frame count
    rows = conn.execute(
        """SELECT l.name, COUNT(*) as cnt
           FROM frames f
           JOIN lenses l ON f.lens_id = l.id
           JOIN rolls r ON f.roll_id = r.id
           WHERE r.user_id = ? AND f.lens_id IS NOT NULL
           GROUP BY f.lens_id
           ORDER BY cnt DESC
           LIMIT 5""",
        (user_id,),
    ).fetchall()
    top_lenses = [{"name": r["name"], "count": r["cnt"]} for r in rows]

    # Development type split
    rows = conn.execute(
        """SELECT rd.dev_type, COUNT(*) as cnt
           FROM roll_development rd
           JOIN rolls r ON rd.roll_id = r.id
           WHERE r.user_id = ?
           GROUP BY rd.dev_type""",
        (user_id,),
    ).fetchall()
    dev_type_split = {r["dev_type"]: r["cnt"] for r in rows}

    # Total development cost
    row = conn.execute(
        """SELECT COALESCE(SUM(rd.cost_amount), 0) as total
           FROM roll_development rd
           JOIN rolls r ON rd.roll_id = r.id
           WHERE r.user_id = ?""",
        (user_id,),
    ).fetchone()
    total_dev_cost = float(row["total"])

    # Top shooting locations
    rows = conn.execute(
        """SELECT location, COUNT(*) as cnt
           FROM rolls
           WHERE user_id = ? AND location != ''
           GROUP BY location
           ORDER BY cnt DESC
           LIMIT 5""",
        (user_id,),
    ).fetchall()
    top_locations = [{"location": r["location"], "count": r["cnt"]} for r in rows]

    # Rolls by month (last 12 months, based on loaded_date)
    rows = conn.execute(
        """SELECT strftime('%Y-%m', loaded_date) as month, COUNT(*) as cnt
           FROM rolls
           WHERE user_id = ? AND loaded_date IS NOT NULL
           GROUP BY month
           ORDER BY month DESC
           LIMIT 12""",
        (user_id,),
    ).fetchall()
    rolls_by_month = [{"month": r["month"], "count": r["cnt"]} for r in rows]

    return {
        "rolls_by_status": rolls_by_status,
        "total_frames_logged": total_frames_logged,
        "top_film_stocks": top_film_stocks,
        "rolls_by_format": rolls_by_format,
        "rolls_by_type": rolls_by_type,
        "top_cameras": top_cameras,
        "top_lenses": top_lenses,
        "dev_type_split": dev_type_split,
        "total_dev_cost": total_dev_cost,
        "top_locations": top_locations,
        "rolls_by_month": rolls_by_month,
    }


# --- Utility ---

def vacuum_db(conn: sqlite3.Connection) -> None:
    conn.execute("VACUUM")


def get_counts(conn: sqlite3.Connection, user_id: int) -> dict[str, int]:
    counts = {}
    for table in ("cameras", "lenses", "film_stocks", "rolls"):
        row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id = ?", (user_id,)
        ).fetchone()
        counts[table] = row["cnt"]
    return counts


def get_usage_stats(conn: sqlite3.Connection, user_id: int) -> dict[str, str | None]:
    """Return most-used film stock, camera, and lens by roll/frame count."""
    row = conn.execute(
        """SELECT fs.brand || ' ' || fs.name as name
           FROM rolls r
           JOIN film_stocks fs ON r.film_stock_id = fs.id
           WHERE r.user_id = ?
           GROUP BY r.film_stock_id
           ORDER BY COUNT(*) DESC
           LIMIT 1""",
        (user_id,),
    ).fetchone()
    most_film = row["name"] if row else None

    row = conn.execute(
        """SELECT c.name
           FROM rolls r
           JOIN cameras c ON r.camera_id = c.id
           WHERE r.user_id = ? AND r.camera_id IS NOT NULL
           GROUP BY r.camera_id
           ORDER BY COUNT(*) DESC
           LIMIT 1""",
        (user_id,),
    ).fetchone()
    most_camera = row["name"] if row else None

    row = conn.execute(
        """SELECT l.name
           FROM frames f
           JOIN lenses l ON f.lens_id = l.id
           JOIN rolls r ON f.roll_id = r.id
           WHERE r.user_id = ? AND f.lens_id IS NOT NULL
           GROUP BY f.lens_id
           ORDER BY COUNT(*) DESC
           LIMIT 1""",
        (user_id,),
    ).fetchone()
    most_lens = row["name"] if row else None

    return {"film_stock": most_film, "camera": most_camera, "lens": most_lens}


def get_loaded_cameras(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT c.name as camera_name, c.id as camera_id,
                  fs.brand || ' ' || fs.name as film_name, r.status
           FROM rolls r
           JOIN cameras c ON r.camera_id = c.id
           JOIN film_stocks fs ON r.film_stock_id = fs.id
           WHERE r.user_id = ? AND r.status IN ('loaded', 'shooting')
           ORDER BY c.name""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]
