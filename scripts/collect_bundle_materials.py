"""Collect notices and the installed pystray source into a Windows bundle.

Run with the same Python environment used for the PyInstaller build. No package
is imported, and no network requests or personal settings are accessed.
"""

from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "dist" / "MimamoriBreach"
DOCUMENTS = (
    "README.md",
    "README.en.md",
    "PRIVACY.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
)
PACKAGES = ("mimamori-breach", "pystray", "Pillow", "six", "PyInstaller")


def main() -> None:
    if not (BUNDLE / "MimamoriBreach.exe").is_file():
        raise SystemExit("Build dist/MimamoriBreach/MimamoriBreach.exe first.")

    distribution = metadata.distribution("pystray")
    source_root = Path(distribution.locate_file("pystray")).resolve()
    if not (source_root / "__init__.py").is_file():
        raise SystemExit("The installed pystray source package could not be found.")

    source_files = sorted(
        path
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.relative_to(source_root).parts
        and path.is_file()
    )
    for source in source_files:
        if not source.resolve().is_relative_to(source_root):
            raise SystemExit("A pystray source file points outside its package.")

    versions = {name: metadata.version(name) for name in PACKAGES}
    for name in DOCUMENTS:
        shutil.copy2(ROOT / name, BUNDLE / name)
    shutil.copytree(ROOT / "licenses", BUNDLE / "licenses", dirs_exist_ok=True)
    (BUNDLE / "Demo.cmd").write_bytes(
        b'@echo off\r\nstart "" "%~dp0MimamoriBreach.exe" --demo\r\n'
    )

    sources = BUNDLE / "third_party_sources"
    package_target = sources / "pystray"
    package_target.mkdir(parents=True, exist_ok=True)
    relative_files = {source.relative_to(source_root) for source in source_files}
    # A repeated collection must not retain source files from an older version.
    for previous in package_target.rglob("*.py"):
        if previous.relative_to(package_target) not in relative_files:
            if not previous.resolve().is_relative_to(package_target.resolve()):
                raise SystemExit("An existing source file points outside its package.")
            previous.unlink()

    hashes = {}
    for source in source_files:
        relative = source.relative_to(source_root)
        target = package_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()

    package_metadata = distribution.read_text("METADATA")
    if not package_metadata:
        raise SystemExit("The installed pystray metadata could not be found.")
    (sources / "pystray-METADATA.txt").write_text(package_metadata, encoding="utf-8")
    manifest = {
        "python": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "packages": versions,
        "pystray_source_directory": "third_party_sources/pystray",
        "pystray_source_sha256": hashes,
    }
    (BUNDLE / "recorded-versions.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Collected documentation, licenses, and {len(source_files)} pystray source files.")


if __name__ == "__main__":
    main()
