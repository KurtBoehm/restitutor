# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from docutils import nodes

from .context import FmtCtx
from .nodes import (
    ContentsNode,
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

adornments: Final[list[str]] = ["#", "*", "=", "-", "^"]
space_re: Final[re.Pattern[str]] = re.compile("\\s+")
admonition_map: Final[dict[type[nodes.Admonition], str]] = {
    nodes.note: "note",
    nodes.warning: "warning",
    nodes.tip: "tip",
    nodes.hint: "hint",
    nodes.caution: "caution",
    nodes.danger: "danger",
    nodes.error: "error",
    nodes.attention: "attention",
    nodes.important: "important",
}
bibliographic_map: Final[dict[type[nodes.Node], str]] = {
    nodes.author: "Author",
    nodes.organization: "Organization",
    nodes.contact: "Contact",
    nodes.version: "Version",
    nodes.revision: "Revision",
    nodes.status: "Status",
    nodes.date: "Date",
    nodes.copyright: "Copyright",
}


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
    node: nodes.Node,
    ctx: FmtCtx,
    preproc: PreprocessInfo,
    split_ctx: bool = False,
) -> str:
    if split_ctx:
        return "".join(
            ast_to_rst(child, ctx.ctx(i), preproc)
            for i, child in enumerate(node.children)
        )
    return "".join(ast_to_rst(child, ctx, preproc) for child in node.children)


@dataclass
class PreprocessInfo:
    collected_labels: dict[str, str]


