import os
import tempfile

import sublime

from unittesting import DeferrableTestCase

SYNTAX = "Packages/sublime-odoo/OdooView.sublime-syntax"

CONTENT = """<odoo>
    <t t-name="sublime_odoo_test.goto_view_template">
        <div>Report</div>
    </t>
    <t t-call="sublime_odoo_test.goto_view_template"/>

    <record id="social.social_stream_post_view_kanban" model="ir.ui.view">
        <field name="name">social.stream.post.view.kanban</field>
    </record>
    <record id="my_module.inherit_view" model="ir.ui.view">
        <field name="inherit_id" ref="social.social_stream_post_view_kanban"/>
    </record>

    <template id="sublime_odoo_test.goto_view_parent">
        <div>Parent</div>
    </template>
    <template
        id="sublime_odoo_test.goto_view_child"
        inherit_id="sublime_odoo_test.goto_view_parent"
    />

    <button name="action_confirm"
        string="Confirm"
        type="object" class="oe_highlight"
        invisible="state != 'draft'"
    />
</odoo>
"""

PYTHON_CONTENT = """class TestModel:
    def action_confirm(self):
        pass
"""


class _ViewFixture:
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="goto_view_test_",
            dir=os.path.join(sublime.packages_path(), "User"),
        )
        self.file_path = os.path.join(self.temp_dir.name, "fixture.xml")
        with open(self.file_path, "w") as f:
            f.write(CONTENT)
        self.window = sublime.active_window()
        self.view = self.window.open_file(self.file_path)
        yield lambda: not self.view.is_loading()
        self.view.assign_syntax(SYNTAX)

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.window.focus_view(self.view)
            self.window.run_command("close_file")
        self.temp_dir.cleanup()


class _ViewGotoMixin(_ViewFixture):
    definition_anchor = None
    reference_anchor = None

    def setUp(self):
        yield from super().setUp()
        symbol = self._symbol_name(self.definition_anchor)
        yield lambda: (
            any(s.name == symbol for s in self.view.symbol_regions())
            and any(s.name == symbol for s in self.view.indexed_symbol_regions())
        )

    def _symbol_name(self, anchor):
        quote = anchor.index('"')
        return anchor[quote + 1:-1]

    def _value_region(self, anchor):
        region = self.view.find(anchor, 0, sublime.LITERAL)
        self.assertIsNotNone(region)
        self.assertNotEqual(region.a, -1, "expected to find %r in the buffer" % anchor)
        quote = anchor.index('"')
        start = region.a + quote + 1
        end = region.b - 1
        return sublime.Region(start, end)

    def _select(self, region):
        self.view.sel().clear()
        self.view.sel().add(region)

    def _selection_touches(self, view, region):
        if region is None or region.a == -1:
            return False
        return any(
            region.a <= sel.a <= region.b or region.a <= sel.b <= region.b
            for sel in view.sel()
        )

    def test_goto_definition_from_reference(self):
        self._select(self._value_region(self.reference_anchor))
        self.window.run_command("goto_definition_odoo_xml")
        def_region = self.view.find(self.definition_anchor, 0, sublime.LITERAL)
        yield {
            "condition": lambda: self._selection_touches(self.window.active_view(), def_region),
            "timeout": 2000,
        }

        after = self.window.active_view()
        self.assertEqual(after, self.view, "goto_definition should stay in the same buffer")
        self.assertTrue(
            self._selection_touches(after, def_region),
            "cursor did not land on the definition, sel=%r" % list(after.sel()),
        )

    def test_goto_reference_from_definition(self):
        self._select(self._value_region(self.definition_anchor))
        self.window.run_command("goto_reference_odoo_xml")
        ref_region = self.view.find(self.reference_anchor, 0, sublime.LITERAL)
        yield {
            "condition": lambda: self._selection_touches(self.window.active_view(), ref_region),
            "timeout": 2000,
        }

        after = self.window.active_view()
        self.assertEqual(after, self.view, "goto_reference should stay in the same buffer")
        self.assertTrue(
            self._selection_touches(after, ref_region),
            "cursor did not land on the reference, sel=%r" % list(after.sel()),
        )


class TestViewGotoTCall(_ViewGotoMixin, DeferrableTestCase):
    definition_anchor = 't-name="sublime_odoo_test.goto_view_template"'
    reference_anchor = 't-call="sublime_odoo_test.goto_view_template"'


class TestViewGotoRef(_ViewGotoMixin, DeferrableTestCase):
    definition_anchor = 'id="social.social_stream_post_view_kanban"'
    reference_anchor = 'ref="social.social_stream_post_view_kanban"'


class TestViewGotoInheritId(_ViewGotoMixin, DeferrableTestCase):
    definition_anchor = 'id="sublime_odoo_test.goto_view_parent"'
    reference_anchor = 'inherit_id="sublime_odoo_test.goto_view_parent"'


class TestViewGotoPythonMethod(_ViewFixture, DeferrableTestCase):
    def setUp(self):
        yield from super().setUp()
        self.python_path = os.path.join(self.temp_dir.name, "model.py")
        with open(self.python_path, "w") as f:
            f.write(PYTHON_CONTENT)
        self.python_view = self.window.open_file(self.python_path)
        yield lambda: not self.python_view.is_loading()
        yield lambda: any(
            symbol.name == "action_confirm"
            for symbol in self.python_view.indexed_symbol_regions()
        )

    def tearDown(self):
        if getattr(self, "python_view", None):
            self.python_view.set_scratch(True)
            self.window.focus_view(self.python_view)
            self.window.run_command("close_file")
        super().tearDown()

    def test_goto_definition_from_object_button(self):
        name = self.view.find('name="action_confirm"', 0, sublime.LITERAL)
        self.window.focus_view(self.view)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(name.b - 2))

        self.window.run_command("goto_definition_odoo_xml")

        yield {
            "condition": lambda: self.window.active_view().file_name() == self.python_path,
            "timeout": 2000,
        }
        method = self.python_view.find("action_confirm", 0, sublime.LITERAL)
        self.assertTrue(method.contains(self.python_view.sel()[0].a))

    def test_goto_reference_from_python_method(self):
        method = self.python_view.find("action_confirm", 0, sublime.LITERAL)
        self.window.focus_view(self.python_view)
        self.python_view.sel().clear()
        self.python_view.sel().add(sublime.Region(method.a))

        self.window.run_command("goto_reference")

        yield {
            "condition": lambda: self.window.active_view().file_name() == self.file_path,
            "timeout": 2000,
        }
        name = self.view.find('name="action_confirm"', 0, sublime.LITERAL)
        self.assertTrue(name.contains(self.view.sel()[0].a))
