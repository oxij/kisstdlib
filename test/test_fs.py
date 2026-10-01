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
import typing as _t

import pytest

from kisstdlib.failure import *
from kisstdlib.fs import *


def test_fs_basics() -> None:
    assert fsreencode("abc", "") == "abc"
    assert fsreencode(b"abc", "") == "abc"
    assert fsreencode("abc", b"") == b"abc"
    assert fsreencode(b"abc", b"") == b"abc"

    assert equal_path("abc", "abc")
    assert equal_path(b"abc", b"abc")
    assert equal_path("abc", b"abc")
    assert equal_path(b"abc", "abc")

    assert not equal_path("abc", "abcd")
    assert not equal_path(b"abc", b"abcd")
    assert not equal_path("abc", b"abcd")
    assert not equal_path(b"abc", "abcd")


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


def fs1(
    tmp_path: str,
    sync: Deferred[str] | bool,
    simulate_whole: bool = False,
) -> None:
    os.chdir(tmp_path)

    log: list[tuple[_t.Any, ...]] = []
    sync_acc: list[tuple[_t.Any, ...]] = []
    nosync_acc: list[tuple[_t.Any, ...]] = []

    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None
    if simulate_whole:

        def simulate(*args: str) -> None:
            log.append(args)

    def check_ex(
        flush: bool,
        main: list[tuple[_t.Any, ...]],
        syncs: list[tuple[_t.Any, ...]],
        defer_main: list[tuple[_t.Any, ...]] | None = None,
        defer_syncs: list[tuple[_t.Any, ...]] | None = None,
        full_main: list[tuple[_t.Any, ...]] | None = None,
    ) -> None:
        for e in (main, syncs):
            sync_acc.extend(e)
            nosync_acc.extend(filter(lambda x: x[0] != "fsync", e))

        if defer_main is None:
            defer_main = main
        if defer_syncs is None:
            defer_syncs = syncs
        defer_log = defer_main + defer_syncs

        if isinstance(sync, Deferred):
            log2: list[tuple[_t.Any, ...]] = []

            def simulate2(*args: str) -> None:
                log2.append(args)

            sync.copy().flush(simulate=simulate2)

            if sync.defer:
                assert log2 == defer_log
            else:
                assert log2 == defer_syncs

            if flush:
                sync.flush(simulate=simulate)

        if simulate is not None:
            if isinstance(sync, Deferred):
                if not flush:
                    pass
                elif sync.defer:
                    assert log == defer_log
                else:
                    assert log == (defer_log if full_main is None else full_main + defer_syncs)
            elif sync:
                assert log == sync_acc
            else:
                assert log == nosync_acc

        if flush:
            log.clear()
            nosync_acc.clear()
            sync_acc.clear()

    def check(*args: _t.Any) -> None:
        check_ex(False, *args)

    def check_flush(*args: _t.Any) -> None:
        check_ex(True, *args)

    def check_forest(ed: list[list[str]]) -> None:
        if simulate is not None:
            return

        gd = list(describe_forest(["."], hash_length=8))
        assert gd == ed

    write_file(b"test a", "test.a", sync=sync, simulate=simulate)
    check(
        [
            ("make", "test.a.part"),
            ("fsync", "test.a.part", 0),
            ("rename", "test.a.part", "test.a"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("fsync", "test.a.part", 0),
            ("rename", "test.a.part", "test.a"),
        ],
    )

    with pytest.raises(FileExistsError):
        if simulate_whole:
            raise FileExistsError()
        write_file(b"test e", "test.a", sync=sync, simulate=simulate)

    write_file(b"test b", "test.b", sync=sync, simulate=simulate)
    check(
        [
            ("make", "test.b.part"),
            ("fsync", "test.b.part", 0),
            ("rename", "test.b.part", "test.b"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.b.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.b.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("rename", "test.b.part", "test.b"),
        ],
    )
    write_file(b"test c", "test.c", sync=sync, simulate=simulate)
    check(
        [
            ("make", "test.c.part"),
            ("fsync", "test.c.part", 0),
            ("rename", "test.c.part", "test.c"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.b.part"),
            ("make", "test.c.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.b.part", 0),
            ("fsync", "test.c.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("rename", "test.b.part", "test.b"),
            ("rename", "test.c.part", "test.c"),
        ],
    )
    rename_file("test.a", "a/test.a", False, sync=sync, simulate=simulate)
    check(
        [
            ("makedirs", "a"),
            ("rename", "test.a", "a/test.a"),
        ],
        [
            ("fsync", "a", os.O_DIRECTORY),
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.b.part"),
            ("make", "test.c.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.b.part", 0),
            ("fsync", "test.c.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("rename", "test.b.part", "test.b"),
            ("rename", "test.c.part", "test.c"),
            ("fsync", ".", os.O_DIRECTORY),
            ("makedirs", "a"),
            ("rename", "test.a", "a/test.a"),
        ],
    )
    rename_file("test.b", "a/test.b", False, sync=sync, simulate=simulate)
    check(
        [
            ("makedirs", "a"),
            ("rename", "test.b", "a/test.b"),
        ],
        [
            ("fsync", "a", os.O_DIRECTORY),
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.b.part"),
            ("make", "test.c.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.b.part", 0),
            ("fsync", "test.c.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("rename", "test.b.part", "test.b"),
            ("rename", "test.c.part", "test.c"),
            ("fsync", ".", os.O_DIRECTORY),
            ("makedirs", "a"),
            ("rename", "test.a", "a/test.a"),
            ("rename", "test.b", "a/test.b"),
        ],
    )
    rename_file("test.c", "b/test.c", False, sync=sync, simulate=simulate)
    check_flush(
        [
            ("makedirs", "b"),
            ("rename", "test.c", "b/test.c"),
        ],
        [
            ("fsync", "b", os.O_DIRECTORY),
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.b.part"),
            ("make", "test.c.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.b.part", 0),
            ("fsync", "test.c.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("rename", "test.b.part", "test.b"),
            ("rename", "test.c.part", "test.c"),
            ("fsync", ".", os.O_DIRECTORY),
            ("makedirs", "a"),
            ("rename", "test.a", "a/test.a"),
            ("rename", "test.b", "a/test.b"),
            ("makedirs", "b"),
            ("rename", "test.c", "b/test.c"),
        ],
        [
            ("fsync", "a", os.O_DIRECTORY),
            ("fsync", "b", os.O_DIRECTORY),
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("fsync", "test.a.part", 0),
            ("rename", "test.a.part", "test.a"),
            ("make", "test.b.part"),
            ("fsync", "test.b.part", 0),
            ("rename", "test.b.part", "test.b"),
            ("make", "test.c.part"),
            ("fsync", "test.c.part", 0),
            ("rename", "test.c.part", "test.c"),
            ("fsync", ".", os.O_DIRECTORY),
            ("makedirs", "a"),
            ("rename", "test.a", "a/test.a"),
            ("makedirs", "a"),
            ("rename", "test.b", "a/test.b"),
            ("makedirs", "b"),
            ("rename", "test.c", "b/test.c"),
        ],
    )

    check_forest(
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["a/test.b", "reg", "size", "6", "sha256", "6346935e"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
        ]
    )

    rename_file("a/test.b", "test.b", False, sync=sync, simulate=simulate)
    check_flush(
        [
            ("rename", "a/test.b", "test.b"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
            ("fsync", "a", os.O_DIRECTORY),
        ],
    )

    check_forest(
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["test.b", "reg", "size", "6", "sha256", "6346935e"],
        ]
    )

    link_file("a/test.a", "test.a", True, sync=sync, simulate=simulate)
    symlink_file("b/test.c", "test.c", True, sync=sync, simulate=simulate)
    check_flush(
        [
            ("make", "test.a.part"),
            ("replace", "test.a.part", "test.a"),
            ("fsync", ".", os.O_DIRECTORY),
            ("make", "test.c.part"),
            ("fsync", "test.c.part", 0),
            ("replace", "test.c.part", "test.c"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("make", "test.a.part"),
            ("make", "test.c.part"),
            ("fsync", "test.a.part", 0),
            ("fsync", "test.c.part", 0),
            ("replace", "test.a.part", "test.a"),
            ("replace", "test.c.part", "test.c"),
        ],
        None,
        [
            ("make", "test.a.part"),
            ("fsync", "test.a.part", 0),
            ("replace", "test.a.part", "test.a"),
            ("make", "test.c.part"),
            ("fsync", "test.c.part", 0),
            ("replace", "test.c.part", "test.c"),
        ],
    )

    check_forest(
        [
            ["./", "dir"],
            ["a/", "dir"],
            ["a/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["b/", "dir"],
            ["b/test.c", "reg", "size", "6", "sha256", "806b51ad"],
            ["test.a", "ref", "==>", "a/test.a"],
            ["test.b", "reg", "size", "6", "sha256", "6346935e"],
            ["test.c", "sym", "->", "b/test.c"],
        ]
    )

    copy_file("test.a", "x/test.a", True, sync=sync, simulate=simulate)
    clone_file("test.c", "x/test.c", True, sync=sync, simulate=simulate)
    link_file("test.c", "x/test.c.lnk", True, sync=sync, simulate=simulate)
    clone_file("test.c", "x/test.c.sym", True, sync=sync, simulate=simulate)
    check_flush(
        [
            ("makedirs", "x"),
            ("make", "x/test.a.part"),
            ("fsync", "x/test.a.part", 0),
            ("replace", "x/test.a.part", "x/test.a"),
            ("fsync", "x", os.O_DIRECTORY),
            ("makedirs", "x"),
            ("make", "x/test.c.part"),
            ("fsync", "x/test.c.part", 0),
            ("replace", "x/test.c.part", "x/test.c"),
            ("fsync", "x", os.O_DIRECTORY),
            ("makedirs", "x"),
            ("make", "x/test.c.lnk.part"),
            ("replace", "x/test.c.lnk.part", "x/test.c.lnk"),
            ("fsync", "x", os.O_DIRECTORY),
            ("makedirs", "x"),
            ("make", "x/test.c.sym.part"),
            ("fsync", "x/test.c.sym.part", 0),
            ("replace", "x/test.c.sym.part", "x/test.c.sym"),
        ],
        [
            ("fsync", "x", os.O_DIRECTORY),
        ],
        [
            ("makedirs", "x"),
            ("make", "x/test.a.part"),
            ("make", "x/test.c.part"),
            ("make", "x/test.c.lnk.part"),
            ("make", "x/test.c.sym.part"),
            ("fsync", "x/test.a.part", 0),
            ("fsync", "x/test.c.lnk.part", 0),
            ("fsync", "x/test.c.part", 0),
            ("fsync", "x/test.c.sym.part", 0),
            ("replace", "x/test.a.part", "x/test.a"),
            ("replace", "x/test.c.part", "x/test.c"),
            ("replace", "x/test.c.lnk.part", "x/test.c.lnk"),
            ("replace", "x/test.c.sym.part", "x/test.c.sym"),
        ],
        None,
        [
            ("makedirs", "x"),
            ("make", "x/test.a.part"),
            ("fsync", "x/test.a.part", 0),
            ("replace", "x/test.a.part", "x/test.a"),
            ("makedirs", "x"),
            ("make", "x/test.c.part"),
            ("fsync", "x/test.c.part", 0),
            ("replace", "x/test.c.part", "x/test.c"),
            ("makedirs", "x"),
            ("make", "x/test.c.lnk.part"),
            ("fsync", "x/test.c.lnk.part", 0),
            ("replace", "x/test.c.lnk.part", "x/test.c.lnk"),
            ("makedirs", "x"),
            ("make", "x/test.c.sym.part"),
            ("fsync", "x/test.c.sym.part", 0),
            ("replace", "x/test.c.sym.part", "x/test.c.sym"),
        ],
    )

    check_forest(
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
            ["x/test.c", "sym", "->", "b/test.c"],
            ["x/test.c.lnk", "ref", "==>", "test.c"],
            ["x/test.c.sym", "sym", "->", "b/test.c"],
        ]
    )

    copy_file("test.a", "y/test.a", True, sync=sync, simulate=simulate)
    clone_file("test.c", "y/test.c", True, sync=sync, simulate=simulate)
    link_file("test.c", "y/test.c.lnk", True, sync=sync, simulate=simulate)
    clone_file("test.c", "y/test.c.sym", True, sync=sync, simulate=simulate)
    move_file("test.c", "z/test.c", True, sync=sync, simulate=simulate)
    check_flush(
        [
            ("makedirs", "y"),
            ("make", "y/test.a.part"),
            ("fsync", "y/test.a.part", 0),
            ("replace", "y/test.a.part", "y/test.a"),
            ("fsync", "y", os.O_DIRECTORY),
            ("makedirs", "y"),
            ("make", "y/test.c.part"),
            ("fsync", "y/test.c.part", 0),
            ("replace", "y/test.c.part", "y/test.c"),
            ("fsync", "y", os.O_DIRECTORY),
            ("makedirs", "y"),
            ("make", "y/test.c.lnk.part"),
            ("replace", "y/test.c.lnk.part", "y/test.c.lnk"),
            ("fsync", "y", os.O_DIRECTORY),
            ("makedirs", "y"),
            ("make", "y/test.c.sym.part"),
            ("fsync", "y/test.c.sym.part", 0),
            ("replace", "y/test.c.sym.part", "y/test.c.sym"),
            ("fsync", "y", os.O_DIRECTORY),
            ("makedirs", "z"),
            ("make", "z/test.c.part"),
            ("replace", "z/test.c.part", "z/test.c"),
            ("fsync", "z", os.O_DIRECTORY),
            ("unlink", "test.c"),
        ],
        [
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("makedirs", "y"),
            ("make", "y/test.a.part"),
            ("make", "y/test.c.part"),
            ("make", "y/test.c.lnk.part"),
            ("make", "y/test.c.sym.part"),
            ("makedirs", "z"),
            ("make", "z/test.c.part"),
            ("fsync", "y/test.a.part", 0),
            ("fsync", "y/test.c.lnk.part", 0),
            ("fsync", "y/test.c.part", 0),
            ("fsync", "y/test.c.sym.part", 0),
            ("fsync", "z/test.c.part", 0),
            ("replace", "y/test.a.part", "y/test.a"),
            ("replace", "y/test.c.part", "y/test.c"),
            ("replace", "y/test.c.lnk.part", "y/test.c.lnk"),
            ("replace", "y/test.c.sym.part", "y/test.c.sym"),
            ("replace", "z/test.c.part", "z/test.c"),
        ],
        [
            ("fsync", "y", os.O_DIRECTORY),
            ("fsync", "z", os.O_DIRECTORY),
            ("unlink", "test.c"),
            ("fsync", ".", os.O_DIRECTORY),
        ],
        [
            ("makedirs", "y"),
            ("make", "y/test.a.part"),
            ("fsync", "y/test.a.part", 0),
            ("replace", "y/test.a.part", "y/test.a"),
            ("makedirs", "y"),
            ("make", "y/test.c.part"),
            ("fsync", "y/test.c.part", 0),
            ("replace", "y/test.c.part", "y/test.c"),
            ("makedirs", "y"),
            ("make", "y/test.c.lnk.part"),
            ("fsync", "y/test.c.lnk.part", 0),
            ("replace", "y/test.c.lnk.part", "y/test.c.lnk"),
            ("makedirs", "y"),
            ("make", "y/test.c.sym.part"),
            ("fsync", "y/test.c.sym.part", 0),
            ("replace", "y/test.c.sym.part", "y/test.c.sym"),
            ("makedirs", "z"),
            ("make", "z/test.c.part"),
            ("fsync", "z/test.c.part", 0),
            ("replace", "z/test.c.part", "z/test.c"),
        ],
    )

    check_forest(
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
            ["x/test.c", "sym", "->", "b/test.c"],
            ["x/test.c.lnk", "sym", "->", "b/test.c"],
            ["x/test.c.sym", "sym", "->", "b/test.c"],
            ["y/", "dir"],
            ["y/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
            ["y/test.c", "sym", "->", "b/test.c"],
            ["y/test.c.lnk", "ref", "==>", "x/test.c.lnk"],
            ["y/test.c.sym", "sym", "->", "b/test.c"],
            ["z/", "dir"],
            ["z/test.c", "ref", "==>", "y/test.c.lnk"],
        ]
    )

    symlink_file("/home", "y/home")

    for create in (True, False):
        for p in ("test.a", "test.b"):
            pp = p + "x"
            dp = "r/" + p
            dpp = "r/" + pp

            if create:
                clone_file(p, dp, sync=sync, simulate=simulate)
                clone_file(p, dpp, sync=sync, simulate=simulate)
                continue

            unlink_file(dp, True, sync=sync, simulate=simulate)
            unlink_file(dp, False, sync=sync, simulate=simulate)
            unlink_file(dp, False, sync=sync, simulate=simulate)

            unlink_file(dpp, False, sync=sync, simulate=simulate)
            if simulate_whole or isinstance(sync, Deferred) and sync.defer:
                unlink_file(dpp, True, sync=sync, simulate=simulate)
            else:
                with pytest.raises(FileNotFoundError):
                    unlink_file(dpp, True, sync=sync, simulate=simulate)
            unlink_file(dpp, False, sync=sync, simulate=simulate)

    check_flush(
        [
            ("makedirs", "r"),
            ("make", "r/test.a.part"),
            ("fsync", "r/test.a.part", 0),
            ("rename", "r/test.a.part", "r/test.a"),
            ("fsync", "r", os.O_DIRECTORY),
            ("makedirs", "r"),
            ("make", "r/test.ax.part"),
            ("fsync", "r/test.ax.part", 0),
            ("rename", "r/test.ax.part", "r/test.ax"),
            ("fsync", "r", os.O_DIRECTORY),
            ("makedirs", "r"),
            ("make", "r/test.b.part"),
            ("fsync", "r/test.b.part", 0),
            ("rename", "r/test.b.part", "r/test.b"),
            ("fsync", "r", os.O_DIRECTORY),
            ("makedirs", "r"),
            ("make", "r/test.bx.part"),
            ("fsync", "r/test.bx.part", 0),
            ("rename", "r/test.bx.part", "r/test.bx"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.a"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.a"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.a"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.ax"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.ax"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.ax"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.b"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.b"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.b"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.bx"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.bx"),
            ("fsync", "r", os.O_DIRECTORY),
            ("unlink", "r/test.bx"),
        ],
        [
            ("fsync", "r", os.O_DIRECTORY),
        ],
        [
            ("makedirs", "r"),
            ("make", "r/test.a.part"),
            ("make", "r/test.ax.part"),
            ("make", "r/test.b.part"),
            ("make", "r/test.bx.part"),
            ("fsync", "r/test.a.part", 0),
            ("fsync", "r/test.ax.part", 0),
            ("fsync", "r/test.b.part", 0),
            ("fsync", "r/test.bx.part", 0),
            ("rename", "r/test.a.part", "r/test.a"),
            ("rename", "r/test.ax.part", "r/test.ax"),
            ("rename", "r/test.b.part", "r/test.b"),
            ("rename", "r/test.bx.part", "r/test.bx"),
            ("unlink", "r/test.a"),
            ("unlink", "r/test.ax"),
            ("unlink", "r/test.b"),
            ("unlink", "r/test.bx"),
        ],
        None,
        [
            ("makedirs", "r"),
            ("make", "r/test.a.part"),
            ("fsync", "r/test.a.part", 0),
            ("rename", "r/test.a.part", "r/test.a"),
            ("makedirs", "r"),
            ("make", "r/test.ax.part"),
            ("fsync", "r/test.ax.part", 0),
            ("rename", "r/test.ax.part", "r/test.ax"),
            ("makedirs", "r"),
            ("make", "r/test.b.part"),
            ("fsync", "r/test.b.part", 0),
            ("rename", "r/test.b.part", "r/test.b"),
            ("makedirs", "r"),
            ("make", "r/test.bx.part"),
            ("fsync", "r/test.bx.part", 0),
            ("rename", "r/test.bx.part", "r/test.bx"),
            ("unlink", "r/test.a"),
            ("unlink", "r/test.a"),
            ("unlink", "r/test.a"),
            ("unlink", "r/test.ax"),
            ("unlink", "r/test.ax"),
            ("unlink", "r/test.ax"),
            ("unlink", "r/test.b"),
            ("unlink", "r/test.b"),
            ("unlink", "r/test.b"),
            ("unlink", "r/test.bx"),
            ("unlink", "r/test.bx"),
            ("unlink", "r/test.bx"),
        ],
    )

    if simulate is not None:
        return

    # to test `describe_forest` with multiple paths
    w = list(describe_forest(["x", "y"], hash_length=8))
    # print(repr(w))
    assert w == [
        ["0/", "dir"],
        ["0/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
        ["0/test.c", "sym", "->", "b/test.c"],
        ["0/test.c.lnk", "sym", "->", "b/test.c"],
        ["0/test.c.sym", "sym", "->", "b/test.c"],
        ["1/", "dir"],
        ["1/home", "sym", "->", "/home"],
        ["1/test.a", "reg", "size", "6", "sha256", "1136b2eb"],
        ["1/test.c", "sym", "->", "b/test.c"],
        ["1/test.c.lnk", "ref", "==>", "0/test.c.lnk"],
        ["1/test.c.sym", "sym", "->", "b/test.c"],
    ]


def test_fs_without_Deferred_no_fsync(tmp_path: str) -> None:
    fs1(tmp_path, False)


def test_fs_without_Deferred_no_fsync_simulate(tmp_path: str) -> None:
    fs1(tmp_path, False, True)


def test_fs_without_Deferred(tmp_path: str) -> None:
    fs1(tmp_path, True)


def test_fs_without_Deferred_simulate(tmp_path: str) -> None:
    fs1(tmp_path, True, True)


def test_fs_with_Deferred_no_defer(tmp_path: str) -> None:
    fs1(tmp_path, Deferred(False))


def test_fs_with_Deferred_no_defer_simulate(tmp_path: str) -> None:
    fs1(tmp_path, Deferred(False), True)


def test_fs_with_Deferred_defer(tmp_path: str) -> None:
    fs1(tmp_path, Deferred(True))


def test_fs_with_Deferred_defer_simulate(tmp_path: str) -> None:
    fs1(tmp_path, Deferred(True), True)
