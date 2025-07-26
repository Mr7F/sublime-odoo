import ast
import os
import json
import sublime_plugin
import functools
import sublime
import re


from .utils import find_modules


def list_directories(root_dir):
    return [dirpath for dirpath, *_ in os.walk(root_dir)]


class OdooNewFieldWidgetCommand(sublime_plugin.TextCommand):
    """Command to create a new JS field."""

    def run(self, edit, module, directory, widget_name):
        # Heuristic to split the name (camel case, snake case, using dot, etc)
        next_name = ""
        prev = ""
        for x in widget_name:
            if prev.isupper() != x.isupper():
                next_name += "_"
            next_name += x
            prev = x
        part_name = re.split(r"[^a-zA-Z0-9]", next_name)
        part_name = [x for x in part_name if x]
        snake_name = "_".join(part_name).lower()
        del widget_name
        camel_name = "".join(p.capitalize() for p in part_name)
        small_camel_name = camel_name[:1].lower() + camel_name[1:]
        module_name = module.split("/")[-1]

        os.makedirs(f"{directory}/{snake_name}", exist_ok=True)
        with open(f"{directory}/{snake_name}/{snake_name}.js", "w") as file:
            file.write(
                DEFAULT_JS_TEMPLATE
                % dict(
                    camel_name=camel_name,
                    small_camel_name=small_camel_name,
                    module=module_name,
                    snake_name=snake_name,
                ),
            )

        with open(f"{directory}/{snake_name}/{snake_name}.xml", "w") as file:
            file.write(
                DEFAULT_XML_TEMPLATE
                % dict(
                    camel_name=camel_name,
                    small_camel_name=small_camel_name,
                    module=module_name,
                    snake_name=snake_name,
                ),
            )

        view_js = self.view.window().open_file(
            f"{directory}/{snake_name}/{snake_name}.js",
            flags=64,
        )
        self.view.window().open_file(
            f"{directory}/{snake_name}/{snake_name}.xml",
            flags=64,
        )

        if import_in_manifest(module, directory, snake_name):
            view = self.view.window().open_file(
                f"{module}/__manifest__.py",
                flags=64,
            )
            self.view.window().focus_view(view)

            def _scroll_manifest():
                view.show(view.size())

            sublime.set_timeout(_scroll_manifest, 100)
        else:
            self.view.window().focus_view(view_js)

    def input(self, args):
        self.modules = {}
        for folder in self.view.window().folders():
            self.modules.update(find_modules(folder))

        current_file_name = self.view.file_name()
        current_module = next(
            (m for m in self.modules.values() if current_file_name.startswith(m + "/")),
            None,
        )
        if not self.modules:
            sublime.error_message("No Odoo modules found")
            return

        return NewFieldWidgetModuleInputHandler(
            self.modules, current_module, self.view.window()
        )


class NewFieldWidgetModuleInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, modules, current_module, window):
        self.modules = modules
        self.current_module = current_module
        self.window = window
        if current_module:
            sublime.set_timeout(functools.partial(self._select, window))

    def name(self):
        return "module"

    def placeholder(self):
        return "Module"

    def list_items(self):
        modules = list(self.modules.items())
        modules = sorted(modules, key=lambda m: len(m[1]))
        i = next(
            (i for i, (m, p) in enumerate(modules) if p == self.current_module), None
        )
        if i is not None:
            return modules, i
        return modules

    def validate(self, text):
        return True

    def preview(self, text):
        return text

    def next_input(self, args):
        return NewFieldWidgetDirectoryInputHandler(args["module"], self.window)

    def _select(self, window):
        # Automatically select the first option
        # TODO: remove `set_timeout` once issue is fixed
        # https://github.com/sublimehq/sublime_text/issues/5507
        window.run_command("select")


