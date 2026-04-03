# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, final, override

from docutils import core, nodes, readers, transforms
from docutils.transforms.frontmatter import DocInfo, DocTitle

from .context import FmtCtx
from .nodes import (
    ContentsNode,
    CppNode,
    CurrentModuleNode,
    DoxyClassNode,
    DoxyConceptNode,
    DoxyFunctionNode,
    DoxyNode,
    DoxyStructNode,
    DoxyTypedefNode,
    DoxyVariableNode,
    TocTreeNode,
    XRefNode,
)


class Buffer:
    def __init__(self) -> None:
        self.data: str = ""

    def __len__(self) -> int:
        return len(self.data)

    def append(self, entry: str) -> None:
        self.data += entry

    def rstrip(self, chars: str | None = None, /) -> None:
        self.data = self.data.rstrip(chars)

    def endswith(self, suffix: str) -> bool:
        return self.data.endswith(suffix)

    @override
    def __str__(self) -> str:
        return self.data


adornments: Final[list[str]] = ["#", "*", "=", "-", "^"]
space_re: Final[re.Pattern[str]] = re.compile("\\s+")


def _to_roman(n: int) -> str:
    """Very small helper for roman numerals (enough for common list sizes)."""
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    res: list[str] = []
    for v, s in vals:
        while n >= v:
            res.append(s)
            n -= v
    return "".join(res)


def children_to_rst(
    buf: Buffer,
    node: nodes.Node,
    ctx: FmtCtx,
    preproc: PreprocessInfo,
    split_ctx: bool = False,
) -> None:
    if split_ctx:
        for i, child in enumerate(node.children):
            ast_to_rst(buf, child, ctx.ctx(i), preproc)
    else:
        for child in node.children:
            ast_to_rst(buf, child, ctx, preproc)


@dataclass
class PreprocessInfo:
    collected_labels: dict[str, str]


