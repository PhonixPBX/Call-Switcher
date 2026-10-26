import pytest

pytest.importorskip("AppKit")

from AppKit import NSApplication  # noqa: E402

from call_switcher import i18n, settings  # noqa: E402
from call_switcher.settings_window import SettingsWindowController  # noqa: E402

MARGIN = 20


@pytest.fixture(scope="module")
def controller():
    NSApplication.sharedApplication()
    return SettingsWindowController.alloc().init()


@pytest.mark.parametrize("mode", settings.MODES)
def test_margins_for_every_method(controller, mode):
    controller.mode_picker.setSelectedSegment_(settings.MODES.index(mode))
    controller._update_visible_rows()
    container = controller.container
    container.layoutSubtreeIfNeeded()

    stack = container.subviews()[0].frame()
    size = container.frame().size
    assert (stack.origin.x, stack.origin.y) == (MARGIN, MARGIN)
    assert size.width - stack.origin.x - stack.size.width == MARGIN
    assert size.height - stack.origin.y - stack.size.height == MARGIN


def test_only_selected_method_is_visible(controller):
    controller.mode_picker.setSelectedSegment_(settings.MODES.index(settings.MODE_PHONIX))
    controller._update_visible_rows()
    for mode, rows in controller.mode_rows.items():
        hidden = {controller.grid.rowAtIndex_(i).isHidden() for i in rows}
        assert hidden == {mode != settings.MODE_PHONIX}


def test_enabled_checkboxes_go_into_form_values(controller):
    for mode, checkbox in controller.enabled.items():
        checkbox.setState_(1 if mode == settings.MODE_ARI else 0)
    values = controller._form_values()
    assert settings.enabled_modes(values) == [settings.MODE_ARI]


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_layout_fits_in_every_language(language):
    i18n.set_language(language)
    try:
        c = SettingsWindowController.alloc().init()
        layouts = set()
        for mode in settings.MODES:
            c.mode_picker.setSelectedSegment_(settings.MODES.index(mode))
            c._update_visible_rows()
            c.container.layoutSubtreeIfNeeded()
            stack = c.container.subviews()[0].frame()
            size = c.container.frame().size
            assert (stack.origin.x, stack.origin.y) == (MARGIN, MARGIN)
            assert size.width - stack.origin.x - stack.size.width == MARGIN
            assert size.width < 800, f"{language}/{mode}: window too wide ({size.width})"
            field_x = c.grid.cellForView_(c.mode_picker).contentView().frame().origin.x
            layouts.add((c.window.frame().size.width, c.window.frame().size.height, field_x))
        # Switching methods must not resize the window or move the fields.
        assert len(layouts) == 1, layouts
    finally:
        i18n.set_language("en")
