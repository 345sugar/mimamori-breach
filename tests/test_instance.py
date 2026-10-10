from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mimamori_breach.instance import InstanceError, InstanceLock


@unittest.skipUnless(os.name == "nt", "Windows named mutexes are required")
class WindowsInstanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "state.bin"

    def lock(self, path=None):
        lock = InstanceLock(path if path is not None else self.path)
        self.addCleanup(lock.close)
        return lock

    def test_second_instance_is_blocked_until_first_closes(self):
        first = self.lock()
        second = self.lock()
        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())
        first.close()
        self.assertTrue(second.acquire())
        third = self.lock()
        self.assertFalse(third.acquire())

    def test_close_before_acquisition_and_repeated_close_are_safe(self):
        first = self.lock()
        first.close()
        first.close()
        self.assertTrue(first.acquire())
        self.assertTrue(first.acquire())
        first.close()
        first.close()
        self.assertTrue(self.lock().acquire())

    def test_different_state_paths_do_not_conflict(self):
        first = self.lock()
        second = self.lock(self.path.parent / "different.bin")
        self.assertTrue(first.acquire())
        self.assertTrue(second.acquire())

    def test_case_and_dot_components_resolve_to_same_lock(self):
        first = self.lock()
        equivalent = self.path.parent / "unused" / ".." / "STATE.BIN"
        second = self.lock(equivalent)
        self.assertEqual(first.name, second.name)
        self.assertTrue(first.acquire())
        self.assertFalse(second.acquire())

    def test_default_uses_the_same_state_path(self):
        with patch("mimamori_breach.instance.default_path", return_value=self.path):
            default_lock = InstanceLock()
            self.addCleanup(default_lock.close)
        self.assertTrue(default_lock.acquire())
        self.assertFalse(self.lock().acquire())
        self.assertNotIn(str(self.path), default_lock.name)


class InstancePlatformTests(unittest.TestCase):
    def test_unsupported_platform_cannot_acquire(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = InstanceLock(Path(directory) / "state.bin")
            with patch("mimamori_breach.instance.os.name", "posix"):
                with self.assertRaises(InstanceError):
                    lock.acquire()
            lock.close()


if __name__ == "__main__":
    unittest.main()
