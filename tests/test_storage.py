from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mimamori_breach.storage import MAX_FILE_BYTES, StorageError, Store, default_path


@unittest.skipUnless(os.name == "nt", "Windows DPAPI is required")
class WindowsStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "nested" / "state.bin"
        self.store = Store(self.path)

    def test_missing_state_and_encrypted_roundtrip(self):
        self.assertEqual(self.store.load(), {})
        data = {
            "email": "synthetic@example.invalid",
            "api_key": "test-only-key-never-a-real-credential",
            "findings": [{"name": "架空の漏洩", "acknowledged": False}],
        }
        self.store.save(data)
        self.assertEqual(self.store.load(), data)
        ciphertext = self.path.read_bytes()
        for secret in (data["email"], data["api_key"], "架空の漏洩"):
            self.assertNotIn(secret.encode("utf-8"), ciphertext)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_atomic_replacement_updates_existing_state(self):
        self.store.save({"value": "before"})
        self.store.save({"value": "after"})
        self.assertEqual(self.store.load(), {"value": "after"})

    def test_interrupted_replace_preserves_previous_ciphertext(self):
        self.store.save({"value": "before"})
        before = self.path.read_bytes()
        with patch("mimamori_breach.storage.os.replace", side_effect=OSError("sensitive/path")):
            with self.assertRaises(StorageError) as error:
                self.store.save({"value": "after"})
        self.assertNotIn("sensitive", str(error.exception))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.load(), {"value": "before"})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_interrupted_flush_preserves_previous_ciphertext(self):
        self.store.save({"value": "before"})
        before = self.path.read_bytes()
        with patch("mimamori_breach.storage.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaises(StorageError):
                self.store.save({"value": "after"})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_payload_does_not_overwrite_previous_state(self):
        self.store.save({"value": "before"})
        before = self.path.read_bytes()
        for payload in (["wrong root type"], {"bad": float("nan")}, {"bad": object()}):
            with self.subTest(payload_type=type(payload).__name__):
                with self.assertRaises(StorageError):
                    self.store.save(payload)
                self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_state_is_preserved_on_load_and_save(self):
        self.path.parent.mkdir()
        corrupt = b"not-a-dpapi-blob"
        self.path.write_bytes(corrupt)
        with self.assertRaises(StorageError):
            self.store.load()
        with self.assertRaises(StorageError):
            self.store.save({"replacement": True})
        self.assertEqual(self.path.read_bytes(), corrupt)

    def test_oversized_file_and_payload_are_rejected_without_overwrite(self):
        self.path.parent.mkdir()
        original = b"x" * (MAX_FILE_BYTES + 1)
        self.path.write_bytes(original)
        with self.assertRaises(StorageError):
            self.store.load()
        with self.assertRaises(StorageError):
            self.store.save({"large": "x" * MAX_FILE_BYTES})
        self.assertEqual(self.path.read_bytes(), original)

    def test_valid_encryption_with_invalid_json_is_rejected(self):
        from mimamori_breach.storage import _protect
        self.path.parent.mkdir()
        for raw in (b"[]", b'{"a":NaN}', b'{"a":1,"a":2}', b"not-json"):
            with self.subTest(raw=raw):
                encrypted = _protect(raw)
                self.path.write_bytes(encrypted)
                with self.assertRaises(StorageError):
                    self.store.load()
                self.assertEqual(self.path.read_bytes(), encrypted)

    def test_default_path_is_under_local_app_data(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": self.temporary.name}):
            self.assertEqual(default_path(), Path(self.temporary.name) / "MimamoriBreach" / "state.bin")


class PlatformTests(unittest.TestCase):
    def test_unsupported_platform_has_no_plaintext_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.bin"
            store = Store(path)
            with patch("mimamori_breach.storage.os.name", "posix"):
                with self.assertRaises(StorageError):
                    store.load()
                with self.assertRaises(StorageError):
                    store.save({"api_key": "synthetic"})
                with self.assertRaises(StorageError):
                    default_path()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
