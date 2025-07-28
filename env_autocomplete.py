import sublime
import sublime_plugin
from functools import partial
from .utils import get_models


class OdooEnvAutoCompleteInsertCommand(sublime_plugin.TextCommand):
    """Allow to use better detection to trigger the snippets."""

    def run(self, edit, model):
        self.view.run_command("insert_snippet", {"contents": model})
        for pt in list(self.view.sel()):
            next_pt = self.view.expand_to_scope(pt.a, "meta.brackets.python")
            self.view.sel().subtract(pt)
            self.view.sel().add(sublime.Region(next_pt.b, next_pt.b))


class OdooEnvAutoCompleteEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if not all(view.match_selector(pt, "source.python") for pt in locations):
            return None

        if not all(view.match_selector(pt, "string") for pt in locations):
            return None

        for pt in locations:
            if not view.match_selector(pt, "string"):
                return None

            pt = view.expand_to_scope(pt, "string").a + 1
            r = view.find(r"\Wenv\s*\[('|\")", pt + 1, flags=8)
            # text = view.substr(sublime.Region(r.a, pt))
            if r.a < 0 or r.b != pt:
                return None

            bracket_pos = view.find("[", r.a, flags=1)
            if bracket_pos.a < 0:
                return None

            if not view.match_selector(
                bracket_pos.a, "punctuation.section.brackets.begin.python"
            ):
                return None

            if not view.match_selector(r.a + 1, "meta.generic-name"):
                return None

        completion_list = sublime.CompletionList()

        sublime.set_timeout_async(
            partial(
                self._fill_completion_list,
                completion_list=completion_list,
                view=view,
            ),
        )

        return completion_list

    def _fill_completion_list(self, completion_list, view):
        models = set()
        for folder in view.window().folders():
            models |= get_models(folder)

        completion_list.set_completions(
            [
                sublime.CompletionItem.command_completion(
                    model,
                    "odoo_env_auto_complete_insert",
                    {"model": model},
                    kind=sublime.KIND_SNIPPET,
                )
                for model in models
            ]
        )
