# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import final

from docutils import nodes


class ContentsNode(nodes.General, nodes.Element):
    """Minimal node type for ``.. contents::``."""


class TocTreeNode(nodes.General, nodes.Element):
    """Node for inserting a Sphinx-style TOC tree."""


class _BaseDoxyNode(nodes.General, nodes.Element):
    """Base type for Doxygen-related node types."""


@final
class DoxyClassNode(_BaseDoxyNode):
    """Node produced by ``.. doxygenclass::``."""
    directive = "doxygenclass"


@final
class DoxyConceptNode(_BaseDoxyNode):
    """Node produced by ``.. doxygenconcept::``."""
    directive = "doxygenconcept"


@final
class DoxyFunctionNode(_BaseDoxyNode):
    """Node produced by ``.. doxygenfunction::``."""
    directive = "doxygenfunction"


@final
class DoxyStructNode(_BaseDoxyNode):
    """Node produced by ``.. doxygenstruct::``."""
    directive = "doxygenstruct"


@final
class DoxyTypedefNode(_BaseDoxyNode):
    """Node produced by ``.. doxygentypedef::``."""
    directive = "doxygentypedef"


@final
class DoxyVariableNode(_BaseDoxyNode):
    """Node produced by ``.. doxygenvariable::``."""
    directive = "doxygenvariable"


type DoxyNode = (
    DoxyClassNode
    | DoxyConceptNode
    | DoxyFunctionNode
    | DoxyStructNode
    | DoxyTypedefNode
    | DoxyVariableNode
)


class CppNode(nodes.General, nodes.Element):
    """Generic container for Sphinx ``cpp:`` directives."""


@final
class CurrentModuleNode(nodes.General, nodes.Element):
    """Node representing a Sphinx-style ``currentmodule`` directive."""


class XRefNode(nodes.reference):
    """Cross-reference node used by our Sphinx-like roles."""
