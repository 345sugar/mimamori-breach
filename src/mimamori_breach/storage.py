"""Bounded, atomic JSON persistence protected by the current Windows user.

No plaintext is written to disk. DPAPI protects this file at rest; programs
running as the same Windows user can still decrypt it.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import tempfile


MAX_FILE_BYTES = 4 * 1024 * 1024
_ENTROPY = b"MimamoriBreach/state/v1"
_FLAGS = 0x1  # CRYPTPROTECT_UI_FORBIDDEN, current-user protection (not LOCAL_MACHINE).
_ERROR_MESSAGE = "Encrypted local storage is unavailable."


class StorageError(Exception):
    """Safe to show to the user: contains no paths, input, or Windows errors."""


def _require_windows() -> None:
    if os.name != "nt":
        raise StorageError("Encrypted local storage requires Windows.")


def default_path() -> Path:
    """Return a per-user app-data path without inspecting existing secrets."""
    _require_windows()
    location = os.environ.get("LOCALAPPDATA")
    if not location or not Path(location).is_absolute():
        raise StorageError(_ERROR_MESSAGE)
    return Path(location) / "MimamoriBreach" / "state.bin"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    _require_windows()
    if not data or len(data) > MAX_FILE_BYTES:
        raise StorageError(_ERROR_MESSAGE)
    try:
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        blob_pointer = ctypes.POINTER(_DataBlob)
        crypt32.CryptProtectData.argtypes = [
            blob_pointer, wintypes.LPCWSTR, blob_pointer, ctypes.c_void_p,
            ctypes.c_void_p, wintypes.DWORD, blob_pointer,
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL
        crypt32.CryptUnprotectData.argtypes = [
            blob_pointer, ctypes.c_void_p, blob_pointer, ctypes.c_void_p,
            ctypes.c_void_p, wintypes.DWORD, blob_pointer,
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        # Keep these buffers alive until the Windows call has finished.
        input_buffer = ctypes.create_string_buffer(data)
        entropy_buffer = ctypes.create_string_buffer(_ENTROPY)
        source = _DataBlob(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        entropy = _DataBlob(len(_ENTROPY), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        result = _DataBlob()
        function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
        description = None if decrypt else "Mimamori Breach local state"
        try:
            success = function(
                ctypes.byref(source), description, ctypes.byref(entropy),
                None, None, _FLAGS, ctypes.byref(result),
            )
            if not success or not result.pbData or not 0 < result.cbData <= MAX_FILE_BYTES:
                raise StorageError(_ERROR_MESSAGE)
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            if result.pbData:
                kernel32.LocalFree(ctypes.cast(result.pbData, ctypes.c_void_p))
    except StorageError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, ctypes.ArgumentError):
        raise StorageError(_ERROR_MESSAGE) from None


def _protect(data: bytes) -> bytes:
    return _dpapi(data, decrypt=False)


def _unprotect(data: bytes) -> bytes:
    return _dpapi(data, decrypt=True)


def _reject_constant(_value: str) -> None:
    raise ValueError("Invalid JSON constant")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_path()

    def load(self) -> dict:
        """Read an encrypted JSON object; a missing file is an empty state."""
        _require_windows()
        try:
            try:
                with self.path.open("rb") as handle:
                    encrypted = handle.read(MAX_FILE_BYTES + 1)
            except FileNotFoundError:
                return {}
            if not encrypted or len(encrypted) > MAX_FILE_BYTES:
                raise StorageError(_ERROR_MESSAGE)
            plaintext = _unprotect(encrypted)
            if len(plaintext) > MAX_FILE_BYTES:
                raise StorageError(_ERROR_MESSAGE)
            payload = json.loads(
                plaintext.decode("utf-8"), parse_constant=_reject_constant,
                object_pairs_hook=_unique_object,
            )
            if not isinstance(payload, dict):
                raise StorageError(_ERROR_MESSAGE)
            return payload
        except StorageError:
            raise
        except (OSError, ValueError, TypeError, RecursionError):
            raise StorageError(_ERROR_MESSAGE) from None

    def save(self, payload: dict) -> None:
        """Replace the state only after encryption and a complete disk write."""
        _require_windows()
        temporary: str | None = None
        descriptor: int | None = None
        try:
            if not isinstance(payload, dict):
                raise StorageError(_ERROR_MESSAGE)
            plaintext = json.dumps(
                payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
            ).encode("utf-8")
            if len(plaintext) > MAX_FILE_BYTES:
                raise StorageError(_ERROR_MESSAGE)
            encrypted = _protect(plaintext)
            if not encrypted or len(encrypted) > MAX_FILE_BYTES:
                raise StorageError(_ERROR_MESSAGE)
            # Fail closed if an existing state cannot be read. A caller should
            # not silently reset corrupted or differently protected state.
            self.load()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=self.path.parent)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None  # The context manager now owns the descriptor.
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except StorageError:
            raise
        except (OSError, ValueError, TypeError, RecursionError):
            raise StorageError(_ERROR_MESSAGE) from None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
