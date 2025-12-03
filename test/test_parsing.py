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
