import os

import sublime
import sublime_plugin

from Default import symbol as default_symbol

from .lib.utils import find_modules


_MANIFESTS = ("__manifest__.py", "__openerp__.py")
_ODOO_SYNTAXES = {"OdooView", "OdooOwl", "OdooXml"}
_SYMBOL_SELECTOR = (
    "entity.name.class.owl, variable.function.owl, "
    "entity.name.class.qweb, variable.function.qweb, "
    "entity.name.tag.localname.xml"
)


def _is_addon_dir(path):
    return any(os.path.isfile(os.path.join(path, manifest)) for manifest in _MANIFESTS)


def _find_addon_dir(file_path):
    path = os.path.dirname(os.path.abspath(file_path))
    while not _is_addon_dir(path):
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent
    return path


def _current_module_name(file_path):
    addon_dir = _find_addon_dir(file_path) if file_path else None
    return os.path.basename(addon_dir) if addon_dir else None


def _roots(window, file_path):
    addon_dir = _find_addon_dir(file_path) if file_path else None
    roots = ([os.path.dirname(addon_dir)] if addon_dir else []) + window.folders()
    seen = set()
    for root in roots:
        real_root = os.path.realpath(root)
        if real_root not in seen:
            seen.add(real_root)
            yield root


def _find_module_dir(window, file_path, module_name):
    addon_dir = _find_addon_dir(file_path) if file_path else None
    if addon_dir:
        sibling = os.path.join(os.path.dirname(addon_dir), module_name)
        if _is_addon_dir(sibling):
            return sibling

    for root in _roots(window, file_path):
        for path in find_modules(root).values():
            if os.path.basename(path) == module_name:
                return path
    return None


def _split_name(view, name):
    if "." in name:
        module, short_name = name.split(".", 1)
        return module, short_name, name

    module = _current_module_name(view.file_name())
    full_name = "%s.%s" % (module, name) if module else name
    return module, name, full_name


def _dedupe_locations(locations):
    result = []
    seen = set()
    for location in locations:
        key = (os.path.realpath(location.path), location.row, location.col)
        if key not in seen:
            seen.add(key)
            result.append(location)
    return result


def _finalize(locations):
    return _dedupe_locations(
        location for location in locations if location.syntax in _ODOO_SYNTAXES
    )


def _resolve_locations(window, view, name, lookup):
    module, short_name, full_name = _split_name(view, name)
    locations = list(lookup(window, full_name))

    if not locations and module:
        bare_locations = list(lookup(window, short_name))
        if bare_locations:
            module_dir = _find_module_dir(window, view.file_name(), module)
            if module_dir:
                prefix = os.path.normpath(module_dir) + os.sep
                locations = [
                    location for location in bare_locations
                    if os.path.normpath(location.path).startswith(prefix)
                ]

    return full_name, _finalize(locations)


def _point(pt):
    return pt.a if isinstance(pt, sublime.Region) else pt


def _on_tag_name(view, pt):
    pt = _point(pt)
    return pt is not None and pt >= 0 and view.match_selector(
        pt, "entity.name.tag.localname.xml"
    )


def _on_plain_tag_name(view, pt):
    if not _on_tag_name(view, pt):
        return False
    name = view.substr(view.word(_point(pt)))
    return not name[:1].isupper()


def _full_word(view, pt):
    pt = _point(pt)
    if pt is None or pt < 0:
        return None
    if not view.match_selector(pt, _SYMBOL_SELECTOR):
        pt -= 1
        if pt < 0 or not view.match_selector(pt, _SYMBOL_SELECTOR):
            return None
    return view.substr(view.expand_to_scope(pt, _SYMBOL_SELECTOR))


def _js_locations(window, name):
    return [
        location for location in default_symbol.lookup_symbol(window, name)
        if location.path.endswith((".js", ".ts"))
    ]


def _python_locations(window, name):
    return [
        location for location in default_symbol.lookup_symbol(window, name)
        if location.path.endswith(".py")
    ]


def _definition_fallback(window, view, pt):
    point = _point(pt)
    if point is not None and point >= 0:
        is_js = view.match_selector(point, "source.js")
        is_python = view.match_selector(point, "source.python")
        if is_js or is_python:
            name, _ = default_symbol.symbol_at_point(view, pt)
            locations = (
                _js_locations(window, name)
                if is_js else _python_locations(window, name)
            )
            return name, locations

    if _on_plain_tag_name(view, pt):
        return "", []

    name = _full_word(view, pt)
    if name:
        if _on_tag_name(view, pt):
            return name, _js_locations(window, name)
        full_name, locations = _resolve_locations(
            window, view, name, default_symbol.lookup_symbol
        )
        if locations:
            return full_name, locations

    name, locations = default_symbol.symbol_at_point(view, pt)
    return name, _finalize(locations)


def _reference_fallback(window, view, pt):
    if _on_plain_tag_name(view, pt):
        return "", []

    name = _full_word(view, pt)
    if name:
        full_name, locations = _resolve_locations(
            window, view, name, default_symbol.lookup_references
        )
        if locations:
            return full_name, locations

    name, locations = default_symbol.reference_at_point(view, pt)
    return name, _finalize(locations)


def _navigate(view, symbol, locations, title):
    default_symbol.navigate_to_symbol(
        view, symbol, locations, False, False, False,
        "%s of %s" % (title, symbol),
    )


class GotoDefinitionOdooXmlCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not view:
            return

        pt = view.sel()[0] if view.sel() else -1
        symbol, locations = _definition_fallback(self.window, view, pt)
        _navigate(view, symbol, locations, "Definitions")


class GotoReferenceOdooXmlCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not view:
            return

        pt = view.sel()[0] if view.sel() else -1
        symbol, locations = _reference_fallback(self.window, view, pt)
        _navigate(view, symbol, locations, "References")
