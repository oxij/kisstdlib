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

"""Random utility functions."""


import io as _io
import traceback as _traceback
import typing as _t

InType = _t.TypeVar("InType")
OutType = _t.TypeVar("OutType")


def map_optional(f: _t.Callable[[InType], OutType], x: InType | None) -> OutType | None:
    if x is None:
        return None
    return f(x)


def map_optionals(f: _t.Callable[[InType], list[OutType]], x: InType | None) -> list[OutType]:
    if x is None:
        return []
    return f(x)


def first(x: tuple[InType, ...]) -> InType:
    return x[0]


def str_Exception(exc: Exception) -> str:
    fobj = _io.StringIO()
    _traceback.print_exception(type(exc), exc, exc.__traceback__, 100, fobj)
    return fobj.getvalue()
