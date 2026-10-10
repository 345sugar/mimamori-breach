"""A Windows session-local mutex for one running app per state file."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path

from .storage import StorageError, default_path


_ERROR_ALREADY_EXISTS = 183
_ERROR_MESSAGE = "The application instance lock is unavailable."


class InstanceError(Exception):
    """An instance-lock failure with no paths or native error details."""


class InstanceLock:
    def __init__(self, path: Path | None = None):
        try:
            state_path = Path(path) if path is not None else default_path()
            normalized = os.path.normcase(str(state_path.resolve()))
            digest = hashlib.sha256(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()[:24]
            self.name = "Local\\MimamoriBreach-" + digest
        except (StorageError, OSError, ValueError, TypeError, RuntimeError):
            raise InstanceError(_ERROR_MESSAGE) from None
        self._handle: int | None = None
        self._kernel32 = None

    def acquire(self) -> bool:
        """Keep a named handle open, or return False if another app has one.

        The mutex does not use thread ownership. Its lifetime is the lifetime
        of our handle, and Windows releases the handle if the app exits.
        """
        if os.name != "nt":
            raise InstanceError(_ERROR_MESSAGE)
        if self._handle is not None:
            return True
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            ctypes.set_last_error(0)
            handle = kernel32.CreateMutexW(None, False, self.name)
            error = ctypes.get_last_error()
            if not handle:
                raise InstanceError(_ERROR_MESSAGE)
            if error == _ERROR_ALREADY_EXISTS:
                # Keep no reference to somebody else's mutex: otherwise that
                # mutex would outlive the first app and block a later retry.
                if not kernel32.CloseHandle(handle):
                    raise InstanceError(_ERROR_MESSAGE)
                return False
            self._kernel32 = kernel32
            self._handle = handle
            return True
        except InstanceError:
            raise
        except (OSError, ValueError, TypeError, AttributeError, ctypes.ArgumentError):
            raise InstanceError(_ERROR_MESSAGE) from None

    def close(self) -> None:
        """Close this instance's handle; repeated calls are harmless."""
        if self._handle is None:
            return
        try:
            if not self._kernel32.CloseHandle(self._handle):
                raise InstanceError(_ERROR_MESSAGE)
            self._handle = None
            self._kernel32 = None
        except InstanceError:
            raise
        except (OSError, ValueError, TypeError, AttributeError, ctypes.ArgumentError):
            raise InstanceError(_ERROR_MESSAGE) from None
