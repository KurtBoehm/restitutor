# This file is part of https://github.com/KurtBoehm/restitutor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path

from restitutor.formatting import format_rst

base_path = Path(__file__).parent
data_path = base_path / "data"


def test_general() -> None:
    ante = (data_path / "general-ante.rst").read_text(encoding="utf-8")
    post = (data_path / "general-post.rst").read_text(encoding="utf-8")
    out = format_rst(ante, clean=False)
    assert out == post
