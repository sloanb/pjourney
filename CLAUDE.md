# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

pjourney — a Textual TUI application for managing camera collections, lenses, and film inventory. Tracks equipment, film rolls through their lifecycle (fresh → loaded → shooting → finished → developing → developed), and per-frame shooting details.

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

- **Python 3.12+** with **Textual** for TUI, **SQLite** for storage, **argon2-cffi** for auth
- Database stored at `~/.pjourney/pjourney.db`, auto-created on first run
- Default user: `admin` / `pjourney`

### Key directories

- `pjourney/db/` — database.py (connection, schema, CRUD), models.py (dataclasses)
- `pjourney/screens/` — login, dashboard, cameras, lenses, film_stock, rolls, frames, admin
- `pjourney/widgets/` — reusable InventoryTable widget
- `tests/` — test_database.py (38 tests covering all CRUD), test_models.py

### Screen flow

Login → Dashboard → Cameras / Lenses / Film Stock / Rolls → Frames / Camera Detail → Admin
