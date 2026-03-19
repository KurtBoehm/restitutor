# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from docutils import nodes
from docutils.core import publish_doctree

from .context import FmtCtx
from .directives import register_directives
from .formatting import ast_to_rst
from .roles import register_sphinx_text_roles
from .tables import register_list_table

# Register roles and directives with docutils
register_sphinx_text_roles()
register_directives()
register_list_table()


def _print_header(label: str) -> None:
    hashes = "#" * (len(label) + 2)
    print(f"{hashes}\n {label}\n{hashes}\n")


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("rst", type=Path, nargs="+")
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Rewrite the given .rst files in-place instead of printing",
    )
    parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="Normalize newlines",
    )
    args = parser.parse_args()
    rst_paths: list[Path] = args.rst
    in_place: bool = args.in_place
    clean: bool = args.clean

    for i, rst_path in enumerate(rst_paths):
        rst_source = rst_path.read_text(encoding="utf8")
        doctree: nodes.document = publish_doctree(rst_source)

        reconstructed = ast_to_rst(doctree, FmtCtx(preserve_row_newlines=not clean))

        if in_place:
            rst_path.write_text(reconstructed, encoding="utf8")
        else:
            if i:
                print()
            _print_header(str(rst_path))
            print(reconstructed)


if __name__ == "__main__":
    main()
