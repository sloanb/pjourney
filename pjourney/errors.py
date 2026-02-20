"""Centralised error codes and user-facing error notification helper."""
from enum import Enum

ERROR_TITLE = "Well that seems underexposed"


class ErrorCode(str, Enum):
    DB_LOAD        = "PJ-DB01"
    DB_SAVE        = "PJ-DB02"
    DB_DELETE      = "PJ-DB03"
    DB_CONNECT     = "PJ-DB04"
    DB_VACUUM      = "PJ-DB05"
    IO_BACKUP      = "PJ-IO01"
    VAL_NUMBER     = "PJ-VAL01"
    VAL_DATE       = "PJ-VAL02"
    APP_UNEXPECTED = "PJ-APP01"


_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.DB_LOAD:        "Your data could not be loaded. The list may appear empty.",
    ErrorCode.DB_SAVE:        "Your changes could not be saved. Please try again.",
    ErrorCode.DB_DELETE:      "This item could not be deleted. Please try again.",
    ErrorCode.DB_CONNECT:     "Could not open the database. Restart the app and try again.",
    ErrorCode.DB_VACUUM:      "The database optimisation did not complete.",
    ErrorCode.IO_BACKUP:      "The backup file could not be written. Check available disk space.",
    ErrorCode.VAL_NUMBER:     "Please enter a valid number in that field.",
    ErrorCode.VAL_DATE:       "Please enter a date in YYYY-MM-DD format.",
    ErrorCode.APP_UNEXPECTED: "Something unexpected happened. No data was lost.",
}


def app_error(widget, code: ErrorCode, *, detail: str = "") -> None:
    """Show a user-friendly error Toast without crashing the application."""
    base = _MESSAGES.get(code, "An unexpected error occurred.")
    message = f"{base}{' ' + detail if detail else ''}\n\nReference: {code.value}"
    widget.notify(message, title=ERROR_TITLE, severity="error", timeout=12)
