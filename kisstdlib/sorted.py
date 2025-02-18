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

import abc as _abc
import collections.abc as _cabc
import dataclasses as _dc
import typing as _t

from bisect import bisect_left as _bisect_left, bisect_right as _bisect_right

from sortedcontainers import SortedList, SortedKeyList, SortedDict  # pylint: disable=unused-import

from kisstdlib.base import (
    Decimal as _Decimal,
    Number as _Number,
    AnyNumber as _AnyNumber,
    is_infinite as _is_infinite,
    add_ as _add_,
    sub_ as _sub_,
)

from kisstdlib.itertools_ext import (
    chain as _chain,
    first as _first,
    take as _take,
)


def nearer_to_than(ideal: _AnyNumber, value: _AnyNumber, other: _AnyNumber) -> bool | None:
    """Check whether `value` is nearer to `ideal` than `other`.
    Return `None` if `other` and `value` are the same.
    """
    if other == value:
        return None
    if _is_infinite(ideal):
        return (ideal < 0) ^ (other < value)  # type: ignore
    return abs(ideal - value) < abs(ideal - other)  # type: ignore


KeyType = _t.TypeVar("KeyType")
ValueType = _t.TypeVar("ValueType")


class AbstractSortedIndex(_t.Generic[KeyType, _AnyNumber, ValueType], metaclass=_abc.ABCMeta):
    """Essentially, `SortedDict[KeyType, SortedList[ValueType]]` + a pair of
    functions:

    - `key_key: KeyType -> ComparableKey`,
    - `value_key: ValueType -> AnyNumber`.

    with some uselful indexing-relevant operations on top.
    """

    # Sorting key functions.
    key_key: _t.Callable[[KeyType], _t.Any]
    value_key: _t.Callable[[ValueType], _AnyNumber]

    # Total number of stored elements.
    size: int

    @_abc.abstractmethod
    def __len__(self) -> int:
        """Total number of stored keys."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def keys(self) -> _t.Iterable[KeyType]:
        """Iterable over keys."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def values(self) -> _t.Iterable[ValueType]:
        """Iterable over values."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def insert(self, key: KeyType, value: ValueType) -> bool:
        """`self[key].add(value)`, except the implementation can accept some `value`s,
        while rejecting others.

        Should return `True` when the `value` was inserted and `False` otherwise.
        """
        raise NotImplementedError()

    @_abc.abstractmethod
    def internal_from_to(
        self,
        key: KeyType,
        start: _Number,
        end: _Number,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[ValueType]:
        """Iterate over `self[key]` elements from `start` to `end`.

        The case of `end < start` should be supported, iterating in reverse.
        """
        raise NotImplementedError()

    @_abc.abstractmethod
    def internal_from_nearest(self, key: KeyType, ideal: _Number) -> _t.Iterator[ValueType]:
        """Iterate over `self[key]` elements in order of ascending distance from
        `ideal`.
        """
        raise NotImplementedError()

    def internal_from_to_step(
        self,
        key: KeyType,
        start: _Number,
        end: _Number,
        step: _Number = 0,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[ValueType]:
        """`internal_from_to` with `step` support.

        This implements a default implementation that works well when
        `internal_from_to` does logarithmic search. In other cases, a subclass
        can redefine this and define `internal_from_to` through this instead.
        """
        if step == 0:
            yield from self.internal_from_to(
                key, start, end, include_start=include_start, include_end=include_end
            )
            return

        forwards = start <= end
        prev = None
        again = True
        while again:
            again = False
            for e in self.internal_from_to(
                key, start, end, include_start=include_start, include_end=include_end
            ):
                if prev is not None:
                    # check that `e` is no less than `step` away from `prev`
                    if forwards:
                        if e[0] - prev[0] < step:
                            start = _add_(prev[0], step)
                            if start > end:
                                return
                            include_start = True
                            again = True
                            break
                    else:
                        if prev[0] - e[0] < step:
                            start = _sub_(prev[0], step)
                            if start < end:
                                return
                            include_start = True
                            again = True
                            break
                yield e
                prev = e

    def iter_range(
        self,
        key: KeyType,
        start: _Number,
        end: _Number,
        step: _Number = 0,
        predicate: _t.Callable[[ValueType], bool] | None = None,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[ValueType]:
        """Iterate over `self[key]` elements satisfying `predicate` from `start` to
        `end`, producing elements separated with no less than `step`.

        By default, this includes the start and excludes the end, like `range`
        does, but bounds can be toggled.
        """
        if predicate is None:
            yield from self.internal_from_to_step(
                key, start, end, step, include_start=include_start, include_end=include_end
            )
            return

        for e in self.internal_from_to_step(
            key, start, end, step, include_start=include_start, include_end=include_end
        ):
            if predicate(e):
                yield e

    def iter_nearest(
        self,
        key: KeyType,
        ideal: _Number,
        predicate: _t.Callable[[ValueType], bool] | None = None,
    ) -> _t.Iterator[ValueType]:
        """Iterate over `self[key]` elements satisfying `predicate` in order of
        ascending distance from `ideal`.
        """
        if predicate is None:
            yield from self.internal_from_nearest(key, ideal)
            return

        for e in self.internal_from_nearest(key, ideal):
            if predicate(e):
                yield e

    def get_nearest(
        self,
        n: int,
        key: KeyType,
        ideal: _Number,
        predicate: _t.Callable[[ValueType], bool] | None = None,
    ) -> list[ValueType]:
        """Of `self[key]` elements satisfying `predicate`, get `n` closest to `ideal`."""
        return _take(n, self.iter_nearest(key, ideal, predicate))

    def get_nearest1(
        self,
        key: KeyType,
        ideal: _Number,
        predicate: _t.Callable[[ValueType], bool] | None = None,
    ) -> ValueType | None:
        """Of `self[key]` elements satisfying `predicate`, get the one closest to `ideal`."""
        return _first(self.iter_nearest(key, ideal, predicate), None)

    def get_neighboring(
        self,
        n: int,
        key: KeyType,
        ideal: _Number,
        step: _Number = 0,
        predicate: _t.Callable[[ValueType], bool] | None = None,
        *,
        include_start: bool = False,
    ) -> tuple[list[ValueType], list[ValueType]]:
        """For `self[key]`, get `n` (or less) neighbours of `ideal` satisfying
        `predicate`, both to its left and to its right, each separated by at
        least `step`.

        If `include_start` is `False` (the default), the neighbourhood gets
        punctured at `ideal`, so elements with `order == ideal` will not appear
        in the output. Setting `step` also widens the puncture by that amount.

        If the index contains elements with `order == ideal`, then calling this
        with `include_start` set to `True` will return the first such element in
        both sides of the produced result.
        """
        include_start = include_start or step != 0
        left = _take(
            n,
            self.iter_range(
                key,
                _sub_(ideal, step),
                _Decimal("-inf"),
                step,
                predicate,
                include_start=include_start,
            ),
        )
        right = _take(
            n,
            self.iter_range(
                key,
                _add_(ideal, step),
                _Decimal("+inf"),
                step,
                predicate,
                include_start=include_start,
            ),
        )
        return left, right

    def get_neighboring2(
        self,
        key: KeyType,
        ideal: _Number,
        step: _Number = 0,
        predicate: _t.Callable[[ValueType], bool] | None = None,
    ) -> tuple[ValueType | None, ValueType | None]:
        """For `self[key]`, get its two closest neighbours satisfying `predicate`, to
        its left and right.

        The neighbourhood gets punctured at `ideal`, so elements with `order ==
        ideal` will not appear in the output.

        Setting `step` also widens the puncture by that amount.
        """
        include_start = step != 0
        left = _first(
            self.iter_range(
                key,
                _sub_(ideal, step),
                _Decimal("-inf"),
                step,
                predicate,
                include_start=include_start,
            ),
            None,
        )
        right = _first(
            self.iter_range(
                key,
                _add_(ideal, step),
                _Decimal("+inf"),
                step,
                predicate,
                include_start=include_start,
            ),
            None,
        )
        return left, right


class SortedIndex(
    SortedDict[KeyType, SortedList[ValueType]],  # type: ignore
    AbstractSortedIndex[KeyType, _AnyNumber, ValueType],
    _t.Generic[KeyType, _AnyNumber, ValueType],
):
    """`AbstractSortedIndex` implementation over a simple
    `SortedDict[KeyType, SortedList[ValueType]]`.

    Except, when `ideal` init parameter is set, `insert` will story only the
    `value` closest to `ideal`.
    """

    def __init__(
        self,
        key_key: _t.Callable[[KeyType], _t.Any],
        value_key: _t.Callable[[ValueType], _AnyNumber],
        ideal: _AnyNumber | None = None,
    ) -> None:
        super().__init__(key_key)
        self.key_key = key_key
        self.value_key = value_key
        self.ideal = ideal
        self.size = 0

    def values(self) -> _t.Iterable[ValueType]:  # type: ignore
        return _chain.from_iterable(SortedDict.values(self))

    def insert(self, key: KeyType, value: ValueType) -> bool:
        iobjs = self.get(key, None)
        if iobjs is None:
            # first time seeing this `key`
            self[key] = SortedKeyList([value], key=self.value_key)
            self.size += 1
        elif self.ideal is not None:
            if nearer_to_than(self.ideal, self.value_key(value), iobjs[0][0]):
                iobjs.clear()
                iobjs.add(value)
            else:
                return False
        else:
            iobjs.add(value)
            self.size += 1
        return True

    def internal_from_to(
        self,
        key: KeyType,
        start: _Number,
        end: _Number,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[ValueType]:
        try:
            iobjs = self[key]
        except KeyError:
            # unavailable
            return

        if start == end and (not include_start or not include_end):
            return
        if start <= end:
            if include_start:
                left = _bisect_left(iobjs, start, key=self.value_key)
            else:
                left = _bisect_right(iobjs, start, key=self.value_key)

            for i in range(left, len(iobjs)):
                cur = iobjs[i]
                curi = cur[0]
                if (
                    start < curi < end
                    or include_start
                    and curi == start
                    or include_end
                    and curi == end
                ):
                    yield cur
                else:
                    return
        else:
            if include_start:
                right = _bisect_right(iobjs, start, key=self.value_key)
            else:
                right = _bisect_left(iobjs, start, key=self.value_key)

            for i in range(right - 1, -1, -1):
                cur = iobjs[i]
                curi = cur[0]
                if (
                    end < curi < start
                    or include_start
                    and curi == start
                    or include_end
                    and curi == end
                ):
                    yield cur
                else:
                    return

    def internal_from_nearest(self, key: KeyType, ideal: _Number) -> _t.Iterator[ValueType]:
        try:
            iobjs = self[key]
        except KeyError:
            # unavailable
            return

        ilen = len(iobjs)
        if ilen == 1:
            yield iobjs[0]
            return
        if _is_infinite(ideal):
            # oldest or latest
            yield from iter(iobjs) if ideal < 0 else reversed(iobjs)
            return
        # else: # nearest to `ideal`

        right = _bisect_right(iobjs, ideal, key=self.value_key)
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
            for i in range(left, -1, -1):
                yield iobjs[i]


# /Sorted
