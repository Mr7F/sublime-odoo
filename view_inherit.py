import sublime_plugin
import sublime

from .utils import get_models, get_views

TEMPLATE = """
<record id="%(model_snake)s_view_%(view_type)s" model="ir.ui.view">
    <field name="name">%(model)s.view.%(view_type)s.inherit.%(current_module)s</field>
    <field name="model">%(model)s</field>
    <field name="inherit_id" ref="%(original_ref)s"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='${1:name}']" position="${2:after}">
            $3
        </xpath>
    </field>
</record>$0
""".strip()


class OdooNewViewInheritCommand(sublime_plugin.TextCommand):
    def run(self, edit, model, view_type, view_id):
        contents = TEMPLATE % {
            "model": model,
            "model_snake": model.replace(".", "_"),
            "view_type": view_type,
            "original_ref": view_id,
            "current_module": self.current_module,
        }
        self.view.run_command("insert_snippet", {"contents": contents})

    def input(self, args):
        self.modules = {}
        self.models = set()
        self.current_module = None

        file_name = self.view.file_name()
        if not file_name.endswith(".xml") or "/views/" not in file_name:
            sublime.error_message(
                "The current file should be in module/views/views.xml"
            )
            return

        self.current_module = file_name.split("/views/")[0].split("/")[-1]

        for folder in self.view.window().folders():
            self.models |= get_models(folder)

        if not self.models:
            sublime.error_message("No Odoo model found")
            return

        return NewViewInheritModelInputHandler(
            self.models,
            self.view.window().folders(),
            self.view.window(),
        )


class NewViewInheritModelInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, models, folders, window):
        self.models = models
        self.folders = folders
        self.window = window

    def name(self):
        return "model"

    def placeholder(self):
        return "res.partner"

    def list_items(self):
        return sorted(self.models, key=lambda m: len(m))

    def validate(self, text):
        return True

    def preview(self, text):
        return text

    def next_input(self, args):
        views = {}
        for folder in self.folders:
            next_views = get_views(folder, args["model"])

            for k in next_views:
                views[k] = views.get(k, []) + next_views[k]

        return NewViewInheritViewTypeInputHandler(views)


class NewViewInheritViewTypeInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, views):
        self.views = views

    def name(self):
        return "view_type"

    def placeholder(self):
        return "Form"

    def list_items(self):
        return sorted(self.views, key=lambda m: len(m))

    def validate(self, text):
        return True

    def preview(self, text):
        return text

    def next_input(self, args):
        return NewViewInheritViewIdInputHandler(self.views[args["view_type"]])


class NewViewInheritViewIdInputHandler(sublime_plugin.ListInputHandler):
    def __init__(self, views):
        self.views = views

    def name(self):
        return "view_id"

    def placeholder(self):
        return "View"

    def list_items(self):
        return sorted(self.views, key=lambda m: len(m))

    def validate(self, text):
        return True

    def preview(self, text):
        return text
