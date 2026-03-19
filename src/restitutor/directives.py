from __future__ import annotations

from typing import ClassVar, final, override

from docutils import nodes
from docutils.parsers.rst import Directive, directives

from .nodes import (
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


def register_directives() -> None:
    """Register our custom directives with docutils."""
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