def ast_to_rst(node: nodes.Node, ctx: FmtCtx, preproc: PreprocessInfo) -> str:
    """Very simple doctree -> reST converter for a subset of nodes."""
    buf: list[str] = []

    match node:
        case nodes.document():
            text = children_to_rst(node, ctx, preproc)
            # Single trailing newline, strip trailing spaces in the whole doc
            return "\n".join(part.rstrip() for part in (text,) if part.strip()) + "\n"

        case nodes.docinfo():
            width = max(len(bibliographic_map[type(child)]) for child in node.children)
            width += 2
            for child in node.children:
                key = f":{bibliographic_map[type(child)]}:"
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
            assert ctx.empty

            title_text = node.astext()

            level = -1
            curr: nodes.Node = node
            while isinstance(curr.parent, nodes.section):
                level += 1
                curr = curr.parent
            level = max(level, 0)

            adornment_char = adornments[level] if level < len(adornments) else '"'
            adornment = adornment_char * len(title_text)

            if level < 2:
                buf.append(f"{adornment}\n{title_text}\n{adornment}\n\n")
            else:
                buf.append(f"{title_text}\n{adornment}\n\n")

        case nodes.paragraph():
            buf.append(ctx.head_prefix + children_to_rst(node, ctx, preproc) + "\n\n")

        case nodes.literal_block():
            classes = node.get("classes", [])
            language = next((c for c in classes if c != "code"), None)

            text = node.astext()

            if language:
                directive = node.get("directive", "code")
                buf.append(f"{ctx.head_prefix}.. {directive}:: {language}\n\n")
            else:
                buf.append("::\n\n")

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
                buf.append(ast_to_rst(child, item_ctx, preproc))
            buf.append("\n")

        case nodes.enumerated_list():
            enumtype = node.attributes.get("enumtype", "arabic")
            start = int(node.attributes.get("start", 1))
            suffix = node.attributes.get("suffix") or "."

            for idx, child in enumerate(node.children, start=start):
                if enumtype == "loweralpha":
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
                buf.append(ast_to_rst(child, item_ctx, preproc))
            buf.append("\n")

        case nodes.list_item():
            content = children_to_rst(node, ctx, preproc, split_ctx=True)
            if content.endswith("\n\n"):
                content = content[:-1]
            buf.append(content)

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

                # Render body children with an extra indent
                body_ctx = ctx.with_tail_indent("   ")
                body_text = children_to_rst(body, body_ctx, preproc, split_ctx=True)
                body_text = body_text.rstrip()
                if body_text:
                    body_text = f" {body_text}"

                # Emit the field header
                buf.append(
                    f"{ctx.head_prefix}{field_name:<{max_name_width}}{body_text}\n"
                )

            buf.append("\n")

        case nodes.option_list():
            # Render a docutils option list in classic definition-like form.
            # Each child is an option_list_item with an option_group and a description.
            for idx, item in enumerate(node.children):
                if not isinstance(item, nodes.option_list_item):
                    continue

                # Find the option_group and description children
                opt_group = None
                descr = None
                for child in item.children:
                    if isinstance(child, nodes.option_group):
                        opt_group = child
                    elif isinstance(child, nodes.description):
                        descr = child

                if opt_group is None or descr is None:
                    continue

                # Collect rendered options (e.g. "-a", "--all", "-b FILE")
                option_texts: list[str] = []
                for opt in opt_group.children:
                    if not isinstance(opt, nodes.option):
                        continue

                    # option_string child (e.g. "-a", "--all")
                    opt_strings = [
                        c.astext()
                        for c in opt.children
                        if isinstance(c, nodes.option_string)
                    ]
                    base = ", ".join(opt_strings) if opt_strings else ""

                    # optional option_argument child (e.g. "FILE", "<src dest>")
                    arg_nodes = [
                        c for c in opt.children if isinstance(c, nodes.option_argument)
                    ]
                    if arg_nodes:
                        arg = arg_nodes[0]
                        delim = arg.get("delimiter", " ")
                        base = f"{base}{delim}{arg.astext()}"

                    option_texts.append(base)

                opt_label = ", ".join(option_texts)

                # Render description with indentation so it lines up under the label
                # Use a context with indent, but not list-prefix.
                descr_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
                descr_text = ast_to_rst(descr, descr_ctx, preproc).rstrip()

                # The description paragraphs rendered by ast_to_rst() already
                # have newlines. We want the usual “definition list–like” form:
                # "<options>  First line...\n<indent>More lines..."
                if "\n" in descr_text:
                    first_line, rest = descr_text.split("\n", 1)
                    buf.append(f"{ctx.head_prefix}{opt_label}  {first_line}\n")
                    if rest.strip():
                        # Subsequent lines should already be indented by descr_ctx
                        buf.append(rest + "\n")
                    else:
                        buf.append("\n")
                else:
                    buf.append(f"{ctx.head_prefix}{opt_label}  {descr_text}\n")

                # Blank line between option_list_items
                if idx != len(node.children) - 1:
                    buf.append("\n")

        case nodes.description():
            buf.append(children_to_rst(node, ctx, preproc))

        case nodes.emphasis():
            buf.append(f"*{node.astext()}*")

        case nodes.strong():
            buf.append(f"**{node.astext()}**")

        case nodes.literal():
            buf.append(f"``{node.astext()}``")

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
                first_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
                first_text = ast_to_rst(body_children[0], first_ctx, preproc)

                # ast_to_rst(paragraph) ends with "\n\n"; keep only one newline
                if first_text.endswith("\n\n"):
                    first_text = first_text[:-1]

                # If the first child is a paragraph, its text already starts
                # at the correct indent, so just append. Otherwise, ensure a
                # newline before the body.
                if isinstance(body_children[0], nodes.paragraph):
                    # Paragraph text already includes the head_prefix; we only
                    # need to drop the prefix we just wrote (".. [label] ").
                    # So we move its content to the next line, indented.
                    # Start with a newline, then the paragraph content.
                    buf.append("\n")
                    buf.append(first_text)
                else:
                    buf.append(first_text)

                # Remaining children (e.g. additional paragraphs) follow,
                # all fully indented.
                for child in body_children[1:]:
                    buf.append(ast_to_rst(child, first_ctx, preproc))

                # Ensure a blank line after the citation block
                if not buf[-1].endswith("\n\n"):
                    buf.append("\n")

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
                    text = children_to_rst(first, ctx, preproc).rstrip("\n")
                    # children_to_rst for a paragraph adds "\n\n" at the end; strip it
                    if text.endswith("\n"):
                        text = text.rstrip()
                    buf.append(text)
                    buf.append("\n")
                else:
                    # Non‑paragraph: put a newline and indent as a block
                    buf.append("\n")
                    body_ctx = ctx.with_indent("   ")
                    for child in body_children:
                        buf.append(ast_to_rst(child, body_ctx, preproc))
            else:
                buf.append("\n")

            buf.append("\n")

        case nodes.line_block():
            # Top-level indent for this line block
            for i, child in enumerate(node.children):
                prefix = ctx.head_prefix if i == 0 else f"\n{ctx.tail_prefix}"
                match child:
                    case nodes.line():
                        [child] = child.children
                        buf.append(f"{prefix}| " + ast_to_rst(child, ctx, preproc))
                    case nodes.line_block():
                        # Nested line block: increase indent under current base_prefix
                        nested_ctx = ctx.with_indent("   ")
                        buf.append(prefix + ast_to_rst(child, nested_ctx, preproc))
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
                buf.append(ast_to_rst(item, ctx, preproc))
            buf.append("\n")

        case nodes.definition_list_item():
            # Expected children: term, definition
            term_nodes = [c for c in node.children if isinstance(c, nodes.term)]
            def_nodes = [c for c in node.children if isinstance(c, nodes.definition)]

            # Term on its own line (no indentation)
            for i, term in enumerate(term_nodes):
                child_rst = children_to_rst(term, ctx, preproc).rstrip()
                buf.append(ctx.prefix(i) + child_rst + "\n")

            # Definitions, indented by 3 spaces as standard in reST
            def_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
            for d in def_nodes:
                content = ast_to_rst(d, def_ctx, preproc)
                if content.endswith("\n\n"):
                    content = content[:-1]
                buf.append(content)

        case nodes.term() | nodes.definition():
            # Just the children
            buf.append(children_to_rst(node, ctx, preproc))

        case nodes.Text():
            clean = node.astext().replace("\n", " ")
            clean = re.sub(space_re, " ", clean)
            buf.append(clean.replace(". ", f".\n{ctx.tail_prefix}"))

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

        case CurrentModuleNode():
            buf.append(f".. currentmodule:: {node['module']}\n\n")

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
                                cell_txt = ast_to_rst(entries[0], cell_ctx, preproc)
                                if cell_txt.endswith("\n\n"):
                                    cell_txt = cell_txt[:-1]
                                row_buf.append(cell_txt)
                            else:
                                row_buf.append("\n")

                            for entry in entries[1:]:
                                cell_ctx = ctx.with_list_prefix("     - ")
                                cell_txt = ast_to_rst(entry, cell_ctx, preproc)
                                if cell_txt.endswith("\n\n"):
                                    cell_txt = cell_txt[:-1]
                                row_buf.append(cell_txt)

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
            else:
                tgroups = [c for c in node.children if isinstance(c, nodes.tgroup)]
                if not tgroups:
                    # Empty or unusual table – just drop children
                    return children_to_rst(node, ctx, preproc)

                tgroup = tgroups[0]
                rows = _split_table_rows(tgroup)
                widths = _compute_column_widths(rows, ctx, preproc)
                border = ctx.tail_prefix + _render_table_border(widths)

                # Separate header (thead) from body if present
                thead = [c for c in tgroup.children if isinstance(c, nodes.thead)]

                def _rows_from_container(
                    container: nodes.Element,
                ) -> list[list[nodes.entry]]:
                    r: list[list[nodes.entry]] = []
                    for row in container.children:
                        if isinstance(row, nodes.row):
                            r.append(
                                [e for e in row.children if isinstance(e, nodes.entry)]
                            )
                    return r

                header_rows: list[list[nodes.entry]] = []
                body_rows: list[list[nodes.entry]] = []

                if thead:
                    header_rows = _rows_from_container(thead[0])
                # All other rows (including those in tbody) go to body
                body_rows = rows[len(header_rows) :] if header_rows else rows

                # Render table
                buf.append(border)

                # Header
                if header_rows:
                    for row in header_rows:
                        texts = [_entry_text(e, ctx, preproc) for e in row]
                        # pad with empty cells if short
                        while len(texts) < len(widths):
                            texts.append("")
                        buf.append(ctx.tail_prefix + _render_table_row(texts, widths))
                    # Header separator
                    buf.append(
                        ctx.tail_prefix
                        + _render_table_border(widths, below_header=True)
                    )

                # Body
                for row in body_rows:
                    texts = [_entry_text(e, ctx, preproc) for e in row]
                    while len(texts) < len(widths):
                        texts.append("")
                    buf.append(ctx.tail_prefix + _render_table_row(texts, widths))
                    buf.append(ctx.tail_prefix + _render_table_border(widths))

                buf.append("\n")

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
            # The first child is typically a title node.
            title_text = ""
            body_children: list[nodes.Node] = []

            if node.children and isinstance(node.children[0], nodes.title):
                title_text = node.children[0].astext()
                body_children = node.children[1:]
            else:
                # Fallback if title is missing/unusual
                title_text = node.get("title", "Note")
                body_children = list(node.children)

            # Directive line
            buf.append(f"{ctx.head_prefix}.. admonition:: {title_text}\n\n")

            # Body is indented under the directive
            body_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
            for child in body_children:
                buf.append(ast_to_rst(child, body_ctx, preproc))

            # Ensure a blank line after the admonition block
            if not buf[-1].endswith("\n\n"):
                buf.append("\n")

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
            # Look up the directive keyword based on the node’s class
            buf.append(f"{ctx.head_prefix}.. {admonition_map[type(node)]}::\n\n")

            body_ctx = ctx.with_indent(ctx.tail_prefix + "   ")
            for child in node.children:
                buf.append(ast_to_rst(child, body_ctx, preproc))

            if not buf[-1].endswith("\n\n"):
                buf.append("\n")

        case nodes.section():
            return children_to_rst(node, ctx, preproc)

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
                return f".. _{label}:\n\n"
            if node.get("anonymous"):
                if refuri := node.get("refuri"):
                    return f"__ {refuri}\n\n"
            return children_to_rst(node, ctx, preproc)

        case nodes.substitution_definition():
            # Pick the first name as the substitution name
            names = node.get("names") or []
            name = names[0] if names else ""

            # Render the body using existing machinery
            # Substitutions are inline, so we don’t want trailing blank lines
            body = children_to_rst(node, ctx, preproc).rstrip("\n")

            # Emit the standard reST form:
            # .. |name| replace:: body
            buf.append(f"{ctx.head_prefix}.. |{name}| replace:: {body}\n\n")

        case nodes.substitution_reference():
            # Re‑emit substitution references like |name|
            # Use refname when present, otherwise fall back to the visible text.
            name = node.get("refname") or node.astext()
            buf.append(f"|{name}|")

        case _:
            raise RuntimeError(f"Unknown node type: {type(node)} {node}")

    return "".join(buf)


def _render_doxygen_classlike_options(node: DoxyNode, buf: list[str]) -> None:
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
    # Import here to avoid circular import with formatting.ast_to_rst
    from .formatting import children_to_rst

    # Render children as RST, then strip extra blank lines
    raw = children_to_rst(entry, ctx, preproc)
    # Remove paragraph-level extra spacing (two newlines) for table cells
    lines: list[str] = []
    for line in raw.splitlines():
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
