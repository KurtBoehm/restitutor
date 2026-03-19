# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from argparse import ArgumentParser
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, ClassVar, Final, final, override

from docutils import nodes
from docutils.core import publish_doctree
from docutils.parsers.rst import Directive, directives, languages, roles
from docutils.parsers.rst.directives.tables import ListTable
from docutils.parsers.rst.states import Inliner

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


def int_or_nothing(argument: str | None) -> int:
    return 999 if not argument else int(argument)


class TocTreeNode(nodes.General, nodes.Element):
    """Node for inserting a TOC tree."""


class _BaseDoxyNode(nodes.General, nodes.Element):
    """Base type for Doxy nodes."""


@final
class DoxyClassNode(_BaseDoxyNode):
    directive = "doxygenclass"


@final
class DoxyConceptNode(_BaseDoxyNode):
    directive = "doxygenconcept"


@final
class DoxyFunctionNode(_BaseDoxyNode):
    directive = "doxygenfunction"


@final
class DoxyStructNode(_BaseDoxyNode):
    directive = "doxygenstruct"


@final
class DoxyTypedefNode(_BaseDoxyNode):
    directive = "doxygentypedef"


@final
class DoxyVariableNode(_BaseDoxyNode):
    directive = "doxygenvariable"


type DoxyNode = (
    DoxyClassNode
    | DoxyConceptNode
    | DoxyFunctionNode
    | DoxyStructNode
    | DoxyTypedefNode
    | DoxyVariableNode
)


@final
class CurrentModuleNode(nodes.General, nodes.Element):
    """A Sphinx-style currentmodule directive."""


@final
class TocTreeDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "maxdepth": int,
        "name": directives.unchanged,
        "class": directives.class_option,
        "caption": directives.unchanged_required,
        "glob": directives.flag,
        "hidden": directives.flag,
        "includehidden": directives.flag,
        "numbered": int_or_nothing,
        "titlesonly": directives.flag,
        "reversed": directives.flag,
    }

    @override
    def run(self) -> list[nodes.Node]:
        node = TocTreeNode(
            maxdepth=self.options.get("maxdepth"),
            caption=self.options.get("caption"),
            glob="glob" in self.options,
            hidden="hidden" in self.options,
            includehidden="includehidden" in self.options,
            numbered=self.options.get("numbered"),
            titlesonly="titlesonly" in self.options,
            # Store the raw entries from the directive content
            entries=list(self.content),
        )
        self.add_name(node)
        return [node]


class _BaseDoxyDirective(Directive):
    """
    Shared run() logic for doxygen directives.

    Subclasses must define:
      - node: type[DoxyNode]
      - required_arguments / optional_arguments / option_spec / has_content
    """

    node: ClassVar[type[DoxyNode]]
    required_arguments: ClassVar[int]
    optional_arguments: ClassVar[int]
    has_content: ClassVar[bool]
    final_argument_whitespace: ClassVar[bool] = True

    @override
    def run(self) -> list[nodes.Node]:
        node = self.node(**self.options)
        node["name"] = " ".join(self.arguments)
        node["newline"] = self.block_text.endswith("\n")
        return [node]


class _DoxyBaseItemDirective(_BaseDoxyDirective):
    required_arguments: ClassVar[int] = 1
    optional_arguments: ClassVar[int] = 1
    option_spec = {
        "path": directives.unchanged_required,
        "project": directives.unchanged_required,
        "outline": directives.flag,
        "no-link": directives.flag,
    }
    has_content: ClassVar[bool] = False


class _DoxyClassLikeDirective(_BaseDoxyDirective):
    required_arguments: ClassVar[int] = 1
    optional_arguments: ClassVar[int] = 0
    option_spec = {
        "path": directives.unchanged_required,
        "project": directives.unchanged_required,
        "members": directives.unchanged,
        "membergroups": directives.unchanged_required,
        "members-only": directives.flag,
        "protected-members": directives.flag,
        "private-members": directives.flag,
        "undoc-members": directives.flag,
        "show": directives.unchanged_required,
        "outline": directives.flag,
        "no-link": directives.flag,
        "allow-dot-graphs": directives.flag,
    }
    has_content: ClassVar[bool] = False


@final
class DoxyClassDirective(_DoxyClassLikeDirective):
    node = DoxyClassNode


@final
class DoxyConceptDirective(_DoxyBaseItemDirective):
    node = DoxyConceptNode


@final
class DoxyFunctionDirective(_DoxyBaseItemDirective):
    node = DoxyFunctionNode


