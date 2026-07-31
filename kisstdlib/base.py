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

"""Basic utilities."""

import dataclasses as _dc
import io as _io
import math as _math
import os as _os
import traceback as _traceback
import typing as _t

from decimal import Decimal
from functools import partial, partialmethod  # pylint: disable=unused-import


### Primitive types

# Bytes-like object
BytesLike = bytes | bytearray | memoryview

### Common constants

# OS detection
POSIX = _os.name == "posix"
WINDOWS = _os.name == "nt"

# Time lengths, in seconds
MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
AVG_MONTH = 30 * DAY
AVG_YEAR = 365 * DAY

# Common byte sizes
KiB = 1024
MiB = 1024 * KiB
GiB = 1024 * MiB


### Placeholder values


class Missing:
    """A type for unspecified function arguments.

    This is similar to JavaScript's `undefined`, but only intended to
    be used in function arguments, not their return values.

    I.e, in JavaScript `obj.field === undefined` when `not
    hasattr("field", obj)` is an anti-pattern that frequently
    introduces errors and should be avoided. Python, thankfully, does
    not do that.

    However, in Python, having a function take `MISSING` as an
    argument can be pretty useful, and some standard functions like
    `dict.get` do that already, which is why this thing exists.

    For Haskell programmers, think `Missing` to be an implicit `Maybe`
    in function type which gets impliticty set to `Just value` when an
    optional arguments gets set to `value`.
    """

    def __bool__(self) -> bool:
        return False


MISSING = Missing()


### Structured unions


class Maybe[T]:
    """Similar to `Optional[T]`, i.e. `T | None`, but allows
    arbitrary nesting.

    E.g. `Maybe[Maybe[int]]` does not get flattened into `Maybe[int]`.
    """


@_dc.dataclass(order=True)
class Nothing[T](Maybe[T]):
    pass


@_dc.dataclass(order=True, slots=True)
class Just[T](Maybe[T]):
    just: T


class Either[A, B]():
    """Either a value of type `A` or a value of type `B`, without flattening.

    E.g., `Either[int, int]` is not just `int`.
    """


@_dc.dataclass(order=True, slots=True)
class Left[A, B](Either[A, B]):
    left: A


@_dc.dataclass(order=True, slots=True)
class Right[A, B](Either[A, B]):
    right: B


### Operations on Numbers


class SupportsCmp(_t.Protocol):
    # `__eq__` and `__ne__` belong to `object` and are always available
    def __lt__(self, x: int | _t.Self) -> bool: ...
    def __le__(self, x: int | _t.Self) -> bool: ...
    def __gt__(self, x: int | _t.Self) -> bool: ...
    def __ge__(self, x: int | _t.Self) -> bool: ...


class SupportsCounting(SupportsCmp, _t.Protocol):
    def __add__(self, x: int | _t.Self) -> _t.Self: ...
    def __sub__(self, x: int | _t.Self) -> _t.Self: ...

    # because this can be implemented using the above
    # note that from the result, only `SupportsCmp` is required
    def __abs__(self) -> SupportsCmp: ...


def clamp[A: (int, float, Decimal)](minv: A, maxv: A, v: A) -> A:
    return min(maxv, max(minv, v))


def is_infinite(x: _t.Any) -> bool:
    return isinstance(x, float) and _math.isinf(x) or hasattr(x, "is_infinite") and x.is_infinite()


def is_closer[A: SupportsCounting](ideal: A, a: A, b: A) -> bool:
    """Check whether `a` is closer to `ideal` than `b` is. That is, essentially, `abs(ideal - a) <
    abs(ideal - b)`, but with infinite `ideal` cases handled properly.

    Note that the above implies that this function always returns `False` when `a == b`.
    """
    if is_infinite(ideal):
        if ideal < 0:
            return a < b
        return b < a
    return abs(ideal - a) < abs(ideal - b)


### Simple functions


def noop() -> None:
    """A noop."""


def noop_(*_args: _t.Any, **_kwargs: _t.Any) -> None:
    """A noop, with a bunch of ignored arguments."""


def identity[T](x: T, /) -> T:
    """Identity function."""
    return x


def identity_[T](x: T, /, *_args: _t.Any, **_kwargs: _t.Any) -> T:
    """Identity function, with a bunch of ignored arguments."""
    return x


def const[A, B](x: A, /) -> _t.Callable[[B], A]:
    """Return a function that always returns `a`."""
    return lambda y: x


def const_[A, B, **PS](x: A, /) -> _t.Callable[_t.Concatenate[B, PS], A]:
    """Return a function that always returns `a`, and has a bunch of ignored arguments."""

    def sub(_y: B, /, *_args: PS.args, **_kwargs: PS.kwargs) -> A:
        return x

    return sub


def fst[A, B](x: tuple[A, B]) -> A:
    """Get the first element of a given 2-elemnt tuple."""
    return x[0]


def snd[A, B](x: tuple[A, B]) -> B:
    """Get the second element of a given 2-elemnt tuple."""
    return x[1]


def first_def[A](*args: A | None) -> A:
    """Return first argument that is not `None`."""
    for e in args:
        if e is not None:
            return e
    raise IndexError("no matching elements")


