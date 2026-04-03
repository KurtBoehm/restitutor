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

    def _clone(
        self,
        *,
        head_prefix: str | None = None,
        tail_prefix: str | None = None,
    ) -> FmtCtx:
        return replace(
            self,
            head_prefix=self.head_prefix if head_prefix is None else head_prefix,
            tail_prefix=self.tail_prefix if tail_prefix is None else tail_prefix,
        )

    def with_indent(self, extra: str) -> FmtCtx:
        return self._clone(
            head_prefix=self.head_prefix + extra,
            tail_prefix=self.tail_prefix + extra,
        )

    def with_tail_indent(self, extra: str) -> FmtCtx:
        return self._clone(
            tail_prefix=self.tail_prefix + extra,
        )

    def with_list_prefix(self, prefix: str) -> FmtCtx:
        return self._clone(
            head_prefix=self.head_prefix + prefix,
            tail_prefix=self.tail_prefix + " " * len(prefix),
        )

    @property
    def tail_ctx(self) -> FmtCtx:
        return self._clone(
            head_prefix=self.tail_prefix,
            tail_prefix=self.tail_prefix,
        )

    def ctx(self, index: int) -> FmtCtx:
        return self if index == 0 else self.tail_ctx
