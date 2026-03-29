# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import ClassVar, final, override

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.parsers.rst.directives.body import CodeBlock
from docutils.parsers.rst.directives.tables import ListTable

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
    return 999 if not argument else int(argument)


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


class RememberingCodeBlock(CodeBlock):
    @override
    def run(self) -> list[nodes.literal_block]:
        [node] = super().run()
        assert isinstance(node, nodes.literal_block)
        node["directive"] = self.name
        return [node]


class ContentsDirective(Directive):
    has_content: ClassVar[bool] = False
    option_spec = {
        "local": directives.flag,
        "depth": directives.nonnegative_int,
        "backlinks": directives.unchanged,
        "titlesonly": directives.flag,
    }

    @override
    def run(self) -> list[nodes.Node]:
        node = ContentsNode(
            local="local" in self.options,
            depth=self.options.get("depth"),
            backlinks=self.options.get("backlinks"),
            titlesonly="titlesonly" in self.options,
        )
        return [node]


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


class CppDirective(Directive):
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


def register_directives() -> None:
    """Register our custom directives with docutils."""
    directives.register_directive("contents", ContentsDirective)
    directives.register_directive("list-table", MarkingListTable)
    directives.register_directive("toctree", TocTreeDirective)
    directives.register_directive("code", RememberingCodeBlock)
    directives.register_directive("code-block", RememberingCodeBlock)

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

    for directive in [
        "cpp:function",
        "cpp:class",
        "cpp:struct",
        "cpp:var",
        "cpp:type",
        "cpp:namespace",
    ]:
        directives.register_directive(directive, CppDirective)

    directives.register_directive("currentmodule", CurrentModuleDirective)
