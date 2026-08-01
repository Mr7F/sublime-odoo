import importlib
import os
import shutil
import sublime

from unittesting import DeferrableTestCase

SYNTAX = "Packages/sublime-odoo/OdooOwl.sublime-syntax"
FILE_PATH = os.path.join(sublime.packages_path(), "User", "_goto_test_owl_fixture.xml")

CONTENT = """<templates>
    <t t-name="my_module.MyComponent">
        <div>Hello</div>
    </t>
    <t t-name="my_module.Parent">
        <t t-call="my_module.MyComponent"/>
    </t>
    <t t-name="my_module.Base">
        <div>Base</div>
    </t>
    <t t-name="my_module.Child" t-inherit="my_module.Base" t-inherit-mode="primary">
    </t>
</templates>
"""

DEFINITION_ANCHOR = 't-name="my_module.MyComponent"'
REFERENCE_ANCHOR = 't-call="my_module.MyComponent"'
T_INHERIT_DEFINITION_ANCHOR = 't-name="my_module.Base"'
T_INHERIT_REFERENCE_ANCHOR = 't-inherit="my_module.Base"'


class TestOwlGotoDefinitionAndReference(DeferrableTestCase):

    def setUp(self):
        with open(FILE_PATH, "w") as f:
            f.write(CONTENT)
        self.window = sublime.active_window()
        self.view = self.window.open_file(FILE_PATH)
        yield lambda: not self.view.is_loading()
        self.view.assign_syntax(SYNTAX)
        yield lambda: (
            all(any(s.name == n for s in self.view.symbol_regions())
                for n in ("my_module.MyComponent", "my_module.Base"))
            and all(any(s.name == n for s in self.view.indexed_symbol_regions())
                    for n in ("my_module.MyComponent", "my_module.Base"))
        )

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.window.focus_view(self.view)
            self.window.run_command("close_file")
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)

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
        self._select(self._value_region(REFERENCE_ANCHOR))
        self.window.run_command("goto_definition_odoo_xml")
        def_region = self.view.find(DEFINITION_ANCHOR, 0, sublime.LITERAL)
        yield {
            "condition": lambda: self._selection_touches(self.window.active_view(), def_region),
            "timeout": 2000,
        }

        after = self.window.active_view()
        self.assertEqual(after, self.view, "goto_definition should stay in the same buffer")
        self.assertTrue(
            self._selection_touches(after, def_region),
            "cursor did not land on the t-name definition, sel=%r" % list(after.sel()),
        )

    def test_goto_reference_from_definition(self):
        self._select(self._value_region(DEFINITION_ANCHOR))
        self.window.run_command("goto_reference_odoo_xml")
        ref_region = self.view.find(REFERENCE_ANCHOR, 0, sublime.LITERAL)
        yield {
            "condition": lambda: self._selection_touches(self.window.active_view(), ref_region),
            "timeout": 2000,
        }

        after = self.window.active_view()
        self.assertEqual(after, self.view, "goto_reference should stay in the same buffer")
        self.assertTrue(
            self._selection_touches(after, ref_region),
            "cursor did not land on the t-call reference, sel=%r" % list(after.sel()),
        )

    def test_goto_definition_from_t_inherit_reference(self):
        self._select(self._value_region(T_INHERIT_REFERENCE_ANCHOR))
        self.window.run_command("goto_definition_odoo_xml")
        def_region = self.view.find(T_INHERIT_DEFINITION_ANCHOR, 0, sublime.LITERAL)
        yield {
            "condition": lambda: self._selection_touches(self.window.active_view(), def_region),
            "timeout": 2000,
        }

        after = self.window.active_view()
        self.assertEqual(after, self.view, "goto_definition should stay in the same buffer")
        self.assertTrue(
            self._selection_touches(after, def_region),
            "cursor did not land on the t-name definition, sel=%r" % list(after.sel()),
        )


COMPONENT_TAG_FILE_PATH = os.path.join(
    sublime.packages_path(), "User", "_goto_test_owl_component_tag_fixture.xml")