@final
class DoxyStructDirective(_DoxyClassLikeDirective):
    node = DoxyStructNode


@final
class DoxyTypedefDirective(_DoxyBaseItemDirective):
    node = DoxyTypedefNode


@final
class DoxyVariableDirective(_DoxyBaseItemDirective):
    node = DoxyVariableNode


type DoxyDirective = (
    DoxyClassDirective
    | DoxyConceptDirective
    | DoxyFunctionDirective
    | DoxyStructDirective
    | DoxyTypedefDirective
    | DoxyVariableDirective
)


@final
class CurrentModuleDirective(Directive):
    has_content = False
    required_arguments = 1  # the module name
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    @override
    def run(self) -> list[nodes.Node]:
        node = CurrentModuleNode()
        node["module"] = self.arguments[0]
        return [node]


type XRefTuple = tuple[Sequence[nodes.reference], Sequence[nodes.reference]]
type RoleFn = Callable[
    [str, str, str, int, Inliner, Mapping[str, Any], Sequence[str]],
    XRefTuple,
]


class XRefNode(nodes.reference):
    pass


title_target_re: Final = re.compile("(.*?)(?<!\x00)<(.*?)>\\s*$")


def _make_xref_role(role: str) -> RoleFn:
    """
    Create a role function that mimics Sphinx’s cross-reference behavior
    for a single role, e.g. :func:, :class:, :mod:, etc.
    """

    def role_fn(
        role_name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        options: Mapping[str, Any] | None = None,
        content: Sequence[str] | None = None,
    ) -> XRefTuple:
        from docutils.utils import unescape

        m = title_target_re.match(text)
        if m:
            # "title <target>" form
            title, target = m.groups()
            assert isinstance(title, str) and isinstance(target, str)
        else:
            title = target = text
        title, target = unescape(title).strip(), unescape(target).strip()

        node = XRefNode(text, title)
        node["reftarget"] = target
        node["xref_role"] = role

        return [node], []

    return role_fn


def _register_sphinx_text_roles() -> None:
    lang = languages.get_language("en")

    # Python domain roles
    for role in ("func", "meth", "class", "exc", "attr", "data", "mod", "obj"):
        roles.register_canonical_role(role, _make_xref_role(role))
        roles.register_canonical_role(f"cpp:{role}", _make_xref_role(f"cpp:{role}"))
        lang.roles.setdefault(role, role)

    # Common "std" roles
    for role in ("ref", "doc", "term", "envvar"):
        roles.register_canonical_role(role, _make_xref_role(role))
        lang.roles.setdefault(role, role)


# Register directives with docutils
directives.register_directive("toctree", TocTreeDirective)
doxys: list[type[DoxyDirective]] = [
    DoxyClassDirective,
    DoxyConceptDirective,
    DoxyFunctionDirective,
    DoxyStructDirective,
    DoxyTypedefDirective,
    DoxyVariableDirective,
]
for directive in doxys:
    directives.register_directive(directive.node.directive, directive)
directives.register_directive("currentmodule", CurrentModuleDirective)
_register_sphinx_text_roles()


class MarkingListTable(ListTable):
    @override
    def run(self):
        result = super().run()
        for node in result:
            if isinstance(node, nodes.table):
                node["source_format"] = "list-table"
                node["header_rows"] = self.options.get("header-rows")
                node["widths"] = self.options.get("widths")
                node["row_blank_lines"] = self._compute_row_blank_lines()
        return result

    def _compute_row_blank_lines(self) -> list[int]:
        """
        Inspect the directive body (``self.content``) and derive how many *blank*
        lines separated each top-level list-table row in the original source.

        Returns a list of length ``(num_rows - 1)``; element ``i`` is the number of
        blank lines that were between row ``i`` and row ``i + 1`` (only trailing
        blanks at the end of row ``i`` are counted).
        """
        # self.content is a StringList, treat it as a list of strings.
        lines = list(self.content)

        # The start of a row is a line that begins with `* -` ignoring leading spaces.
        row_line_indices: list[int] = []
        for idx, line in enumerate(lines):
            if line.lstrip().startswith("* -"):
                row_line_indices.append(idx)

        if len(row_line_indices) < 2:
            return []

        blank_counts: list[int] = []
        for i in range(len(row_line_indices) - 1):
            start = row_line_indices[i]
            nxt = row_line_indices[i + 1]
            segment = lines[start + 1 : nxt]

            trailing_blanks = 0
            for line in reversed(segment):
                if line.strip():
                    break
                trailing_blanks += 1

            blank_counts.append(trailing_blanks)

        return blank_counts


