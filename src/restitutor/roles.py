from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any, Callable, Final

from docutils.parsers.rst import languages, roles
from docutils.parsers.rst.states import Inliner

from .nodes import XRefNode

title_target_re: Final = re.compile("(.*?)(?<!\x00)<(.*?)>\\s*$")

type XRefTuple = tuple[Sequence[XRefNode], Sequence[XRefNode]]
type RoleFn = Callable[
    [str, str, str, int, Inliner, Mapping[str, Any], Sequence[str]],
    XRefTuple,
]


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


def register_sphinx_text_roles() -> None:
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