COMPONENT_TAG_CONTENT = """<templates>
    <t t-name="my_module.Parent">
        <Dropdown>
            <t t-set-slot="content">
                <DropdownItem>Option</DropdownItem>
            </t>
        </Dropdown>
    </t>
</templates>
"""


class TestOwlComponentTagInSymbolList(DeferrableTestCase):

    def setUp(self):
        with open(COMPONENT_TAG_FILE_PATH, "w") as f:
            f.write(COMPONENT_TAG_CONTENT)
        self.window = sublime.active_window()
        self.view = self.window.open_file(COMPONENT_TAG_FILE_PATH)
        yield lambda: not self.view.is_loading()
        self.view.assign_syntax(SYNTAX)
        yield lambda: any(
            s.name == "Dropdown" for s in self.view.symbol_regions()
        )

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.window.focus_view(self.view)
            self.window.run_command("close_file")
        if os.path.exists(COMPONENT_TAG_FILE_PATH):
            os.remove(COMPONENT_TAG_FILE_PATH)

    def test_component_tags_are_in_symbol_list(self):
        names = [s.name for s in self.view.symbol_regions()]
        self.assertIn("Dropdown", names)
        self.assertIn("DropdownItem", names)

    def test_t_set_slot_wrapper_tag_is_not_in_symbol_list(self):
        names = [s.name for s in self.view.symbol_regions()]
        self.assertNotIn("t", names)
        self.assertEqual(sorted(names), ["Dropdown", "DropdownItem", "my_module.Parent"])


CROSS_MODULE_FIXTURE_ROOT = os.path.join(
    sublime.packages_path(), "User", "_cross_module_fixture")
MODULE_X_DIR = os.path.join(CROSS_MODULE_FIXTURE_ROOT, "module_x")
MODULE_Y_DIR = os.path.join(CROSS_MODULE_FIXTURE_ROOT, "module_y")
MODULE_Z_DIR = os.path.join(CROSS_MODULE_FIXTURE_ROOT, "module_z")
MODULE_X_FILE = os.path.join(MODULE_X_DIR, "templates.xml")
MODULE_Y_FILE = os.path.join(MODULE_Y_DIR, "templates.xml")
MODULE_Z_FILE = os.path.join(MODULE_Z_DIR, "templates.xml")

MODULE_X_CONTENT = """<templates>
    <t t-name="module_x.Local">
        <div>Local, defined with its full prefix</div>
    </t>
    <t t-call="Local"/>
    <t t-call="module_y.Shared"/>
    <t t-name="Bare">
        <div>Bare, defined without any prefix</div>
    </t>
</templates>
"""

MODULE_Y_CONTENT = """<templates>
    <t t-name="Shared">
        <div>The real Shared, defined without any prefix</div>
    </t>
    <t t-call="module_x.Bare"/>
</templates>
"""

MODULE_Z_CONTENT = """<templates>
    <t t-name="Shared">
        <div>WRONG decoy Shared in an unrelated module - should never be navigated to</div>
    </t>
</templates>
"""


def _select_value(view, anchor):
    region = view.find(anchor, 0, sublime.LITERAL)
    assert region.a != -1, "expected to find %r in the buffer" % anchor
    quote = anchor.index('"')
    start = region.a + quote + 1
    end = region.b - 1
    view.sel().clear()
    view.sel().add(sublime.Region(start, end))


