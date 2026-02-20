"""Abstract cloud storage provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class CloudProviderError(Exception):
    """Wraps all SDK-specific exceptions from cloud providers."""


@dataclass
class CloudAccountInfo:
    display_name: str = ""
    email: str = ""


@dataclass
class CloudFolderEntry:
    name: str = ""
    path: str = ""
    is_folder: bool = True


@dataclass
class CloudFileEntry:
    name: str = ""
    path: str = ""
    size: int = 0
    modified: str = ""


class CloudProvider(ABC):
    """Strategy interface for cloud storage backends."""

    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def get_auth_url(self) -> tuple[str, str]:
        """Return (authorization_url, pkce_state) to start OAuth flow."""
        ...

    @abstractmethod
    def finish_auth(self, code: str, state: str) -> CloudAccountInfo:
        """Exchange auth code for tokens, store them, return account info."""
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        ...

    @abstractmethod
    def get_account_info(self) -> CloudAccountInfo | None:
        ...

    @abstractmethod
    def list_folder(self, path: str) -> list[CloudFolderEntry]:
        """List subfolders in the given remote path."""
        ...

    @abstractmethod
    def list_files(self, path: str) -> list[CloudFileEntry]:
        """List .db files in the given remote path (for restore browser)."""
        ...

    @abstractmethod
    def create_folder(self, path: str) -> None:
        ...

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        ...

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Revoke tokens and clear stored credentials."""
        ...
