# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import final

from docutils import nodes


class ContentsNode(nodes.General, nodes.Element):
    """Node for contents."""


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


class CppNode(nodes.General, nodes.Element):
    pass


@final
class CurrentModuleNode(nodes.General, nodes.Element):
    """A Sphinx-style currentmodule directive."""


class XRefNode(nodes.reference):
    """Cross-reference node used by our Sphinx-like roles."""
