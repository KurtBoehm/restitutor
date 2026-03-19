# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import override

from docutils import nodes
from docutils.core import publish_doctree
from docutils.readers.standalone import Reader
from docutils.transforms.references import Substitutions

from .context import FmtCtx
from .directives import register_directives
from .formatting import ast_to_rst
from .roles import register_sphinx_text_roles

# Register roles and directives with docutils
register_sphinx_text_roles()
register_directives()


def _print_header(label: str) -> None:
    hashes = "#" * (len(label) + 2)
    print(f"{hashes}\n {label}\n{hashes}\n")


class NoSubstitutionReader(Reader[str]):
    @override
    def get_transforms(self):
        # Get the default transforms
        transforms = list(super().get_transforms())
        # Filter out the Substitutions transform
        transforms = [t for t in transforms if t is not Substitutions]
        return transforms


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
        doctree: nodes.document = publish_doctree(
            rst_source,
            reader=NoSubstitutionReader(),
        )

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
