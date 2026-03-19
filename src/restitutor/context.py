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

    def with_indent(self, extra: str) -> FmtCtx:
        """Return a new context with increased indent (for child content)."""
        return FmtCtx(
            head_prefix=self.head_prefix + extra,
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
