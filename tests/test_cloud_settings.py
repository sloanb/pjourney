"""Tests for cloud_settings DB CRUD operations."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pjourney.db import database as db
from pjourney.db.models import CloudSettings


@pytest.fixture
def conn():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.db"
        connection = db.get_connection(path)
        db.init_db(connection)
        yield connection
        connection.close()


class TestCloudSettingsSchema:
    def test_cloud_settings_table_exists(self, conn):
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "cloud_settings" in names


class TestCloudSettingsCRUD:
    def test_get_returns_none_when_absent(self, conn):
        user = db.get_users(conn)[0]
        result = db.get_cloud_settings(conn, user.id)
        assert result is None

    def test_save_and_retrieve(self, conn):
        user = db.get_users(conn)[0]
        settings = CloudSettings(
            user_id=user.id,
            provider="Dropbox",
            remote_folder="/backups",
            account_display_name="Test User",
            account_email="test@example.com",
            enabled=True,
        )
        saved = db.save_cloud_settings(conn, settings)
        assert saved is not None
        assert saved.id is not None
        assert saved.provider == "Dropbox"
        assert saved.remote_folder == "/backups"
        assert saved.account_display_name == "Test User"
        assert saved.account_email == "test@example.com"

    def test_update_existing(self, conn):
        user = db.get_users(conn)[0]
        settings = CloudSettings(
            user_id=user.id,
            provider="Dropbox",
            remote_folder="/old",
            enabled=True,
        )
        saved = db.save_cloud_settings(conn, settings)
        saved.remote_folder = "/new"
        saved.last_sync_at = "2025-01-01 12:00:00"
        updated = db.save_cloud_settings(conn, saved)
        assert updated.remote_folder == "/new"
        assert updated.last_sync_at == "2025-01-01 12:00:00"

    def test_delete(self, conn):
        user = db.get_users(conn)[0]
        settings = CloudSettings(
            user_id=user.id,
            provider="Dropbox",
            remote_folder="/backups",
            enabled=True,
        )
        db.save_cloud_settings(conn, settings)
        assert db.get_cloud_settings(conn, user.id) is not None
        db.delete_cloud_settings(conn, user.id)
        assert db.get_cloud_settings(conn, user.id) is None

    def test_unique_per_user(self, conn):
        user = db.get_users(conn)[0]
        s1 = CloudSettings(user_id=user.id, provider="Dropbox", enabled=True)
        db.save_cloud_settings(conn, s1)
        s2 = CloudSettings(user_id=user.id, provider="GDrive", enabled=True)
        with pytest.raises(Exception):
            db.save_cloud_settings(conn, s2)
