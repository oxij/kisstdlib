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

"""Testing `kisstdlib.io` modules."""

import io as _io
import typing as _t

from kisstdlib.io.base import *
from kisstdlib.io.adapter import *
from kisstdlib.io.wrapper import *


def test_adapters() -> None:
    buf = _io.BytesIO()

    u2d = UNIX2DOSWriter(buf)
    orig = b"Hello, World!\nFoo\rBar\r"
    u2d.write(orig)
    assert buf.getvalue() == b"Hello, World!\r\nFoo\rBar\r"

    buf.seek(0)

    d2u = DOS2UNIXReader(buf)
    assert d2u.read() == orig


def test_ansi_set() -> None:
    def check(*args: _t.Any, **kwargs: _t.Any) -> bytes:
        x = TIOWrappedWriter(_io.BytesIO(), ansi=True)
        x.ansi_set(*args, **kwargs)
        return x.fobj.getvalue()  # type: ignore

    assert check() == b""
    assert check(reset=True) == b"\x1b[0m"
    assert check(modes=1, reset=True) == b"\x1b[0;1m"
    assert check(0, 0, 0) == b"\x1b[0;30;40m"
    assert check(0, 0, 1) == b"\x1b[1;30;40m"
    assert check(0, 0, 1, True) == b"\x1b[0;1;30;40m"
    assert check(1, 1, 0) == b"\x1b[0;31;41m"
    assert check(8, 8, 0) == b"\x1b[0;90;100m"
    assert check(9, 9, 0) == b"\x1b[0;91;101m"
    assert check(16, 16, 0) == b"\x1b[0m\x1b[38;5;16m\x1b[48;5;16m"
    assert check(255, 255, 0) == b"\x1b[0m\x1b[38;5;255m\x1b[48;5;255m"


def run_TIOWrappers(ansi: bool) -> tuple[bytes, bytes, bytes]:
    a = TIOWrappedWriter(_io.BytesIO(), ansi=ansi)
    a.write_str_ln("Hello, World!")
    a.write_str_ln("This is default red.", color=1)

    b = TIOWrappedWriter(_io.BytesIO(), ansi=ansi)
    b.write_str_ln("Hello, World!")
    b.write_str_ln("This is bold red on white.", modes=[1], color=1, background=7)

    c = TIOWrappedWriter(_io.BytesIO(), ansi=ansi)
    c.write_str_ln("Hello, World!")
    c.ansi_clear_line()
    c.ansi_clear_line(False)
    c.ansi_clear_line(after=False)
    c.ansi_clear_screen()
    c.ansi_clear_screen(False)
    c.ansi_clear_screen(after=False)
    c.ansi_move(2, 2)
    c.ansi_move(-2, -2)
    return (a.fobj.getvalue(), b.fobj.getvalue(), c.fobj.getvalue())


def test_TIOWrappers() -> None:
    assert run_TIOWrappers(False) == (
        b"Hello, World!\nThis is default red.\n",
        b"Hello, World!\nThis is bold red on white.\n",
        b"Hello, World!\n\n\n\n\n\n\n",
    )
    assert run_TIOWrappers(True) == (
        b"Hello, World!\n\x1b[0;31mThis is default red.\x1b[0m\n",
        b"Hello, World!\n\x1b[0;1;31;47mThis is bold red on white.\x1b[0m\n",
        b"Hello, World!\n\x1b[2K\x1b[0K\x1b[1K\x1b[2J\x1b[0J\x1b[1J\x1b[2B\x1b[2C\x1b[2A\x1b[2D",
    )
