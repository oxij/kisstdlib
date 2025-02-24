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

"""Testing basic `kisstdlib` modules."""

import typing as _t
import pytest

from kisstdlib import *


def test_basics() -> None:
    assert not MISSING

    assert clamp(0, 1, -1) == 0
    assert clamp(0, 1, 0) == 0
    assert clamp(0, 1, 1) == 1
    assert clamp(0, 1, 2) == 1

    assert add_(Decimal(1), 1.0) == 2
    assert sub_(Decimal(1), 1.0) == 0
    assert mul_(Decimal(1), 1.0) == 1
    assert truediv_(Decimal(1), 1.0) == 1

    assert first([], None) == first((), None) == None
    assert last([], None) == last((), None) == None
    assert first([123], None) == first((123,), None) == 123
    assert last([123], None) == last((123,), None) == 123
    assert nth(0, [], None) == nth(0, (), None) == None

    e: _t.Any
    for e in ((), []):
        with pytest.raises(IndexError):
            first(e)
        with pytest.raises(IndexError):
            last(e)
    for i in (-10, -1, 0, 1, 10):
        for e in ((), []):
            with pytest.raises(IndexError):
                nth(i, e)

    l = [123, 456, 789] + list(range(0, 10))
    while l:
        t = tuple(l)

        assert first(l, None) == first(t, None) == l[0]
        assert last(l, None) == last(t, None) == l[-1]

        assert not take(-1, l)
        for i in range(0, len(l) + 1):
            assert take(i, l) == l[:i]

        assert drop(-1, l) == l
        for i in range(0, len(l) + 1):
            assert drop(i, l) == l[i:]

        for i in range(0, len(l) + 1):
            assert drop(i, l) == l[i:]

        assert nth(0, l, None) == nth(0, t, None) == l[0]
        assert nth(1, l, None) == nth(1, t, None) == (l[1] if len(l) > 1 else None)

        l.pop()

    assert list(diff_sorted([1, 3, 4], [2, 3, 5])) == [
        Left(1),
        Right(2),
        (3, 3),
        Left(4),
        Right(5),
    ]

    # string abbreviation

    for n in range(0, 4):
        assert abbrev("abcde", n, False, True) == "..."
        assert abbrev("abcde", n, True, False) == "..."
        assert abbrev("abcde", n, False, False) == "..."
        assert abbrev("abcde", n, True, True) == "..."

    assert abbrev("abcde", 4, False, True) == "a..."
    assert abbrev("abcde", 4, True, False) == "...e"
    assert abbrev("abcde", 4, False, False) == "a..."
    assert abbrev("abcde", 4, True, True) == "..."

    assert abbrev("abcdef", 4, False, True) == "a..."
    assert abbrev("abcdef", 4, True, False) == "...f"
    assert abbrev("abcdef", 4, False, False) == "a..."
    assert abbrev("abcdef", 4, True, True) == "..."

    assert abbrev("abcde", 5, False, True) == "abcde"
    assert abbrev("abcde", 5, True, False) == "abcde"
    assert abbrev("abcde", 5, False, False) == "abcde"
    assert abbrev("abcde", 5, True, True) == "abcde"

    assert abbrev("abcdef", 5, False, True) == "ab..."
    assert abbrev("abcdef", 5, True, False) == "...ef"
    assert abbrev("abcdef", 5, False, False) == "a...f"
    assert abbrev("abcdef", 5, True, True) == "..."

    assert abbrev("abcde", 2, False, True, ".") == "a."
    assert abbrev("abcde", 2, True, False, ".") == ".e"
    assert abbrev("abcde", 2, False, False, ".") == "a."
    assert abbrev("abcde", 2, True, True, ".") == "."

    assert abbrev("abcde", 3, False, True, ".") == "ab."
    assert abbrev("abcde", 3, True, False, ".") == ".de"
    assert abbrev("abcde", 3, False, False, ".") == "a.e"
    assert abbrev("abcde", 3, True, True, ".") == ".c."

    assert abbrev("abcde", 4, False, False, ".") == "ab.e"
    assert abbrev("abcde", 4, True, True, ".") == ".bc."

    assert abbrev("abcdef", 3, False, True, ".") == "ab."
    assert abbrev("abcdef", 3, True, False, ".") == ".ef"
    assert abbrev("abcdef", 3, False, False, ".") == "a.f"
    assert abbrev("abcdef", 3, True, True, ".") == ".d."
    assert abbrev("abcdef", 4, True, True, ".") == ".cd."
    assert abbrev("abcdef", 5, True, True, ".") == ".cde."
    assert abbrev("abcdef", 6, True, True, ".") == "abcdef"
    assert abbrev("abcdefg", 6, True, True, ".") == ".bcde."
