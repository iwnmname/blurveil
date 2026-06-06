import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QSettings

from gui.onboarding import mark_onboarding_seen, should_show_onboarding


class OnboardingSettingsTests(unittest.TestCase):
    def test_onboarding_is_shown_until_marked_seen(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.ini"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)

            self.assertTrue(should_show_onboarding(settings))

            mark_onboarding_seen(settings)

            self.assertFalse(should_show_onboarding(settings))


if __name__ == "__main__":
    unittest.main()