class NewFieldWidgetDirectoryInputHandler(sublime_plugin.ListInputHandler):
    # Try to automatically select those paths in that order if possible
    ALLOWED_DEFAULT_SELECTED = (
        "/static/src/views/fields",
        "/static/src/components",
        "/static/src",
    )

    def __init__(self, module, window):
        self.module = module
        self.base_dir = module + "/static/src"
        blacklist = ["/tests", "/lib", "/scss", "/css", "/tours", "/img"]
        self.dirs = [
            d
            for d in list_directories(self.base_dir)
            if all(b not in d for b in blacklist)
        ]
        self.select_name = None
        if not self.dirs:
            self.dirs.append(self.base_dir + "/components")
        sublime.set_timeout(functools.partial(self._select, window))

    def name(self):
        return "directory"

    def placeholder(self):
        return "Directory"

    def list_items(self):
        dirs = [(d[len(self.module) :], d) for d in self.dirs]
        dirs = sorted(dirs, key=lambda m: len(m[0]))
        for try_default in self.ALLOWED_DEFAULT_SELECTED:
            i = next(
                (i for i, (name, path) in enumerate(dirs) if name == try_default),
                None,
            )
            if i is not None:
                return dirs, i

        return dirs

    def validate(self, text):
        return True

    def next_input(self, args):
        return NewFieldWidgetNameInputHandler()

    def preview(self, text):
        return text

    def _select(self, window):
        # Automatically select the first option
        # TODO: remove `set_timeout` once issue is fixed
        # https://github.com/sublimehq/sublime_text/issues/5507
        window.run_command("select")


class NewFieldWidgetNameInputHandler(sublime_plugin.TextInputHandler):
    def name(self):
        return "widget_name"

    def placeholder(self):
        return "many2many_tags"

    def validate(self, text):
        return True


DEFAULT_JS_TEMPLATE = """import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class %(camel_name)s extends Component {
    static template = "%(module)s.%(camel_name)s";
    static props = {
        ...standardFieldProps,
        __TEST_PROPS__: { type: Boolean, optional: true },
    };
    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({});
    }
}

const %(small_camel_name)s = {
    component: %(camel_name)s,
};

registry.category("fields").add("%(snake_name)s", %(small_camel_name)s);
"""

DEFAULT_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="%(module)s.%(camel_name)s">
    </t>
</templates>
"""


def glob_translate(pattern):
    # TODO: use glob.translate once it runs on python 3.13
    # https://docs.python.org/3/library/glob.html
    i = 0
    n = len(pattern)
    res = ""
    while i < n:
        if pattern[i] == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                res += ".*"
                i += 2
                if i < n and pattern[i] == "/":
                    res += "/"
                    i += 1
            else:
                res += "[^/]*"
                i += 1
        elif pattern[i] == "/":
            res += "/"
            i += 1
        elif pattern[i] in ".()[]{}+^$\\|":
            res += "\\" + pattern[i]
            i += 1
        else:
            res += pattern[i]
            i += 1
    return "^" + res + "$"


def import_in_manifest(module, component_directory, name):
    # Add a TODO in the manifest if needed to import the new component
    assert component_directory.startswith(module)
    component_directory = component_directory[len(module.rsplit("/", 1)[0]) + 1 :]

    with open(f"{module}/__manifest__.py") as file:
        manifest_content = file.read()
        assets = (
            ast.literal_eval(manifest_content)
            .get("assets", {})
            .get("web.assets_backend", ())
        )

    ok_js = False
    ok_xml = False
    for asset in assets:
        asset = glob_translate(asset)
        if re.match(asset, f"{component_directory}/{name}/{name}.js"):
            ok_js = True
        if re.match(asset, f"{component_directory}/{name}/{name}.xml"):
            ok_xml = True

    if not ok_js or not ok_xml:
        # Make a syntax error on purpose to be sure we don't forget
        manifest_content += "\nTODO: include component"
        manifest_content += "\n" + json.dumps(
            {"assets": {"web.assets_backend": [f"{component_directory}/**/*"]}},
            indent=4,
        )
        manifest_content += "\n"
        with open(f"{module}/__manifest__.py", "w") as file:
            file.write(manifest_content)
        return True
    return False
