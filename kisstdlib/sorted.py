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

"""Various sorted containers."""

import bisect as _bisect
import collections.abc as _abc
import dataclasses as _dc
import math as _math
import typing as _t

from decimal import Decimal

from sortedcontainers import SortedList, SortedKeyList, SortedDict  # pylint: disable=unused-import

import kisstdlib.util as _ku

NumericType = _t.TypeVar("NumericType", bound=Decimal | float | int)


def is_infinite(value: NumericType) -> bool:
    return (
        hasattr(value, "is_infinite")
        and value.is_infinite()
        or isinstance(value, float)
        and _math.isinf(value)
    )


def nearer_to_than(ideal: NumericType, value: NumericType, other: NumericType) -> bool | None:
    """Check whether `value` is nearer to `ideal` than `other`.
    Return `None` if `other` and `value` are the same.
    """
    if other == value:
        return None
    if is_infinite(ideal):
        return (ideal < 0) ^ (other < value)  # type: ignore
    return abs(ideal - value) < abs(ideal - other)  # type: ignore


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


KeyType = _t.TypeVar("KeyType")
ValueType = _t.TypeVar("ValueType")


class SortedIndex(
    dict[KeyType, SortedList[tuple[NumericType, ValueType]]],
    _t.Generic[KeyType, NumericType, ValueType],
):
    """Essentially,
    `dict[KeyType, SortedList[tuple[NumericType, ValueType]]]`
     with some uselful indexing-relevant operations on top.
    """

    def __init__(self) -> None:
        super().__init__()
        self.size = 0

    def insert(
        self, key: KeyType, order: NumericType, value: ValueType, ideal: NumericType | None = None
    ) -> bool:
        """`self[key].add((order, value))`, except when `ideal` init param is set, the
        `SortedList` will only store a single `value`, the one for
        which the `order` is closest to `ideal`.

        Returns `True` when the `value` was inserted and `False` otherwise.
        """

        iobjs = self.get(key, None)
        if iobjs is None:
            # first time seeing this `key`
            self[key] = SortedKeyList([(order, value)], key=_ku.first)
            self.size += 1
        elif ideal is not None:
            if nearer_to_than(ideal, order, iobjs[0][0]):
                iobjs.clear()
                iobjs.add((order, value))
            else:
                return False
        else:
            iobjs.add((order, value))
            self.size += 1
        return True

    def iter_from_to(
        self, key: KeyType, start: NumericType, end: NumericType
    ) -> _t.Iterator[tuple[NumericType, ValueType]]:
        """Iterate `self[key]` `list` values from `start` (including) to `end` (not including)."""

        try:
            iobjs = self[key]
        except KeyError:
            # unavailable
            return

        left = _bisect.bisect_left(iobjs, start, key=_ku.first)
        for i in range(left, len(iobjs)):
            cur = iobjs[i]
            if start <= cur[0] < end:
                yield cur
            else:
                return

    def iter_from_nearest(
        self, key: KeyType, ideal: NumericType
    ) -> _t.Iterator[tuple[NumericType, ValueType]]:
        """Iterate `self[key]` `list` values in order of closeness to `ideal`."""

        try:
            iobjs = self[key]
        except KeyError:
            # unavailable
            return

        ilen = len(iobjs)
        if ilen == 1:
            yield iobjs[0]
            return
        if is_infinite(ideal):
            # oldest or latest
            yield from iter(iobjs) if ideal < 0 else reversed(iobjs)
            return
        # else: # nearest to `ideal`

        right = _bisect.bisect_right(iobjs, ideal, key=_ku.first)
        if right == 0:
            yield from iter(iobjs)
            return
        if right >= ilen:
            yield from reversed(iobjs)
            return

        # the complicated case, when `right` is in the middle somewhere
        left = right - 1
        if left >= 0 and right < ilen:
            ileft = iobjs[left]
            iright = iobjs[right]
            while True:
                if nearer_to_than(ideal, ileft[0], iright[0]):
                    yield ileft
                    left -= 1
                    if left >= 0:
                        ileft = iobjs[left]
                    else:
                        break
                else:
                    yield iright
                    right += 1
                    if right < ilen:
                        iright = iobjs[right]
                    else:
                        break

        # yield any leftovers
        if left < 0:
            for i in range(right, ilen):
                yield iobjs[i]
        elif right >= ilen:
            for i in range(left - 1, -1, -1):
                yield iobjs[i]

    def iter_nearest(
        self,
        key: KeyType,
        ideal: NumericType,
        predicate: _t.Callable[[NumericType, ValueType], bool] | None = None,
    ) -> _t.Iterator[tuple[NumericType, ValueType]]:
        if predicate is None:
            yield from self.iter_from_nearest(key, ideal)
        else:
            for e in self.iter_from_nearest(key, ideal):
                if predicate(*e):
                    yield e

    def get_nearest(
        self,
        key: KeyType,
        ideal: NumericType,
        predicate: _t.Callable[[NumericType, ValueType], bool] | None = None,
    ) -> tuple[NumericType, ValueType] | None:
        """Of `self[key]` `list` values satisfying `predicate`, get one closest to `ideal`."""
        for e in self.iter_nearest(key, ideal, predicate):
            return e
        return None
