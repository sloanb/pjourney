# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

pjourney — a Textual TUI application for managing camera collections, lenses, and film inventory. Tracks equipment, film rolls through their lifecycle (fresh → loaded → shooting → finished → developing → developed; self-develop skips directly to developed), and per-frame shooting details.

## Setup

```bash
pip install -e ".[dev]"
python main.py
```

## Commands

```bash
# Run the app
python main.py

# Run tests
python -m pytest tests/ -v
```

## Architecture

- **Python 3.12+** with **Textual** for TUI, **SQLite** for storage, **argon2-cffi** for auth, **dropbox** + **keyring** for cloud backup
- Database stored at `~/.pjourney/pjourney.db`, auto-created on first run
- Default user: `admin` / `pjourney`

### Key directories

- `pjourney/db/` — database.py (connection, schema, CRUD, get_stats(), recipe CRUD), models.py (dataclasses: Roll, FilmStock, DevRecipe, DevRecipeStep, etc.)
- `pjourney/screens/` — login, dashboard, cameras, lenses, film_stock, rolls (rolls.py also contains ScanRollModal and RecipePickerModal), frames, stats (StatsScreen with aggregated photography data), admin (admin.py also contains CloudAuthModal, CloudFolderBrowserModal, CloudRestoreModal, NewFolderModal, RecipeFormModal)
- `pjourney/widgets/` — reusable InventoryTable widget
- `pjourney/cloud/` — provider.py (CloudProvider ABC, dataclasses, CloudProviderError), credentials.py (CredentialStore wrapping OS keyring), dropbox_provider.py (DropboxProvider: PKCE OAuth, folder browse, upload/download/disconnect)
- `pjourney/export.py` — export_rolls_csv(), export_frames_csv()
- `pjourney/errors.py` — ErrorCode enum (PJ-DB01…PJ-DB05, PJ-IO01, PJ-VAL01…PJ-VAL02, PJ-CLD01…PJ-CLD05, PJ-APP01) and app_error() toast helper
- `docs/` — ERROR_CODES.md (user-facing error code reference)
- `tests/` — test_database.py (120 tests), test_models.py (33 tests), test_errors.py (14 tests), test_dev_modals.py (28 tests), test_confirm_modal.py (16 tests), test_camera_form_modal.py (9 tests), test_dashboard.py (2 tests), test_cloud_settings.py (6 tests), test_cloud_provider.py (11 tests), test_dropbox_provider.py (25 tests), test_cloud_modals.py (22 tests), test_scan_modal.py (7 tests), test_stats_screen.py (6 tests), test_recipe_modals.py (14 tests), test_export.py (10 tests) — **323 total tests**

### Screen flow

Login → Dashboard → Cameras / Lenses / Film Stock / Rolls / Stats → Frames / Camera Detail → Admin