class TestOwlCrossModuleResolution(DeferrableTestCase):

    def setUp(self):
        for d in (MODULE_X_DIR, MODULE_Y_DIR, MODULE_Z_DIR):
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "__manifest__.py"), "w").close()
        with open(MODULE_X_FILE, "w") as f:
            f.write(MODULE_X_CONTENT)
        with open(MODULE_Y_FILE, "w") as f:
            f.write(MODULE_Y_CONTENT)
        with open(MODULE_Z_FILE, "w") as f:
            f.write(MODULE_Z_CONTENT)

        self.window = sublime.active_window()

        self.z_view = self.window.open_file(MODULE_Z_FILE)
        yield lambda: not self.z_view.is_loading()
        self.z_view.assign_syntax(SYNTAX)
        yield lambda: (
            any(s.name == "Shared" for s in self.z_view.symbol_regions())
            and any(s.name == "Shared" for s in self.z_view.indexed_symbol_regions())
        )

        self.y_view = self.window.open_file(MODULE_Y_FILE)
        yield lambda: not self.y_view.is_loading()
        self.y_view.assign_syntax(SYNTAX)
        yield lambda: (
            all(any(s.name == n for s in self.y_view.symbol_regions())
                for n in ("Shared",))
            and all(any(s.name == n for s in self.y_view.indexed_symbol_regions())
                    for n in ("Shared", "module_x.Bare"))
        )

        self.x_view = self.window.open_file(MODULE_X_FILE)
        yield lambda: not self.x_view.is_loading()
        self.x_view.assign_syntax(SYNTAX)
        yield lambda: (
            all(any(s.name == n for s in self.x_view.symbol_regions())
                for n in ("module_x.Local", "Bare"))
            and all(any(s.name == n for s in self.x_view.indexed_symbol_regions())
                    for n in ("Local", "module_y.Shared"))
        )

    def tearDown(self):
        for v in (getattr(self, "x_view", None), getattr(self, "y_view", None),
                  getattr(self, "z_view", None)):
            if v:
                v.set_scratch(True)
                self.window.focus_view(v)
                self.window.run_command("close_file")
        shutil.rmtree(CROSS_MODULE_FIXTURE_ROOT, ignore_errors=True)

    def _run_goto_definition_and_wait_for(self, view, expected_file):
        self.window.focus_view(view)
        self.window.run_command("goto_definition_odoo_xml")
        yield {
            "condition": lambda: self.window.active_view().file_name() == expected_file,
            "timeout": 2000,
        }
        after = self.window.active_view()
        self.assertEqual(
            after.file_name(), expected_file,
            "goto_definition landed in %r, expected %r" % (after.file_name(), expected_file),
        )
        return after

    def test_bare_reference_resolves_against_current_module(self):
        _select_value(self.x_view, 't-call="Local"')
        after = yield from self._run_goto_definition_and_wait_for(self.x_view, MODULE_X_FILE)
        def_region = after.find('t-name="module_x.Local"', 0, sublime.LITERAL)
        self.assertNotEqual(def_region.a, -1)
        sel = after.sel()[0]
        self.assertTrue(
            def_region.a <= sel.a <= def_region.b,
            "cursor did not land on module_x.Local's definition, sel=%r" % list(after.sel()),
        )

    def test_prefixed_reference_resolves_to_bare_definition_in_that_module(self):
        _select_value(self.x_view, 't-call="module_y.Shared"')
        yield from self._run_goto_definition_and_wait_for(self.x_view, MODULE_Y_FILE)

    def test_bare_definition_found_by_prefixed_reference_elsewhere(self):
        _select_value(self.x_view, 't-name="Bare"')
        self.window.focus_view(self.x_view)
        self.window.run_command("goto_reference_odoo_xml")

        yield {
            "condition": lambda: self.window.active_view().file_name() == MODULE_Y_FILE,
            "timeout": 2000,
        }
        after = self.window.active_view()
        self.assertEqual(
            after.file_name(), MODULE_Y_FILE,
            "goto_reference did not land in module_y's file, active view is %r"
            % after.file_name(),
        )
        ref_region = after.find('t-call="module_x.Bare"', 0, sublime.LITERAL)
        self.assertNotEqual(ref_region.a, -1)
        sel = after.sel()[0]
        self.assertTrue(
            ref_region.a <= sel.a <= ref_region.b,
            "cursor did not land on the module_x.Bare reference, sel=%r" % list(after.sel()),
        )


FIND_MODULE_DIR_FIXTURE_ROOT = os.path.join(
    sublime.packages_path(), "User", "_find_module_dir_fixture")
