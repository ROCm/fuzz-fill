import tempfile
import unittest
from pathlib import Path

from coverage.lit_config import (
    PATCH_MARKER,
    ensure_lit_sancov_env_forwarding,
    lit_site_config_path,
    lit_test_suite_path,
)


class LitConfigPatchTest(unittest.TestCase):
    def test_patch_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            bin_dir = build / "bin"
            bin_dir.mkdir()
            site_cfg = build / "test" / "lit.site.cfg.py"
            site_cfg.parent.mkdir(parents=True)
            site_cfg.write_text(
                "lit_config.load_config(config, 'lit.cfg.py')\n",
                encoding="utf-8",
            )

            first = ensure_lit_sancov_env_forwarding(bin_dir)
            first_text = first.read_text(encoding="utf-8")
            self.assertIn(PATCH_MARKER, first_text)

            second = ensure_lit_sancov_env_forwarding(bin_dir)
            self.assertEqual(first_text, second.read_text(encoding="utf-8"))
            self.assertEqual(site_cfg, second)

    def test_lit_site_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            bin_dir = build / "bin"
            bin_dir.mkdir()
            self.assertEqual(
                lit_site_config_path(bin_dir),
                build / "test" / "lit.site.cfg.py",
            )
            self.assertEqual(lit_test_suite_path(bin_dir), build / "test")

    def test_missing_site_config_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            with self.assertRaises(FileNotFoundError):
                ensure_lit_sancov_env_forwarding(bin_dir)


if __name__ == "__main__":
    unittest.main()
