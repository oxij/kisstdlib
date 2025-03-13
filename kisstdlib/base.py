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

# Placeholders
AType = _t.TypeVar("AType")
BType = _t.TypeVar("BType")
CType = _t.TypeVar("CType")
DType = _t.TypeVar("DType")
EType = _t.TypeVar("EType")
AParamSpec = _t.ParamSpec("AParamSpec")
BParamSpec = _t.ParamSpec("BParamSpec")

# Bytes-like object
BytesLike = bytes | bytearray | memoryview

# Numbers
Number = Decimal | float | int
AnyNumber = _t.TypeVar("AnyNumber", bound=Number)


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


class Maybe(_t.Generic[AType]):
    """Similar to `Optional[AType]`, i.e. `AType | None`, but allows
    arbitrary nesting.

    E.g. `Maybe[Maybe[int]]` does not get flattened into `Maybe[int]`.
    """


@_dc.dataclass(order=True)
class Nothing(Maybe[AType], _t.Generic[AType]):
    pass


@_dc.dataclass(order=True, slots=True)
class Just(Maybe[AType], _t.Generic[AType]):
    just: AType


class Either(_t.Generic[AType, BType]):
    """Either a value of `AType` or a value `BType`, without flattening.

    E.g., `Either[int, int]` is not just `int`.
    """


@_dc.dataclass(order=True, slots=True)
class Left(Either[AType, BType], _t.Generic[AType, BType]):
    left: AType


@_dc.dataclass(order=True, slots=True)
class Right(Either[AType, BType], _t.Generic[AType, BType]):
    right: BType


### Operations on Numbers


def clamp(minv: AnyNumber, maxv: AnyNumber, v: AnyNumber) -> AnyNumber:
    return min(maxv, max(minv, v))


def is_infinite(x: Number) -> bool:
    return hasattr(x, "is_infinite") and x.is_infinite() or isinstance(x, float) and _math.isinf(x)


def add_(x: Number, y: Number) -> Number:
    """`x + y` that always works."""
    if isinstance(x, float) and isinstance(y, Decimal):
        return Decimal(x) + y
    if isinstance(x, Decimal) and isinstance(y, float):
        return x + Decimal(y)
    return x + y  # type: ignore


def sub_(x: Number, y: Number) -> Number:
    """`x - y` that always works."""
    if isinstance(x, float) and isinstance(y, Decimal):
        return Decimal(x) - y
    if isinstance(x, Decimal) and isinstance(y, float):
        return x - Decimal(y)
    return x - y  # type: ignore


def mul_(x: Number, y: Number) -> Number:
    """`x * y` that always works."""
    if isinstance(x, float) and isinstance(y, Decimal):
        return Decimal(x) * y
    if isinstance(x, Decimal) and isinstance(y, float):
        return x * Decimal(y)
    return x * y  # type: ignore


def truediv_(x: Number, y: Number) -> Number:
    """`x / y` that always works."""
    if isinstance(x, float) and isinstance(y, Decimal):
        return Decimal(x) / y
    if isinstance(x, Decimal) and isinstance(y, float):
        return x / Decimal(y)
    return x / y  # type: ignore


### Simple functions


def identity(x: AType, /) -> AType:
    """Identity function."""
    return x


def identity_(x: AType, /, *_args: _t.Any, **_kwargs: _t.Any) -> AType:
    """Identity function, with a bunch of ignored arguments."""
    return x


def const(x: AType, /) -> _t.Callable[[BType], AType]:
    """Return a function that always returns `a`."""
    return lambda y: x


def const_(x: AType, /) -> _t.Callable[_t.Concatenate[BType, BParamSpec], AType]:
    """Return a function that always returns `a`, and has a bunch of ignored arguments."""

    def sub(_y: BType, /, *_args: BParamSpec.args, **_kwargs: BParamSpec.kwargs) -> AType:
        return x

    return sub


def fst(x: tuple[AType, BType]) -> AType:
    """Get the first element of a given 2-elemnt tuple."""
    return x[0]


def snd(x: tuple[AType, BType]) -> BType:
    """Get the second element of a given 2-elemnt tuple."""
    return x[1]