MODULE_M_DIR = os.path.join(FIND_MODULE_DIR_FIXTURE_ROOT, "module_m")
MODULE_N_DIR = os.path.join(FIND_MODULE_DIR_FIXTURE_ROOT, "module_n")
MODULE_M_FILE = os.path.join(MODULE_M_DIR, "templates.xml")
MODULE_N_FILE = os.path.join(MODULE_N_DIR, "templates.xml")

MODULE_M_CONTENT = """<templates>
    <t t-call="module_n.Target"/>
</templates>
"""

MODULE_N_CONTENT = """<templates>
    <t t-name="Target">
        <div>Target</div>
    </t>
</templates>
"""


class TestFindModuleDirDoesNotScanWhenSiblingExists(DeferrableTestCase):

    def setUp(self):
        os.makedirs(MODULE_M_DIR, exist_ok=True)
        os.makedirs(MODULE_N_DIR, exist_ok=True)
        open(os.path.join(MODULE_M_DIR, "__manifest__.py"), "w").close()
        open(os.path.join(MODULE_N_DIR, "__manifest__.py"), "w").close()
        with open(MODULE_M_FILE, "w") as f:
            f.write(MODULE_M_CONTENT)
        with open(MODULE_N_FILE, "w") as f:
            f.write(MODULE_N_CONTENT)

        self.window = sublime.active_window()

        self.n_view = self.window.open_file(MODULE_N_FILE)
        yield lambda: not self.n_view.is_loading()
        self.n_view.assign_syntax(SYNTAX)
        yield lambda: (
            any(s.name == "Target" for s in self.n_view.symbol_regions())
            and any(s.name == "Target" for s in self.n_view.indexed_symbol_regions())
        )

        self.m_view = self.window.open_file(MODULE_M_FILE)
        yield lambda: not self.m_view.is_loading()
        self.m_view.assign_syntax(SYNTAX)
        yield lambda: self.m_view.find('t-call="module_n.Target"', 0, sublime.LITERAL).a != -1

        self.mod = importlib.import_module("sublime-odoo.odoo_goto_symbol")
        self.original_find_modules = self.mod.find_modules

        def _forbidden_find_modules(root_dir):
            raise AssertionError(
                "find_modules(%r) was called - the sibling fast path in "
                "_find_module_dir should have found module_n without a "
                "full project scan" % root_dir)

        self.mod.find_modules = _forbidden_find_modules

    def tearDown(self):
        self.mod.find_modules = self.original_find_modules
        for v in (getattr(self, "m_view", None), getattr(self, "n_view", None)):
            if v:
                v.set_scratch(True)
                self.window.focus_view(v)
                self.window.run_command("close_file")
        shutil.rmtree(FIND_MODULE_DIR_FIXTURE_ROOT, ignore_errors=True)

    def test_goto_definition_with_prefix_does_not_scan_all_modules(self):
        self.window.focus_view(self.m_view)
        _select_value(self.m_view, 't-call="module_n.Target"')
        self.window.run_command("goto_definition_odoo_xml")

        yield {
            "condition": lambda: self.window.active_view().file_name() == MODULE_N_FILE,
            "timeout": 2000,
        }
        after = self.window.active_view()
        self.assertEqual(
            after.file_name(), MODULE_N_FILE,
            "goto_definition did not land in module_n's file, active view is %r"
            % after.file_name(),
        )


