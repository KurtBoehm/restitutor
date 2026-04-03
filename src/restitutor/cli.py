# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Final, final, override

from docutils import nodes
from docutils.core import publish_doctree
from docutils.readers.standalone import Reader
from docutils.transforms import Transform
from docutils.transforms.frontmatter import DocInfo, DocTitle

from .context import FmtCtx
from .directives import register_directives
from .formatting import Buffer, PreprocessInfo, ast_to_rst
from .roles import register_sphinx_text_roles

# Register roles and directives with docutils
register_sphinx_text_roles()
register_directives()


def _print_header(label: str) -> None:
    hashes = "#" * (len(label) + 2)
    print(f"{hashes}\n {label}\n{hashes}\n")


label_re: Final = re.compile(r"^\s*\.\.\s+_([^:]+):\s*$")


def collect_labels(src: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in src.splitlines():
        m = label_re.match(line)
        if not m:
            continue
        raw = m.group(1)
        # Run docutils’ own normalization so you get the same id
        norm = nodes.make_id(nodes.fully_normalize_name(raw))
        mapping[norm] = raw
    return mapping


def make_auto_list_transform(src: list[str]) -> type[Transform]:
    @final
    class AutoList(Transform):
        default_priority = 340

        def apply(self) -> None:
            for target in self.document.findall(nodes.enumerated_list):
                for c in target.children:
                    assert isinstance(c, nodes.list_item)
                    line = c.line
                    assert line
                    c["auto"] = src[line - 1].lstrip().startswith("#")

    return AutoList


@final
class NoSubstitutionReader(Reader):  # pyright: ignore[reportMissingTypeArgument]
    def __init__(self, src: str) -> None:
        super().__init__()
        self.src = src.splitlines()

    @override
    def get_transforms(self) -> list[type[Transform]]:
        # Get the default transforms
        # transforms = list(super().get_transforms())
        # Filter out the Substitutions transform
        # transforms = [
        #     t for t in transforms if t is not Substitutions and t is not Footnotes
        # ]
        return [DocTitle, DocInfo, make_auto_list_transform(self.src)]


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
            reader=NoSubstitutionReader(src=rst_source),
        )

        buf = Buffer()
        ast_to_rst(
            buf,
            doctree,
            FmtCtx(preserve_row_newlines=not clean),
            PreprocessInfo(collected_labels=collect_labels(rst_source)),
        )
        reconstructed = str(buf)

        if in_place:
            rst_path.write_text(reconstructed, encoding="utf8")
        else:
            if i:
                print()
            _print_header(str(rst_path))
            print(reconstructed, end="")


if __name__ == "__main__":
    main()
