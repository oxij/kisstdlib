# Copyright (c) 2025 Jan Malakhovski <oxij@oxij.org>
#
# This file is a part of `kisstdlib` project.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Testing `kisstdlib.fs` module."""

import os

from kisstdlib.failure import *
from kisstdlib.fs import *


def test_iter_subtree(tmp_path: str) -> None:
    os.chdir(tmp_path)

    def touch(path: str) -> None:
        with open(path, "wb") as f:
            f.close()

    os.makedirs("example")
    touch("example/a")
    touch("example/aa")
    touch("example/b")
    touch("example/c")
    touch("example.dot")
    touch("example*not")

    w = list(map(lambda x: os.path.relpath(x[0], tmp_path), iter_subtree(".")))
    assert w == [
        ".",
        "example*not",
        "example.dot",
        "example",
        "example/a",
        "example/aa",
        "example/b",
        "example/c",
    ]


def atomic1(defer: bool, tmp_path: str) -> None:
    os.chdir(tmp_path)

    sync: DeferredSync[str] | bool = True
    if defer:
        sync = DeferredSync(True)

    def check(es: list[list[str]], ed: list[list[str]] | None = None) -> None:
        if isinstance(sync, DeferredSync):
            gs: list[list[str]] = []
            sync.copy().sync(True, gs)
            assert es == gs

        if ed is not None:
            gd = list(describe_forest(["."], hash_length=8))
            assert ed == gd

    atomic_write(b"test a", "test.a", sync=sync)
    atomic_write(b"test b", "test.b", sync=sync)
    atomic_write(b"test c", "test.c", sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.b.part"],
            ["fsync", "test.c.part"],
            ["rename", "test.a.part", "test.a"],
            ["rename", "test.b.part", "test.b"],
            ["rename", "test.c.part", "test.c"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.b"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
        ]
    )
    atomic_rename("test.a", "a/test.a", False, sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.b.part"],
            ["fsync", "test.c.part"],
            ["rename", "test.a.part", "test.a"],
            ["rename", "test.b.part", "test.b"],
            ["rename", "test.c.part", "test.c"],
            ["barrier"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.b"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
            ["rename", "test.a", "a/test.a"],
            ["fsync_win", "a/test.a"],
            ["fsync_dir", "a"],
            ["fsync_dir", "."],
        ]
    )
    atomic_rename("test.b", "a/test.b", False, sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.b.part"],
            ["fsync", "test.c.part"],
            ["rename", "test.a.part", "test.a"],
            ["rename", "test.b.part", "test.b"],
            ["rename", "test.c.part", "test.c"],
            ["barrier"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.b"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
            ["rename", "test.a", "a/test.a"],
            ["rename", "test.b", "a/test.b"],
            ["fsync_win", "a/test.a"],
            ["fsync_win", "a/test.b"],
            ["fsync_dir", "a"],
            ["fsync_dir", "."],
        ]
    )
    atomic_rename("test.c", "b/test.c", False, sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.b.part"],
            ["fsync", "test.c.part"],
            ["rename", "test.a.part", "test.a"],
            ["rename", "test.b.part", "test.b"],
            ["rename", "test.c.part", "test.c"],
            ["barrier"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.b"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
            ["rename", "test.a", "a/test.a"],
            ["rename", "test.b", "a/test.b"],
            ["rename", "test.c", "b/test.c"],
            ["fsync_win", "a/test.a"],
            ["fsync_win", "a/test.b"],
            ["fsync_win", "b/test.c"],
            ["fsync_dir", "a"],
            ["fsync_dir", "b"],
            ["fsync_dir", "."],
        ]
    )
    atomic_rename("a/test.b", "test.b", False, sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.b.part"],
            ["fsync", "test.c.part"],
            ["rename", "test.a.part", "test.a"],
            ["rename", "test.b.part", "test.b"],
            ["rename", "test.c.part", "test.c"],
            ["barrier"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.b"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
            ["rename", "test.a", "a/test.a"],
            ["rename", "test.b", "a/test.b"],
            ["rename", "test.c", "b/test.c"],
            ["barrier"],
            ["fsync_win", "a/test.a"],
            ["fsync_win", "a/test.b"],
            ["fsync_win", "b/test.c"],
            ["fsync_dir", "a"],
            ["fsync_dir", "b"],
            ["fsync_dir", "."],
            ["rename", "a/test.b", "test.b"],
            ["fsync_win", "test.b"],
            ["fsync_dir", "."],
            ["fsync_dir", "a"],
        ]
    )
    if isinstance(sync, DeferredSync):
        sync.flush()
    check(
        [],
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["test.b", "reg", "size", "6", "sha256", "6346935e"],
        ],
    )

    atomic_link("a/test.a", "test.a", True, sync=sync)
    atomic_symlink("b/test.c", "test.c", True, sync=sync)
    check(
        [
            ["fsync", "test.a.part"],
            ["fsync", "test.c.part"],
            ["replace", "test.a.part", "test.a"],
            ["replace", "test.c.part", "test.c"],
            ["fsync_win", "test.a"],
            ["fsync_win", "test.c"],
            ["fsync_dir", "."],
        ]
    )
    if isinstance(sync, DeferredSync):
        sync.flush()
    check([])

    atomic_copy2("test.a", "x/test.a", True, sync=sync)
    atomic_copy2("test.c", "x/test.c", True, sync=sync)
    atomic_link("test.c", "x/test.c.lnk", True, follow_symlinks=False, sync=sync)
    atomic_copy2("test.c", "x/test.c.sym", True, follow_symlinks=False, sync=sync)
    check(
        [
            ["fsync", "x/test.a.part"],
            ["fsync", "x/test.c.lnk.part"],
            ["fsync", "x/test.c.part"],
            ["fsync", "x/test.c.sym.part"],
            ["replace", "x/test.a.part", "x/test.a"],
            ["replace", "x/test.c.part", "x/test.c"],
            ["replace", "x/test.c.lnk.part", "x/test.c.lnk"],
            ["replace", "x/test.c.sym.part", "x/test.c.sym"],
            ["fsync_win", "x/test.a"],
            ["fsync_win", "x/test.c"],
            ["fsync_win", "x/test.c.lnk"],
            ["fsync_win", "x/test.c.sym"],
            ["fsync_dir", "x"],
        ]
    )
    if isinstance(sync, DeferredSync):
        sync.flush()
    check(
        [],
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["test.a", "ref", "==>", "a/test.a"],
            ["test.b", "reg", "size", "6", "sha256", "6346935e"],
            ["test.c", "sym", "->", "b/test.c"],
            ["x/", "dir"],
            ["x/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["x/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["x/test.c.lnk", "ref", "==>", "test.c"],
            ["x/test.c.sym", "sym", "->", "b/test.c"],
        ],
    )

    atomic_copy2("test.a", "y/test.a", True, sync=sync)
    atomic_copy2("test.c", "y/test.c", True, sync=sync)
    atomic_link("test.c", "y/test.c.lnk", True, follow_symlinks=False, sync=sync)
    atomic_copy2("test.c", "y/test.c.sym", True, follow_symlinks=False, sync=sync)
    atomic_move("test.c", "z/test.c", True, sync=sync)
    check(
        [
            ["fsync", "y/test.a.part"],
            ["fsync", "y/test.c.lnk.part"],
            ["fsync", "y/test.c.part"],
            ["fsync", "y/test.c.sym.part"],
            ["fsync", "z/test.c.part"],
            ["replace", "y/test.a.part", "y/test.a"],
            ["replace", "y/test.c.part", "y/test.c"],
            ["replace", "y/test.c.lnk.part", "y/test.c.lnk"],
            ["replace", "y/test.c.sym.part", "y/test.c.sym"],
            ["replace", "z/test.c.part", "z/test.c"],
            ["fsync_win", "y/test.a"],
            ["fsync_win", "y/test.c"],
            ["fsync_win", "y/test.c.lnk"],
            ["fsync_win", "y/test.c.sym"],
            ["fsync_win", "z/test.c"],
            ["fsync_dir", "y"],
            ["fsync_dir", "z"],
            ["unlink", "test.c"],
            ["fsync_dir", "."],
        ]
    )
    if isinstance(sync, DeferredSync):
        sync.flush()
    check(
        [],
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["test.a", "ref", "==>", "a/test.a"],
            ["test.b", "reg", "size", "6", "sha256", "6346935e"],
            ["x/", "dir"],
            ["x/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["x/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["x/test.c.lnk", "sym", "->", "b/test.c"],
            ["x/test.c.sym", "sym", "->", "b/test.c"],
            ["y/", "dir"],
            ["y/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["y/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["y/test.c.lnk", "ref", "==>", "x/test.c.lnk"],
            ["y/test.c.sym", "sym", "->", "b/test.c"],
            ["z/", "dir"],
            ["z/test.c", "ref", "==>", "y/test.c.lnk"],
        ],
    )

    atomic_symlink("/home", "y/home")

    # to test `describe_forest` with multiple paths
    w = list(describe_forest(["x", "y"], hash_length=8))
    # print(repr(w))
    assert w == [
        ["0/", "dir"],
        ["0/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
        ["0/test.c", "reg", "size", "6", "sha256", "806b51ad"],
        ["0/test.c.lnk", "sym", "->", "b/test.c"],
        ["0/test.c.sym", "sym", "->", "b/test.c"],
        ["1/", "dir"],
        ["1/home", "sym", "->", "/home"],
        ["1/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
        ["1/test.c", "reg", "size", "6", "sha256", "806b51ad"],
        ["1/test.c.lnk", "ref", "==>", "0/test.c.lnk"],
        ["1/test.c.sym", "sym", "->", "b/test.c"],
    ]


def test_without_DeferredSync(tmp_path: str) -> None:
    return atomic1(False, tmp_path)


def test_with_DeferredSync(tmp_path: str) -> None:
    return atomic1(True, tmp_path)