class TestDedupeLocations(DeferrableTestCase):

    def setUp(self):
        self.mod = importlib.import_module("sublime-odoo.odoo_goto_symbol")

    def _loc(self, path, row, col):
        return sublime.SymbolLocation(
            path, path, row, col, "OdooOwl", sublime.SYMBOL_TYPE_REFERENCE,
            (sublime.KIND_ID_AMBIGUOUS, "", ""))

    def test_drops_exact_duplicate_position(self):
        a = self._loc("/tmp/ai/templates.xml", 21, 14)
        b = self._loc("/tmp/ai/templates.xml", 21, 14)
        c = self._loc("/tmp/ai/templates.xml", 8, 2)
        result = self.mod._dedupe_locations([a, b, c])
        self.assertEqual(len(result), 2)
        positions = sorted((l.row, l.col) for l in result)
        self.assertEqual(positions, [(8, 2), (21, 14)])

    def test_keeps_different_positions_in_the_same_file(self):
        a = self._loc("/tmp/ai/templates.xml", 4, 10)
        b = self._loc("/tmp/ai/templates.xml", 9, 3)
        result = self.mod._dedupe_locations([a, b])
        self.assertEqual(len(result), 2)

    def test_normalizes_symlinked_paths_to_the_same_file(self):
        real_dir = os.path.join(sublime.packages_path(), "User", "_dedupe_real_dir")
        symlink_dir = os.path.join(sublime.packages_path(), "User", "_dedupe_symlink_dir")
        os.makedirs(real_dir, exist_ok=True)
        real_file = os.path.join(real_dir, "x.xml")
        open(real_file, "w").close()
        try:
            os.symlink(real_dir, symlink_dir)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported in this environment")
        try:
            a = self._loc(real_file, 1, 1)
            b = self._loc(os.path.join(symlink_dir, "x.xml"), 1, 1)
            result = self.mod._dedupe_locations([a, b])
            self.assertEqual(len(result), 1)
        finally:
            if os.path.islink(symlink_dir):
                os.remove(symlink_dir)
            shutil.rmtree(real_dir, ignore_errors=True)


class TestJsClassLocationsAcrossSyntaxPackages(DeferrableTestCase):

    def setUp(self):
        self.mod = importlib.import_module("sublime-odoo.odoo_goto_symbol")
        self.original_lookup_symbol = self.mod.default_symbol.lookup_symbol

    def tearDown(self):
        self.mod.default_symbol.lookup_symbol = self.original_lookup_symbol

    def test_finds_js_class_indexed_under_a_different_syntax_and_kind(self):
        fake_location = sublime.SymbolLocation(
            "/tmp/action_helper.js", "/tmp/action_helper.js", 3, 6,
            "JavaScript (Babel)", sublime.SYMBOL_TYPE_DEFINITION,
            (sublime.KIND_ID_AMBIGUOUS, "", ""))
        self.mod.default_symbol.lookup_symbol = lambda window, name: [fake_location]

        locations = self.mod._js_locations(sublime.active_window(), "ActionHelper")

        self.assertEqual(locations, [fake_location])

    def test_ignores_a_same_named_match_in_a_non_js_file(self):
        fake_location = sublime.SymbolLocation(
            "/tmp/action_helper.xml", "/tmp/action_helper.xml", 3, 6,
            "OdooOwl", sublime.SYMBOL_TYPE_DEFINITION,
            (sublime.KIND_ID_AMBIGUOUS, "", ""))
        self.mod.default_symbol.lookup_symbol = lambda window, name: [fake_location]

        locations = self.mod._js_locations(sublime.active_window(), "ActionHelper")

        self.assertEqual(locations, [])


JS_CLASS_FILE_PATH = os.path.join(sublime.packages_path(), "User", "_goto_test_js_class.js")
JS_CLASS_CONTENT = """export class Test extends Component {
    static template = "my_module.Test";
    onClick() {}
    _refreshView() {}
}
"""

OWL_WITH_JS_FILE_PATH = os.path.join(sublime.packages_path(), "User", "_goto_test_owl_with_js.xml")
OWL_WITH_JS_CONTENT = """<templates>
    <t t-name="my_module.Test">
        <div>Test template - should NOT be navigated to</div>
    </t>
    <t t-name="my_module.Parent">
        <Test t-on-click="onClick"/>
        <NewContentRefreshBanner onClickRefresh.bind="this._refreshView"/>
    </t>
    <t t-name="my_module.NoJsComponent">
        <div>Should not be navigated to - no JS class registers this component</div>
    </t>
    <t t-name="my_module.Parent2">
        <NoJsComponent/>
    </t>
</templates>
"""


