#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a deterministic source release using only the Python standard library."""

import argparse
import gzip
import hashlib
import io
import os
from pathlib import Path
import re
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parent.parent
FILES = (
    ".github/workflows/ci.yml",
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "horodater.sh",
    "tests/test_cli.py",
    "tests/test_distribution.py",
    "tools/dist.py",
)


def build(output, epoch):
    source = (ROOT / "horodater.sh").read_text(encoding="utf-8")
    match = re.search(r"^HORODATER_VERSION='([0-9]+\.[0-9]+\.[0-9]+)'$", source, re.M)
    if not match:
        raise ValueError("horodater.sh must define a numeric MAJOR.MINOR.PATCH version")
    version = match.group(1)
    # Read all inputs before creating output, and never follow a release symlink.
    contents = {}
    for name in sorted(FILES):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"release input is not a regular file: {name}")
        contents[name] = path.read_bytes()

    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"horodater-{version}.tar.gz"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, delete=False) as raw:
            temporary = Path(raw.name)
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as zipped:
                with tarfile.open(fileobj=zipped, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                    for name, data in contents.items():
                        info = tarfile.TarInfo(f"horodater-{version}/{name}")
                        info.size = len(data)
                        info.mode = 0o755 if name == "horodater.sh" else 0o644
                        info.mtime = epoch
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        tar.addfile(info, io.BytesIO(data))
        temporary.chmod(0o644)
        temporary.replace(archive)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
        if not 0 <= epoch <= 0xFFFFFFFF:
            raise ValueError("SOURCE_DATE_EPOCH must be between 0 and 4294967295")
        archive = build(args.output_dir, epoch)
    except (OSError, ValueError) as error:
        parser.exit(1, f"dist: {error}\n")
    print(archive)


if __name__ == "__main__":
    main()
