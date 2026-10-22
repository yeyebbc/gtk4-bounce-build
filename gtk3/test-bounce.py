#!/usr/bin/env python3
"""Exercise real smooth-scroll events, native child geometry, drawing and rebound."""
import argparse
import os
from pathlib import Path
import sys
import time
import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

args = argparse.ArgumentParser()
args.add_argument("--stock", action="store_true")
options = args.parse_args()
Gtk.init([])
css = Gtk.CssProvider()
css.load_from_data(b"scrolledwindow, viewport { background-color: #ffffff; border: none; padding: 0; }")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
context = GLib.MainContext.default()

def settle(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.001)

def point(widget, target, x=0, y=0):
    result = widget.translate_coordinates(target, x, y)
    assert result is not None
    return tuple(result[-2:])

def make_child(kind):
    if kind == "textview":
        child = Gtk.TextView()
        child.get_buffer().set_text("\n".join("Line %d: " % i + "long content " * 15 for i in range(150)))
        return child
    if kind == "treeview":
        store = Gtk.ListStore(str)
        for i in range(150):
            store.append(["Row %d: " % i + "long content " * 15])
        child = Gtk.TreeView(model=store)
        child.append_column(Gtk.TreeViewColumn("Heading", Gtk.CellRendererText(), text=0))
        return child
    child = Gtk.DrawingArea()
    child.set_size_request(1400, 1400)
    def draw(widget, cr):
        cr.set_source_rgb(1, 0, 0)
        cr.paint()
        return False
    child.connect("draw", draw)
    return child

def smooth(scroller, axis, delta):
    event = Gdk.Event.new(Gdk.EventType.SCROLL)
    event.window = scroller.get_window()
    event.send_event = True
    event.time = Gdk.CURRENT_TIME
    event.x = event.y = 100
    event.direction = Gdk.ScrollDirection.SMOOTH
    event.delta_x = delta if axis == "x" else 0.0
    event.delta_y = delta if axis == "y" else 0.0
    pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
    event.set_device(pointer)
    event.set_source_device(pointer)
    assert scroller.event(event), "smooth scroll was not handled"

def red_pixel(surface, x, y):
    surface.flush()
    offset = y * surface.get_stride() + x * 4
    data = bytes(surface.get_data()[offset:offset+4])
    b, g, r, a = data
    return r > 220 and g < 40 and b < 40 and a > 220

def drawing(scroller, window, before, after, axis, delta):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, window.get_allocated_width(), window.get_allocated_height())
    window.draw(cairo.Context(surface))
    # For a plain drawing area, the exposed top/left gap must not retain the
    # child's red pixels. This also covers gtk_widget_draw(), not only expose.
    if delta < 0 and not options.stock:
        x, y = before[0] + 4, before[1] + 4
        if red_pixel(surface, x, y):
            out = Path(os.environ.get("GTK3_TEST_OUTPUT", "/tmp"))
            out.mkdir(parents=True, exist_ok=True)
            surface.write_to_png(str(out / ("bad-gap-" + axis + ".png")))
            raise AssertionError("overscroll gap still contains child pixels")
        assert red_pixel(surface, after[0] + 8, after[1] + 8), "shifted content disappeared"
    return surface

count = 0
for kind in ("textview", "treeview", "viewport"):
    for overlay in (False, True):
        window = Gtk.Window()
        window.set_default_size(420, 340)
        window.set_border_width(13)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        scroller.set_overlay_scrolling(overlay)
        window.add(scroller)
        scroller.add(make_child(kind))
        window.show_all()
        settle(0.12)
        child = scroller.get_child()
        bars = (scroller.get_hscrollbar(), scroller.get_vscrollbar())
        for axis, delta in (("y", -6.0), ("y", 6.0), ("x", -6.0), ("x", 6.0)):
            hadj, vadj = scroller.get_hadjustment(), scroller.get_vadjustment()
            hadj.set_value(hadj.get_lower())
            vadj.set_value(vadj.get_lower())
            adjustment = hadj if axis == "x" else vadj
            edge = adjustment.get_lower() if delta < 0 else adjustment.get_upper() - adjustment.get_page_size()
            adjustment.set_value(edge)
            settle(0.08)
            assert adjustment.get_upper() > adjustment.get_page_size(), (kind, axis, "not scrollable")
            before = point(child, window)
            bar_before = tuple(point(bar, window) for bar in bars)
            smooth(scroller, axis, delta)
            after = point(child, window)
            displacement = after[0] - before[0] if axis == "x" else after[1] - before[1]
            if options.stock:
                assert displacement == 0, ("stock baseline moved", kind, axis, displacement)
            else:
                assert 3 < abs(displacement) < 240, (kind, overlay, axis, displacement)
                assert displacement * delta < 0, ("bounce direction", kind, axis, displacement)
            assert abs(adjustment.get_value() - edge) < 0.01, "bounce changed logical adjustment"
            assert tuple(point(bar, window) for bar in bars) == bar_before, "scrollbars moved with content"
            if kind == "viewport":
                drawing(scroller, window, before, after, axis, delta)
            settle(1.15)
            assert point(child, window) == before, ("content did not spring back", kind, axis, point(child, window), before)
            count += 1
            print("PASS:", kind, "overlay=" + str(overlay), axis, delta, "displacement", displacement, flush=True)
        # Cover destruction/recreation of the added native windows.
        window.hide()
        window.unrealize()
        window.show_all()
        settle(0.08)
        assert point(child, window) == before
        window.destroy()
        settle(0.02)

# Empty container and adding/removing a child after realization.
window = Gtk.Window()
scroller = Gtk.ScrolledWindow()
window.add(scroller)
window.show_all()
settle(0.05)
child = Gtk.TextView()
scroller.add(child)
child.show()
settle(0.05)
scroller.remove(child)
settle(0.02)
replacement = Gtk.TextView()
scroller.add(replacement)
replacement.show()
settle(0.05)
window.hide()
window.unrealize()
window.show_all()
settle(0.05)
window.destroy()
settle(0.02)
print("PASS:", count, "scroll cases plus empty/add/remove/unrealize lifecycle;", "stock baseline" if options.stock else "patched GTK 3 bounce")
