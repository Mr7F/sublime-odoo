# Sublime - Odoo
## Snippets
Add some snippets for common code
- new model
- overwrite a model
- views (form, list, kanban, search, etc)
- common methods (create, write, etc)

Check the snippet folder to see what's available.

## Syntax highlighting
Syntax highlighting for QWeb templates, OWL templates, views, and access CSV files.

Choose "XML - Odoo", and it will automatically choose the right syntax
- OWL syntax (with JS in expression) if inside `<templates/>`
- View syntax (with python in expression) if inside `<odoo/>`

<p align="center">
  <img src="img/installation.png">
</p>

It highlight JS template inside Python template (eg template of kanban views)

<p align="center">
  <img src="img/demo.png">
</p>

It also highlight mail templates and "backend" templates.
<p align="center">
  <img src="img/demo_template.png">
</p>

And ir.model.access.csv
<p align="center">
  <img src="img/ir.model.access.csv.png">
</p>

With this syntax highlighting comes the symbols, you can jump to view / component template with `ctrl+r` / `ctrl+shift+r`
<p align="center">
  <img src="img/demo_symbols.gif">
</p>

## Go To Definition
You can configure key bind to make "go to definition" work in views / OWL components
(it uses sublime text symbols indexes, and so many results can be returned, they are sorted with a heuristic,
similar filenames are displayed first).

```json
// Standard sublime text `goto_definition`
{ "keys": ["primary+d"], "command": "goto_definition" },
// When the LSP has the feature
{
  "keys": ["primary+d"],
  "command": "lsp_symbol_definition",
  "context": [
    { "key": "lsp.session_with_capability", "operand": "definitionProvider" },
    { "key": "auto_complete_visible", "operand": false }
  ]
},
// Custom Odoo "Go To Definition"
{
  "keys": ["primary+d"],
  "command": "goto_definition_odoo_xml",
  "context": [{ "key": "selector", "operator": "equal", "operand": "text.xml.odoo-view, text.xml.owl, text.xml.odoo" }]
},
```

Same for `goto_reference`.
```json
{ "keys": ["primary+shift+r"], "command": "goto_reference" },
{
  "keys": ["primary+shift+r"],
  "command": "goto_reference_odoo_xml",
  "context": [{ "key": "selector", "operator": "equal", "operand": "text.xml.odoo-view, text.xml.owl, text.xml.odoo" }]
},
```


<p align="center">
  <img src="img/go_to_definition_1.png">
</p>

<p align="center">
  <img src="img/go_to_definition_2.png">
</p>

<p align="center">
  <img src="img/go_to_definition_3.png">
</p>

<p align="center">
  <img src="img/go_to_definition_4.png">
</p>

<p align="center">
  <img src="img/go_to_definition_5.png">
</p>

<p align="center">
  <img src="img/go_to_references.png">
</p>


## Commands
Please install [ripgrep](https://github.com/BurntSushi/ripgrep) to use most of commands (they are use instead of slow python code to get the list of modules, list of models, etc)

> sudo apt install ripgrep

You can automatically create Python inherit, JS component, search a view and overwrite it, etc
<p align="center">
  <img src="img/demo_view.gif">
</p>

Type "Odoo" in the command palette to see what's available.
> https://youtu.be/lkYhHB83vJ8

## Auto-complete
<p align="center">
  <img src="img/demo_env.gif">
</p>

## TODO
- find a way to automatically change `__manifest__.py` without reformatting
- automatically insert the python import at the right place
