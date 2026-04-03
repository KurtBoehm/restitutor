# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(kw_only=True)
class FmtCtx:
    """
    Formatting context used while rendering reST lines.

    :ivar head_prefix: Prefix for the first line.
    :ivar tail_prefix: Prefix for subsequent lines.
    :ivar preserve_row_newlines: Preserve blank lines between table rows.
    """

    head_prefix: str = ""
    tail_prefix: str = ""
    preserve_row_newlines: bool

    @property
    def empty(self) -> bool:
        """Return ``True`` if both prefixes are empty."""
        return not self.head_prefix and not self.tail_prefix

    def prefix(self, index: int) -> str:
        """
        Return the prefix for a line by index.

        :param index: Line index (0-based).
        :return: ``head_prefix`` for ``0``, else ``tail_prefix``.
        """
        return self.head_prefix if index == 0 else self.tail_prefix

    def _clone(
        self,
        *,
        head_prefix: str | None = None,
        tail_prefix: str | None = None,
    ) -> FmtCtx:
        """
        Return a shallow copy with optional prefix overrides.

        :param head_prefix: New head prefix, if given.
        :param tail_prefix: New tail prefix, if given.
        """
        return replace(
            self,
            head_prefix=self.head_prefix if head_prefix is None else head_prefix,
            tail_prefix=self.tail_prefix if tail_prefix is None else tail_prefix,
        )

    def with_indent(self, extra: str) -> FmtCtx:
        """
        Add ``extra`` to both prefixes.

        :param extra: Indentation to append.
        """
        return self._clone(
            head_prefix=self.head_prefix + extra,
            tail_prefix=self.tail_prefix + extra,
        )

    def with_tail_indent(self, extra: str) -> FmtCtx:
        """
        Add ``extra`` only to the tail prefix.

        :param extra: Indentation to append after the first line.
        """
        return self._clone(
            tail_prefix=self.tail_prefix + extra,
        )

    def with_list_prefix(self, prefix: str) -> FmtCtx:
        """
        Adapt prefixes for a list item.

        :param prefix: Bullet or enumerator text (e.g. ``"- "``).
        """
        return self._clone(
            head_prefix=self.head_prefix + prefix,
            tail_prefix=self.tail_prefix + " " * len(prefix),
        )

    @property
    def tail_ctx(self) -> FmtCtx:
        """
        Context for subsequent lines.

        :return: Copy where ``head_prefix`` equals ``tail_prefix``.
        """
        return self._clone(
            head_prefix=self.tail_prefix,
            tail_prefix=self.tail_prefix,
        )

    def ctx(self, index: int) -> FmtCtx:
        """Return context for a given line index."""
        return self if index == 0 else self.tail_ctx
