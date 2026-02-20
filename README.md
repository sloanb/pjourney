# pjourney

A terminal TUI application for managing camera collections, lenses, and film inventory.

Tracks your gear and follows film rolls through their full lifecycle — from loading the camera to getting negatives back from the lab. Works for film and digital shooters.

---

## Requirements

- Python 3.12+
- Dependencies listed in `pyproject.toml` (Textual, argon2-cffi, dropbox, keyring)

## Setup

```bash
pip install -e ".[dev]"
```

## Running

```bash
python main.py
```

Default login: `admin` / `pjourney`

Database is stored at `~/.pjourney/pjourney.db` and created automatically on first run.

## Tests

```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
pjourney/
  app.py                  — App entry point, screen registry, DB connection
  errors.py               — ErrorCode enum and app_error() toast helper
  db/
    database.py           — Schema, migrations, all CRUD functions
    models.py             — Dataclasses (Camera, Lens, FilmStock, Roll, Frame, CloudSettings, …)
  screens/
    login.py              — Login / account creation
    dashboard.py          — Home screen with inventory stats and loaded cameras
    cameras.py            — Camera list, edit form, issue/maintenance log
    lenses.py             — Lens list, edit form, per-lens notes
    film_stock.py         — Film stock catalogue
    rolls.py              — Roll lifecycle management and frame access
    frames.py             — Per-frame shooting details
    admin.py              — DB backup/vacuum, cloud sync, and user management
  widgets/
    inventory_table.py    — Shared DataTable with vim-style navigation
    app_header.py         — Common screen header
    confirm_modal.py      — Reusable delete confirmation modal
  cloud/
    provider.py           — CloudProvider ABC, CloudProviderError, shared dataclasses
    credentials.py        — CredentialStore (OS keyring wrapper)
    dropbox_provider.py   — DropboxProvider implementation (PKCE OAuth, folder browse, upload/download/disconnect)
docs/
  ERROR_CODES.md          — User-facing error code reference
tests/
  test_database.py        — CRUD and schema tests (42 tests)
  test_models.py          — Dataclass default/value tests (22 tests)
  test_confirm_modal.py   — ConfirmModal and delete-confirmation integration tests (16 tests)
  test_camera_form_modal.py — CameraFormModal rendering and save/cancel tests (9 tests)
  test_errors.py          — ErrorCode enum and app_error() helper tests (14 tests)
  test_dev_modals.py      — Development flow modal tests (21 tests)
  test_cloud_settings.py  — cloud_settings DB CRUD tests (6 tests)
  test_cloud_provider.py  — CloudProvider ABC and CredentialStore tests (11 tests)
  test_dropbox_provider.py — DropboxProvider tests with mocked SDK (24 tests)
  test_cloud_modals.py    — Cloud admin modal tests (22 tests)
```

## Roll Lifecycle

```
Fresh → Loaded → Shooting → Finished → Developing → Developed
```

Each transition records a date automatically. Frames are pre-created when a roll is started, based on the frames-per-roll setting of the selected film stock.

## Architecture Notes

- **Textual 8** for the TUI — screens are pushed/popped on a stack
- **SQLite** via `sqlite3` with `row_factory = sqlite3.Row` — no ORM
- Schema migrations handled in `_migrate_db()` using `ALTER TABLE … ADD COLUMN` with exception swallowing
- Passwords hashed with **argon2-cffi**; rehash-on-verify is supported
- Screen-to-screen data passing uses app-level instance variables (`_camera_detail_id`, `_lens_detail_id`, `_frames_roll_id`)
- Cloud sync uses PKCE OAuth (no client secret) via the Dropbox SDK; tokens are stored in the OS keyring via `keyring`; Dropbox API calls run off the main thread with `asyncio.to_thread` to keep the TUI responsive
