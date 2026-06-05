import unittest
from unittest.mock import patch

from gui.permissions import should_show_macos_permissions_preflight


class PermissionsPreflightTests(unittest.TestCase):
    def test_preflight_is_disabled_on_non_macos(self):
        with patch("gui.permissions.is_macos", return_value=False):
            with patch("gui.permissions.has_missing_macos_permissions", return_value=True):
                self.assertFalse(should_show_macos_permissions_preflight())

    def test_preflight_is_enabled_for_missing_macos_permissions(self):
        with patch("gui.permissions.is_macos", return_value=True):
            with patch("gui.permissions.has_missing_macos_permissions", return_value=True):
                self.assertTrue(should_show_macos_permissions_preflight())


if __name__ == "__main__":
    unittest.main()
