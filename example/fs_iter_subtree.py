#!/usr/bin/env python3
#
# Copyright (c) 2025 Jan Malakhovski <oxij@oxij.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.


"""An example demonstating `kisstdlib.fs:iter_subtree` usage."""

import logging
import os
import sys
import typing as _t

from kisstdlib.fs import *


def test_iter_subtree(tmpdir: _t.Any) -> None:
    tmpdir = os.fspath(tmpdir)

    print(".py files:")

    for e in iter_subtree(
        tmpdir,
        include_directories=False,
        include_files=with_extension_in([".py"]),
        handle_error=logging.error,
    ):
        print(e)

    print("leaf directories:")

    for e in iter_subtree(tmpdir, include_directories=leaf_directories, include_files=False):
        print(e)


if __name__ == "__main__":
    test_iter_subtree(sys.argv[1] if len(sys.argv) > 1 else ".")
