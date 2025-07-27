import os

template = """<snippet>
    <content><![CDATA[
%(name)s="$1"$0
]]></content>
    <tabTrigger>%(name)s=</tabTrigger>
    <scope>meta.tag.xml entity</scope>
    <description>%(title)s</description>
</snippet>
"""

template_default = """<snippet>
    <content><![CDATA[
%(name)s="${1:%(default)s}"$0
]]></content>
    <tabTrigger>%(name)s=</tabTrigger>
    <scope>meta.tag.xml entity</scope>
    <description>%(title)s</description>
</snippet>
"""

if __name__ == "__main__":
    os.system("rm ./*.sublime-snippet")

    attributes = [
        "name",
        "label",
        "domain",
        "help",
        "string",
        "help",
        "class",
        "type",
        "icon",
        "context",
        "widget",
        "placeholder",
        "t-out",
        "t-set",
        "t-if",
        "t-elif",
        "t-else",
    ]
    attributes_default = {
        "groups": "base.group_no_one",
        "required": "1",
        "readonly": "1",
        "invisible": "1",
        "optional": "hide",
    }
    for attribute in attributes:
        with open(f"xml-attribute-{attribute}.sublime-snippet", "w") as file:
            file.write(
                template
                % {
                    "name": attribute,
                    "title": attribute.capitalize(),
                }
            )

    for attribute, default in attributes_default.items():
        with open(f"xml-attribute-{attribute}.sublime-snippet", "w") as file:
            file.write(
                template_default
                % {
                    "name": attribute,
                    "title": attribute.capitalize(),
                    "default": default,
                }
            )
