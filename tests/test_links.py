"""The managed copy's claude-dev:// links (@links), in synthetic bundles only."""
import plistlib
import unittest

import test_hardening as hardening

EXPECTED = [{"CFBundleURLName": "Claude One links", "CFBundleURLSchemes": ["claude-dev"]}]


class LinksTests(unittest.TestCase):
    def setUp(self):
        self.fixture = hardening.HardeningTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.rows = self.fixture.config.read_text()
        # The stock app declares claude:// (and more); the copy must never inherit it.
        info = plistlib.loads((self.fixture.source / "Contents/Info.plist").read_bytes())
        info["CFBundleURLTypes"] = [{"CFBundleURLName": "Claude", "CFBundleURLSchemes": ["claude"]}]
        (self.fixture.source / "Contents/Info.plist").write_bytes(plistlib.dumps(info))

    def configure(self, *headers):
        self.fixture.config.write_text("".join(h + "\n" for h in headers) + self.rows)

    def info(self):
        return plistlib.loads((self.fixture.app / "Contents/Info.plist").read_bytes())

    def test_links_register_only_claude_dev_and_the_record_verifies_it(self):
        self.configure("@mode original-copy", "@links claude-dev")
        self.fixture.build()
        self.assertEqual(self.info()["CFBundleURLTypes"], EXPECTED)
        self.assertNotIn("NSUserActivityTypes", self.info())
        verified = self.fixture.run_script("--verify")
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_without_links_the_copy_declares_no_scheme(self):
        for headers in (("@mode original-copy",), ("@mode original-copy", "@links none")):
            with self.subTest(headers=headers):
                self.configure(*headers)
                self.fixture.build()
                self.assertNotIn("CFBundleURLTypes", self.info())
                self.assertEqual(self.fixture.run_script("--verify").returncode, 0)

    def test_turning_links_on_or_off_requires_a_rebuild(self):
        self.configure("@mode original-copy")
        self.fixture.build()
        self.configure("@mode original-copy", "@links claude-dev")
        self.assertNotEqual(self.fixture.run_script("--verify").returncode, 0)
        self.fixture.build()
        self.assertEqual(self.fixture.run_script("--verify").returncode, 0)
        self.configure("@mode original-copy")
        self.assertNotEqual(self.fixture.run_script("--verify").returncode, 0)

    def test_a_scheme_other_than_the_planned_one_is_refused_before_publication(self):
        self.configure("@mode original-copy", "@links claude-dev")
        pb = self.fixture.bin / "pb"
        # A builder that wrote claude:// instead: the record regenerates the
        # expected plist from the source and refuses the difference.
        pb.write_text('#!/bin/bash\nargs=()\nfor a in "$@"; do args+=("${a/string claude-dev/string claude}"); done\n'
                      'exec /usr/libexec/PlistBuddy "${args[@]}"\n')
        result = self.fixture.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Info.plist differs", result.stderr)
        self.assertFalse(self.fixture.app.exists())

    def test_tampering_with_the_url_types_after_the_build_is_detected(self):
        self.configure("@mode original-copy", "@links claude-dev")
        self.fixture.build()
        info = self.info()
        info["CFBundleURLTypes"][0]["CFBundleURLSchemes"].append("claude")
        (self.fixture.app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        self.assertNotEqual(self.fixture.run_script("--verify").returncode, 0)

    def test_links_are_config_data_with_one_reviewed_value(self):
        for headers in (("@links claude-dev",),  # legacy copies: several apps would fight over the scheme
                        ("@mode original-copy", "@links claude"),
                        ("@mode original-copy", "@links claude-duo"),
                        ("@mode original-copy", "@links claude-dev extra"),
                        ("@mode original-copy", "@links $(touch marker)"),
                        ("@mode original-copy", "@links claude-dev", "@links claude-dev")):
            with self.subTest(headers=headers):
                self.configure(*headers)
                result = self.fixture.run_script("--list")
                self.assertNotEqual(result.returncode, 0)
        self.fixture.config.write_text("@mode original-copy\n" + self.rows + "@links claude-dev\n")
        self.assertNotEqual(self.fixture.run_script("--list").returncode, 0)
        self.assertFalse((self.fixture.root / "marker").exists())


if __name__ == "__main__":
    unittest.main()