def first_def(*args: AType | None) -> AType:
    """Return first argument that is not `None`."""
    for e in args:
        if e is not None:
            return e
    raise IndexError("no matching elements")


def first_ok(*args: AType) -> AType:
    """Return first `True`-like argument."""
    for e in args:
        if e:
            return e
    raise IndexError("no matching elements")


def optional(b: BType, f: _t.Callable[[AType], BType], x: AType | None) -> BType:
    """`f(x) if x is not None else b`."""
    return f(x) if x is not None else b


def maybe(b: BType, f: _t.Callable[[AType], BType], x: Maybe[AType]) -> BType:
    """`f(x.just) if x is Just else b`."""
    return f(x.just) if isinstance(x, Just) else b


def either(
    fa: _t.Callable[[AType], CType], fb: _t.Callable[[BType], CType], x: Either[AType, BType]
) -> CType:
    """`fa(x.left) if x is Left`, `fb(x.right) if x is Right`, `AssertionError` otherwise."""
    if isinstance(x, Left):
        return fa(x.left)
    if isinstance(x, Right):
        return fb(x.right)
    assert False


### Injectors into `list`


def singleton(x: AType) -> list[AType]:
    """`[x]`."""
    return [x]


def optlist(p: bool, x: AType) -> list[AType]:
    """`[x] if p else []`."""
    return [x] if p else []


def optslist(p: bool, xs: list[AType]) -> list[AType]:
    """`xs if p else []`."""
    return xs if p else []


def optional2list(x: AType | None) -> list[AType]:
    """`[x] if x is not None else []`."""
    return [x] if x is not None else []


### Functors, i.e. applying functions to elements contained in structures


def map_optional(f: _t.Callable[[AType], BType], x: AType | None) -> BType | None:
    """`f(x) if x is not None else x`."""
    return f(x) if x is not None else x


def map_optional2list(f: _t.Callable[[AType], list[BType]], x: AType | None) -> list[BType]:
    """`f(x) if x is not None else []`."""
    return f(x) if x is not None else []


def map_maybe(f: _t.Callable[[AType], BType], x: Maybe[AType]) -> Maybe[BType]:
    """`Just(f(x.just)) if x is Just else x`."""
    return Just(f(x.just)) if isinstance(x, Just) else _t.cast(Maybe[BType], x)


def map_maybe2list(f: _t.Callable[[AType], list[BType]], x: Maybe[AType]) -> list[BType]:
    """`f(x.just) if x is Just else []`."""
    return f(x.just) if isinstance(x, Just) else []


def map_left(f: _t.Callable[[AType], CType], x: Either[AType, BType]) -> Either[CType, BType]:
    """`Right(f(x.left)) if x is Left else x`."""
    return Left(f(x.left)) if isinstance(x, Left) else _t.cast(Either[CType, BType], x)


def map_right(f: _t.Callable[[BType], CType], x: Either[AType, BType]) -> Either[AType, CType]:
    """`Right(f(x.right)) if x is Right else x`."""
    return Right(f(x.right)) if isinstance(x, Right) else _t.cast(Either[AType, CType], x)


### Function composition


def compose(
    f: _t.Callable[[BType], CType], g: _t.Callable[[AType], BType]
) -> _t.Callable[[AType], CType]:
    return lambda x: f(g(x))


def compose_pipe(
    pipe: list[_t.Callable[_t.Concatenate[AType, AParamSpec], AType]], /
) -> _t.Callable[_t.Concatenate[AType, AParamSpec], AType]:
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

    def sub(x: AType, /, *args: AParamSpec.args, **kwargs: AParamSpec.kwargs) -> AType:
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


_BaseExeceptionType = _t.TypeVar("_BaseExeceptionType", bound=BaseException)


def flat_exceptions(
    es: BaseExceptionGroup[_BaseExeceptionType], /
) -> _t.Iterator[_BaseExeceptionType]:
    """For simplifying some `try ... except*` expressions."""

    def sub(
        excs: _BaseExeceptionType | BaseExceptionGroup[_BaseExeceptionType],
    ) -> _t.Iterator[_BaseExeceptionType]:
        if isinstance(excs, BaseExceptionGroup):
            for e in excs.exceptions:
                yield from sub(e)
        else:
            yield excs

    yield from sub(es)
