from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.tables import ListTable
from typing import override

from .context import FmtCtx


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


def register_list_table() -> None:
    """Register our enhanced list-table directive."""
    directives.register_directive("list-table", MarkingListTable)


def split_table_rows(tgroup: nodes.tgroup) -> list[list[nodes.entry]]:
    """Collect rows as lists of entries, ignoring colspec details."""
    rows: list[list[nodes.entry]] = []
    for part in tgroup.children:
        if isinstance(part, (nodes.thead, nodes.tbody)):
            for row in part.children:
                if isinstance(row, nodes.row):
                    row_entries = [
                        e for e in row.children if isinstance(e, nodes.entry)
                    ]
                    rows.append(row_entries)
    return rows


def entry_text(entry: nodes.entry, ctx: FmtCtx) -> str:
    # Import here to avoid circular import with formatting.ast_to_rst
    from .formatting import children_to_rst

    # Render children as RST, then strip extra blank lines
    raw = children_to_rst(entry, ctx.with_indent(""))
    # Remove paragraph-level extra spacing (two newlines) for table cells
    lines: list[str] = []
    for line in raw.splitlines():
        if line.strip() == "":
            # omit empty lines inside cells to keep tables compact
            continue
        lines.append(line.rstrip())
    return "\n".join(lines) if lines else ""


def compute_column_widths(rows: list[list[nodes.entry]], ctx: FmtCtx) -> list[int]:
    """Compute minimal column widths based on textual content."""
    if not rows:
        return []

    ncols = max(len(r) for r in rows)
    widths = [0] * ncols

    for row in rows:
        for i, entry in enumerate(row):
            text = entry_text(entry, ctx)
            col_width = max(len(line) for line in text.splitlines()) if text else 0
            widths[i] = max(widths[i], col_width)

    # Ensure each column has at least width 1
    return [max(w, 1) for w in widths]


def render_table_border(widths: list[int], below_header: bool = False) -> str:
    # +-----+---+------+ style
    parts = ["+"]
    char = "=" if below_header else "-"
    for w in widths:
        parts.append(char * (w + 2))
        parts.append("+")
    return "".join(parts) + "\n"


def render_table_row(cells: list[str], widths: list[int]) -> str:
    """
    Render a single logical row that may have multiline cells.

    `cells` is list of already-prepared text for each cell.
    """
    # Split each cell into lines
    split_cells: list[list[str]] = []
    for text in cells:
        cell_lines = text.splitlines() if text else [""]
        split_cells.append(cell_lines)

    # Determine how many physical lines this row will have
    max_lines = max(len(c) for c in split_cells) if split_cells else 0

    out_lines: list[str] = []
    for line_idx in range(max_lines):
        parts = ["|"]
        for col_idx, width in enumerate(widths):
            cell_lines = split_cells[col_idx] if col_idx < len(split_cells) else [""]
            line_text = cell_lines[line_idx] if line_idx < len(cell_lines) else ""
            parts.append(" " + line_text.ljust(width) + " ")
            parts.append("|")
        out_lines.append("".join(parts) + "\n")
    return "".join(out_lines)
