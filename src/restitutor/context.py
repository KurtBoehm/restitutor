# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass


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

    def prefix(self, index: int) -> str:
        return self.head_prefix if index == 0 else self.tail_prefix

    def with_indent(self, extra: str) -> FmtCtx:
        """Return a new context with increased indent (for child content)."""
        return FmtCtx(
            head_prefix=self.head_prefix + extra,
            tail_prefix=self.tail_prefix + extra,
            preserve_row_newlines=self.preserve_row_newlines,
        )

    def with_tail_indent(self, extra: str) -> FmtCtx:
        """Return a new context with increased indent (for child content)."""
        return FmtCtx(
            head_prefix=self.head_prefix,
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

    @property
    def tail_ctx(self) -> FmtCtx:
        return FmtCtx(
            head_prefix=self.tail_prefix,
            tail_prefix=self.tail_prefix,
            preserve_row_newlines=self.preserve_row_newlines,
        )

    def ctx(self, index: int) -> FmtCtx:
        return self if index == 0 else self.tail_ctx