def ast_to_rst(
    buf: Buffer,
    node: nodes.Node,
    ctx: FmtCtx,
    preproc: PreprocessInfo,
) -> None:
    """Very simple doctree -> reST converter for a subset of nodes."""
    match node:
        case nodes.document():
            children_to_rst(buf, node, ctx, preproc)
            # Single trailing newline, strip trailing spaces in the whole doc
            buf.rstrip()
            buf.append("\n")

        case nodes.docinfo():
            dinfos: list[nodes.TextElement] = []
            for c in node.children:
                assert isinstance(c, nodes.TextElement)
                dinfos.append(c)
            width = max(len(child.tagname) for child in dinfos)
            width += 2
            for child in dinfos:
                key = f":{child.tagname.capitalize()}:"
                buf.append(f"{key:<{width}} {child.astext()}\n")
            buf.append("\n")

        case ContentsNode():
            buf.append(".. contents::\n")
            if node.get("local"):
                buf.append("   :local:\n")
            if (depth := node.get("depth")) is not None:
                buf.append(f"   :depth: {depth}\n")
            if (backlinks := node.get("backlinks")) is not None:
                buf.append(f"   :backlinks: {backlinks}\n")
            if node.get("titlesonly"):
                buf.append("   :titlesonly:\n")
            buf.append("\n")

        case nodes.title():
            title_text = node.astext()

            level = -1
            curr: nodes.Node = node
            while curr.parent is not None:
                level += isinstance(curr.parent, nodes.section)
                curr = curr.parent
            level = max(level, 0)

            adornment_char = adornments[level] if level < len(adornments) else '"'
            adornment = adornment_char * len(title_text)

            if level < 2:
                buf.append(f"{ctx.tail_prefix}{adornment}\n")
            buf.append(f"{ctx.tail_prefix}{title_text}\n")
            buf.append(f"{ctx.tail_prefix}{adornment}\n\n")

        case nodes.paragraph():
            buf.append(ctx.head_prefix)
            children_to_rst(buf, node, ctx, preproc)
            buf.append("\n\n")

        case nodes.literal_block():
            classes = node.get("classes", [])
            language = next((c for c in classes if c != "code"), None)

            text = node.astext()

            if language:
                directive = node.get("directive", "code")
                buf.append(f"{ctx.head_prefix}.. {directive}:: {language}\n\n")
            else:
                buf.rstrip()
                buf.append(":\n\n" if buf.endswith(":") else " ::\n\n")

            for line in text.splitlines():
                stripped = line.rstrip()
                if stripped:
                    buf.append(f"{ctx.tail_prefix}   {stripped}\n")
                else:
                    buf.append("\n")
            buf.append("\n")

        case nodes.bullet_list():
            for child in node.children:
                item_ctx = ctx.with_list_prefix("- ")
                ast_to_rst(buf, child, item_ctx, preproc)
            buf.append("\n")

        case nodes.enumerated_list():
            enumtype = node.attributes.get("enumtype", "arabic")
            start = int(node.attributes.get("start", 1))
            suffix = node.attributes.get("suffix") or "."

            for idx, child in enumerate(node.children, start=start):
                assert isinstance(child, nodes.list_item)

                if child["auto"]:
                    label = "#"
                elif enumtype == "loweralpha":
                    label = chr(ord("a") + (idx - start))
                elif enumtype == "upperalpha":
                    label = chr(ord("A") + (idx - start))
                elif enumtype == "lowerroman":
                    label = _to_roman(idx).lower()
                elif enumtype == "upperroman":
                    label = _to_roman(idx).upper()
                else:  # "arabic" and fallback
                    label = str(idx)

                prefix = f"{label}{suffix} "
                item_ctx = ctx.with_list_prefix(prefix)
                ast_to_rst(buf, child, item_ctx, preproc)
            buf.append("\n")

        case nodes.list_item():
            # Render the list item content, potentially with a split context
            children_to_rst(buf, node, ctx, preproc, split_ctx=True)

            # If the item ends with exactly two newlines, trim one so we have
            # a single blank line by default.
            buf.rstrip()
            buf.append("\n")

            # Detect whether the last child is itself a list (bullet or enum)
            last_child = node.children[-1] if node.children else None
            is_nested_list = isinstance(
                last_child, (nodes.bullet_list, nodes.enumerated_list)
            )

            # If this item ends with a nested list, ensure there is an extra
            # blank line after it so that following content is visually separated.
            if is_nested_list:
                buf.append("\n")

        case nodes.field_list():
            # Render as classic reStructuredText field list
            # Each field:
            #   <field>
            #     <field_name>name</field_name>
            #     <field_body>...</field_body>
            #   </field>
            children: list[tuple[nodes.field_name, nodes.field_body]] = []
            for field in node.children:
                assert isinstance(field, nodes.field)
                assert len(field.children) == 2
                [name, body] = field.children
                assert isinstance(name, nodes.field_name)
                assert isinstance(body, nodes.field_body)
                children.append((name, body))

            max_name_width = max(len(name.astext()) for name, _ in children) + 2

            for name, body in children:
                field_name = f":{name.astext()}:"
                buf.append(f"{ctx.head_prefix}{field_name:<{max_name_width}} ")

                # Render body children with an extra indent
                body_ctx = ctx.with_tail_indent("   ")
                children_to_rst(buf, body, body_ctx, preproc, split_ctx=True)
                buf.rstrip()

                # Emit the field header
                buf.append("\n")

            buf.append("\n")

        case nodes.option_list():
            # Render a docutils option list close to the standard
            # human-written form, e.g.:
            #
            # -a, --all  Description...
            #
            # -b FILE  Description...
            #
            # We do NOT try to reflow or otherwise "improve" the text; we
            # simply reconstruct from the doctree while keeping explicit
            # line breaks and indentation.

            for item in node.children:
                if not isinstance(item, nodes.option_list_item):
                    continue

                # Find option_group and description
                opt_group = None
                descr = None
                for child in item.children:
                    if isinstance(child, nodes.option_group):
                        opt_group = child
                    elif isinstance(child, nodes.description):
                        descr = child

                if opt_group is None or descr is None:
                    continue

                # Reconstruct the option label text, e.g. "-a, --all", "-b FILE"
                option_texts: list[str] = []
                for opt in opt_group.children:
                    if not isinstance(opt, nodes.option):
                        continue

                    # all option_string children: "-a", "--all"
                    parts = [
                        c.astext()
                        for c in opt.children
                        if isinstance(c, nodes.option_string)
                    ]

                    label = ", ".join(parts) if parts else ""

                    # optional argument, with its delimiter
                    arg_nodes = [
                        c for c in opt.children if isinstance(c, nodes.option_argument)
                    ]
                    if arg_nodes:
                        label = f"{label}{arg_nodes[0].astext()}"

                    option_texts.append(label)

                opt_label = ", ".join(option_texts)
                prefix = f"{ctx.head_prefix}{opt_label}  "

                descr_ctx = FmtCtx(
                    head_prefix=prefix,
                    tail_prefix=" " * len(prefix),
                    preserve_row_newlines=ctx.preserve_row_newlines,
                )
                ast_to_rst(buf, descr, descr_ctx, preproc)
            buf.append("\n")

        case nodes.description():
            children_to_rst(buf, node, ctx, preproc, split_ctx=True)
            buf.rstrip()
            buf.append("\n")

        case nodes.emphasis():
            text = node.astext()
            buf.append(f":emphasis:`{text}`" if node.get("role") else f"*{text}*")

        case nodes.strong():
            text = node.astext()
            buf.append(f":strong:`{text}`" if node.get("role") else f"**{text}**")

        case nodes.literal():
            text = node.astext()
            buf.append(f":literal:`{text}`" if node.get("role") else f"``{text}``")

        case XRefNode():
            text = node.astext().replace("<", "\\<")
            reftarget = node["reftarget"]
            if reftarget == node.astext():
                buf.append(f":{node['xref_role']}:`{text}`")
            else:
                buf.append(f":{node['xref_role']}:`{text} <{reftarget}>`")

        case nodes.reference():
            text = node.astext()
            if refuri := node.get("refuri"):
                # If the visible text is exactly the same as the target URL,
                # keep it as a bare URL instead of reST explicit link syntax.
                if text == refuri:
                    buf.append(refuri)
                else:
                    buf.append(f"`{text} <{refuri}>`_")
            else:
                if node.get("anonymous"):
                    buf.append(f"`{text}`__")
                else:
                    buf.append(f"`{text}`_")

        case nodes.citation_reference():
            # Render citations in standard reST form: [label]_
            label = node.astext()
            buf.append(f"[{label}]_")

        case nodes.citation():
            # A citation has a label (e.g. "Ref01") and one or more body nodes.
            # Render as ".. [Ref01] ..." with the body as indented content.
            label_nodes = [c for c in node.children if isinstance(c, nodes.label)]
            body_children = [c for c in node.children if not isinstance(c, nodes.label)]

            if label_nodes:
                label_text = label_nodes[0].astext()
            else:
                # Fallback: try first name or id if no explicit label node exists
                label_text = (
                    node["names"][0]
                    if node.get("names")
                    else node["ids"][0]
                    if node.get("ids")
                    else ""
                )

            # Start the citation; body is indented by 3 spaces
            buf.append(f"{ctx.head_prefix}.. [{label_text}] ")

            if not body_children:
                buf.append("\n\n")
            else:
                # First child is rendered starting on the same line; if it's a
                # paragraph we strip its final blank line.
                first_ctx = ctx.with_tail_indent(ctx.tail_prefix + "   ")
                ast_to_rst(buf, body_children[0], first_ctx, preproc)

                # ast_to_rst(paragraph) ends with "\n\n"; keep only one newline
                buf.rstrip()
                buf.append("\n")

                # Remaining children (e.g. additional paragraphs) follow,
                # all fully indented.
                for child in body_children[1:]:
                    ast_to_rst(buf, child, first_ctx, preproc)

                # Ensure a blank line after the citation block
                buf.rstrip()
                buf.append("\n\n")

        case nodes.footnote_reference():
            # Render footnote references as [#label]_
            # node.astext() is the visible label (e.g. "1")
            label = node.astext() or node.get("refid") or "#"
            buf.append(f"[{label}]_")

        case nodes.footnote():
            # Determine label: prefer explicit label child, than auto, then "names",
            # then "ids"
            label = None
            for child in node.children:
                if isinstance(child, nodes.label):
                    label = child.astext()
                    break
            if label is None:
                if node.get("auto") == 1:
                    label = "#"
                elif names := node.get("names"):
                    label = names[0]
                elif ids := node.get("ids"):
                    label = ids[0]
                else:
                    # Fallback if everything else fails
                    label = "#"

            # Body children = everything except the label node
            body_children = [c for c in node.children if not isinstance(c, nodes.label)]

            # Render body with indentation under the footnote directive
            buf.append(f".. [{label}] ")
            if body_children:
                # First child rendered directly after the marker
                first = body_children[0]
                # Reuse paragraph/list/etc. rendering, but adjusted indentation
                # We want content starting right after the marker on the same line
                if isinstance(first, nodes.paragraph):
                    # Inline the paragraph text
                    children_to_rst(buf, first, ctx, preproc)
                    # children_to_rst for a paragraph adds "\n\n" at the end; strip it
                    buf.rstrip()
                    buf.append("\n")
                else:
                    # Non‑paragraph: put a newline and indent as a block
                    buf.append("\n")
                    body_ctx = ctx.with_indent("   ")
                    for child in body_children:
                        ast_to_rst(buf, child, body_ctx, preproc)
            else:
                buf.append("\n")

            parent = node.parent
            assert isinstance(parent, nodes.Element)
            pc = parent.children
            idx = pc.index(node)
            if idx + 1 >= len(pc) or not isinstance(pc[idx + 1], nodes.footnote):
                buf.append("\n")

        case nodes.line_block():
            # Top-level indent for this line block
            for i, child in enumerate(node.children):
                prefix = ctx.head_prefix if i == 0 else f"\n{ctx.tail_prefix}"
                match child:
                    case nodes.line():
                        [child] = child.children
                        buf.append(f"{prefix}| ")
                        ast_to_rst(buf, child, ctx, preproc)
                    case nodes.line_block():
                        # Nested line block: increase indent under current base_prefix
                        nested_ctx = ctx.with_indent("   ")
                        buf.append(prefix)
                        ast_to_rst(buf, child, nested_ctx, preproc)
                    case _:
                        raise RuntimeError(f"Invalid line block child: {child}")
            buf.append("\n")

        case nodes.definition_list():
            # A definition list is rendered as:
            #
            # term 1
            #    Definition...
            #
            # term 2
            #    Definition...
            #
            first = True
            for item in node.children:
                if not isinstance(item, nodes.definition_list_item):
                    continue
                if not first:
                    buf.append("\n")  # blank line between items
                first = False
                ast_to_rst(buf, item, ctx, preproc)
            buf.append("\n")

        case nodes.definition_list_item():
            # Expected children: term, definition
            term_nodes = [c for c in node.children if isinstance(c, nodes.term)]
            def_nodes = [c for c in node.children if isinstance(c, nodes.definition)]

            # Term on its own line (no indentation)
            for i, term in enumerate(term_nodes):
                buf.append(ctx.prefix(i))
                children_to_rst(buf, term, ctx, preproc)
                buf.rstrip()
                buf.append("\n")

            # Definitions, indented by 3 spaces as standard in reST
            def_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
            for d in def_nodes:
                ast_to_rst(buf, d, def_ctx, preproc)
                buf.rstrip()
                buf.append("\n")

        case nodes.term() | nodes.definition():
            # Just the children
            children_to_rst(buf, node, ctx, preproc)

        case nodes.Text():
            clean = node.astext().replace("\n", " ")
            clean = re.sub(space_re, " ", clean)

            sclean = clean.rstrip()
            rclean = sclean.replace(". ", f".\n{ctx.tail_prefix}")
            rclean += clean[len(sclean) :]
            buf.append(rclean)

        case TocTreeNode():
            buf.append(".. toctree::\n")

            if (maxdepth := node.get("maxdepth")) is not None:
                buf.append(f"   :maxdepth: {maxdepth}\n")
            if caption := node.get("caption"):
                buf.append(f"   :caption: {caption}\n")
            if node.get("glob"):
                buf.append("   :glob:\n")
            if node.get("hidden"):
                buf.append("   :hidden:\n")
            if node.get("includehidden"):
                buf.append("   :includehidden:\n")

            numbered = node.get("numbered")
            if numbered not in (None, False):
                if numbered is True:
                    buf.append("   :numbered:\n")
                else:
                    buf.append(f"   :numbered: {numbered}\n")

            if node.get("titlesonly"):
                buf.append("   :titlesonly:\n")

            buf.append("\n")

            for entry in node.get("entries", ()):
                buf.append(f"   {entry}\n")

            buf.append("\n")

        case (
            DoxyClassNode()
            | DoxyConceptNode()
            | DoxyFunctionNode()
            | DoxyTypedefNode()
            | DoxyStructNode()
        ):
            buf.append(f".. {node.directive}:: ")
            buf.append(node.get("name", ""))
            buf.append("\n")
            _render_doxygen_classlike_options(node, buf)
            if node.get("newline", True):
                buf.append("\n")

        case DoxyVariableNode():
            buf.append(".. doxygenvariable:: ")
            buf.append(node.get("name", ""))
            buf.append("\n")

            if path := node.get("path"):
                buf.append(f"   :path: {path}\n")
            if project := node.get("project"):
                buf.append(f"   :project: {project}\n")
            if node.get("outline"):
                buf.append("   :outline:\n")
            if node.get("no-link"):
                buf.append("   :no-link:\n")

            buf.append("\n")

        case CppNode():
            buf.append(f".. {node['cpp_directive']}:: {node['cpp_signature']}\n")
            if node.children:
                buf.append("\n")
            children_to_rst(buf, node, ctx.with_indent("   "), preproc)
            buf.rstrip()
            if node.children:
                buf.append("\n")
            buf.append("\n")

        case CurrentModuleNode():
            buf.append(f".. currentmodule:: {node['module']}\n\n")

        case nodes.math():
            buf.append(f":math:`{node.astext()}`")

        case nodes.table():
            source_format = node.get("source_format")

            if source_format == "list-table":
                # Render as a .. list-table:: directive instead of grid table
                buf.append(f"{ctx.head_prefix}.. list-table::\n")

                header_row_num = node.get("header_rows")
                if header_row_num is not None:
                    assert isinstance(header_row_num, int)
                    buf.append(f"{ctx.tail_prefix}   :header-rows: {header_row_num}\n")

                widths = node.get("widths")
                if widths is not None:
                    if not isinstance(widths, str):
                        assert isinstance(widths, list)
                        widths = " ".join(str(w) for w in widths)
                    buf.append(f"{ctx.tail_prefix}   :widths: {widths}\n")

                buf.append("\n")

                # Get any captured blank-line info
                row_blank_lines: list[int] = node.get("row_blank_lines") or []

                tgroups = [c for c in node.children if isinstance(c, nodes.tgroup)]
                if tgroups:
                    tgroup = tgroups[0]

                    # Collect rendered rows as strings
                    rendered_rows: list[str] = []

                    for part in tgroup.children:
                        if isinstance(part, nodes.colspec):
                            continue
                        if not isinstance(part, (nodes.thead, nodes.tbody)):
                            raise RuntimeError(f"Expected thead or tbody, got {part}")

                        for row in part.children:
                            if not isinstance(row, nodes.row):
                                raise RuntimeError(f"Expected row, got {row}")

                            entries = [
                                e.children[0]
                                for e in row.children
                                if isinstance(e, nodes.entry)
                            ]

                            row_buf: list[str] = []

                            if entries:
                                cell_ctx = ctx.with_list_prefix("   * - ")
                                ast_to_rst(buf, entries[0], cell_ctx, preproc)
                                buf.rstrip()
                                buf.append("\n")
                            else:
                                row_buf.append("\n")

                            for entry in entries[1:]:
                                cell_ctx = ctx.with_list_prefix("     - ")
                                ast_to_rst(buf, entry, cell_ctx, preproc)
                                buf.rstrip()
                                buf.append("\n")

                            rendered_rows.append("".join(row_buf))

                    # Emit rows, inserting extra blank lines according to
                    # row_blank_lines that we captured in MarkingListTable.
                    for idx, row_text in enumerate(rendered_rows):
                        buf.append(row_text)
                        # Between rows only; no extra after the last one
                        if (
                            ctx.preserve_row_newlines
                            and idx < len(rendered_rows) - 1
                            and idx < len(row_blank_lines)
                        ):
                            buf.append("\n" * row_blank_lines[idx])
            elif source_format == "grid-table":
                # Reconstruct .. table:: wrapper and delegate grid body
                tiles = [
                    child for child in node.children if isinstance(child, nodes.title)
                ]
                if tiles:
                    [title] = tiles
                    buf.append(f"{ctx.head_prefix}.. table:: {title.astext()}\n")
                else:
                    buf.append(f"{ctx.head_prefix}.. table::\n")

                grid_widths = node.get("grid_widths")
                if grid_widths is not None:
                    if isinstance(grid_widths, (list, tuple)):
                        w_str = " ".join(str(w) for w in grid_widths)
                    else:
                        w_str = str(grid_widths)
                    buf.append(f"{ctx.tail_prefix}   :widths: {w_str}\n")
                buf.append("\n")

                # Reuse generic grid renderer for the inner table
                inner_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
                _render_grid_table(buf, node, inner_ctx, preproc)

            else:
                _render_grid_table(buf, node, ctx, preproc)

        case (
            nodes.tgroup()
            | nodes.colspec()
            | nodes.thead()
            | nodes.tbody()
            | nodes.row()
            | nodes.entry()
        ):
            raise RuntimeError(
                f"Table node {node} should be handled through a table node!"
            )

        case nodes.image():
            # Basic required attribute: uri (path or URL)
            uri = node.get("uri", "")

            # Start directive
            buf.append(f"{ctx.head_prefix}.. image:: {uri}\n")

            # Collect common options if present
            def _opt(name: str, opt_name: str | None = None) -> None:
                val = node.get(name)
                if val is not None:
                    buf.append(f"{ctx.tail_prefix}   :{opt_name or name}: {val}\n")

            # Standard image options
            _opt("alt")
            _opt("height")
            _opt("width")
            _opt("scale")
            _opt("align")
            _opt("target")

            # A blank line after the directive
            buf.append("\n")

        case nodes.admonition():
            # Generic admonition with an explicit title
            # The first child is optionally a title node.
            if node.children and isinstance(node.children[0], nodes.title):
                title_text = node.children[0].astext()
            else:
                # Fallback if title is missing/unusual
                title_text = node.get("title", "Note")

            _render_admonition(buf, node, ctx, "admonition", preproc, title=title_text)

        case (
            nodes.attention()
            | nodes.caution()
            | nodes.danger()
            | nodes.error()
            | nodes.important()
            | nodes.note()
            | nodes.tip()
            | nodes.hint()
            | nodes.warning()
        ):
            _render_admonition(buf, node, ctx, node.tagname, preproc)

        case nodes.section():
            children_to_rst(buf, node, ctx, preproc)
            buf.rstrip()
            buf.append("\n\n")

        case nodes.target():
            labels: list[str] = []
            if ids := node.get("ids"):
                assert isinstance(ids, list)
                for id in ids:
                    assert isinstance(id, str)
                    if label := preproc.collected_labels.get(id):
                        labels.append(label)
            if labels:
                [label] = labels
                buf.append(f".. _{label}:\n\n")
                return
            if node.get("anonymous"):
                if refuri := node.get("refuri"):
                    buf.append(f"__ {refuri}\n\n")
                    return
            children_to_rst(buf, node, ctx, preproc)

        case nodes.substitution_definition():
            # Pick the first name as the substitution name
            names = node.get("names") or []
            name = names[0] if names else ""

            # Render the body using existing machinery
            # Substitutions are inline, so we don’t want trailing blank lines
            body = Buffer()
            children_to_rst(body, node, ctx, preproc)
            body.rstrip("\n")

            # Emit the standard reST form:
            # .. |name| replace:: body
            buf.append(f"{ctx.head_prefix}.. |{name}| replace:: {body}\n\n")

        case nodes.substitution_reference():
            # Re‑emit substitution references like |name|
            # Use refname when present, otherwise fall back to the visible text.
            name = node.get("refname") or node.astext()
            buf.append(f"|{name}|")

        case nodes.system_message():
            print(node)
            if node["type"] not in {"INFO"}:
                raise RuntimeError("Non-INFO system message!")

        case _:
            raise RuntimeError(f"Unknown node type: {type(node)} {node}")


