from trendsubs.core.font_utils import resolve_ass_font_name


def test_resolve_ass_font_name_falls_back_to_file_stem_for_unknown_font():
    font_name = resolve_ass_font_name("C:\\Fonts\\Caveat-VariableFont_wght.ttf")
    assert font_name == "Caveat-VariableFont_wght"
