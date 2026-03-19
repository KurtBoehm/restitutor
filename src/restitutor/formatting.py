from __future__ import annotations

from docutils import nodes

from .context import FmtCtx
from .nodes import (
    CurrentModuleNode,
    DoxyClassNode,
    DoxyConceptNode,
    DoxyFunctionNode,
    DoxyStructNode,
    DoxyTypedefNode,
    DoxyVariableNode,
    DoxyNode,
    TocTreeNode,
    XRefNode,
)
from .tables import (
    compute_column_widths,
    entry_text,
    render_table_border,
    render_table_row,
    split_table_rows,
)

ADORNMENTS = ["#", "*", "=", "-", "^"]


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


def children_to_rst(node: nodes.Node, ctx: FmtCtx) -> str:
    return "".join(ast_to_rst(child, ctx) for child in node.children)


def ast_to_rst(node: nodes.Node, ctx: FmtCtx) -> str:
    """Very simple doctree -> reST converter for a subset of nodes."""
    buf: list[str] = []

    match node:
        case nodes.document():
            text = children_to_rst(node, ctx)
            # Single trailing newline, strip trailing spaces in the whole doc
            return "\n".join(part.rstrip() for part in (text,) if part.strip()) + "\n"

        case nodes.title():
            assert ctx.empty

            title_text = node.astext()

            level = -1
            curr: nodes.Node = node
            while isinstance(curr.parent, nodes.section):
                level += 1
                curr = curr.parent
            level = max(level, 0)

            adornment_char = ADORNMENTS[level] if level < len(ADORNMENTS) else '"'
            adornment = adornment_char * len(title_text)

            if level < 2:
                buf.append(f"{adornment}\n{title_text}\n{adornment}\n\n")
            else:
                buf.append(f"{title_text}\n{adornment}\n\n")

        case nodes.paragraph():
            buf.append(ctx.head_prefix + children_to_rst(node, ctx) + "\n\n")

        case nodes.literal_block():
            classes = node.get("classes", [])
            language = next((c for c in classes if c != "code"), None)

            text = node.astext()

            if language:
                buf.append(f"{ctx.head_prefix}.. code:: {language}\n\n")
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
                buf.append(ast_to_rst(child, item_ctx))
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
                buf.append(ast_to_rst(child, item_ctx))
            buf.append("\n")

        case nodes.list_item():
            content = children_to_rst(node, ctx)
            if content.endswith("\n\n"):
                content = content[:-1]
            buf.append(content)

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
                buf.append(f"`{text} <{refuri}>`_")
            else:
                buf.append(text)

        case nodes.line_block():
            # Top-level indent for this line block
            for i, child in enumerate(node.children):
                prefix = ctx.head_prefix if i == 0 else f"\n{ctx.tail_prefix}"
                match child:
                    case nodes.line():
                        [child] = child.children
                        buf.append(f"{prefix}| " + ast_to_rst(child, ctx))
                    case nodes.line_block():
                        # Nested line block: increase indent under current base_prefix
                        nested_ctx = ctx.with_indent("   ")
                        buf.append(prefix + ast_to_rst(child, nested_ctx))
                    case _:
                        raise RuntimeError(f"Invalid line block child: {child}")
            buf.append("\n")

        case nodes.Text():
            clean = node.astext().replace("\n", " ")
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
                                cell_txt = ast_to_rst(entries[0], cell_ctx)
                                if cell_txt.endswith("\n\n"):
                                    cell_txt = cell_txt[:-1]
                                row_buf.append(cell_txt)
                            else:
                                row_buf.append("\n")

                            for entry in entries[1:]:
                                cell_ctx = ctx.with_list_prefix("     - ")
                                cell_txt = ast_to_rst(entry, cell_ctx)
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
                    return children_to_rst(node, ctx)

                tgroup = tgroups[0]
                rows = split_table_rows(tgroup)
                widths = compute_column_widths(rows, ctx)
                border = ctx.tail_prefix + render_table_border(widths)

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
                        texts = [entry_text(e, ctx) for e in row]
                        # pad with empty cells if short
                        while len(texts) < len(widths):
                            texts.append("")
                        buf.append(ctx.tail_prefix + render_table_row(texts, widths))
                    # Header separator
                    buf.append(
                        ctx.tail_prefix + render_table_border(widths, below_header=True)
                    )

                # Body
                for row in body_rows:
                    texts = [entry_text(e, ctx) for e in row]
                    while len(texts) < len(widths):
                        texts.append("")
                    buf.append(ctx.tail_prefix + render_table_row(texts, widths))
                    buf.append(ctx.tail_prefix + render_table_border(widths))

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
                buf.append(ast_to_rst(child, body_ctx))

            # Ensure a blank line after the admonition block
            if not buf[-1].endswith("\n\n"):
                buf.append("\n")

        case nodes.section() | nodes.target():
            return children_to_rst(node, ctx)

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
