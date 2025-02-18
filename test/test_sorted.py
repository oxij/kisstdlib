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

import math as _math
import typing as _t

from kisstdlib import *
from kisstdlib.sorted import *


def test_nearer_to_than() -> None:
    assert nearer_to_than(1, 0, 0) is None
    assert nearer_to_than(0, 10, 100)
    assert nearer_to_than(0, 100, 10) is False

    inf: Decimal | float
    for inf in [Decimal("+inf"), _math.inf]:  # type: ignore
        assert nearer_to_than(inf, 1, 0)
        assert nearer_to_than(-inf, 0, 1)
        assert nearer_to_than(inf, 0, 1) is False
        assert nearer_to_than(-inf, 1, 0) is False


def prefill_AbstractSortedIndex(
    index: AbstractSortedIndex[str, Number, tuple[Number, None]],
    key: str,
    elements: list[tuple[Number, None]],
    ranges: list[tuple[Number, Number, Number]],
) -> None:
    for mini, maxi, step in ranges:
        for i in count_from_to(mini, maxi, step):
            e = (i, None)
            index.insert(key, e)
            elements.append(e)


def skip(step: Number, xs: _t.Iterable[tuple[Number, AType]]) -> _t.Iterator[tuple[Number, AType]]:
    prev = None
    for x in xs:
        if prev is not None and abs(prev[0] - x[0]) < step:
            continue
        yield x
        prev = x


def iter_range_result(
    elements: list[tuple[Number, AType]],
    start: Number,
    end: Number,
    step: Number,
    i_s: bool,
    i_e: bool,
) -> list[tuple[Number, AType]]:
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


def check_AbstractSortedIndex_range(
    index: AbstractSortedIndex[str, Number, tuple[Number, AType]],
    key: str,
    elements: list[tuple[Number, AType]],
    mini: Number,
    maxi: Number,
    maxstep: Number,
    nstep: Number,
) -> None:
    for i in count_from_to(mini, maxi, nstep):
        for j in count_from_to(mini, maxi, nstep):
            for step in count_from_to(0, maxstep, nstep):
                for i_s in (True, False):
                    for i_e in (True, False):
                        # print((i, j, step, i_s, i_e))
                        # if (i, j, step, i_s, i_e) == (0.0, 0.0, 0, True, True):
                        #    breakpoint()
                        r = list(
                            index.iter_range(key, i, j, step, include_start=i_s, include_end=i_e)
                        )
                        assert r == iter_range_result(elements, i, j, step, i_s, i_e)


def check_AbstractSortedIndex_nearest(
    index: AbstractSortedIndex[str, Number, tuple[Number, AType]],
    key: str,
    elements: list[tuple[Number, AType]],
    mini: Number,
    maxi: Number,
    nstep: Number,
) -> None:
    for i in count_from_to(mini, maxi, nstep):
        # print(i)
        r = list(index.iter_nearest(key, i))
        # because right-most elements go first
        s: list[tuple[Number, AType]]
        s = list(filter(lambda x: x[0] >= i, elements))  # pylint: disable=cell-var-from-loop
        s += list(filter(lambda x: x[0] < i, elements))  # pylint: disable=cell-var-from-loop
        s.sort(key=lambda x: abs(sub_(x[0], i)))  # type: ignore # pylint: disable=cell-var-from-loop
        assert r == s


def check_AbstractSortedIndex(
    index: AbstractSortedIndex[str, Number, tuple[Number, None]], maxi: int = 102
) -> None:
    elements_a: list[tuple[Number, None]] = []
    prefill_AbstractSortedIndex(
        index, "a", elements_a, [(0, 8, 1), (20, 31, 0.5), (32, 50, 0.25), (59, 100, 0.3)]
    )
    prefill_AbstractSortedIndex(index, "b", [], [(30, 50, 1)])
    check_AbstractSortedIndex_nearest(index, "a", elements_a, -2, 102, 0.5)
    check_AbstractSortedIndex_range(index, "a", elements_a, -2, maxi, 3, 0.5)


def test_SortedIndex_quick() -> None:
    test_SortedIndex_slow(10)


def test_SortedIndex_slow(maxi: int = 102) -> None:
    check_AbstractSortedIndex(SortedIndex(key_key=identity, value_key=fst), maxi)
