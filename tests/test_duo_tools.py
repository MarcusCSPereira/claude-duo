"""Claude Duo installer/updater/update check in a temporary HOME.

Dialogs, notifications, process lists, quitting and the toolset dispatcher
are mocked; plist handling and the shell logic are real. Nothing touches the
caller's apps, profiles, launch agents or toolset.
"""
import os
from pathlib import Path
import re
import plistlib
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]

OSASCRIPT = '''#!/bin/bash
printf '%s\\n' "$*" >> "$MOCK_DIR/osascript.log"
case "$*" in
 *"display alert"*) printf '%s\\n' "${MOCK_ANSWER:-}" ;;
 *claudefordesktop*" to quit"*) [ "${MOCK_STUCK:-}" = 1 ] || { grep -v "/Claude.app/" "$MOCK_DIR/running" > "$MOCK_DIR/r"; mv "$MOCK_DIR/r" "$MOCK_DIR/running"; } ;;
 *" to quit"*) [ "${MOCK_STUCK:-}" = 1 ] || { grep -v "/Claude Duo.app/" "$MOCK_DIR/running" > "$MOCK_DIR/r"; mv "$MOCK_DIR/r" "$MOCK_DIR/running"; } ;;
esac
exit 0
'''
# ps -o ppid=,comm= -p PID answers MOCK_PARENT for any PID: one ancestor, then launchd.
PS = '''#!/bin/bash
case "$*" in *ppid=*) printf '%s\\n' "${MOCK_PARENT:-1 /sbin/launchd}" ;; *) cat "$MOCK_DIR/running" 2>/dev/null ;; esac
exit 0
'''
OPEN = '#!/bin/bash\nprintf "%s\\n" "$*" >> "$MOCK_DIR/open.log"\n'
DISPATCHER = '''#!/bin/bash
printf '%s|%s\\n' "$CLAUDE_INSTANCES_CONF" "$*" >> "$MOCK_DIR/dispatcher.log"
[ "${MOCK_DISPATCH_FAIL:-}" != 1 ] || { echo "synthetic build failure" >&2; exit 1; }
[ ! -e "$MOCK_DIR/dispatch-stale" ] || { echo "process 4242 (chrome-native-host) runs a deleted executable; quit it and retry" >&2; exit 1; }
exit 0
'''


class DuoToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="duo-tools-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.mock = self.root / "mock"
        self.mock.mkdir()
        self.language = "en"
        (self.home / "Applications").mkdir(parents=True, mode=0o700)
        self.source_app = self.root / "Applications/Claude.app"
        self.duo_app = self.home / "Applications/Claude Duo.app"
        self.make_app(self.source_app, "2.0.0", "com.anthropic.claudefordesktop")
        self.make_app(self.duo_app, "1.0.0", "io.github.test.claude-duo")
        self.tools = self.home / ".local/share/claude-duo"
        self.tools.mkdir(parents=True)
        self.dispatcher = self.home / ".local/share/claude-instances/toolsets/dispatcher"
        self.dispatcher.parent.mkdir(parents=True)
        self.write_mock(self.dispatcher, DISPATCHER.replace("$MOCK_DIR", str(self.mock))
                        .replace('"${MOCK_DISPATCH_FAIL:-}" != 1', f'! -e "{self.mock}/dispatch-fail"'))
        for name, code in (("osascript", OSASCRIPT), ("ps", PS), ("open", OPEN), ("sleep", "#!/bin/bash\nexit 0\n")):
            self.write_mock(self.mock / name, code)
        self.config = self.home / ".config/claude-instances/claude-duo.conf"
        self.config.parent.mkdir(parents=True)
        self.config.write_text("@mode original-copy\n")
        (self.tools / "config-path").write_text(str(self.config) + "\n")
        for name in ("duo-common.sh", "update-duo.sh", "check-update.sh"):
            self.install_patched(REPO / "duo" / name, self.tools / name)
        self.env = {"HOME": str(self.home), "USER": "tester", "PATH": "/usr/bin:/bin", "MOCK_DIR": str(self.mock)}

    def make_app(self, app, version, identifier):
        (app / "Contents/MacOS").mkdir(parents=True)
        (app / "Contents/Info.plist").write_bytes(plistlib.dumps(
            {"CFBundleShortVersionString": version, "CFBundleIdentifier": identifier}))

    @staticmethod
    def write_mock(path, code):
        path.write_text(code)
        path.chmod(0o755)

    def patch(self, code):
        for old, new in (("OSASCRIPT=/usr/bin/osascript", f"OSASCRIPT={self.mock}/osascript"),
                         ("OPEN=/usr/bin/open", f"OPEN={self.mock}/open"),
                         ("PS=/bin/ps", f"PS={self.mock}/ps"),
                         ("SLEEP=/bin/sleep", f"SLEEP={self.mock}/sleep"),
                         ("DUO_QUIT_TIMEOUT=60", "DUO_QUIT_TIMEOUT=3"),
                         ('DUO_SOURCE_APP="/Applications/Claude.app"', f'DUO_SOURCE_APP="{self.source_app}"')):
            code = code.replace(old, new)
        return re.sub(r"^DUO_LANGUAGE=.*$", "DUO_LANGUAGE=" + self.language, code, flags=re.M)

    def install_patched(self, source, target):
        target.write_text(self.patch(source.read_text()))
        target.chmod(0o700)

    def run_tool(self, name, *args):
        return subprocess.run(["/bin/bash", "-p", str(self.tools / name), *args], env=self.env,
                              capture_output=True, text=True, timeout=60)

    def log(self, name):
        path = self.mock / name
        return path.read_text() if path.exists() else ""

    def running(self, *apps):
        self.processes(*(f"{app}/Contents/MacOS/Claude" for app in apps))

    def processes(self, *executables):
        # Same shape as ps -axo pid=,comm=: right-aligned PID, then the executable.
        (self.mock / "running").write_text("".join(f"{pid:5d} {exe}\n" for pid, exe in enumerate(executables, 501)))

    def updater_log(self):
        return "".join(p.read_text() for p in (self.home / "Library/Logs/Claude Duo Updater").glob("update-*.log"))

    # Update check (launch agent)
    def test_check_is_silent_when_versions_match(self):
        info = plistlib.loads((self.duo_app / "Contents/Info.plist").read_bytes())
        info["CFBundleShortVersionString"] = "2.0.0"
        (self.duo_app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        self.assertEqual(self.run_tool("check-update.sh").returncode, 0)
        self.assertEqual(self.log("osascript.log"), "")

    def test_check_asks_once_a_day_per_version_and_later_does_nothing(self):
        self.env["MOCK_ANSWER"] = "Later"
        self.assertEqual(self.run_tool("check-update.sh").returncode, 0)
        self.assertIn("2.0.0", self.log("osascript.log"))
        self.assertIn("1.0.0", self.log("osascript.log"))
        self.assertEqual(self.log("dispatcher.log"), "")
        before = self.log("osascript.log")
        self.run_tool("check-update.sh")
        self.assertEqual(self.log("osascript.log"), before)  # Already asked today.

    def test_check_accepting_rebuilds_without_asking_again(self):
        self.env["MOCK_ANSWER"] = "Update now"
        result = self.run_tool("check-update.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log("osascript.log").count("display alert"), 1)
        self.assertEqual(self.log("dispatcher.log").splitlines(),
                         [f"{self.config}|run claude-apps-refresh.sh Duo", f"{self.config}|run claude-apps-refresh.sh --verify"])

    def test_check_does_nothing_when_not_installed(self):
        (self.tools / "config-path").unlink()
        self.assertEqual(self.run_tool("check-update.sh").returncode, 0)
        self.assertEqual(self.log("osascript.log"), "")

    # Updater
    def test_cancel_changes_nothing(self):
        self.running(self.source_app)
        self.env["MOCK_ANSWER"] = "Cancel"
        self.assertEqual(self.run_tool("update-duo.sh").returncode, 0)
        self.assertNotIn(" to quit", self.log("osascript.log"))
        self.assertEqual(self.log("dispatcher.log"), "")

    def test_update_quits_rebuilds_and_reopens_what_was_open(self):
        self.running(self.source_app, self.duo_app)
        self.env["MOCK_ANSWER"] = "Update now"
        result = self.run_tool("update-duo.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log("osascript.log").count(" to quit"), 2)
        self.assertIn("Duo", self.log("dispatcher.log"))
        self.assertEqual(self.log("open.log").splitlines(), [f"-a {self.source_app}", f"-a {self.duo_app}"])
        self.assertIn("updated to", self.log("osascript.log"))

    def test_update_reopens_only_apps_that_were_open(self):
        self.running(self.source_app)
        self.assertEqual(self.run_tool("update-duo.sh", "--yes").returncode, 0)
        self.assertEqual(self.log("open.log").splitlines(), [f"-a {self.source_app}"])

    def test_apps_that_do_not_quit_abort_before_building(self):
        self.running(self.source_app)
        self.env["MOCK_STUCK"] = "1"
        result = self.run_tool("update-duo.sh", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log("dispatcher.log"), "")
        self.assertIn("Could not quit", self.log("osascript.log"))
        self.assertIn(f"still running (PID executable):\n  501 {self.source_app}/Contents/MacOS/Claude\n", self.updater_log())

    def test_build_failure_is_reported_and_claude_reopened(self):
        self.running(self.source_app)
        (self.mock / "dispatch-fail").write_text("1")
        result = self.run_tool("update-duo.sh", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("update failed", self.log("osascript.log"))
        self.assertEqual(self.log("open.log").splitlines(), [f"-a {self.source_app}"])
        self.assertIn("synthetic build failure", self.updater_log())

    def test_process_running_a_deleted_executable_is_named_in_the_notification(self):
        (self.mock / "dispatch-stale").write_text("1")
        result = self.run_tool("update-duo.sh", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chrome-native-host (PID 4242) still runs a file from the previous Claude", self.log("osascript.log"))
        self.assertNotIn("update failed", self.log("osascript.log"))

    def test_bundle_helpers_started_by_other_programs_do_not_block_the_update(self):
        # Chrome starts chrome-native-host and the claude CLI starts disclaimer;
        # both run from Contents/Helpers and survive quitting the app.
        self.processes(f"{self.source_app}/Contents/Helpers/chrome-native-host",
                       f"{self.source_app}/Contents/Helpers/disclaimer")
        self.env["MOCK_STUCK"] = "1"
        result = self.run_tool("update-duo.sh", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Duo", self.log("dispatcher.log"))
        self.assertNotIn(" to quit", self.log("osascript.log"))
        self.assertEqual(self.log("open.log"), "")

    def test_electron_helpers_still_count_as_running(self):
        helper = "Claude Helper (Renderer)"
        self.processes(f"{self.source_app}/Contents/Frameworks/{helper}.app/Contents/MacOS/{helper}")
        self.env["MOCK_STUCK"] = "1"
        result = self.run_tool("update-duo.sh", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log("dispatcher.log"), "")

    def test_config_pointer_outside_the_config_folder_is_refused(self):
        outside = self.root / "evil.conf"
        outside.write_text("@mode original-copy\n")
        (self.tools / "config-path").write_text(str(outside) + "\n")
        self.assertNotEqual(self.run_tool("update-duo.sh", "--yes").returncode, 0)
        self.assertEqual(self.log("dispatcher.log"), "")

    def test_dialog_text_cannot_break_out_of_applescript_strings(self):
        self.env["MOCK_ANSWER"] = "Later"
        info = plistlib.loads((self.source_app / "Contents/Info.plist").read_bytes())
        info["CFBundleShortVersionString"] = '2" & (do shell script "touch PWNED") & "'
        (self.source_app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
        self.run_tool("check-update.sh")
        self.assertIn('2\\" & (do shell script \\"touch PWNED\\") & \\"', self.log("osascript.log"))

    def test_dialogs_follow_a_portuguese_macos_language(self):
        self.language = "pt-BR"
        for name in ("duo-common.sh", "update-duo.sh", "check-update.sh"):
            self.install_patched(REPO / "duo" / name, self.tools / name)
        self.env["MOCK_ANSWER"] = "Atualizar agora"  # The Portuguese button label.
        result = self.run_tool("check-update.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log("osascript.log")
        self.assertIn("O Claude foi atualizado para 2.0.0", log)
        self.assertIn('"Depois"', log)
        self.assertIn("claude-apps-refresh.sh Duo", self.log("dispatcher.log"))
        self.assertIn("Claude Duo atualizado para", self.log("osascript.log"))

    def test_installer_removes_the_earlier_portuguese_named_updater(self):
        installer = self.installer_fixture()
        legacy = self.home / "Applications/Atualizar Claude Duo.app"
        (legacy / "Contents").mkdir(parents=True)
        self.tools.mkdir(parents=True)
        for name in ("atualizar-duo.sh", "verificar-atualizacao.sh"):
            (self.tools / name).write_text("old\n")
        result = self.run_installer(installer, "--no-build", "--no-auto-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(legacy.exists())
        self.assertFalse((self.tools / "atualizar-duo.sh").exists())
        self.assertFalse((self.tools / "verificar-atualizacao.sh").exists())
        self.assertTrue((self.home / "Applications/Update Claude Duo.app").exists())

    # Installer
    def installer_fixture(self):
        checkout = self.root / "checkout"
        (checkout / "duo").mkdir(parents=True)
        (checkout / "scripts").mkdir()
        shutil.copyfile(REPO / "scripts/share-code-profile.py", checkout / "scripts/share-code-profile.py")
        for name in ("duo-common.sh", "update-duo.sh", "check-update.sh"):
            self.install_patched(REPO / "duo" / name, checkout / "duo" / name)
        code = self.patch((REPO / "duo/install-duo.sh").read_text())
        code = code.replace("LAUNCHCTL=/bin/launchctl", f"LAUNCHCTL={self.mock}/launchctl")
        code = code.replace('/usr/bin/python3 -I "$REPO/scripts/prepare-toolset.py" "$work/package"', f"{self.mock}/prepare")
        code = code.replace('/bin/bash -p "$REPO/bin/claude-toolset.sh" install', f"{self.mock}/toolset install")
        (checkout / "duo/install-duo.sh").write_text(code)
        self.write_mock(self.mock / "launchctl", '#!/bin/bash\nprintf "%s\\n" "$*" >> "$MOCK_DIR/launchctl.log"\n')
        self.write_mock(self.mock / "prepare", '#!/bin/bash\necho ' + "a" * 64 + '\n')
        self.write_mock(self.mock / "toolset", f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{self.mock}/toolset.log"\n')
        shutil.rmtree(self.tools)
        self.config.unlink()
        return checkout / "duo/install-duo.sh"

    def run_installer(self, installer, *args):
        return subprocess.run(["/bin/bash", "-p", str(installer), *args], env=self.env,
                              capture_output=True, text=True, timeout=120)

    def test_installer_sets_up_config_tools_app_and_agent(self):
        installer = self.installer_fixture()
        result = self.run_installer(installer, "--no-build")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = self.home / ".config/claude-instances/claude-duo.conf"
        self.assertEqual(config.read_text().splitlines()[:2], ["@mode original-copy", "@apps user"])
        self.assertIn("Duo | io.github.tester.claude-duo |", config.read_text())
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.tools / "config-path").read_text().strip(), str(config))
        for name in ("duo-common.sh", "update-duo.sh", "check-update.sh", "share-code-profile.py"):
            self.assertEqual((self.tools / name).stat().st_mode & 0o777, 0o700, name)
        self.assertIn("install", self.log("toolset.log"))
        applet = self.home / "Applications/Update Claude Duo.app"
        self.assertTrue((applet / "Contents/Info.plist").exists())
        agent = self.home / "Library/LaunchAgents/io.github.guibrbs.claude-duo.update-check.plist"
        data = plistlib.loads(agent.read_bytes())
        self.assertEqual(data["ProgramArguments"], ["/bin/bash", "-p", str(self.tools / "check-update.sh")])
        self.assertEqual(data["StartInterval"], 3600)
        self.assertIn("bootstrap", self.log("launchctl.log"))
        self.assertEqual(self.log("dispatcher.log").count("claude-apps-refresh.sh Duo"), 0)  # --no-build

    def test_installer_rerun_keeps_an_existing_config_and_can_skip_the_agent(self):
        installer = self.installer_fixture()
        self.assertEqual(self.run_installer(installer, "--no-build", "--no-auto-check").returncode, 0)
        config = self.home / ".config/claude-instances/claude-duo.conf"
        config.write_text(config.read_text().replace("| 212 |", "| 100 |"))
        again = self.run_installer(installer, "--no-build", "--no-auto-check")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("| 100 |", config.read_text())
        self.assertFalse((self.home / "Library/LaunchAgents").exists())
        self.assertEqual(self.log("launchctl.log"), "")

    def test_installer_reuses_an_earlier_manual_duo_config(self):
        installer = self.installer_fixture()
        manual = self.home / ".config/claude-instances/duo-validation.conf"
        manual.write_text("@mode original-copy\n@apps user\nDuo | com.example.duo | ~/x | 212 |\n")
        self.assertEqual(self.run_installer(installer, "--no-build", "--no-auto-check").returncode, 0)
        self.assertEqual((self.tools / "config-path").read_text().strip(), str(manual))
        self.assertFalse((self.home / ".config/claude-instances/claude-duo.conf").exists())

    def test_installer_inside_claude_hands_the_build_to_the_updater_app(self):
        # Run from Claude's Code tab: building would quit the caller's own app.
        installer = self.installer_fixture()
        self.env["MOCK_PARENT"] = f"1 {self.source_app}/Contents/MacOS/Claude"
        result = self.run_installer(installer, "--no-auto-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.log("dispatcher.log").count("claude-apps-refresh.sh Duo"), 0)
        self.assertEqual(self.log("open.log").splitlines(), [f"-a {self.home}/Applications/Update Claude Duo.app"])
        self.assertIn("runs inside Claude", result.stdout)
        self.assertIn('choose "Update now"', result.stdout)

    def test_installer_from_a_terminal_claude_cli_builds_now(self):
        # The CLI only puts Contents/Helpers/disclaimer in the chain.
        installer = self.installer_fixture()
        self.env["MOCK_PARENT"] = f"1 {self.source_app}/Contents/Helpers/disclaimer"
        self.env["MOCK_ANSWER"] = "Update now"
        result = self.run_installer(installer, "--no-auto-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.log("dispatcher.log").count("claude-apps-refresh.sh Duo"), 1)
        self.assertNotIn("Update Claude Duo.app", self.log("open.log"))

    # Uninstaller
    def uninstall_fixture(self):
        installer = self.installer_fixture()
        self.assertEqual(self.run_installer(installer, "--no-build").returncode, 0)
        code = self.patch((REPO / "duo/uninstall-duo.sh").read_text())
        uninstaller = installer.parent / "uninstall-duo.sh"
        uninstaller.write_text(code.replace("LAUNCHCTL=/bin/launchctl", f"LAUNCHCTL={self.mock}/launchctl"))
        (self.home / "Library/Logs/Claude Duo Updater").mkdir(parents=True)
        (self.home / "Library/Logs/Claude Duo Updater/update-1.log").write_text("OK\n")
        (self.home / "Applications/.claude-txn.ABCDEFGH").mkdir()
        self.account = [self.home / "Library/Application Support/Claude-Duo", self.home / ".claude-duo"]
        for path in self.account:
            path.mkdir(parents=True)
            (path / "invented-account-data").write_text("keep")
        return uninstaller

    def uninstall(self, uninstaller, *args):
        return subprocess.run(["/bin/bash", "-p", str(uninstaller), *args], env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=60)

    def trashed(self):
        folders = list((self.home / ".Trash").glob("Claude Duo uninstalled *"))
        self.assertEqual(len(folders), 1)
        return folders[0]

    def test_uninstaller_moves_the_duo_to_the_trash_and_keeps_account_data(self):
        uninstaller = self.uninstall_fixture()
        (self.home / "Applications/Atualizar Claude Duo.app/Contents").mkdir(parents=True)  # From an earlier release.
        result = self.uninstall(uninstaller, "--yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        moved = ("Applications/Claude Duo.app", "Applications/Update Claude Duo.app",
                 "Applications/Atualizar Claude Duo.app",
                 "Library/LaunchAgents/io.github.guibrbs.claude-duo.update-check.plist", ".local/share/claude-duo",
                 ".config/claude-instances/claude-duo.conf", "Library/Logs/Claude Duo Updater",
                 ".local/share/claude-instances", "Applications/.claude-txn.ABCDEFGH")
        for relative in moved:
            self.assertFalse((self.home / relative).exists(), relative)
            self.assertTrue((self.trashed() / relative).exists(), relative)
        self.assertFalse((self.home / ".config/claude-instances").exists())
        for path in self.account:
            self.assertEqual((path / "invented-account-data").read_text(), "keep")
        self.assertIn("bootout", self.log("launchctl.log"))

    def test_uninstaller_moves_account_data_only_when_asked(self):
        uninstaller = self.uninstall_fixture()
        result = self.uninstall(uninstaller, "--yes", "--include-account-data")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in self.account:
            self.assertFalse(path.exists())
            self.assertTrue((self.trashed() / path.relative_to(self.home) / "invented-account-data").exists())

    def test_uninstaller_keeps_the_shared_toolset_while_another_config_uses_it(self):
        uninstaller = self.uninstall_fixture()
        (self.home / ".config/claude-instances/other.conf").write_text("@mode original-copy\n")
        result = self.uninstall(uninstaller, "--yes")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".config/claude-instances/claude-duo.conf").exists())
        for kept in (".local/share/claude-instances", "Applications/.claude-txn.ABCDEFGH", ".config/claude-instances/other.conf"):
            self.assertTrue((self.home / kept).exists(), kept)

    def test_uninstaller_changes_nothing_while_the_duo_runs_or_without_confirmation(self):
        uninstaller = self.uninstall_fixture()
        self.running(self.duo_app)
        self.assertNotEqual(self.uninstall(uninstaller, "--yes").returncode, 0)
        (self.mock / "running").unlink()
        result = self.uninstall(uninstaller)  # no terminal to confirm and no --yes
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes", result.stderr)
        self.assertTrue(self.duo_app.exists())
        self.assertFalse((self.home / ".Trash").exists())

    def test_installer_refuses_without_prerequisites(self):
        installer = self.installer_fixture()
        (self.home / "Applications").chmod(0o755)
        result = self.run_installer(installer, "--no-build", "--no-auto-check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chmod 700 ~/Applications", result.stderr)
        (self.home / "Applications").chmod(0o700)
        shutil.rmtree(self.source_app)
        missing = self.run_installer(installer, "--no-build", "--no-auto-check")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("official Claude", missing.stderr)
        self.assertEqual(self.log("toolset.log"), "")


if __name__ == "__main__":
    unittest.main()
