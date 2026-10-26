"""Writes packaging/windows/CallSwitcher.ico from assets/icon.png (PNG images, 16 to 256 px).

    uv run packaging/windows/make_ico.py
"""
import os
import pathlib
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage  # noqa: E402

ROOT = pathlib.Path(__file__).parents[2]
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _png(image: QImage, size: int) -> bytes:
    scaled = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    scaled.save(buffer, "PNG")
    return bytes(data)


def main():
    app = QGuiApplication([])  # noqa: F841 (QImage scaling needs it)
    # Without the margin of the macOS icon grid (824 pt body on 1024 pt), which looks too small on Windows.
    image = QImage(str(ROOT / "assets" / "icon.png")).copy(100, 100, 824, 824)
    images = [_png(image, size) for size in SIZES]

    # ICONDIR, one ICONDIRENTRY per image (0 means 256), then the PNG data.
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, data = b"", b""
    for size, png in zip(SIZES, images):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    output = pathlib.Path(__file__).with_name("CallSwitcher.ico")
    output.write_bytes(header + entries + data)
    print(f"{output.relative_to(ROOT)}: {len(SIZES)} sizes")


if __name__ == "__main__":
    main()
