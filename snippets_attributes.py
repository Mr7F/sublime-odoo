from tempfile import tempdir
import sublime
import sublime_plugin


snippets = [
    (
        """_read_group(domain=[$1], groupby=["${2:parent_id}"])""",
        "_read_group",
        "Odoo / _read_group",
    ),
    (
        """browse($1)""",
        "browse",
        "Odoo / browse",
    ),
    (
        """create({$1})""",
        "create",
        "Odoo / create({})",
    ),
    (
        """env["$1"]""",
        "env",
        "Odoo / env[]",
    ),
    (
        """filtered($1)""",
        "filtered",
        "Odoo / filtered({})",
    ),
    (
        """search($1)""",
        "search",
        "Odoo / search()",
    ),
    (
        """with_context($1)""",
        "with_context",
        "Odoo / with_context()",
    ),
    (
        """write({$1})""",
        "write",
        "Odoo / write({})",
    ),
]


class SnippetPythonAttributeInsertCommand(sublime_plugin.TextCommand):
    """Allow to use better detection to trigger the snippets."""

    def run(self, edit, snippet):
        self.view.run_command("insert_snippet", {"contents": snippet})


class SnippetPythonAttributeEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if not all(view.match_selector(pt, "source.python") for pt in locations):
            return None

        for pt in locations:
            pt -= len(prefix)
            r = view.find(".", pt, flags=8 | 1)
            if r.a < 0:
                return None
            text = view.substr(sublime.Region(r.a, pt))
            if text != "." + " " * (len(text) - 1):
                return None

            obj_pos = view.find("[^ ]", r.a, flags=8)
            if obj_pos.a < 0:
                return None

            if not view.match_selector(
                obj_pos.a,
                "meta.path | punctuation.section.brackets.end.python",
            ):
                return None

        return [
            sublime.CompletionItem.snippet_completion(
                trigger,
                snippet,
                name,
            )
            for snippet, trigger, name in snippets
        ]
