import unittest
from unittest.mock import patch

from gui.hotkey import format_hotkey_for_display


class HotkeyFormattingTests(unittest.TestCase):
    def test_formats_macos_alt_as_option_and_cmd_as_cmd(self):
        with patch("gui.hotkey.platform.system", return_value="Darwin"):
            self.assertEqual("Ctrl+Option+S", format_hotkey_for_display("<ctrl>+<alt>+s"))
            self.assertEqual("Cmd+Shift+S", format_hotkey_for_display("<cmd>+<shift>+s"))

    def test_formats_windows_alt_and_cmd_as_win(self):
        with patch("gui.hotkey.platform.system", return_value="Windows"):
            self.assertEqual("Ctrl+Alt+S", format_hotkey_for_display("<ctrl>+<alt>+s"))
            self.assertEqual("Win+Shift+S", format_hotkey_for_display("<cmd>+<shift>+s"))


if __name__ == "__main__":
    unittest.main()