def first_ok[A](*args: A) -> A:
    """Return first `True`-like argument."""
    for e in args:
        if e:
            return e
    raise IndexError("no matching elements")


def optional[A, B](b: B, f: _t.Callable[[A], B], x: A | None) -> B:
    """`f(x) if x is not None else b`."""
    return f(x) if x is not None else b


def maybe[A, B](b: B, f: _t.Callable[[A], B], x: Maybe[A]) -> B:
    """`f(x.just) if x is Just else b`."""
    return f(x.just) if isinstance(x, Just) else b


def either[A, B, C](fa: _t.Callable[[A], C], fb: _t.Callable[[B], C], x: Either[A, B]) -> C:
    """`fa(x.left) if x is Left`, `fb(x.right) if x is Right`, `AssertionError` otherwise."""
    if isinstance(x, Left):
        return fa(x.left)
    if isinstance(x, Right):
        return fb(x.right)
    assert False


### Injectors into `list`


def singleton[A](x: A) -> list[A]:
    """`[x]`."""
    return [x]


def optlist[A](p: bool, x: A) -> list[A]:
    """`[x] if p else []`."""
    return [x] if p else []


def optslist[A](p: bool, xs: list[A]) -> list[A]:
    """`xs if p else []`."""
    return xs if p else []


def optional2list[A](x: A | None) -> list[A]:
    """`[x] if x is not None else []`."""
    return [x] if x is not None else []


### Functors, i.e. applying functions to elements contained in structures


def map_optional[A, B](f: _t.Callable[[A], B], x: A | None) -> B | None:
    """`f(x) if x is not None else x`."""
    return f(x) if x is not None else x


def map_optional2list[A, B](f: _t.Callable[[A], list[B]], x: A | None) -> list[B]:
    """`f(x) if x is not None else []`."""
    return f(x) if x is not None else []


def map_maybe[A, B](f: _t.Callable[[A], B], x: Maybe[A]) -> Maybe[B]:
    """`Just(f(x.just)) if x is Just else x`."""
    return Just(f(x.just)) if isinstance(x, Just) else _t.cast(Maybe[B], x)


def map_maybe2list[A, B](f: _t.Callable[[A], list[B]], x: Maybe[A]) -> list[B]:
    """`f(x.just) if x is Just else []`."""
    return f(x.just) if isinstance(x, Just) else []


def map_left[A, B, C](f: _t.Callable[[A], C], x: Either[A, B]) -> Either[C, B]:
    """`Right(f(x.left)) if x is Left else x`."""
    return Left(f(x.left)) if isinstance(x, Left) else _t.cast(Either[C, B], x)


def map_right[A, B, C](f: _t.Callable[[B], C], x: Either[A, B]) -> Either[A, C]:
    """`Right(f(x.right)) if x is Right else x`."""
    return Right(f(x.right)) if isinstance(x, Right) else _t.cast(Either[A, C], x)


### Function composition


def compose[A, B, C](f: _t.Callable[[B], C], g: _t.Callable[[A], B]) -> _t.Callable[[A], C]:
    return lambda x: f(g(x))


def compose_pipe[A, **PS](
    pipe: list[_t.Callable[_t.Concatenate[A, PS], A]], /
) -> _t.Callable[_t.Concatenate[A, PS], A]:
    """Compose a list of functions, similarly to how a shell pipe ("|")
    exression does it. I.e. compose them in reverse order.

    The mutating value gets passed as the first argument, all other
    arguments get passed unchanged.

    `compose_pipe([])` is `identity_`.
    `compose_pipe([x])` is `x`.
    """
    if len(pipe) == 0:
        return identity_
    if len(pipe) == 1:
        return pipe[0]

    def sub(x: A, /, *args: PS.args, **kwargs: PS.kwargs) -> A:
        for func in pipe:
            x = func(x, *args, **kwargs)
        return x

    return sub


### Other stuff


def getattr_rec(obj: _t.Any, names: list[str], /) -> _t.Any:
    """Recursively apply `gettatr` or `dict.get`."""
    if len(names) == 0:
        return obj

    name, *rest = names
    if hasattr(obj, name):
        return getattr_rec(getattr(obj, name), rest)
    if isinstance(obj, dict) and name in obj:
        return getattr_rec(obj[name], rest)

    raise AttributeError(name=name, obj=obj)


def get_traceback(exc: BaseException, /, lines: int = 128) -> str:
    """Pretty-print a traceback of a given exception."""
    fobj = _io.StringIO()
    _traceback.print_exception(type(exc), exc, exc.__traceback__, lines, fobj)
    return fobj.getvalue()


def flat_exceptions[ExceptionType: BaseException](
    es: BaseExceptionGroup[ExceptionType], /
) -> _t.Iterator[ExceptionType]:
    """For simplifying some `try ... except*` expressions."""

    def sub(
        excs: ExceptionType | BaseExceptionGroup[ExceptionType],
    ) -> _t.Iterator[ExceptionType]:
        if isinstance(excs, BaseExceptionGroup):
            for e in excs.exceptions:
                yield from sub(e)
        else:
            yield excs

    yield from sub(es)
