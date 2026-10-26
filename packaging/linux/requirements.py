"""Writes python3-requirements.json, the flatpak-builder module with the app's Python dependencies.

Takes the exact versions and wheel hashes from uv.lock, so the Flatpak runs what the tests ran.
PySide6 is not included; it comes with io.qt.PySide.BaseApp.

    .venv/bin/python packaging/linux/requirements.py
"""
import json
import pathlib
import sys
import tomllib

from packaging.markers import Marker
from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = pathlib.Path(__file__).parents[2]
OUTPUT = pathlib.Path(__file__).with_name("python3-requirements.json")
PROJECT = "call-switcher"
FROM_BASE_APP = {"pyside6-essentials", "shiboken6"}

# Python and glibc of org.kde.Platform 6.11 (freedesktop 25.08).
PYTHON = (3, 13)
GLIBC = (2, 41)
ARCHES = ("x86_64", "aarch64")


def _tags(arch):
    platforms = [f"manylinux_{GLIBC[0]}_{minor}_{arch}" for minor in range(GLIBC[1], 16, -1)]
    platforms += [f"manylinux2014_{arch}", f"manylinux2010_{arch}", f"manylinux1_{arch}", f"linux_{arch}"]
    py = f"cp{PYTHON[0]}{PYTHON[1]}"
    return [*cpython_tags(PYTHON, abis=[py, "abi3", "none"], platforms=platforms),
            *compatible_tags(PYTHON, py, platforms=platforms)]


def _environment(arch):
    return {"sys_platform": "linux", "platform_system": "Linux", "platform_machine": arch,
            "implementation_name": "cpython", "platform_python_implementation": "CPython",
            "python_version": f"{PYTHON[0]}.{PYTHON[1]}", "python_full_version": f"{PYTHON[0]}.{PYTHON[1]}.0",
            "os_name": "posix", "extra": ""}


def _dependencies(packages, arch):
    """Names of all packages the project needs at runtime on Linux/arch."""
    env = _environment(arch)
    needed, todo = set(), [PROJECT]
    while todo:
        for dep in packages[todo.pop()].get("dependencies", []):
            name = canonicalize_name(dep["name"])
            if name in needed or ("marker" in dep and not Marker(dep["marker"]).evaluate(env)):
                continue
            needed.add(name)
            todo.append(name)
    return needed - FROM_BASE_APP


def _wheel(package, arch):
    wheels = {}
    for wheel in package.get("wheels", []):
        filename = wheel["url"].rsplit("/", 1)[1]
        for tag in parse_wheel_filename(filename)[3]:
            wheels.setdefault(tag, wheel)
    for tag in _tags(arch):  # most specific first
        if tag in wheels:
            return wheels[tag]
    sys.exit(f"No wheel of {package['name']} {package['version']} for {arch}")


def main():
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    packages = {canonicalize_name(p["name"]): p for p in lock["package"]}

    sources = {}  # url -> source, so wheels for all architectures are listed once
    for arch in ARCHES:
        for name in sorted(_dependencies(packages, arch)):
            wheel = _wheel(packages[name], arch)
            source = sources.setdefault(wheel["url"], {
                "type": "file",
                "url": wheel["url"],
                "sha256": wheel["hash"].removeprefix("sha256:"),
                "only-arches": [],
            })
            source["only-arches"].append(arch)
    for source in sources.values():
        if len(source["only-arches"]) == len(ARCHES):
            del source["only-arches"]

    module = {
        "name": "python3-requirements",
        "buildsystem": "simple",
        "build-commands": [
            "pip3 install --no-index --no-deps --no-build-isolation --prefix=${FLATPAK_DEST} *.whl",
        ],
        "sources": list(sources.values()),
    }
    OUTPUT.write_text(json.dumps(module, indent=2) + "\n")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(sources)} wheels")


if __name__ == "__main__":
    main()
