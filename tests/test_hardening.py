"""Regression tests in fixtures, never against real apps/accounts.

Uses macOS Bash/PlistBuddy/plutil; signatures and process observations are mocked.
No HOME override, no network, and no registration of fixture apps.
"""
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="multi-claude-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.apps = self.root / "apps"
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.home.mkdir()
        self.source = self.apps / "Claude.app"
        (self.source / "Contents/MacOS").mkdir(parents=True)
        (self.source / "Contents/Resources").mkdir()
        self.info = {
            "CFBundleIdentifier": "com.anthropic.claudefordesktop",
            "CFBundleShortVersionString": "1.0.fixture",
            "CFBundleDisplayName": "Claude",
            "CFBundleExecutable": "Claude",
            "CFBundleIconFile": "electron.icns",
            "CFBundleIconName": "electron",
            "CFBundleURLTypes": [], "NSUserActivityTypes": [],
        }
        (self.source / "Contents/Info.plist").write_bytes(plistlib.dumps(self.info))
        binary = self.source / "Contents/MacOS/Claude"
        binary.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\nprintf "CONFIG=%s VALUE=%s\\n" "${CLAUDE_CONFIG_DIR:-}" "${AUDIT_VALUE:-}"\n')
        binary.chmod(0o755)
        self.config = self.root / "instances.conf"
        self.env = os.environ.copy()
        self.env.update({
            "PATH": str(self.bin) + ":" + self.env["PATH"],
            "CLAUDE_INSTANCES_CONF": str(self.config),
            "MULTI_CLAUDE_TEST_HOME": str(self.home),
        })
        for src in (REPO / "bin").glob("*.sh"):
            code = src.read_text().replace("$HOME", "$MULTI_CLAUDE_TEST_HOME")
            code = code.replace("/Applications", str(self.apps))
            code = code.replace("CI_PB=/usr/libexec/PlistBuddy", "CI_PB=" + str(self.bin / "pb"))
            code = code.replace("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister", "/usr/bin/true")
            code = code.replace("/usr/bin/osascript", str(self.bin / "osascript"))
            (self.bin / src.name).write_text(code)
        mocks = {
            "ps": '''#!/bin/bash
[ "${MOCK_PS_FAIL:-}" != 1 ] || exit 99
if [ "$1" = -Aww ]; then
 [ -z "${MOCK_RUNNING_APP:-}" ] || printf '101 %s/Contents/MacOS/Claude\n' "$MOCK_RUNNING_APP"
else
 printf 'Claude --user-data-dir=%s\n' "${MOCK_PROFILE:-}"
fi
exit 0
''',
            "codesign": '''#!/bin/bash
previous=""
for arg in "$@"; do
 if [[ "$previous" == -R && "$arg" != =anchor* ]]; then exit 98; fi
 previous="$arg"
done
if [[ "$*" == *"-R "* && "${MOCK_SOURCE_BAD:-}" == 1 ]]; then exit 1; fi
if [[ "$1" == --force && "${MOCK_SIGN_BAD:-}" == 1 ]]; then exit 1; fi
exit 0
''',
            "spctl": '#!/bin/bash\n[ "${MOCK_GATEKEEPER_BAD:-}" != 1 ]\n',
            "pb": '''#!/bin/bash
if [[ "${MOCK_PLIST_FAIL:-}" == 1 && "$2" == "Set :CFBundleIdentifier "* ]]; then exit 99; fi
exec /usr/libexec/PlistBuddy "$@"
''',
            "mv": '''#!/bin/bash
if [[ "${MOCK_PUBLISH_FAIL:-}" == 1 && "$1" == */instance.app ]]; then exit 1; fi
exec /bin/mv "$@"
''',
            "cp": '#!/bin/bash\n[ "${MOCK_COPY_FAIL:-}" != 1 ] || exit 1\nexec /bin/cp "$@"\n',
            "open": '#!/bin/bash\nexit 0\n',
            "osascript": '#!/bin/bash\nexit 0\n',
            "claude-recolor-icon.sh": '#!/bin/bash\nprintf fixture-icon > "$2"\n',
        }
        for name, code in mocks.items():
            p = self.bin / name
            p.write_text(code)
            p.chmod(0o755)
        self.write_config()

    def write_config(self, rows=None):
        if rows is None:
            rows = [("One", "com.audit.one", str(self.home / "profile one"), "142", "CLAUDE_CONFIG_DIR=" + str(self.home / "code one"))]
        self.config.write_text("\n".join(" | ".join(row) for row in rows) + "\n")

    def run_script(self, *args, script="claude-apps-refresh.sh"):
        return subprocess.run(["/bin/bash", str(self.bin / script), *args], env=self.env,
                              text=True, capture_output=True, timeout=20)

    @property
    def app(self):
        return self.apps / "Claude One.app"

    def build(self):
        p = self.run_script()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_build_and_gui_launcher_environment(self):
        self.build()
        p = subprocess.run(["/bin/bash", str(self.app / "Contents/MacOS/launcher")],
                           env=self.env, text=True, capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--user-data-dir=" + str(self.home / "profile one"), p.stdout)
        self.assertIn("CONFIG=" + str(self.home / "code one"), p.stdout)
        self.assertEqual(self.run_script("--verify").returncode, 0)
        for path in [self.home / "profile one", self.home / "code one"]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_invalid_names_and_traversal_rejected_before_mutation(self):
        for name in ["X/../../victim", "bad name", "../Claude", "A$(touch marker)", "-bad"]:
            with self.subTest(name=name):
                self.write_config([(name, "com.audit.one", str(self.home / "p"), "142", "")])
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertFalse(self.app.exists())

    def test_invalid_environment_names_rejected(self):
        marker = self.root / "marker"
        for env in ["X$(touch " + str(marker) + ")=ok", "BASH_ENV=bad", "DYLD_INSERT_LIBRARIES=bad", "PATH=/bad", "HOME=/bad", "NODE_OPTIONS=bad", "A=one;A=two"]:
            with self.subTest(env=env):
                self.write_config([("One", "com.audit.one", str(self.home / "p"), "142", env)])
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertFalse(marker.exists())

    def test_environment_values_are_data_and_list_redacts_them(self):
        marker = self.root / "marker"
        value = "$(touch " + str(marker) + ")"
        self.write_config([("One", "com.audit.one", str(self.home / "p"), "142", "AUDIT_VALUE=" + value)])
        self.build()
        p = subprocess.run(["/bin/bash", str(self.app / "Contents/MacOS/launcher")], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(value, p.stdout)
        self.assertFalse(marker.exists())
        listed = self.run_script("--list")
        self.assertIn("AUDIT_VALUE", listed.stdout)
        self.assertNotIn(value, listed.stdout)

    def test_verification_never_executes_tampered_launcher(self):
        self.build()
        marker = self.root / "marker"
        (self.app / "Contents/MacOS/launcher").write_text("#!/bin/bash\nDATA_DIR=$(touch " + str(marker) + ")\n")
        self.assertNotEqual(self.run_script("--verify").returncode, 0)
        self.assertFalse(marker.exists())

    def test_verification_compares_environment_values(self):
        self.build()
        p = self.app / "Contents/MacOS/launcher"
        p.write_text(p.read_text().replace("code\\ one", "code\\ other"))
        self.assertNotEqual(self.run_script("--verify").returncode, 0)

    def test_missing_apps_are_a_failure(self):
        self.assertNotEqual(self.run_script("--verify").returncode, 0)

    def test_duplicates_and_alias_profiles_rejected(self):
        real = self.home / "real"
        real.mkdir()
        alias = self.home / "alias"
        alias.symlink_to(real, target_is_directory=True)
        variants = [
            ("Two", "com.audit.one", str(self.home / "other"), str(self.home / "c2")),
            ("one", "com.audit.two", str(self.home / "other"), str(self.home / "c2")),
            ("Two", "com.audit.two", str(real), str(self.home / "c2")),
            ("Two", "com.audit.two", str(alias), str(self.home / "c2")),
            ("Two", "com.audit.two", str(real) + "/.", str(self.home / "c2")),
            ("Two", "com.audit.two", str(self.home / "other"), str(self.home / "c1")),
        ]
        for name, bid, profile, code in variants:
            self.write_config([("One", "com.audit.one", str(real), "142", "CLAUDE_CONFIG_DIR=" + str(self.home / "c1")),
                               (name, bid, profile, "212", "CLAUDE_CONFIG_DIR=" + code)])
            self.assertNotEqual(self.run_script().returncode, 0)

    def test_two_default_code_directories_rejected(self):
        self.write_config([("One", "com.audit.one", str(self.home / "p1"), "142", ""),
                           ("Two", "com.audit.two", str(self.home / "p2"), "212", "")])
        self.assertNotEqual(self.run_script().returncode, 0)

    def test_source_and_gatekeeper_failure_leave_apps_untouched(self):
        self.build()
        sentinel = self.app / "sentinel"
        sentinel.write_text("keep")
        for flag in ["MOCK_SOURCE_BAD", "MOCK_GATEKEEPER_BAD"]:
            self.env[flag] = "1"
            self.assertNotEqual(self.run_script().returncode, 0)
            self.assertEqual(sentinel.read_text(), "keep")
            del self.env[flag]

    def test_failed_copy_plist_or_signing_preserves_old_bundle(self):
        self.build()
        sentinel = self.app / "sentinel"
        sentinel.write_text("keep")
        for flag in ["MOCK_COPY_FAIL", "MOCK_PLIST_FAIL", "MOCK_SIGN_BAD"]:
            with self.subTest(flag=flag):
                self.env[flag] = "1"
                self.assertNotEqual(self.run_script().returncode, 0)
                self.assertEqual(sentinel.read_text(), "keep")
                self.assertFalse(list(self.apps.glob(".claude-build.*")))
                del self.env[flag]

    def test_failed_publication_restores_previous_app(self):
        self.build()
        sentinel = self.app / "sentinel"
        sentinel.write_text("keep")
        self.env["MOCK_PUBLISH_FAIL"] = "1"
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_unknown_process_state_blocks_rebuild_and_health_check(self):
        self.env["MOCK_PS_FAIL"] = "1"
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse(self.app.exists())
        self.assertEqual(self.run_script(script="claude-instance-check.sh").returncode, 2)

    def test_running_app_blocks_rebuild(self):
        self.env["MOCK_RUNNING_APP"] = str(self.app)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse(self.app.exists())

    def test_symlink_destination_rejected(self):
        victim = self.root / "victim"
        victim.mkdir()
        self.app.symlink_to(victim, target_is_directory=True)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertTrue(victim.is_dir())

    def test_lock_does_not_get_removed_by_another_run(self):
        lock = self.home / ".local/share/claude-instances/.refresh-lock"
        lock.mkdir(parents=True)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertTrue(lock.is_dir())

    def test_launcher_rejects_profile_override(self):
        self.build()
        p = subprocess.run(["/bin/bash", str(self.app / "Contents/MacOS/launcher"), "--user-data-dir=/other"], env=self.env, capture_output=True)
        self.assertNotEqual(p.returncode, 0)

    def test_cache_preserves_data_and_refuses_a_shared_running_profile(self):
        self.build()
        profile = self.home / "profile one"
        (profile / "Cache").mkdir()
        (profile / "Cache/sentinel").write_text("cache")
        (profile / "Local Storage").mkdir()
        (profile / "Local Storage/sentinel").write_text("keep")
        self.env["MOCK_RUNNING_APP"] = str(self.source)
        self.env["MOCK_PROFILE"] = str(profile)
        self.assertNotEqual(self.run_script(script="claude-clear-caches.sh").returncode, 0)
        self.assertTrue((profile / "Cache/sentinel").exists())
        del self.env["MOCK_RUNNING_APP"]
        self.assertEqual(self.run_script(script="claude-clear-caches.sh").returncode, 0)
        self.assertFalse((profile / "Cache").exists())
        self.assertEqual((profile / "Local Storage/sentinel").read_text(), "keep")

    def test_watchdog_detects_tampering(self):
        self.build()
        self.env["CLAUDE_STALE_CHECK_DELAY"] = "0"
        self.assertEqual(self.run_script(script="claude-stale-check.sh").returncode, 0)
        p = self.app / "Contents/MacOS/launcher"
        p.write_text(p.read_text() + "\necho altered\n")
        self.assertNotEqual(self.run_script(script="claude-stale-check.sh").returncode, 0)

    def test_source_is_never_modified(self):
        before = {str(p.relative_to(self.source)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.source.rglob("*") if p.is_file()}
        self.build()
        after = {str(p.relative_to(self.source)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.source.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_numeric_hues_and_malformed_config(self):
        for hue in ["0", "000", "359"]:
            self.write_config([("One", "com.audit.one", str(self.home / "p"), hue, "")])
            self.assertEqual(self.run_script("--list").returncode, 0, hue)
        for hue in ["-1", "360", "NaN", "1.5", "1000"]:
            self.write_config([("One", "com.audit.one", str(self.home / "p"), hue, "")])
            self.assertNotEqual(self.run_script("--list").returncode, 0, hue)
        self.config.write_text("One | com.audit.one | /tmp/p | 142 | A=b | extra\n")
        self.assertNotEqual(self.run_script("--list").returncode, 0)

    def test_root_home_application_and_relative_profiles_rejected(self):
        for path in ["/", str(self.home), str(self.source), "relative/path"]:
            self.write_config([("One", "com.audit.one", path, "142", "")])
            self.assertNotEqual(self.run_script("--list").returncode, 0, path)

    def test_config_without_final_newline_and_apostrophe_path(self):
        profile = str(self.home / "user's profile")
        self.write_config([("One", "com.audit.one", profile, "142", "")])
        self.config.write_text(self.config.read_text().rstrip("\n"))
        self.build()
        self.assertEqual(self.run_script("--verify").returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