def _render_doxygen_classlike_options(node: DoxyNode, buf: Buffer) -> None:
    """Render options common to class/struct/interface directives."""
    if path := node.get("path"):
        buf.append(f"   :path: {path}\n")
    if project := node.get("project"):
        buf.append(f"   :project: {project}\n")
    if (members := node.get("members")) is not None:
        suffix = f" {members}" if members else ""
        buf.append(f"   :members:{suffix}\n")
    if (membergroups := node.get("membergroups")) is not None:
        buf.append(f"   :membergroups: {membergroups}\n")
    if node.get("members-only"):
        buf.append("   :members-only:\n")
    if node.get("protected-members"):
        buf.append("   :protected-members:\n")
    if node.get("private-members"):
        buf.append("   :private-members:\n")
    if node.get("undoc-members"):
        buf.append("   :undoc-members:\n")
    if (show := node.get("show")) is not None:
        buf.append(f"   :show: {show}\n")
    if node.get("outline"):
        buf.append("   :outline:\n")
    if node.get("no-link"):
        buf.append("   :no-link:\n")
    if node.get("allow-dot-graphs"):
        buf.append("   :allow-dot-graphs:\n")


def _split_table_rows(tgroup: nodes.tgroup) -> list[list[nodes.entry]]:
    """Collect rows as lists of entries, ignoring colspec details."""
    rows: list[list[nodes.entry]] = []
    for part in tgroup.children:
        if isinstance(part, (nodes.thead, nodes.tbody)):
            for row in part.children:
                if isinstance(row, nodes.row):
                    row_entries = [
                        e for e in row.children if isinstance(e, nodes.entry)
                    ]
                    rows.append(row_entries)
    return rows


