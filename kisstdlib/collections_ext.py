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
import dataclasses as _dc
import typing as _t

from collections import (  # pylint: disable=unused-import
    namedtuple,
    deque,
    ChainMap,
    Counter,
    OrderedDict,
    defaultdict,
)

from bisect import bisect_left as _bisect_left, bisect_right as _bisect_right

from sortedcontainers import SortedList, SortedKeyList, SortedDict

from .base import (
    SupportsCounting as _SupportsCounting,
    is_infinite as _is_infinite,
    is_closer as _is_closer,
    noop_ as _noop_,
)
from .itertools_ext import (
    chain as _chain,
    first as _first,
    take as _take,
)


class LRUCache[Key, Value](OrderedDict[Key, Value]):
    """LRU Cache derived from OrderedDict.

    Also, this class supports eviction pausing so that
    ```
    c = LRUCache(size)
    with c:
        f(c)
    ```
    would make `c` grow-only while `f` is being computed. It will shrink back to `size` as soon as
    that `with` block ends.
    """

    def __init__(
        self, maxsize: int | None = None, onevict: _t.Callable[[Key, Value], None] = _noop_
    ) -> None:
        self.maxsize = maxsize
        self.onevict = onevict

    def shrink(self) -> None:
        """Start evicting items until the size reaches `.maxsize`."""
        if self.maxsize is not None:
            while len(self) > self.maxsize:
                kv = self.popitem(last=False)
                self.onevict(*kv)

    def __setitem__(self, key: Key, value: Value) -> None:
        OrderedDict.__setitem__(self, key, value)
        self.move_to_end(key)
        self.shrink()

    def __enter__(self) -> None:
        self._maxsize = self.maxsize  # pylint: disable=attribute-defined-outside-init
        self.maxsize = None

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        if hasattr(self, "._maxsize"):
            self.maxsize = self._maxsize
            del self._maxsize
        self.shrink()


