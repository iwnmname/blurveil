import unittest
from unittest.mock import patch

from platforms import macos_permissions


class MacOSPermissionsTests(unittest.TestCase):
    def test_returns_no_statuses_on_non_macos(self):
        with patch("platforms.macos_permissions.platform.system", return_value="Windows"):
            self.assertFalse(macos_permissions.is_macos())
            self.assertEqual([], macos_permissions.get_macos_permission_statuses())
            self.assertFalse(macos_permissions.has_missing_macos_permissions())

    def test_detects_missing_checked_permission_on_macos(self):
        with patch("platforms.macos_permissions.platform.system", return_value="Darwin"):
            with patch("platforms.macos_permissions._screen_recording_granted", return_value=False):
                with patch("platforms.macos_permissions._accessibility_granted", return_value=True):
                    statuses = macos_permissions.get_macos_permission_statuses()

        self.assertEqual(["screen_recording", "accessibility", "input_monitoring"], [status.key for status in statuses])
        self.assertFalse(statuses[0].granted)
        self.assertTrue(statuses[1].granted)
        self.assertIsNone(statuses[2].granted)

    def test_unknown_input_monitoring_does_not_force_preflight(self):
        with patch("platforms.macos_permissions.platform.system", return_value="Darwin"):
            with patch("platforms.macos_permissions._screen_recording_granted", return_value=True):
                with patch("platforms.macos_permissions._accessibility_granted", return_value=True):
                    self.assertFalse(macos_permissions.has_missing_macos_permissions())


if __name__ == "__main__":
    unittest.main()
