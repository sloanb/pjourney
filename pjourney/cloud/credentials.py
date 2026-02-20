"""Keyring wrapper for storing cloud provider credentials."""

import keyring
from keyring.errors import PasswordDeleteError

SERVICE_NAME = "pjourney"

# Known keys per provider
_PROVIDER_KEYS = {
    "dropbox": ["access_token", "refresh_token"],
}


class CredentialStore:
    """Thin wrapper around the OS keyring for cloud tokens."""

    def store(self, provider: str, key: str, value: str) -> None:
        keyring.set_password(SERVICE_NAME, f"{provider}:{key}", value)

    def retrieve(self, provider: str, key: str) -> str | None:
        return keyring.get_password(SERVICE_NAME, f"{provider}:{key}")

    def delete(self, provider: str, key: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, f"{provider}:{key}")
        except PasswordDeleteError:
            pass

    def delete_all(self, provider: str) -> None:
        for key in _PROVIDER_KEYS.get(provider, []):
            self.delete(provider, key)
