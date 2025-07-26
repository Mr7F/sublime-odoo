import os
import sublime_plugin
import functools
import shlex
import sublime
import re


def find_modules(root_dir):
    # Use `fdfind` because it's way faster than python on large project
    cmd = (
        "fdfind __manifest__.py --absolute-path --base-directory %s --exec dirname {} \; --strip-cwd-prefix"
        % shlex.quote(root_dir)
    )
    paths = os.popen(cmd).read().split("\n")
    return {path.split("/")[-1]: path for path in paths if path.strip()}


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

        self.view.window().open_file(f"{directory}/{snake_name}/{snake_name}.js")
        self.view.window().open_file(f"{directory}/{snake_name}/{snake_name}.xml")

    def input(self, args):
        self.modules = {}
        for folder in self.view.window().folders():
            self.modules.update(find_modules(folder))

        current_file_name = self.view.file_name()
        current_module = next(
            (m for m in self.modules.values() if current_file_name.startswith(m + "/")),
            None,
        )

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

    def initial_text(self):
        if self.current_module:
            return

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

export class %(camel_name)s extends Component {
    static template = "%(module)s.%(camel_name)s";
    static props = { ...standardFieldProps };

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