class TestOwlComponentTagGotoDefinition(DeferrableTestCase):

    def setUp(self):
        with open(JS_CLASS_FILE_PATH, "w") as f:
            f.write(JS_CLASS_CONTENT)
        with open(OWL_WITH_JS_FILE_PATH, "w") as f:
            f.write(OWL_WITH_JS_CONTENT)

        self.window = sublime.active_window()

        self.js_view = self.window.open_file(JS_CLASS_FILE_PATH)
        yield lambda: not self.js_view.is_loading()
        yield lambda: any(s.name == "Test" for s in self.js_view.indexed_symbol_regions())

        self.view = self.window.open_file(OWL_WITH_JS_FILE_PATH)
        yield lambda: not self.view.is_loading()
        self.view.assign_syntax(SYNTAX)
        yield lambda: (
            any(s.name == "my_module.Test" for s in self.view.indexed_symbol_regions())
            and any(s.name == "my_module.NoJsComponent" for s in self.view.indexed_symbol_regions())
            and any(s.name == "_refreshView" for s in self.view.indexed_symbol_regions())
        )

    def tearDown(self):
        for v in (getattr(self, "view", None), getattr(self, "js_view", None)):
            if v:
                v.set_scratch(True)
                self.window.focus_view(v)
                self.window.run_command("close_file")
        for path in (JS_CLASS_FILE_PATH, OWL_WITH_JS_FILE_PATH):
            if os.path.exists(path):
                os.remove(path)

    def test_goto_definition_from_component_tag_finds_js_class(self):
        tag_region = self.view.find("<Test ", 0, sublime.LITERAL)
        self.assertNotEqual(tag_region.a, -1)
        self.window.focus_view(self.view)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(tag_region.a + 1, tag_region.a + 1))

        self.window.run_command("goto_definition_odoo_xml")

        yield {
            "condition": lambda: self.window.active_view().file_name() == JS_CLASS_FILE_PATH,
            "timeout": 2000,
        }
        after = self.window.active_view()
        self.assertEqual(
            after.file_name(), JS_CLASS_FILE_PATH,
            "goto_definition did not land in the JS class file, active view is %r"
            % after.file_name(),
        )

    def test_goto_definition_from_js_expression_finds_method(self):
        handler = self.view.find('t-on-click="onClick"', 0, sublime.LITERAL)
        self.assertNotEqual(handler.a, -1)
        self.window.focus_view(self.view)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(handler.b - 2))

        self.window.run_command("goto_definition_odoo_xml")

        yield {
            "condition": lambda: self.window.active_view().file_name() == JS_CLASS_FILE_PATH,
            "timeout": 2000,
        }
        after = self.window.active_view()
        method = after.find("onClick()", 0, sublime.LITERAL)
        self.assertNotEqual(method.a, -1)
        self.assertTrue(method.contains(after.sel()[0].a))

    def test_goto_reference_from_js_method_finds_owl_expression(self):
        method = self.js_view.find("_refreshView()", 0, sublime.LITERAL)
        self.window.focus_view(self.js_view)
        self.js_view.sel().clear()
        self.js_view.sel().add(sublime.Region(method.a))

        self.window.run_command("goto_reference")

        yield {
            "condition": lambda: self.window.active_view().file_name() == OWL_WITH_JS_FILE_PATH,
            "timeout": 2000,
        }
        reference = self.view.find("this._refreshView", 0, sublime.LITERAL)
        self.assertTrue(reference.contains(self.view.sel()[0].a))

    def test_goto_definition_from_component_tag_without_js_class_does_not_fall_back_to_t_name(self):
        mod = importlib.import_module("sublime-odoo.odoo_goto_symbol")
        tag_region = self.view.find("<NoJsComponent/>", 0, sublime.LITERAL)
        self.assertNotEqual(tag_region.a, -1)
        pt = tag_region.a + 1

        symbol, locations = mod._definition_fallback(self.window, self.view, pt)

        self.assertEqual(
            locations, [],
            "goto_definition found locations for a component tag with no JS "
            "class - it should not fall back to the t-name template: %r"
            % locations,
        )
