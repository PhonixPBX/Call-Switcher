"""Draws the Call Switcher app icon and writes assets/AppIcon.icns (+ icon.png).

Follows the macOS icon grid (824 pt rounded body on a 1024 pt canvas), so macOS 26+
shows it as a native shape instead of putting it in a grey container.

    .venv/bin/python assets/make_icon.py
"""
import math
import os
import shutil
import subprocess
import tempfile

from AppKit import (
    NSAffineTransform,
    NSBezierPath,
    NSBitmapImageRep,
    NSColor,
    NSCompositingOperationSourceOver,
    NSDeviceRGBColorSpace,
    NSGradient,
    NSGraphicsContext,
    NSImage,
    NSLineCapStyleRound,
    NSPNGFileType,
    NSShadow,
)
from Foundation import NSMakeRect, NSMakeSize, NSPoint

HERE = os.path.dirname(os.path.abspath(__file__))
CANVAS = 1024
BODY = 824
RADIUS = 185.4


def rgb(r, g, b, a=1.0):
    return NSColor.colorWithDeviceRed_green_blue_alpha_(r / 255, g / 255, b / 255, a)


def handset(center: NSPoint, size: float, angle: float) -> tuple[NSBezierPath, list[NSBezierPath]]:
    """Classic handset: a thick arched handle with an ear cup and a mouth cup at its ends."""
    s = size
    arc_center = NSPoint(0, -0.18 * s)
    radius = 0.40 * s
    start, end = 28, 152

    handle = NSBezierPath.bezierPath()
    handle.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(arc_center, radius, start, end, False)
    handle.setLineWidth_(0.15 * s)
    handle.setLineCapStyle_(NSLineCapStyleRound)

    cups = []
    for deg in (start, end):
        # Cup: a rounded block at the end of the handle, along the radius, pointing inwards.
        r = math.radians(deg)
        cup = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(-0.30 * s, -0.15 * s, 0.42 * s, 0.30 * s), 0.13 * s, 0.13 * s)
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(arc_center.x + radius * math.cos(r),
                            arc_center.y + radius * math.sin(r))
        t.rotateByDegrees_(deg)
        cup.transformUsingAffineTransform_(t)
        cups.append(cup)

    t = NSAffineTransform.transform()
    t.translateXBy_yBy_(center.x, center.y)
    t.rotateByDegrees_(angle)
    t.translateXBy_yBy_(0, 0.06 * s)
    for part in [handle, *cups]:
        part.transformUsingAffineTransform_(t)
    return handle, cups


def arrow_arc(center: NSPoint, radius: float, start: float, end: float, width: float):
    """Circular arc (degrees, counter-clockwise) with an arrow head continuing at `end`."""
    arc = NSBezierPath.bezierPath()
    arc.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(center, radius, start, end, False)
    arc.setLineWidth_(width)
    arc.setLineCapStyle_(NSLineCapStyleRound)

    a = math.radians(end)
    radial = (math.cos(a), math.sin(a))
    tangent = (-math.sin(a), math.cos(a))  # direction of travel for a counter-clockwise arc
    base = (center.x + radius * radial[0], center.y + radius * radial[1])
    length, half = width * 1.7, width * 1.25
    tip = NSPoint(base[0] + length * tangent[0], base[1] + length * tangent[1])
    outer = NSPoint(base[0] + half * radial[0], base[1] + half * radial[1])
    inner = NSPoint(base[0] - half * radial[0], base[1] - half * radial[1])

    head = NSBezierPath.bezierPath()
    head.moveToPoint_(tip)
    head.lineToPoint_(outer)
    head.lineToPoint_(inner)
    head.closePath()
    head.setLineJoinStyle_(1)  # round corners
    head.setLineWidth_(width * 0.3)
    return arc, head


def draw(size: int) -> NSBitmapImageRep:
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0)
    rep.setSize_(NSMakeSize(CANVAS, CANVAS))  # draw in 1024 pt units at any pixel size

    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    ctx.setCompositingOperation_(NSCompositingOperationSourceOver)

    inset = (CANVAS - BODY) / 2
    body_rect = NSMakeRect(inset, inset, BODY, BODY)
    body = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(body_rect, RADIUS, RADIUS)

    # Drop shadow as in Apple's icon template.
    NSGraphicsContext.saveGraphicsState()
    shadow = NSShadow.alloc().init()
    shadow.setShadowOffset_((0, -10))
    shadow.setShadowBlurRadius_(28)
    shadow.setShadowColor_(rgb(0, 0, 0, 0.30))
    shadow.set()
    rgb(20, 30, 80).setFill()
    body.fill()
    NSGraphicsContext.restoreGraphicsState()

    # Background: deep indigo to electric teal, plus a soft highlight at the top.
    NSGradient.alloc().initWithColors_([rgb(38, 28, 120), rgb(52, 84, 230), rgb(20, 200, 210)]).drawInBezierPath_angle_(body, 60)
    NSGradient.alloc().initWithColors_([rgb(255, 255, 255, 0.22), rgb(255, 255, 255, 0.0)]).drawInBezierPath_angle_(body, -90)

    center = NSPoint(CANVAS / 2, CANVAS / 2)

    # Two "switch" arrows circling the handset (opaque, so overlaps do not show).
    rgb(225, 245, 255).set()
    for start, end in ((20, 132), (200, 312)):
        arc, head = arrow_arc(center, 300, start, end, 44)
        arc.stroke()
        head.fill()
        head.stroke()

    # Handset, drawn into its own image first so its shadow is cast by the shape as a whole.
    handle, cups = handset(center, 400, -18)
    glyph = NSImage.alloc().initWithSize_(NSMakeSize(CANVAS, CANVAS))
    glyph.lockFocus()
    rgb(255, 255, 255).set()
    handle.stroke()
    for cup in cups:
        cup.fill()
    glyph.unlockFocus()

    NSGraphicsContext.saveGraphicsState()
    shadow = NSShadow.alloc().init()
    shadow.setShadowOffset_((0, -8))
    shadow.setShadowBlurRadius_(18)
    shadow.setShadowColor_(rgb(10, 10, 60, 0.45))
    shadow.set()
    glyph.drawInRect_(NSMakeRect(0, 0, CANVAS, CANVAS))
    NSGraphicsContext.restoreGraphicsState()

    NSGraphicsContext.restoreGraphicsState()
    return rep


def write_png(rep: NSBitmapImageRep, path: str):
    rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(path, True)


def main():
    write_png(draw(1024), os.path.join(HERE, "icon.png"))

    iconset = tempfile.mkdtemp(suffix=".iconset")
    try:
        for points in (16, 32, 128, 256, 512):
            write_png(draw(points), os.path.join(iconset, f"icon_{points}x{points}.png"))
            write_png(draw(points * 2), os.path.join(iconset, f"icon_{points}x{points}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(HERE, "AppIcon.icns")], check=True)
    finally:
        shutil.rmtree(iconset)
    print("assets/icon.png, assets/AppIcon.icns")


if __name__ == "__main__":
    main()
