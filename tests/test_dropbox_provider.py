"""Tests for the DropboxProvider with mocked Dropbox SDK."""

from dataclasses import dataclass
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pjourney.cloud.credentials import CredentialStore
from pjourney.cloud.dropbox_provider import DropboxProvider, PROVIDER_NAME
from pjourney.cloud.provider import CloudAccountInfo, CloudProviderError


@pytest.fixture
def mock_creds():
    """CredentialStore mock with no stored tokens by default."""
    creds = MagicMock(spec=CredentialStore)
    creds.retrieve.return_value = None
    return creds


@pytest.fixture
def authed_creds():
    """CredentialStore mock with a refresh token already stored."""
    creds = MagicMock(spec=CredentialStore)

    def _retrieve(provider, key):
        if key == "refresh_token":
            return "fake_refresh_token"
        if key == "access_token":
            return "fake_access_token"
        return None

    creds.retrieve.side_effect = _retrieve
    return creds


class TestProviderName:
    def test_returns_dropbox(self, mock_creds):
        provider = DropboxProvider(mock_creds)
        assert provider.provider_name() == "Dropbox"


class TestAuth:
    @patch("pjourney.cloud.dropbox_provider.DropboxOAuth2FlowNoRedirect")
    def test_get_auth_url_returns_url(self, mock_flow_cls, mock_creds):
        mock_flow = MagicMock()
        mock_flow.start.return_value = "https://dropbox.com/oauth2/authorize?..."
        mock_flow_cls.return_value = mock_flow

        provider = DropboxProvider(mock_creds)
        url, state = provider.get_auth_url()
        assert "dropbox.com" in url
        assert state == "pkce"

    @patch("pjourney.cloud.dropbox_provider.DropboxOAuth2FlowNoRedirect")
    def test_finish_auth_stores_tokens(self, mock_flow_cls, mock_creds):
        mock_flow = MagicMock()
        mock_flow.start.return_value = "https://dropbox.com/auth"
        mock_result = MagicMock()
        mock_result.access_token = "new_access"
        mock_result.refresh_token = "new_refresh"
        mock_flow.finish.return_value = mock_result
        mock_flow_cls.return_value = mock_flow

        provider = DropboxProvider(mock_creds)
        provider.get_auth_url()

        # Mock the Dropbox client for get_account_info() call inside finish_auth
        with patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox") as mock_dbx_cls:
            mock_client = MagicMock()
            mock_acct = MagicMock()
            mock_acct.name.display_name = "Test User"
            mock_acct.email = "test@example.com"
            mock_client.users_get_current_account.return_value = mock_acct
            mock_dbx_cls.return_value = mock_client

            # Need to make retrieve return the token after store
            mock_creds.retrieve.side_effect = lambda p, k: "new_refresh" if k == "refresh_token" else None

            info = provider.finish_auth("auth_code_123", "pkce")

        mock_creds.store.assert_any_call(PROVIDER_NAME, "access_token", "new_access")
        mock_creds.store.assert_any_call(PROVIDER_NAME, "refresh_token", "new_refresh")
        assert info.display_name == "Test User"
        assert info.email == "test@example.com"

    def test_finish_auth_without_start_raises(self, mock_creds):
        provider = DropboxProvider(mock_creds)
        with pytest.raises(CloudProviderError, match="not started"):
            provider.finish_auth("code", "state")


class TestIsAuthenticated:
    def test_false_when_no_token(self, mock_creds):
        provider = DropboxProvider(mock_creds)
        assert provider.is_authenticated() is False

    def test_true_when_token_exists(self, authed_creds):
        provider = DropboxProvider(authed_creds)
        assert provider.is_authenticated() is True


