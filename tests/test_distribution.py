# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the artifact, installation lifecycle and independence from Git."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="horodater-dist-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.env = dict(os.environ, SOURCE_DATE_EPOCH="0", LC_ALL="C", TZ="UTC0")

    def command(self, args, cwd=None, env=None):
        result = subprocess.run(
            list(map(str, args)), cwd=cwd or self.work, env=env or self.env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def build(self, output="dist", root=ROOT):
        directory = self.work / output
        self.command([sys.executable, "-B", root / "tools/dist.py", "--output-dir", directory])
        return next(directory.glob("horodater-*.tar.gz"))

    def unpack(self, archive):
        destination = self.work / "unpacked"
        destination.mkdir()
        self.command(["tar", "-xzf", archive, "-C", destination])
        return next(destination.iterdir())

    def test_archive_is_reproducible_despite_input_metadata_and_location(self):
        first = self.build("one")
        # Rebuild from the release itself: no checkout or unrelated local files.
        copied = self.unpack(first)
        for path in copied.rglob("*"):
            if path.is_file():
                os.utime(path, (1234567890, 1234567890))
                path.chmod(0o600)
        second = self.build("two", root=copied)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_checksum_and_normalized_metadata(self):
        archive = self.build()
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(
            (archive.parent / "SHA256SUMS").read_text(), f"{digest}  {archive.name}\n"
        )
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            names = [member.name for member in members]
            self.assertEqual(names, sorted(names))
            self.assertTrue(any(name.endswith("/LICENSE") for name in names))
            self.assertFalse(any("/.git/" in name or "/.aws/" in name for name in names))
            for member in members:
                self.assertTrue(member.isfile())
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
                expected = 0o755 if member.name.endswith("/horodater.sh") else 0o644
                self.assertEqual(member.mode, expected)

    def test_source_date_epoch_is_honored(self):
        self.env["SOURCE_DATE_EPOCH"] = "1234567890"
        archive = self.build()
        with tarfile.open(archive) as tar:
            self.assertTrue(all(member.mtime == 1234567890 for member in tar))

    def test_invalid_epoch_fails_without_creating_a_release(self):
        for value in ["invalid", "-1", "4294967296"]:
            with self.subTest(value=value):
                env = dict(self.env, SOURCE_DATE_EPOCH=value)
                result = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "tools/dist.py"), "--output-dir", str(self.work / "dist")],
                    cwd=self.work, env=env, capture_output=True, text=True, timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.work / "dist").exists())

    def test_install_and_uninstall_from_archive_preserve_unrelated_files(self):
        extracted = self.unpack(self.build())
        prefix = self.work / "prefix with spaces"
        self.command(["make", "install", f"PREFIX={prefix}"], cwd=extracted)
        installed = prefix / "bin/horodater"
        self.assertTrue(installed.is_file())
        self.assertFalse(installed.is_symlink())
        self.assertEqual(installed.stat().st_mode & 0o777, 0o755)
        other = prefix / "bin/other-program"
        other.write_text("unrelated")
        source_version = self.command(["sh", ROOT / "horodater.sh", "--version"]).stdout
        self.assertEqual(self.command([installed, "--version"]).stdout, source_version)
        self.command(["make", "uninstall", f"PREFIX={prefix}"], cwd=extracted)
        self.command(["make", "uninstall", f"PREFIX={prefix}"], cwd=extracted)
        self.assertFalse(installed.exists())
        self.assertEqual(other.read_text(), "unrelated")

    def test_installed_command_works_after_deleting_extracted_source_without_git(self):
        extracted = self.unpack(self.build())
        prefix = self.work / "installed"
        self.command(["make", "install", f"PREFIX={prefix}"], cwd=extracted)
        shutil.rmtree(extracted)
        installed = prefix / "bin/horodater"
        isolated_bin = self.work / "runtime-bin"
        isolated_bin.mkdir()
        # The executable needs only the shell, date and mv at runtime.
        for name in ["date", "mv"]:
            (isolated_bin / name).symlink_to(shutil.which(name))
        env = dict(self.env, PATH=str(isolated_bin))
        self.assertIn("horodater", self.command([installed, "--version"], env=env).stdout)
        source = self.work / "standalone.txt"
        source.write_bytes(b"contents")
        self.command([installed, source], env=env)
        self.assertFalse(source.exists())
        destinations = list(self.work.glob("????????_standalone.txt"))
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0].read_bytes(), b"contents")

    def test_destdir_stages_installation_without_embedding_build_paths(self):
        extracted = self.unpack(self.build())
        stage = self.work / "stage"
        self.command(["make", "install", "PREFIX=/usr", f"DESTDIR={stage}"], cwd=extracted)
        installed = stage / "usr/bin/horodater"
        self.assertEqual(installed.read_bytes(), (ROOT / "horodater.sh").read_bytes())
        self.command(["make", "uninstall", "PREFIX=/usr", f"DESTDIR={stage}"], cwd=extracted)
        self.assertFalse(installed.exists())


if __name__ == "__main__":
    unittest.main()
