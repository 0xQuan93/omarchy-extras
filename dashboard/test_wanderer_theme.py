import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import wanderer_theme as theme


class ThemeTests(unittest.TestCase):
    def test_active_palette_switch_and_transient_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            colors = path / 'colors.toml'
            with patch.object(theme, 'THEME', path), patch.object(theme, '_signature', None), patch.object(theme, '_css', b''):
                colors.write_text('background = "#101010"\nforeground = "#eeeeee"\naccent = "#bb88ff"\n')
                dark = theme.stylesheet()
                self.assertIn(b'color-scheme:dark', dark)
                self.assertIn(b'--background:#101010', dark)
                colors.write_text('background = "#fafafa"\nforeground = "#202020"\naccent = "#553399"\nmode = "light"\n')
                light = theme.stylesheet()
                self.assertIn(b'color-scheme:light', light)
                self.assertIn(b'--background:#fafafa', light)
                self.assertNotEqual(dark, light)
                colors.unlink()
                self.assertEqual(theme.stylesheet(), light)

    def test_css_values_cannot_inject_rules(self):
        css = theme.render({'accent': 'red;}body{display:none', 'mode': 'light;bad'})
        self.assertNotIn(b'display:none', css)
        self.assertIn(b'color-scheme:dark', css)


if __name__ == '__main__':
    unittest.main()
