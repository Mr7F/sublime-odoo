import shlex
import os
import re
import xml.etree.ElementTree as ET


def find_modules(root_dir):
    # Use `ripgrep` because it's way faster than python on large project
    cmd = "rg --files --glob '**/__manifest__.py' %s" % shlex.quote(root_dir)
    paths = os.popen(cmd).read().split("\n")
    paths = (p.strip().replace("/__manifest__.py", "") for p in paths if p.strip())
    return {path.split("/")[-1]: path for path in paths if path.strip()}


def get_models(root_dir):
    cmd = (
        "rg -t 'py' --trim --no-filename --no-line-number --fixed-strings ' _name = ' %s"
        % shlex.quote(root_dir)
    )
    lines = os.popen(cmd).readlines()
    lines = (
        line[9:-2] for line in lines if line.startswith(("_name = '", '_name = "'))
    )
    return {line for line in lines if " " not in line}


def get_views(root_dir, model):
    # 1. Early filter with ripgrep
    s = """<field name="model">%s</field>""" % model
    cmd = (
        "rg -t 'xml' --trim --no-line-number --fixed-strings %s --count-matches %s"
        % (shlex.quote(s), root_dir)
    )
    files = os.popen(cmd).readlines()
    files = [f.strip().rsplit(":", 1)[0] for f in files]

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