# Register this instead of the built-in
directives.register_directive("list-table", MarkingListTable)


@dataclass(kw_only=True)
class FmtCtx:
    """
    Formatting context for ast_to_rst.

    - indent: indentation (spaces) for the *logical* line prefix
    - list_prefix: prefix for the current list item relative to indent
      (e.g. "- ", "* ", "1. ", "a) ")
    """

    head_prefix: str = ""
    tail_prefix: str = ""
    preserve_row_newlines: bool

    @property
    def empty(self) -> bool:
        return not self.head_prefix and not self.tail_prefix

    def with_indent(self, extra: str) -> FmtCtx:
        """Return a new context with increased indent (for child content)."""
        return FmtCtx(
            head_prefix=self.head_prefix + extra,
            tail_prefix=self.tail_prefix + extra,
            preserve_row_newlines=self.preserve_row_newlines,
        )

    def with_list_prefix(self, prefix: str) -> FmtCtx:
        """Return a new context for a list item at the same indent."""
        return FmtCtx(
            head_prefix=self.head_prefix + prefix,
            tail_prefix=self.tail_prefix + " " * len(prefix),
            preserve_row_newlines=self.preserve_row_newlines,
        )


def _children_to_rst(node: nodes.Node, ctx: FmtCtx) -> str:
    return "".join(ast_to_rst(child, ctx) for child in node.children)


def ast_to_rst(node: nodes.Node, ctx: FmtCtx) -> str:
    """Very simple doctree -> reST converter for a subset of nodes."""
    buf: list[str] = []

    match node:
        case nodes.document():
            text = _children_to_rst(node, ctx)
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
            buf.append(ctx.head_prefix + _children_to_rst(node, ctx) + "\n\n")

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
            content = _children_to_rst(node, ctx)
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
                # existing grid-table rendering you already wrote
                tgroups = [c for c in node.children if isinstance(c, nodes.tgroup)]
                if not tgroups:
                    # Empty or unusual table – just drop children
                    return _children_to_rst(node, ctx)

                tgroup = tgroups[0]
                rows = _split_table_rows(tgroup)
                widths = _compute_column_widths(rows, ctx)
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
                        texts = [_entry_text(e, ctx) for e in row]
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
                    texts = [_entry_text(e, ctx) for e in row]
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
                buf.append(ast_to_rst(child, body_ctx))

            # Ensure a blank line after the admonition block
            if not buf[-1].endswith("\n\n"):
                buf.append("\n")

        case nodes.section() | nodes.target():
            return _children_to_rst(node, ctx)

        case _:
            raise RuntimeError(f"Unknown node type: {type(node)} {node}")

    return "".join(buf)


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


def _entry_text(entry: nodes.entry, ctx: FmtCtx) -> str:
    # Render children as RST, then strip extra blank lines
    raw = _children_to_rst(entry, ctx.with_indent(""))
    # Remove paragraph-level extra spacing (two newlines) for table cells
    lines: list[str] = []
    for line in raw.splitlines():
        if line.strip() == "":
            # omit empty lines inside cells to keep tables compact
            continue
        lines.append(line.rstrip())
    return "\n".join(lines) if lines else ""


def _compute_column_widths(rows: list[list[nodes.entry]], ctx: FmtCtx) -> list[int]:
    """Compute minimal column widths based on textual content."""
    if not rows:
        return []

    ncols = max(len(r) for r in rows)
    widths = [0] * ncols

    for row in rows:
        for i, entry in enumerate(row):
            text = _entry_text(entry, ctx)
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


def _print_header(label: str) -> None:
    hashes = "#" * (len(label) + 2)
    print(f"{hashes}\n {label}\n{hashes}\n")


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("rst", type=Path, nargs="+")
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Rewrite the given .rst files in-place instead of printing",
    )
    parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="Normalize newlines",
    )
    args = parser.parse_args()
    rst_paths: list[Path] = args.rst
    in_place: bool = args.in_place
    clean: bool = args.clean

    for i, rst_path in enumerate(rst_paths):
        rst_source = rst_path.read_text(encoding="utf8")
        doctree: nodes.document = publish_doctree(rst_source)

        reconstructed = ast_to_rst(doctree, FmtCtx(preserve_row_newlines=not clean))

        if in_place:
            rst_path.write_text(reconstructed, encoding="utf8")
        else:
            if i:
                print()
            _print_header(str(rst_path))
            print(reconstructed)


if __name__ == "__main__":
    main()