def _entry_text(entry: nodes.entry, ctx: FmtCtx, preproc: PreprocessInfo) -> str:
    # Render children as RST, then strip extra blank lines
    raw = Buffer()
    children_to_rst(raw, entry, ctx, preproc)
    # Remove paragraph-level extra spacing (two newlines) for table cells
    lines: list[str] = []
    for line in raw.data.splitlines():
        if line.strip() == "":
            # omit empty lines inside cells to keep tables compact
            continue
        lines.append(line.rstrip())
    return "\n".join(lines) if lines else ""


def _compute_column_widths(
    rows: list[list[nodes.entry]],
    ctx: FmtCtx,
    preproc: PreprocessInfo,
) -> list[int]:
    """Compute minimal column widths based on textual content."""
    if not rows:
        return []

    ncols = max(len(r) for r in rows)
    widths = [0] * ncols

    for row in rows:
        for i, entry in enumerate(row):
            text = _entry_text(entry, ctx, preproc)
            col_width = max(len(line) for line in text.splitlines()) if text else 0
            widths[i] = max(widths[i], col_width)

    # Ensure each column has at least width 1
    return [max(w, 1) for w in widths]


def _separate_header_body(
    tgroup: nodes.tgroup,
) -> tuple[list[list[nodes.entry]], list[list[nodes.entry]]]:
    rows = _split_table_rows(tgroup)
    theads = [c for c in tgroup.children if isinstance(c, nodes.thead)]

    header_rows: list[list[nodes.entry]] = []
    if theads:
        r: list[list[nodes.entry]] = []
        for row in theads[0].children:
            if isinstance(row, nodes.row):
                r.append([e for e in row.children if isinstance(e, nodes.entry)])
        header_rows = r

    body_rows = rows[len(header_rows) :] if header_rows else rows
    return header_rows, body_rows


