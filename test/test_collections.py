# Copyright (c) 2023-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Testing `kisstdlib.sorted` module."""

import typing as _t

from kisstdlib import *


def prefill_Index[ValueKey: SupportsCounting](
    index: ABCIndex[str, ValueKey, tuple[ValueKey, None]],
    key: str,
    ranges: list[tuple[ValueKey, ValueKey, ValueKey]],
    elements: list[tuple[ValueKey, None]],
) -> None:
    for mini, maxi, step in ranges:
        for i in range_(mini, maxi, step):
            e = (i, None)
            index.insert(key, e)
            elements.append(e)


def skip[ValueKey: SupportsCounting, A](
    step: ValueKey, xs: _t.Iterable[tuple[ValueKey, A]]
) -> _t.Iterator[tuple[ValueKey, A]]:
    prev = None
    for x in xs:
        if prev is not None and abs(prev[0] - x[0]) < step:
            continue
        yield x
        prev = x


def iter_range_result[ValueKey: SupportsCounting, A](
    elements: list[tuple[ValueKey, A]],
    start: ValueKey,
    end: ValueKey,
    step: ValueKey,
    i_s: bool,
    i_e: bool,
) -> list[tuple[ValueKey, A]]:
    if start == end:
        if i_s and i_e:
            return [e for e in elements if e[0] == start]
        return []
    if start <= end:
        f = filter(
            lambda x: start < x[0] < end or i_s and x[0] == start or i_e and x[0] == end,
            elements,
        )
        return list(skip(step, f))
    f = filter(
        lambda x: end < x[0] < start or i_s and x[0] == start or i_e and x[0] == end,
        elements,
    )
    l = list(f)
    l.reverse()
    return list(skip(step, l))


def check_Index_range[ValueKey: SupportsCounting, A](
    index: ABCIndex[str, ValueKey, tuple[ValueKey, A]],
    key: str,
    elements: list[tuple[ValueKey, A]],
    mini: ValueKey,
    maxi: ValueKey,
    zero: ValueKey,
    maxstep: ValueKey,
    nstep: ValueKey,
) -> None:
    for i in range_(mini, maxi, nstep):
        for j in range_(mini, maxi, nstep):
            for step in range_(zero, maxstep, nstep):
                for i_s in (True, False):
                    for i_e in (True, False):
                        # print((i, j, step, i_s, i_e))
                        # if (i, j, step, i_s, i_e) == (0.0, 0.0, 0, True, True):
                        #    breakpoint()
                        r = list(
                            index.iter_range(key, i, j, step, include_start=i_s, include_end=i_e)
                        )
                        assert r == iter_range_result(elements, i, j, step, i_s, i_e)


def check_Index_closest[ValueKey: SupportsCounting, A](
    index: ABCIndex[str, ValueKey, tuple[ValueKey, A]],
    key: str,
    elements: list[tuple[ValueKey, A]],
    mini: ValueKey,
    maxi: ValueKey,
    nstep: ValueKey,
) -> None:
    for i in range_(mini, maxi, nstep):
        # print(i)
        r = list(index.iter_closest(key, i))
        # because right-most elements go first
        s: list[tuple[ValueKey, A]]
        s = list(filter(lambda x: x[0] >= i, elements))  # pylint: disable=cell-var-from-loop
        s += list(filter(lambda x: x[0] < i, elements))  # pylint: disable=cell-var-from-loop
        s.sort(key=lambda x: abs(x[0] - i))  # pylint: disable=cell-var-from-loop
        assert r == s


def check_Index[ValueKey: SupportsCounting](
    index: ABCIndex[str, ValueKey, tuple[ValueKey, None]],
    f: _t.Callable[[int | str], ValueKey],
    maxi: int,
) -> None:
    elements_a: list[tuple[ValueKey, None]] = []
    prefill_Index(index, "a", [(f(30), f(50), f(1))], elements_a)
    assert "a" in index
    assert "b" not in index

    elements_b: list[tuple[ValueKey, None]] = []
    prefill_Index(
        index,
        "b",
        [
            (f(0), f(8), f(1)),
            (f(20), f(31), f("0.5")),
            (f(32), f(50), f("0.25")),
            (f(59), f(100), f("0.3")),
        ],
        elements_b,
    )
    assert "a" in index
    assert "b" in index

    for k, els in [("a", elements_a), ("b", elements_b)]:
        check_Index_closest(index, k, els, f(-2), f(102), f("0.5"))
        check_Index_range(index, k, els, f(-2), f(maxi), f(0), f(3), f("0.5"))


def test_DictIndex_slow(maxi: int = 102) -> None:
    check_Index(DictIndex(value_key=fst), float, maxi)
    check_Index(DictIndex(value_key=fst), Decimal, maxi)


def test_DictIndex_quick() -> None:
    test_DictIndex_slow(10)


def test_SortedDictIndex_slow(maxi: int = 102) -> None:
    check_Index(SortedDictIndex(key_key=identity, value_key=fst), float, maxi)
    check_Index(SortedDictIndex(key_key=identity, value_key=fst), Decimal, maxi)


def test_SortedDictIndex_quick() -> None:
    test_SortedDictIndex_slow(10)
