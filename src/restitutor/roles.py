# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Callable, Final

from docutils import nodes
from docutils.parsers.rst import languages, roles
from docutils.parsers.rst.states import Inliner

from .nodes import XRefNode

title_target_re: Final = re.compile("(.*?)(?<!\x00)<(.*?)>\\s*$")

type XRefTuple = tuple[Sequence[XRefNode], Sequence[XRefNode]]
type RoleFn[N1, N2] = Callable[
    [str, str, str, int, Inliner, Mapping[str, Any], Sequence[str]],
    tuple[Sequence[N1], Sequence[N2]],
]


def _make_xref_role(role: str) -> RoleFn[XRefNode, XRefNode]:
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


def make_generic_role(canonical_name: str, node_class: type[nodes.Node]):
    generic = roles.GenericRole(canonical_name, node_class)

    def role(
        role_name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        options: Mapping[str, Any] | None = None,
        content: Sequence[str] | None = None,
    ) -> tuple[Sequence[nodes.Node], Sequence[nodes.system_message]]:
        [a], b = generic(role_name, rawtext, text, lineno, inliner, options, content)
        assert isinstance(a, nodes.TextElement)
        a["role"] = True
        return [a], b

    return role


def register_sphinx_text_roles() -> None:
    lang = languages.get_language("en")

    # Python domain roles
    for role in ("func", "meth", "class", "exc", "attr", "data", "mod", "obj"):
        roles.register_canonical_role(role, _make_xref_role(role))
        roles.register_canonical_role(f"cpp:{role}", _make_xref_role(f"cpp:{role}"))
        lang.roles.setdefault(role, role)
        lang.roles.setdefault(f"cpp:{role}", f"cpp:{role}")

    # Common "std" roles
    for role in ("ref", "doc", "term", "envvar"):
        roles.register_canonical_role(role, _make_xref_role(role))
        lang.roles.setdefault(role, role)

    for canonical_name, node_class in (
        ("emphasis", nodes.emphasis),
        ("literal", nodes.literal),
        ("strong", nodes.strong),
    ):
        role = make_generic_role(canonical_name, node_class)
        roles.register_canonical_role(canonical_name, role)  # pyright: ignore[reportArgumentType]
        lang.roles.setdefault(canonical_name, canonical_name)
