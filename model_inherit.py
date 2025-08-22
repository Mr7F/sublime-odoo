import os
import sublime_plugin
import functools
import sublime
import re

from .utils import find_modules

TEMPLATE_INIT_MODULE = """# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
"""

TEMPLATE_INIT_MODELS = """# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import %(snake_name)s
"""

# Inserted as a snippet to be able to change `inherit` to `name` if needed
TEMPLATE_MODEL = """# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class %(camel_name)s(models.Model):
    _${1:inherit} = "%(model_name)s"

    $0
"""


class OdooNewModelInheritCommand(sublime_plugin.TextCommand):
    def run(self, edit, module, model_name):
        part_name = re.split(r"[^a-zA-Z0-9]", model_name)
        part_name = [x for x in part_name if x]
        snake_name = "_".join(part_name).lower()
        camel_name = "".join(p.capitalize() for p in part_name)

        if os.path.isfile(f"{module}/models/{snake_name}.py"):
            sublime.error_message("The models already exists")
            return

        os.makedirs(f"{module}/models", exist_ok=True)
        to_open = [f"{module}/models/{snake_name}.py"]
        model_content = TEMPLATE_MODEL % {
            "camel_name": camel_name,
            "model_name": model_name,
        }
        with open(f"{module}/models/{snake_name}.py", "w") as file:
            file.write("")

        if not os.path.isfile(f"{module}/__init__.py"):
            with open(f"{module}/__init__.py", "w") as file:
                file.write(TEMPLATE_INIT_MODULE)
            to_open.append(f"{module}/__init__.py")

        if not os.path.isfile(f"{module}/models/__init__.py"):
            with open(f"{module}/models/__init__.py", "w") as file:
                file.write(TEMPLATE_INIT_MODELS % {"snake_name": snake_name})

            to_open.append(f"{module}/models/__init__.py")
        else:
            with open(f"{module}/models/__init__.py") as file:
                data = file.read()

            to_add = f"from . import {snake_name}"
            if to_add + "\n" not in data:
                lines = data.split("\n")
                idx = next(
                    (
                        i
                        for i, l in enumerate(lines)
                        if l.startswith("from . import ") and l > to_add
                    ),
                    None,
                )
                if idx is None:
                    data += to_add + "\n"
                else:
                    data = "\n".join(lines[:idx] + [to_add] + lines[idx:])

                with open(f"{module}/models/__init__.py", "w") as file:
                    file.write(data)
                to_open.append(f"{module}/models/__init__.py")

        views = [
            self.view.window().open_file(file_name, flags=64) for file_name in to_open
        ]
        self.view.window().focus_view(views[0])

        def _scroll_inherit():
            views[0].run_command("insert_snippet", {"contents": model_content})

        sublime.set_timeout(_scroll_inherit, 100)

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

        return NewModelInheritModuleInputHandler(
            self.modules,
            current_module,
            self.view.window(),
        )


class NewModelInheritModuleInputHandler(sublime_plugin.ListInputHandler):
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
        return NewModelInheritNameInputHandler()

    def _select(self, window):
        # Automatically select the first option
        # TODO: remove `set_timeout` once issue is fixed
        # https://github.com/sublimehq/sublime_text/issues/5507
        window.run_command("select")


class NewModelInheritNameInputHandler(sublime_plugin.TextInputHandler):
    def name(self):
        return "model_name"

    def placeholder(self):
        return "mail.message"

    def validate(self, text):
        return bool(re.fullmatch(r"[a-z_.]+", text))