class ABCIndex[Key, ValueKey: _SupportsCounting, Value](metaclass=_abc.ABCMeta):
    """Essentially, `dict[Key, SortedList[Value]]` where `Value`s are ordered via
    `value_key: Value -> ValueKey`, with some uselful indexing-relevant operations on top.
    """

    value_key: _t.Callable[[Value], ValueKey]

    def __init__(self, value_key: _t.Callable[[Value], ValueKey]) -> None:
        self.value_key = value_key

    @_abc.abstractmethod
    def __len__(self) -> int:
        """Total number of stored keys."""
        raise NotImplementedError()

    @property
    def size(self) -> int:
        """Total number of stored elements."""
        n = 0
        for _ in self.values():
            n += 1
        return n

    @_abc.abstractmethod
    def __contains__(self, key: Key) -> bool:
        """Check if a key is present."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def __getitem__(self, key: Key) -> SortedKeyList[Value]:
        """Get all elements associated with a key."""
        raise NotImplementedError()

    def get(self, key: Key, default: list[Value] | None = None) -> SortedKeyList[Value] | None:
        """Get all elements associated with a key, or `default`."""
        try:
            return self[key]
        except KeyError:
            if default is None:
                return default
            return SortedKeyList(default, key=self.value_key)

    @_abc.abstractmethod
    def keys(self) -> _t.Iterable[Key]:
        """Iterable over keys."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def values(self) -> _t.Iterable[Value]:
        """Iterable over values."""
        raise NotImplementedError()

    @_abc.abstractmethod
    def insert(self, key: Key, value: Value) -> bool:
        """`self[key].add(value)`, except the implementation can accept some `value`s,
        while rejecting others.

        Should return `True` when the `value` was inserted and `False` otherwise.
        """
        raise NotImplementedError()

    def _iter_from_to(
        self,
        key: Key,
        start: ValueKey,
        end: ValueKey,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[Value]:
        """Iterate over `self[key]` elements from `start` to `end`.

        When `end < start`, iterates in reverse.
        """
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

    def _iter_closest(self, key: Key, ideal: ValueKey) -> _t.Iterator[Value]:
        """Iterate over `self[key]` elements in order of ascending distance from `ideal`."""
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
                if _is_closer(ideal, ileft[0], iright[0]):
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

    def _iter_range(
        self,
        key: Key,
        start: ValueKey,
        end: ValueKey,
        step: int | ValueKey = 0,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[Value]:
        """`_iter_from_to` with `step` support.

        This is a default implementation that works well when `_iter_from_to` does logarithmic
        search, like the above default implementation does. In other cases, a subclass can redefine
        this and define `_iter_from_to` through this instead.
        """
        if step == 0:
            yield from self._iter_from_to(
                key, start, end, include_start=include_start, include_end=include_end
            )
            return

        forwards = start <= end
        prev = None
        again = True
        while again:
            again = False
            for el in self._iter_from_to(
                key, start, end, include_start=include_start, include_end=include_end
            ):
                e = self.value_key(el)
                if prev is not None:
                    # check that `e` is no less than `step` away from `prev`
                    if forwards:
                        if e - prev < step:
                            start = prev + step
                            if start > end:
                                return
                            include_start = True
                            again = True
                            break
                    else:
                        if prev - e < step:
                            start = prev - step
                            if start < end:
                                return
                            include_start = True
                            again = True
                            break
                yield el
                prev = e

    def iter_range(
        self,
        key: Key,
        start: ValueKey,
        end: ValueKey,
        step: int | ValueKey = 0,
        predicate: _t.Callable[[Value], bool] | None = None,
        *,
        include_start: bool = True,
        include_end: bool = False,
    ) -> _t.Iterator[Value]:
        """Iterate over `self[key]` elements satisfying `predicate` from `start` to `end`, producing
        elements separated with no less than `step`.

        By default, this includes the start and excludes the end, like `range` does, but bounds can
        be toggled.
        """
        if predicate is None:
            yield from self._iter_range(
                key, start, end, step, include_start=include_start, include_end=include_end
            )
            return

        for e in self._iter_range(
            key, start, end, step, include_start=include_start, include_end=include_end
        ):
            if predicate(e):
                yield e

    def iter_closest(
        self,
        key: Key,
        ideal: ValueKey,
        predicate: _t.Callable[[Value], bool] | None = None,
    ) -> _t.Iterator[Value]:
        """Iterate over `self[key]` elements satisfying `predicate` in order of ascending distance from
        `ideal`.
        """
        if predicate is None:
            yield from self._iter_closest(key, ideal)
            return

        for e in self._iter_closest(key, ideal):
            if predicate(e):
                yield e

    def take_closest(
        self,
        n: int,
        key: Key,
        ideal: ValueKey,
        predicate: _t.Callable[[Value], bool] | None = None,
    ) -> list[Value]:
        """Of `self[key]` elements satisfying `predicate`, get `n` closest to `ideal`."""
        return _take(n, self.iter_closest(key, ideal, predicate))

    def get_closest(
        self,
        key: Key,
        ideal: ValueKey,
        predicate: _t.Callable[[Value], bool] | None = None,
    ) -> Value | None:
        """Of `self[key]` elements satisfying `predicate`, get the one closest to `ideal`."""
        return _first(self.iter_closest(key, ideal, predicate), None)

    def take_adjacent(
        self,
        n: int,
        key: Key,
        ideal: ValueKey,
        minimum: ValueKey,
        maximum: ValueKey,
        step: int | ValueKey = 0,
        predicate: _t.Callable[[Value], bool] | None = None,
        *,
        include_start: bool = False,
    ) -> tuple[list[Value], list[Value]]:
        """For `self[key]`, get `n` (or less) neighbours of `ideal` satisfying `predicate`, both to its left
        and to its right, each separated by at least `step`.

        If `include_start` is `False` (the default), the neighbourhood gets punctured at `ideal`, so
        elements with `order == ideal` will not appear in the output. Setting `step` also widens the
        puncture by that amount.

        If the index contains elements with `order == ideal`, then calling this with `include_start`
        set to `True` will return them in both tuple elements of the result.
        """
        include_start = include_start or step != 0
        left = _take(
            n,
            self.iter_range(
                key,
                ideal - step,
                minimum,
                step,
                predicate,
                include_start=include_start,
            ),
        )
        right = _take(
            n,
            self.iter_range(
                key,
                ideal + step,
                maximum,
                step,
                predicate,
                include_start=include_start,
            ),
        )
        return left, right

    def get_adjacent(
        self,
        key: Key,
        ideal: ValueKey,
        minimum: ValueKey,
        maximum: ValueKey,
        step: int | ValueKey = 0,
        predicate: _t.Callable[[Value], bool] | None = None,
    ) -> tuple[Value | None, Value | None]:
        """For `self[key]`, get its two closest neighbours satisfying `predicate`, to its left and right.

        The neighbourhood gets punctured at `ideal`, so elements with `order == ideal` will not
        appear in the output.

        Setting `step` also widens the puncture by that amount.
        """
        include_start = step != 0
        left = _first(
            self.iter_range(
                key,
                ideal - step,
                minimum,
                step,
                predicate,
                include_start=include_start,
            ),
            None,
        )
        right = _first(
            self.iter_range(
                key,
                ideal + step,
                maximum,
                step,
                predicate,
                include_start=include_start,
            ),
            None,
        )
        return left, right


class DictIndex[Key, ValueKey: _SupportsCounting, Value](ABCIndex[Key, ValueKey, Value]):
    """`ABCIndex` implementation over a `dict[Key, SortedList[Value]]`, all of which see.

    When `ideal` init parameter is set, `insert` will story only the `value` closest to `ideal`.
    """

    _dict: dict[Key, SortedList[Value]]
    ideal: ValueKey | None
    _size: int

    def __init__(
        self,
        value_key: _t.Callable[[Value], ValueKey],
        ideal: ValueKey | None = None,
        *,
        dict_factory: _t.Callable[[], dict[Key, SortedList[Value]]] = lambda: {},
    ) -> None:
        ABCIndex.__init__(self, value_key)
        self._dict = dict_factory()
        self.ideal = ideal
        self._size = 0

    def __len__(self) -> int:
        return len(self._dict)

    @property
    def size(self) -> int:
        return self._size

    def __contains__(self, key: Key) -> bool:
        return key in self._dict

    def __getitem__(self, key: Key) -> SortedKeyList[Value]:
        return self._dict[key]

    def get(self, key: Key, default: list[Value] | None = None) -> SortedKeyList[Value] | None:
        return ABCIndex.get(self, key, default)

    def keys(self) -> _t.Iterable[Key]:
        return self._dict.keys()

    def values(self) -> _t.Iterable[Value]:
        return _chain.from_iterable(self._dict.values())

    def insert(self, key: Key, value: Value) -> bool:
        iobjs = self.get(key, None)
        if iobjs is None:
            # first time seeing this `key`
            self._dict[key] = SortedKeyList([value], key=self.value_key)
            self._size += 1
        elif self.ideal is not None:
            if _is_closer(self.ideal, self.value_key(value), iobjs[0][0]):
                iobjs.clear()
                iobjs.add(value)
            else:
                return False
        else:
            iobjs.add(value)
            self._size += 1
        return True


class SortedDictIndex[Key, ValueKey: _SupportsCounting, Value](
    DictIndex[Key, ValueKey, Value],
):
    """`ABCIndex` implementation over `SortedDict[Key, SortedList[Value]]`, all of which see.

    Internally, this is just a wrapper over `DictIndex` with `dict_factory` set to use a
    `SortedDict` instead of just `dict`. Thus, all behavioral properties of `DictIndex` apply here
    too, except for `.keys()` being sorted and such.
    """

    def __init__(
        self,
        key_key: _t.Callable[[Key], _t.Any],
        value_key: _t.Callable[[Value], ValueKey],
        ideal: ValueKey | None = None,
    ) -> None:
        DictIndex.__init__(self, value_key, ideal, dict_factory=lambda: SortedDict(key_key))


# /Sorted
