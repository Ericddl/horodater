# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the public command against disposable files, not the working tree."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "horodater.sh"
DATE = "20260203"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="horodater-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work = self.root / "files"
        self.work.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, LC_ALL="C", TZ="UTC0")
        self.env.update(
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            HORODATER_TEST_DATE=DATE,
            HORODATER_TEST_DATE_STATUS="0",
        )
        self.stub(
            "date",
            'printf "%s\\n" "$HORODATER_TEST_DATE"\n'
            'exit "$HORODATER_TEST_DATE_STATUS"\n',
        )
        self.shell = shlex.split(os.environ.get("HORODATER_TEST_SHELL", "/bin/sh"))

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def file(self, name="note.txt", content=b"original\x00contents\n"):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def run_cli(self, *args, capture=True):
        return subprocess.run(
            self.shell + [str(SCRIPT), *map(str, args)],
            cwd=self.work,
            env=self.env,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
            text=True,
            timeout=10,
        )

    def test_renames_in_place_and_preserves_contents_and_mode(self):
        source = self.file("sub/note.txt")
        source.chmod(0o640)
        os.utime(source, ns=(1234567890000000000, 1234567890000000000))
        original_mtime = source.stat().st_mtime_ns
        content = source.read_bytes()
        result = self.run_cli("sub/note.txt")
        destination = source.with_name(DATE + "_" + source.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(source.exists())
        self.assertEqual(destination.read_bytes(), content)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o640)
        self.assertEqual(destination.stat().st_mtime_ns, original_mtime)

    def test_handles_unusual_names_without_losing_bytes(self):
        names = ["un fichier.txt", "été.txt", "*[x]?.txt", "-n", "fin\n", "a\nb.txt"]
        for name in names:
            with self.subTest(name=repr(name)):
                source = self.file(name)
                content = source.read_bytes()
                result = self.run_cli("--", name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(source.with_name(DATE + "_" + name).read_bytes(), content)
                self.assertFalse(source.exists())

    def test_handles_parent_directory_ending_in_newline(self):
        source = self.file("folder\n/note.txt")
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(source.with_name(DATE + "_note.txt").is_file())

    def test_destination_file_is_not_overwritten(self):
        source = self.file()
        destination = self.file(DATE + "_note.txt", b"keep me")
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(source.exists())
        self.assertEqual(destination.read_bytes(), b"keep me")
        self.assertIn("destination already exists", result.stderr)

    def test_destination_directory_does_not_receive_source(self):
        source = self.file()
        destination = self.work / (DATE + "_note.txt")
        destination.mkdir()
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(source.exists())
        self.assertEqual(list(destination.iterdir()), [])

    def test_existing_destination_links_are_refused_including_dangling_links(self):
        source = self.file()
        for target in [source, self.work / "missing-target"]:
            with self.subTest(target=target.name):
                destination = self.work / (DATE + "_note.txt")
                destination.symlink_to(target)
                result = self.run_cli(source)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(source.exists())
                self.assertTrue(destination.is_symlink())
                self.assertEqual(destination.readlink(), target)
                destination.unlink()

    def test_non_files_and_source_links_are_refused(self):
        source = self.file()
        link = self.work / "link"
        link.symlink_to(source)
        dangling = self.work / "dangling"
        dangling.symlink_to(self.work / "missing")
        folder = self.work / "folder"
        folder.mkdir()
        for operand in ["missing", "", folder, link, dangling]:
            with self.subTest(operand=str(operand)):
                result = self.run_cli(operand)
                self.assertEqual(result.returncode, 1)
        self.assertTrue(source.exists())
        self.assertTrue(link.is_symlink())
        self.assertTrue(dangling.is_symlink())

    def test_already_prefixed_filename_is_unchanged(self):
        source = self.file("20010101_note.txt")
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.work.iterdir()), [source])

    def test_repeated_invocation_does_not_add_another_prefix(self):
        source = self.file()
        destination = source.with_name(DATE + "_note.txt")
        self.assertEqual(self.run_cli(source).returncode, 0)
        self.assertEqual(self.run_cli(destination).returncode, 0)
        self.assertEqual(list(self.work.iterdir()), [destination])

    def test_duplicate_operand_reports_failure_after_first_rename(self):
        source = self.file()
        result = self.run_cli(source, source)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(source.exists())
        self.assertTrue(source.with_name(DATE + "_note.txt").exists())

    def test_partial_failure_does_not_hide_successes(self):
        source = self.file()
        result = self.run_cli("missing", source)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(source.exists())
        self.assertTrue(source.with_name(DATE + "_note.txt").exists())

    def test_dry_run_checks_inputs_without_modifying_files(self):
        source = self.file()
        result = self.run_cli("--dry-run", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(DATE + "_note.txt", result.stdout)
        self.assertEqual(list(self.work.iterdir()), [source])
        self.file(DATE + "_note.txt")
        self.assertEqual(self.run_cli("-n", source).returncode, 1)

    def test_help_and_version_do_not_need_date(self):
        self.env["HORODATER_TEST_DATE_STATUS"] = "1"
        for option in ["--help", "-h", "--version", "-V"]:
            with self.subTest(option=option):
                result = self.run_cli(option)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("horodater", result.stdout)
                self.assertEqual(result.stderr, "")

    def test_invalid_usage_returns_two(self):
        for args in [[], ["--"], ["-n"], ["--unknown"]]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_date_failure_or_invalid_output_stops_before_any_rename(self):
        source = self.file()
        for value, status in [(DATE, "1"), ("", "0"), ("not-a-date", "0")]:
            with self.subTest(value=value, status=status):
                self.env.update(HORODATER_TEST_DATE=value, HORODATER_TEST_DATE_STATUS=status)
                result = self.run_cli(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(list(self.work.iterdir()), [source])

    def test_date_is_computed_once_with_numeric_locale(self):
        log = self.root / "date-calls"
        self.env["HORODATER_TEST_LOG"] = str(log)
        self.stub(
            "date",
            'printf "%s:%s\\n" "$LC_ALL" "$1" >> "$HORODATER_TEST_LOG"\n'
            'printf "%s\\n" "$HORODATER_TEST_DATE"\n',
        )
        first, second = self.file("one"), self.file("two")
        result = self.run_cli(first, second)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log.read_text(), "C:+%Y%m%d\n")

    def test_move_failure_is_reported(self):
        source = self.file()
        self.stub("mv", "exit 7\n")
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(source.exists())

    def test_silent_move_skip_is_not_reported_as_success(self):
        source = self.file()
        self.stub("mv", "exit 0\n")
        self.assertEqual(self.run_cli(source).returncode, 1)
        self.assertTrue(source.exists())

    def test_file_created_between_check_and_move_is_not_overwritten(self):
        source = self.file()
        real_mv = shlex.quote(shutil.which("mv"))
        self.stub("mv", 'printf "concurrent" > "$3"\n' + f'exec {real_mv} "$@"\n')
        result = self.run_cli(source)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(source.exists())
        self.assertEqual(source.with_name(DATE + "_note.txt").read_bytes(), b"concurrent")

    def test_command_waits_for_move_completion(self):
        source = self.file()
        real_mv = shlex.quote(shutil.which("mv"))
        self.stub("mv", f'sleep 0.2\nexec {real_mv} "$@"\n')
        # No captured pipes: a background child cannot keep run() waiting on EOF.
        result = self.run_cli(source, capture=False)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(source.exists())
        self.assertTrue(source.with_name(DATE + "_note.txt").exists())

    @unittest.skipIf(os.geteuid() == 0, "root bypasses ordinary directory permissions")
    def test_unwritable_parent_reports_failure_and_preserves_source(self):
        source = self.file("locked/note.txt")
        source.parent.chmod(0o555)
        try:
            result = self.run_cli(source)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(source.exists())
        finally:
            source.parent.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
