import os
import subprocess
import xml.etree.ElementTree as ET

import sublime


def run_rg(args):
    try:
        result = subprocess.run(
            ["rg", *args],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        sublime.status_message("Odoo: ripgrep (rg) is required for project searches")
        return []
    return result.stdout.splitlines()


def find_modules(root_dir):
    # Use ripgrep because it's way faster than python on large project
    paths = run_rg(["--files", "--glob", "**/__manifest__.py", root_dir])
    paths = (p.strip().replace("/__manifest__.py", "") for p in paths if p.strip())

    modules = {}
    for path in paths:
        if path.strip():
            module = path.split("/")[-1]
            module_i = module
            i = 1
            while module_i in modules:
                i += 1
                module_i = f"{module} ({i})"

            if "social" in module_i:
                print(module_i)
            modules[module_i] = path
    return modules


def get_models(root_dir):
    lines = run_rg(
        [
            "-t",
            "py",
            "--trim",
            "--no-filename",
            "--no-line-number",
            "--fixed-strings",
            " _name = ",
            root_dir,
        ]
    )
    models = (
        line[9:-1] for line in lines if line.startswith(("_name = '", '_name = "'))
    )
    return {model for model in models if " " not in model}


def get_views(root_dir, model):
    # 1. Early filter with ripgrep
    s = """<field name="model">%s</field>""" % model
    files = run_rg(
        [
            "-t",
            "xml",
            "--trim",
            "--files-with-matches",
            "--fixed-strings",
            s,
            root_dir,
        ]
    )

    # 2. Parse the XML files
    views = {
        "search": [],
        "form": [],
        "list": [],
        "kanban": [],
        "graph": [],
        "pivot": [],
        "calendar": [],
        "gantt": [],
        "grid": [],
        "map": [],
    }
    for file in files:
        module = file.split("/views/")[0].split("/")[-1]
        try:
            root = ET.parse(file).getroot()
        except Exception as e:
            print("Error while parsing", file, e)
            continue

        for record in root.findall(".//record[@id][@model='ir.ui.view']"):
            # Keep only the view in primary mode, or without inherit
            if record.find(".//field[@name='inherit_id']") is not None:
                mode_el = record.find(".//field[@name='mode']")
                if mode_el is None or mode_el.text != "primary":
                    continue

            view_id = record.attrib["id"]
            model_el = record.find(".//field[@name='model']")
            if model_el is None or model_el.text != model:
                continue

            if "." not in view_id:
                view_id = f"{module}.{view_id}"

            view_name_part = view_id.split(".")[-1].split("_")
            if "search" in view_name_part or "filter" in view_name_part:
                views["search"].append(view_id)
            if "form" in view_name_part:
                views["form"].append(view_id)
            if "kanban" in view_name_part:
                views["kanban"].append(view_id)
            if "tree" in view_name_part or "list" in view_name_part:
                views["list"].append(view_id)
            if "graph" in view_name_part:
                views["graph"].append(view_id)
            if "pivot" in view_name_part:
                views["pivot"].append(view_id)
            if "graph" in view_name_part:
                views["graph"].append(view_id)
            if "calendar" in view_name_part:
                views["calendar"].append(view_id)
            if "gantt" in view_name_part:
                views["gantt"].append(view_id)
            if "grid" in view_name_part:
                views["grid"].append(view_id)
            if "map" in view_name_part:
                views["map"].append(view_id)

    return views


def add_python_import(filename, import_line):
    """Heuristic that add an import, and try to sort it.

    Return True if the file has been modified.
    """
    if not os.path.isfile(filename):
        with open(filename, "w") as file:
            file.write(TEMPLATE_INIT_MODELS % {"import": import_line})
        return True

    with open(filename) as file:
        data = file.read()

    if import_line + "\n" not in data:
        lines = data.split("\n")
        idx = next(
            (
                i
                for i, l in enumerate(lines)
                if l.startswith(import_line[:5]) and l > import_line
            ),
            None,
        )
        if idx is None:
            data += import_line + "\n"
        else:
            data = "\n".join(lines[:idx] + [import_line] + lines[idx:])

        with open(filename, "w") as file:
            file.write(data)
        return True
    return False


TEMPLATE_INIT_MODELS = """# Part of Odoo. See LICENSE file for full copyright and licensing details.

%(import)s
"""