def _render_grid_table(
    buf: Buffer,
    node: nodes.table,
    ctx: FmtCtx,
    preproc: PreprocessInfo,
) -> None:
    tgroups = [c for c in node.children if isinstance(c, nodes.tgroup)]
    if not tgroups:
        children_to_rst(buf, node, ctx, preproc)
        buf.append("\n")
        return

    clean_ctx = FmtCtx(
        head_prefix="",
        tail_prefix="",
        preserve_row_newlines=ctx.preserve_row_newlines,
    )

    tgroup = tgroups[0]
    rows = _split_table_rows(tgroup)
    widths = _compute_column_widths(rows, clean_ctx, preproc)
    border = ctx.tail_prefix + _render_table_border(widths)

    header_rows, body_rows = _separate_header_body(tgroup)

    buf.append(border)

    if header_rows:
        for row in header_rows:
            texts = [_entry_text(e, clean_ctx, preproc) for e in row]
            while len(texts) < len(widths):
                texts.append("")
            buf.append(ctx.tail_prefix + _render_table_row(texts, widths))
        buf.append(ctx.tail_prefix + _render_table_border(widths, below_header=True))

    for row in body_rows:
        texts = [_entry_text(e, clean_ctx, preproc) for e in row]
        while len(texts) < len(widths):
            texts.append("")
        buf.append(ctx.tail_prefix + _render_table_row(texts, widths))
        buf.append(ctx.tail_prefix + _render_table_border(widths))

    buf.append("\n")