class TestGetAccountInfo:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_returns_account_info(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_acct = MagicMock()
        mock_acct.name.display_name = "Jane Doe"
        mock_acct.email = "jane@example.com"
        mock_client.users_get_current_account.return_value = mock_acct
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        info = provider.get_account_info()
        assert info.display_name == "Jane Doe"
        assert info.email == "jane@example.com"

    def test_returns_none_when_not_authenticated(self, mock_creds):
        provider = DropboxProvider(mock_creds)
        result = provider.get_account_info()
        assert result is None


class TestListFolder:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_lists_only_folders(self, mock_dbx_cls, authed_creds):
        from dropbox.files import FolderMetadata, FileMetadata

        folder = MagicMock(spec=FolderMetadata)
        folder.name = "backups"
        folder.path_display = "/backups"
        file = MagicMock(spec=FileMetadata)
        file.name = "readme.txt"

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.entries = [folder, file]
        mock_client.files_list_folder.return_value = mock_result
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        entries = provider.list_folder("")
        assert len(entries) == 1
        assert entries[0].name == "backups"
        assert entries[0].is_folder is True

    def test_raises_when_not_authenticated(self, mock_creds):
        provider = DropboxProvider(mock_creds)
        with pytest.raises(CloudProviderError):
            provider.list_folder("")


class TestListFiles:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_lists_only_db_files(self, mock_dbx_cls, authed_creds):
        from dropbox.files import FileMetadata, FolderMetadata
        from datetime import datetime

        db_file = MagicMock(spec=FileMetadata)
        db_file.name = "pjourney_20250101.db"
        db_file.path_display = "/backups/pjourney_20250101.db"
        db_file.size = 2048
        db_file.server_modified = datetime(2025, 1, 1, 12, 0)

        txt_file = MagicMock(spec=FileMetadata)
        txt_file.name = "notes.txt"

        folder = MagicMock(spec=FolderMetadata)
        folder.name = "subfolder"

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.entries = [db_file, txt_file, folder]
        mock_client.files_list_folder.return_value = mock_result
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        entries = provider.list_files("/backups")
        assert len(entries) == 1
        assert entries[0].name == "pjourney_20250101.db"
        assert entries[0].size == 2048


class TestUploadDownload:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_upload_calls_files_upload(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        with patch("builtins.open", mock_open(read_data=b"dbdata")):
            provider.upload_file("/tmp/test.db", "/backups/test.db")

        mock_client.files_upload.assert_called_once()

    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_download_calls_files_download_to_file(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        provider.download_file("/backups/test.db", "/tmp/test.db")
        mock_client.files_download_to_file.assert_called_once_with("/tmp/test.db", "/backups/test.db")


class TestCreateFolder:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_create_folder_calls_sdk(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        provider.create_folder("/new_folder")
        mock_client.files_create_folder_v2.assert_called_once_with("/new_folder")


class TestDisconnect:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_disconnect_revokes_and_clears(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        provider.disconnect()
        mock_client.auth_token_revoke.assert_called_once()
        authed_creds.delete_all.assert_called_once_with(PROVIDER_NAME)


class TestSDKExceptionWrapping:
    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_upload_wraps_sdk_exception(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_client.files_upload.side_effect = Exception("network error")
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        with pytest.raises(CloudProviderError, match="Upload failed"):
            with patch("builtins.open", mock_open(read_data=b"data")):
                provider.upload_file("/tmp/test.db", "/remote/test.db")

    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_download_wraps_sdk_exception(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_client.files_download_to_file.side_effect = Exception("not found")
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        with pytest.raises(CloudProviderError, match="Download failed"):
            provider.download_file("/remote/test.db", "/tmp/test.db")

    @patch("pjourney.cloud.dropbox_provider.dropbox.Dropbox")
    def test_list_folder_wraps_sdk_exception(self, mock_dbx_cls, authed_creds):
        mock_client = MagicMock()
        mock_client.files_list_folder.side_effect = Exception("forbidden")
        mock_dbx_cls.return_value = mock_client

        provider = DropboxProvider(authed_creds)
        with pytest.raises(CloudProviderError, match="Failed to list folder"):
            provider.list_folder("")
