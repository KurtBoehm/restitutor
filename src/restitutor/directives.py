# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar, Final, final, override

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.directives.body import CodeBlock
from docutils.parsers.rst.directives.tables import ListTable, RSTTable

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
)


def int_or_nothing(argument: str | None) -> int:
    """
    Convert an option string to an int, or return a large sentinel.

    :param argument: Raw option argument or ``None``.
    :return: Parsed integer or ``999`` if empty.
    """
    return 999 if not argument else int(argument)


class MarkingTable(RSTTable):
    """
    ``table`` directive that leaves reconstruction hints on the node.
    """

    @override
    def run(self) -> Sequence[nodes.table | nodes.system_message]:
        """
        Build the table and mark it as a grid-table source.

        :return: List containing the created table or a system message.
        """
        # Let the base class do all the hard work.
        [node] = super().run()
        assert isinstance(node, nodes.table)
        # Mark that this came from a ``.. table::`` directive.
        node["source_format"] = "grid-table"
        # Preserve options we care about (currently: widths).
        if "widths" in self.options:
            node["grid_widths"] = self.options["widths"]
        return [node]


class MarkingListTable(ListTable):
    """
    ``list-table`` directive that records layout metadata on the node.
    """

    @override
    def run(self) -> Sequence[nodes.table | nodes.system_message]:
        """
        Build the list-table and annotate it for later reconstruction.

        :return: Tables and possible system messages.
        """
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
        Count blank lines between list-table rows in the original text.

        :return: List of trailing blank-line counts per row boundary.
        """
        # self.content is a StringList: treat it as lines.
        lines = list(self.content)

        # The start of a row is a line beginning with ``* -``.
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


class RememberingCodeBlock(CodeBlock):
    """``code``/``code-block`` directive that remembers its own name."""

    @override
    def run(self) -> list[nodes.literal_block]:
        """
        Run the underlying code-block and tag the literal block.

        :return: Single literal block node.
        """
        [node] = super().run()
        assert isinstance(node, nodes.literal_block)
        node["directive"] = self.name
        return [node]


class ContentsDirective(Directive):
    """
    Lightweight ``contents`` directive capturing only a few options.
    """

    has_content: ClassVar[bool] = False
    option_spec = {
        "local": directives.flag,
        "depth": directives.nonnegative_int,
        "backlinks": directives.unchanged,
        "titlesonly": directives.flag,
    }

    @override
    def run(self) -> list[nodes.Node]:
        """
        Build a :class:`ContentsNode` with normalized options.

        :return: A list containing a single contents node.
        """
        node = ContentsNode(
            local="local" in self.options,
            depth=self.options.get("depth"),
            backlinks=self.options.get("backlinks"),
            titlesonly="titlesonly" in self.options,
        )
        return [node]


@final
class TocTreeDirective(Directive):
    """
    Simplified Sphinx-style ``toctree`` directive.
    """

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
        """
        Convert the directive into a :class:`TocTreeNode`.

        :return: A list containing a single toctree node.
        """
        node = TocTreeNode(
            maxdepth=self.options.get("maxdepth"),
            caption=self.options.get("caption"),
            glob="glob" in self.options,
            hidden="hidden" in self.options,
            includehidden="includehidden" in self.options,
            numbered=self.options.get("numbered"),
            titlesonly="titlesonly" in self.options,
            # Store the raw entries from the directive content.
            entries=list(self.content),
        )
        self.add_name(node)
        return [node]


class _BaseDoxyDirective(Directive):
    """
    Shared ``run()`` logic for Doxygen directives.

    Subclasses must define:

    * ``node``: :class:`type[DoxyNode]`
    * ``required_arguments``
    * ``optional_arguments``
    * ``option_spec``
    * ``has_content``
    """

    node: ClassVar[type[DoxyNode]]
    required_arguments: ClassVar[int]
    optional_arguments: ClassVar[int]
    has_content: ClassVar[bool]
    final_argument_whitespace: ClassVar[bool] = True

    @override
    def run(self) -> list[nodes.Node]:
        """
        Create a Doxygen node instance with common attributes.

        :return: List containing the created Doxy node.
        """
        node = self.node(**self.options)
        node["name"] = " ".join(self.arguments)
        node["newline"] = self.block_text.endswith("\n")
        return [node]


class _DoxyBaseItemDirective(_BaseDoxyDirective):
    """Base for simple Doxygen item directives (function, typedef, etc.)."""

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
    """Base for class-like Doxygen directives (class, struct)."""

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
    """``.. doxygenclass::`` directive."""

    node = DoxyClassNode


@final
class DoxyConceptDirective(_DoxyBaseItemDirective):
    """``.. doxygenconcept::`` directive."""

    node = DoxyConceptNode


@final
class DoxyFunctionDirective(_DoxyBaseItemDirective):
    """``.. doxygenfunction::`` directive."""

    node = DoxyFunctionNode


@final
class DoxyStructDirective(_DoxyClassLikeDirective):
    """``.. doxygenstruct::`` directive."""

    node = DoxyStructNode


@final
class DoxyTypedefDirective(_DoxyBaseItemDirective):
    """``.. doxygentypedef::`` directive."""

    node = DoxyTypedefNode


@final
class DoxyVariableDirective(_DoxyBaseItemDirective):
    """``.. doxygenvariable::`` directive."""

    node = DoxyVariableNode


type DoxyDirective = (
    DoxyClassDirective
    | DoxyConceptDirective
    | DoxyFunctionDirective
    | DoxyStructDirective
    | DoxyTypedefDirective
    | DoxyVariableDirective
)


class CppDirective(Directive):
    """
    Wrapper for Sphinx-style ``cpp:`` directives.

    Only preserves enough options to reconstruct source.
    """

    has_content: ClassVar[bool] = True
    required_arguments: ClassVar[int] = 1
    optional_arguments: ClassVar[int] = 0
    final_argument_whitespace: ClassVar[bool] = True
    option_spec = {
        # mirror commonly-used cpp: options enough to preserve them
        "noindex": directives.flag,
        "inline": directives.flag,
        "tparam-line-spec": directives.unchanged,
        "visibility": directives.unchanged,
        "name": directives.unchanged,
    }

    @override
    def run(self) -> list[nodes.Node]:
        """
        Create a :class:`CppNode` and parse nested content into it.

        :return: List containing the created Cpp node.
        """
        node = CppNode()
        node["cpp_directive"] = self.name  # e.g. "cpp:function"
        node["cpp_signature"] = " ".join(self.arguments)
        node["cpp_options"] = dict(self.options)
        node["newline"] = self.block_text.endswith("\n")
        self.state.nested_parse(
            self.content,
            self.content_offset,
            node,
            match_titles=True,
        )
        return [node]


@final
class CurrentModuleDirective(Directive):
    """Minimal ``currentmodule`` directive (Sphinx compatibility)."""

    has_content = False
    required_arguments = 1  # the module name
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    @override
    def run(self) -> list[nodes.Node]:
        """
        Create a :class:`CurrentModuleNode` storing the module name.

        :return: List containing the currentmodule node.
        """
        node = CurrentModuleNode()
        node["module"] = self.arguments[0]
        return [node]


_base_directives: Final[dict[str, type[Directive]]] = {
    "code": RememberingCodeBlock,
    "code-block": RememberingCodeBlock,
    "contents": ContentsDirective,
    "list-table": MarkingListTable,
    "table": MarkingTable,
    "toctree": TocTreeDirective,
    "currentmodule": CurrentModuleDirective,
}
_doxy_directives: Final[list[type[DoxyDirective]]] = [
    DoxyClassDirective,
    DoxyConceptDirective,
    DoxyFunctionDirective,
    DoxyStructDirective,
    DoxyTypedefDirective,
    DoxyVariableDirective,
]
_cpp_directive_names: Final[list[str]] = [
    "cpp:function",
    "cpp:class",
    "cpp:struct",
    "cpp:var",
    "cpp:type",
    "cpp:namespace",
]


def register_directives() -> None:
    """
    Register custom directives with docutils.

    Must be called before parsing reST that uses them.
    """
    for name, directive in _base_directives.items():
        directives.register_directive(name, directive)

    for directive in _doxy_directives:
        directives.register_directive(directive.node.directive, directive)

    for directive in _cpp_directive_names:
        directives.register_directive(directive, CppDirective)