def _render_table_border(widths: list[int], below_header: bool = False) -> str:
    # +-----+---+------+ style
    parts = ["+"]
    char = "=" if below_header else "-"
    for w in widths:
        parts.append(char * (w + 2))
        parts.append("+")
    return "".join(parts) + "\n"


def _render_table_row(cells: list[str], widths: list[int]) -> str:
    """
    Render a single logical row that may have multiline cells.

    `cells` is list of already-prepared text for each cell.
    """
    # Split each cell into lines
    split_cells: list[list[str]] = []
    for text in cells:
        cell_lines = text.splitlines() if text else [""]
        split_cells.append(cell_lines)

    # Determine how many physical lines this row will have
    max_lines = max(len(c) for c in split_cells) if split_cells else 0

    out_lines: list[str] = []
    for line_idx in range(max_lines):
        parts = ["|"]
        for col_idx, width in enumerate(widths):
            cell_lines = split_cells[col_idx] if col_idx < len(split_cells) else [""]
            line_text = cell_lines[line_idx] if line_idx < len(cell_lines) else ""
            parts.append(" " + line_text.ljust(width) + " ")
            parts.append("|")
        out_lines.append("".join(parts) + "\n")
    return "".join(out_lines)


def _render_admonition(
    buf: Buffer,
    node: nodes.Element,
    ctx: FmtCtx,
    kind: str,
    preproc: PreprocessInfo,
    *,
    title: str | None = None,
) -> None:
    # kind is e.g. "note", "warning", or "admonition"
    if title is not None:
        buf.append(f"{ctx.head_prefix}.. {kind}:: {title}\n\n")
    else:
        buf.append(f"{ctx.head_prefix}.. {kind}::\n\n")

    body_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
    for child in node.children:
        # skip the explicit title node for generic admonitions,
        # the title is already rendered on the directive line
        if isinstance(child, nodes.title):
            continue
        ast_to_rst(buf, child, body_ctx, preproc)

    buf.rstrip()
    buf.append("\n\n")


