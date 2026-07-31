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

"""Testing `kisstdlib.parsing` module."""

import typing as _t

import pytest

from kisstdlib.parsing import *


def test_BytesTransformer() -> None:
    unix2dos = BytesTransformer(LF2CRLF)
    dos2unix = BytesTransformer(CRLF2LF)

    def check(a: bytes, b: bytes) -> None:
        assert unix2dos.update(a) == b
        assert dos2unix.update(b) == a

    check(b"", b"")
    check(b"\n", b"\r\n")
    check(b"foo\n", b"foo\r\n")
    check(b"foo\nbar", b"foo\r\nbar")
    check(b"foo\r\n", b"foo\r\r\n")
    check(b"foo\r\nbar", b"foo\r\r\nbar")

    assert dos2unix.update(b"foo\r") == b"foo"
    assert dos2unix.update(b"bar") == b"\rbar"

    assert dos2unix.update(b"foo\r") == b"foo"
    assert dos2unix.update(b"\n") == b"\n"


def test_Parser_advance_pos() -> None:
    s = "abc\ndefj\nghk"
    p = Parser(s)
    assert p.pos == (0, 1, 0) and p.leftovers() == s

    with pytest.raises(IndexError):
        p.advance(-1)
    assert p.pos == (0, 1, 0)

    p.advance(1)
    assert p.pos == (1, 1, 1)
    p.advance(1)
    assert p.pos == (2, 1, 2)
    p.advance(1)
    assert p.pos == (3, 1, 3)
    p.advance(1)
    assert p.pos == (4, 2, 0)
    p.advance(1)
    assert p.pos == (5, 2, 1)
    p.advance(1)
    assert p.pos == (6, 2, 2)
    p.advance(1)
    assert p.pos == (7, 2, 3)
    p.advance(1)
    assert p.pos == (8, 2, 4)
    p.advance(1)
    assert p.pos == (9, 3, 0)
    p.advance(1)
    assert p.pos == (10, 3, 1)
    p.advance(1)
    assert p.pos == (11, 3, 2)
    p.advance(1)
    assert p.pos == (12, 3, 3) and p.leftovers() == ""
    with pytest.raises(IndexError):
        p.advance(1)
    assert p.pos == (12, 3, 3)

    p.advance(-1)
    assert p.pos == (11, 3, 2)
    p.advance(-1)
    assert p.pos == (10, 3, 1)
    p.advance(-1)
    assert p.pos == (9, 3, 0)
    p.advance(-1)
    assert p.pos == (8, 2, 4)
    p.advance(-1)
    assert p.pos == (7, 2, 3)
    p.advance(-1)
    assert p.pos == (6, 2, 2)
    p.advance(-1)
    assert p.pos == (5, 2, 1)
    p.advance(-1)
    assert p.pos == (4, 2, 0)
    p.advance(-1)
    assert p.pos == (3, 1, 3)
    p.advance(-1)
    assert p.pos == (2, 1, 2)
    p.advance(-1)
    assert p.pos == (1, 1, 1)
    p.advance(-1)
    assert p.pos == (0, 1, 0)

    p.move_to(11)
    assert p.pos == (11, 3, 2)
    p.move_to(5)
    assert p.pos == (5, 2, 1)
    p.move_to(11)
    assert p.pos == (11, 3, 2)
    p.move_to(3)
    assert p.pos == (3, 1, 3)
    p.move_to(11)
    assert p.pos == (11, 3, 2)
    p.move_to(1)
    assert p.pos == (1, 1, 1)
