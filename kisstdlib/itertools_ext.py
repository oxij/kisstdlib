# Copyright (c) 2024-2025 Jan Malakhovski <oxij@oxij.org>
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

"""An extension for `itertools`."""

import typing as _t

from itertools import *

from .base import (
    Missing,
    MISSING,
    Number,
    Either,
    Left,
    Right,
    AType as _AType,
    BType as _BType,
    CType as _CType,
    add_ as _add_,
    identity as _identity,
)


def count_(start: Number = 0, step: Number = 1) -> _t.Iterator[Number]:
    """`itertools.count` for arbitrary `Number`s."""
    if isinstance(start, (int, float)) and isinstance(step, (int, float)):
        yield from count(start, step)
        return

    n = start
    while True:
        yield n
        n = _add_(n, step)


def count_from_to(start: Number, stop: Number, step: Number = 1) -> _t.Iterator[Number]:
    """`count`, but with a `stop`. Essentially, `range` for arbitrary types."""
    return takewhile(lambda x: x < stop, count_(start, step))


def first(iterable: _t.Iterable[_AType], default: _AType | Missing = MISSING) -> _AType:
    """Get the first element of a given iterable.
    If the iterable does not have enough elements, return `default`.
    If `default` is unset, raise `IndexError`.
    """
    for e in iterable:
        return e
    if default is MISSING:
        raise IndexError("empty iterable")
    return _t.cast(_AType, default)


def last(iterable: _t.Iterable[_AType], default: _AType | Missing = MISSING) -> _AType:
    """Get the last element of a given iterable.
    If the iterable does not have enough elements, return `default`.
    If `default` is unset, raise `IndexError`.
    """
    prev: _AType | Missing = default
    is_first = True
    for e in iterable:
        prev = e
        is_first = False
    if is_first and default is MISSING:
        raise IndexError("empty iterable")
    return _t.cast(_AType, prev)


def nth(n: int, iterable: _t.Iterable[_AType], default: _AType | Missing = MISSING) -> _AType:
    """Take `n`th element of a given iterable, counting from zero.
    If the iterable does not have enough elements, return `default`.
    If `default` is unset, raise `IndexError`.
    """
    if n >= 0:
        i = n
        for e in iterable:
            if i == 0:
                return e
            i -= 1
    if default is MISSING:
        raise IndexError("not enough elements")
    return _t.cast(_AType, default)


def take(n: int, iterable: _t.Iterable[_AType]) -> list[_AType]:
    """Take the first `n` (or less) elements of a given iterable as a `list`.
    Negative values of `n` are allowed and will be remapped to zero.
    """
    return list(islice(iterable, max(0, n)))


def drop(n: int, iterable: _t.Iterable[_AType]) -> list[_AType]:
    """Skip/drop the first `n` elements of a given iterable as a `list`.
    Negative values of `n` are allowed and will be remapped to zero.
    """
    return list(islice(iterable, max(0, n), None))


# TODO: zip_defaults


def _next_or_missing(iterator: _t.Iterator[_AType]) -> _AType | Missing:
    """`next(iterator)` or `MISSING` if it's finished. This function violates
    the intended usage of `Missing`, which is why it's hidden from view.
    """
    try:
        return next(iterator)
    except StopIteration:
        return MISSING


def diff_sorted(
    a_iterable: _t.Iterable[_AType],
    b_iterable: _t.Iterable[_BType],
    a_key: _t.Callable[[_AType], _CType] = _identity,  # type: ignore
    b_key: _t.Callable[[_BType], _CType] = _identity,  # type: ignore
) -> _t.Iterator[Either[_AType, _BType] | tuple[_AType, _BType]]:
    """Given two sorted iterables, produce an iterator over differences between
    them.

    `a_key` and `b_key` are used to map elements of corresponding iterables
    before comparisons. Both are set to `identity` by default.

    The resulting iterator yields `Left`s with elements of the first iterator
    missing from the second, `Right`s for vice versa, and 2-element `tuple`s
    with both elements when `a_key` and `b_key` produce equal values.
    """

    a_iter = iter(a_iterable)
    b_iter = iter(b_iterable)

    a_e_ = _next_or_missing(a_iter)
    b_e_ = _next_or_missing(b_iter)

    if a_e_ is not MISSING and b_e_ is not MISSING:
        a_e = _t.cast(_AType, a_e_)
        a_k = a_key(a_e)
        b_e = _t.cast(_BType, b_e_)
        b_k = b_key(b_e)

        while True:
            if a_k < b_k:  # type: ignore
                yield Left(a_e)
                a_e_ = _next_or_missing(a_iter)
                if a_e_ is not MISSING:
                    a_e = _t.cast(_AType, a_e_)
                    a_k = a_key(a_e)
                    continue
            elif b_k < a_k:  # type: ignore
                yield Right(b_e)
                b_e_ = _next_or_missing(b_iter)
                if b_e_ is not MISSING:
                    b_e = _t.cast(_BType, b_e_)
                    b_k = b_key(b_e)
                    continue
            else:
                yield a_e, b_e
                a_e_ = _next_or_missing(a_iter)
                b_e_ = _next_or_missing(b_iter)
                if a_e_ is not MISSING and b_e_ is not MISSING:
                    a_e = _t.cast(_AType, a_e_)
                    a_k = a_key(a_e)
                    b_e = _t.cast(_BType, b_e_)
                    b_k = b_key(b_e)
                    continue
            break

    # yield leftovers

    while a_e_ is not MISSING:
        a_e = _t.cast(_AType, a_e_)
        yield Left(a_e)
        a_e_ = _next_or_missing(a_iter)

    while b_e_ is not MISSING:
        b_e = _t.cast(_BType, b_e_)
        yield Right(b_e)
        b_e_ = _next_or_missing(b_iter)