label_re: Final = re.compile(r"^\s*\.\.\s+_([^:]+):\s*$")


def collect_labels(src: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in src.splitlines():
        m = label_re.match(line)
        if not m:
            continue
        raw = m.group(1)
        # Run docutils’ own normalization so you get the same id
        norm = nodes.make_id(nodes.fully_normalize_name(raw))
        mapping[norm] = raw
    return mapping


def make_auto_list_transform(src: list[str]) -> type[transforms.Transform]:
    @final
    class AutoList(transforms.Transform):
        default_priority = 340

        def apply(self) -> None:
            for target in self.document.findall(nodes.enumerated_list):
                for c in target.children:
                    assert isinstance(c, nodes.list_item)
                    line = c.line
                    assert line
                    c["auto"] = src[line - 1].lstrip().startswith("#")

    return AutoList


@final
class NoSubstitutionReader(readers.Reader):  # pyright: ignore[reportMissingTypeArgument]
    def __init__(self, src: str) -> None:
        super().__init__()
        self.src = src.splitlines()

    @override
    def get_transforms(self) -> list[type[transforms.Transform]]:
        # Get the default transforms
        # transforms = list(super().get_transforms())
        # Filter out the Substitutions transform
        # transforms = [
        #     t for t in transforms if t is not Substitutions and t is not Footnotes
        # ]
        return [DocTitle, DocInfo, make_auto_list_transform(self.src)]


def format_rst(rst_source: str, *, clean: bool = True):
    doctree: nodes.document = core.publish_doctree(
        rst_source,
        reader=NoSubstitutionReader(src=rst_source),
    )

    buf = Buffer()
    ast_to_rst(
        buf,
        doctree,
        FmtCtx(preserve_row_newlines=not clean),
        PreprocessInfo(collected_labels=collect_labels(rst_source)),
    )
    return buf.data
