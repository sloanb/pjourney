"""Dropbox cloud storage provider implementation."""

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
from dropbox.files import FileMetadata, FolderMetadata, WriteMode

from .credentials import CredentialStore
from .provider import (
    CloudAccountInfo,
    CloudFileEntry,
    CloudFolderEntry,
    CloudProvider,
    CloudProviderError,
)

# Public app key for PKCE desktop OAuth — not a secret.
DROPBOX_APP_KEY = "naghxm7tskyuush"

PROVIDER_NAME = "dropbox"


class DropboxProvider(CloudProvider):
    def __init__(self, credential_store: CredentialStore | None = None) -> None:
        self._creds = credential_store or CredentialStore()
        self._auth_flow: DropboxOAuth2FlowNoRedirect | None = None

    def provider_name(self) -> str:
        return "Dropbox"

    # --- Auth ---

    def get_auth_url(self) -> tuple[str, str]:
        try:
            self._auth_flow = DropboxOAuth2FlowNoRedirect(
                DROPBOX_APP_KEY,
                use_pkce=True,
                token_access_type="offline",
            )
            url = self._auth_flow.start()
            return (url, "pkce")
        except Exception as exc:
            raise CloudProviderError(f"Failed to start auth flow: {exc}") from exc

    def finish_auth(self, code: str, state: str) -> CloudAccountInfo:
        if self._auth_flow is None:
            raise CloudProviderError("Auth flow not started — call get_auth_url() first")
        try:
            result = self._auth_flow.finish(code.strip())
            self._creds.store(PROVIDER_NAME, "access_token", result.access_token)
            self._creds.store(PROVIDER_NAME, "refresh_token", result.refresh_token)
            self._auth_flow = None
            return self.get_account_info()
        except Exception as exc:
            raise CloudProviderError(f"Auth failed: {exc}") from exc

    def is_authenticated(self) -> bool:
        return self._creds.retrieve(PROVIDER_NAME, "refresh_token") is not None

    def get_account_info(self) -> CloudAccountInfo | None:
        try:
            client = self._get_client()
            acct = client.users_get_current_account()
            return CloudAccountInfo(
                display_name=acct.name.display_name,
                email=acct.email,
            )
        except Exception:
            return None

    # --- File operations ---

    def list_folder(self, path: str) -> list[CloudFolderEntry]:
        try:
            client = self._get_client()
            result = client.files_list_folder(path)
            entries = []
            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    entries.append(CloudFolderEntry(
                        name=entry.name,
                        path=entry.path_display,
                        is_folder=True,
                    ))
            return entries
        except Exception as exc:
            raise CloudProviderError(f"Failed to list folder: {exc}") from exc

    def list_files(self, path: str) -> list[CloudFileEntry]:
        try:
            client = self._get_client()
            result = client.files_list_folder(path)
            entries = []
            for entry in result.entries:
                if isinstance(entry, FileMetadata) and entry.name.endswith(".db"):
                    entries.append(CloudFileEntry(
                        name=entry.name,
                        path=entry.path_display,
                        size=entry.size,
                        modified=entry.server_modified.isoformat() if entry.server_modified else "",
                    ))
            return entries
        except Exception as exc:
            raise CloudProviderError(f"Failed to list files: {exc}") from exc

    def create_folder(self, path: str) -> None:
        try:
            client = self._get_client()
            client.files_create_folder_v2(path)
        except Exception as exc:
            raise CloudProviderError(f"Failed to create folder: {exc}") from exc

    def upload_file(self, local_path: str, remote_path: str) -> None:
        try:
            client = self._get_client()
            with open(local_path, "rb") as f:
                client.files_upload(f.read(), remote_path, mode=WriteMode.overwrite)
        except Exception as exc:
            raise CloudProviderError(f"Upload failed: {exc}") from exc

    def download_file(self, remote_path: str, local_path: str) -> None:
        try:
            client = self._get_client()
            client.files_download_to_file(local_path, remote_path)
        except Exception as exc:
            raise CloudProviderError(f"Download failed: {exc}") from exc

    def disconnect(self) -> None:
        try:
            client = self._get_client()
            client.auth_token_revoke()
        except Exception:
            pass  # Best-effort revoke
        self._creds.delete_all(PROVIDER_NAME)

    # --- Internal ---

    def _get_client(self) -> dropbox.Dropbox:
        refresh_token = self._creds.retrieve(PROVIDER_NAME, "refresh_token")
        if not refresh_token:
            raise CloudProviderError("Not authenticated — no refresh token found")
        return dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=DROPBOX_APP_KEY,
        )
