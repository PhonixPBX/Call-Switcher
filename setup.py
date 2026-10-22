# Adapter for py2app, which only runs as a setuptools command. All settings are in
# pyproject.toml ([project] and [tool.py2app]); build with ./build.sh.
import tomllib

from packaging.version import Version
from py2app.build_app import py2app as _py2app
from setuptools import setup

with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

version = pyproject["project"]["version"]
options = dict(pyproject["tool"]["py2app"])
app = options.pop("app")
# macOS expects plain numbers here, so a release candidate like 0.1.0rc1 is shown as 0.1.0.
bundle_version = Version(version).base_version
options["plist"] = {**options["plist"], "CFBundleShortVersionString": bundle_version, "CFBundleVersion": bundle_version}


class py2app(_py2app):
    def finalize_options(self):
        # setuptools copies [project].dependencies into install_requires, which py2app rejects.
        # uv installs them, and py2app's import scan bundles them anyway.
        self.distribution.install_requires = []
        super().finalize_options()


setup(
    cmdclass={"py2app": py2app},
    name=options["plist"]["CFBundleName"],
    version=version,
    app=app,
    options={"py2app": options},
)
