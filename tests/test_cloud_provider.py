"""Tests for the CloudProvider ABC and CredentialStore."""

from unittest.mock import MagicMock, patch

import pytest

from pjourney.cloud.credentials import CredentialStore, SERVICE_NAME
from pjourney.cloud.provider import (
    CloudAccountInfo,
    CloudFileEntry,
    CloudFolderEntry,
    CloudProvider,
    CloudProviderError,
)


class TestCloudProviderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            CloudProvider()

    def test_cloudprovider_error_is_exception(self):
        err = CloudProviderError("test")
        assert isinstance(err, Exception)
        assert str(err) == "test"


class TestCloudAccountInfo:
    def test_default_fields(self):
        info = CloudAccountInfo()
        assert info.display_name == ""
        assert info.email == ""


class TestCloudFolderEntry:
    def test_fields(self):
        entry = CloudFolderEntry(name="photos", path="/photos", is_folder=True)
        assert entry.name == "photos"
        assert entry.path == "/photos"
        assert entry.is_folder is True


class TestCloudFileEntry:
    def test_fields(self):
        entry = CloudFileEntry(name="backup.db", path="/backup.db", size=1024, modified="2025-01-01")
        assert entry.name == "backup.db"
        assert entry.size == 1024


class TestCredentialStore:
    @patch("pjourney.cloud.credentials.keyring")
    def test_store_calls_set_password(self, mock_keyring):
        store = CredentialStore()
        store.store("dropbox", "access_token", "abc123")
        mock_keyring.set_password.assert_called_once_with(
            SERVICE_NAME, "dropbox:access_token", "abc123"
        )

    @patch("pjourney.cloud.credentials.keyring")
    def test_retrieve_calls_get_password(self, mock_keyring):
        mock_keyring.get_password.return_value = "abc123"
        store = CredentialStore()
        result = store.retrieve("dropbox", "access_token")
        assert result == "abc123"
        mock_keyring.get_password.assert_called_once_with(
            SERVICE_NAME, "dropbox:access_token"
        )

    @patch("pjourney.cloud.credentials.keyring")
    def test_retrieve_returns_none_when_missing(self, mock_keyring):
        mock_keyring.get_password.return_value = None
        store = CredentialStore()
        result = store.retrieve("dropbox", "refresh_token")
        assert result is None

    @patch("pjourney.cloud.credentials.keyring")
    def test_delete_calls_delete_password(self, mock_keyring):
        store = CredentialStore()
        store.delete("dropbox", "access_token")
        mock_keyring.delete_password.assert_called_once_with(
            SERVICE_NAME, "dropbox:access_token"
        )

    @patch("pjourney.cloud.credentials.keyring")
    def test_delete_ignores_missing_key(self, mock_keyring):
        import keyring.errors
        mock_keyring.delete_password.side_effect = keyring.errors.PasswordDeleteError()
        store = CredentialStore()
        store.delete("dropbox", "access_token")  # Should not raise

    @patch("pjourney.cloud.credentials.keyring")
    def test_delete_all_clears_known_keys(self, mock_keyring):
        store = CredentialStore()
        store.delete_all("dropbox")
        assert mock_keyring.delete_password.call_count == 2
        mock_keyring.delete_password.assert_any_call(SERVICE_NAME, "dropbox:access_token")
        mock_keyring.delete_password.assert_any_call(SERVICE_NAME, "dropbox:refresh_token")
