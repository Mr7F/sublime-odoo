import sublime
import sublime_plugin


snippets = [
    (
        """@api.model_create_multi
def create(self, vals_list):
    records = super().create(vals_list)
    $1
    return records
$0
""",
        "create",
        "Odoo / Create",
    ),
    (
        """@api.constrains("${1:field_name}")
def _check_${1:field_name}(self):
    if $2:
        raise ValidationError(_("$3"))
$0
""",
        "_check",
        "Odoo / Constrains",
    ),
    (
        """@api.onchange('${1:field_name}')
def _onchange_${1:field_name}(self):
    $0
""",
        "_onchange",
        "Odoo / On-Change",
    ),
    (
        """@classmethod
def setUpClass(cls):
    super().setUpClass()
    $0
""",
        "setUpClass",
        "Odoo / setUpClass",
    ),
    (
        """def write(self, vals):
    $1
    return super().write(vals)
$0
""",
        "write",
        "Odoo / write",
    ),
    (
        """@api.depends("$2")
def _compute_${1:name}(self):
    for ${3:record} in self:
        ${3:record}.${1:name} = $0
""",
        "_compute",
        "Odoo / Compute",
    ),
]


class SnippetPythonFunctionInsertCommand(sublime_plugin.TextCommand):
    """Allow to use space in trigger.

    Sublime text does not allow space in trigger, so we do custom code
    to be able to insert the functions and remove the `def` keyword.
    """

    def run(self, edit, snippet):
        # Delete `def `
        for _ in range(4):
            self.view.run_command("left_delete")

        self.view.run_command("insert_snippet", {"contents": snippet})


class SnippetPythonFunctionEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if not all(view.match_selector(pt, "source.python") for pt in locations):
            return None

        for pt in locations:
            pt -= len(prefix)
            r = view.find("def", pt, flags=8)
            if r.a < 0:
                return None
            def_text = view.substr(sublime.Region(r.a, pt - 1))
            if def_text != "def" + " " * (len(def_text) - 3):
                return None

            if not view.match_selector(r.a, "keyword.declaration.function.python"):
                return None

        return [
            sublime.CompletionItem.command_completion(
                trigger,
                "snippet_python_function_insert",
                {"snippet": snippet},
                name,
                sublime.KIND_SNIPPET,
            )
            for snippet, trigger, name in snippets
        ]
