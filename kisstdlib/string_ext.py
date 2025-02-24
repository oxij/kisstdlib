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

"""Extensions for the standard `string` module."""

import typing as _t

from string import *


def abbrev(
    x: _t.AnyStr,
    n: int,
    /,
    start_with_rep: bool = False,
    end_with_rep: bool = True,
    rep: _t.AnyStr | None = None,
) -> _t.AnyStr:
    """Abbreviate a `str`ing or `bytes` to length `n` with the abbreviated
    part replaced with optionsal `rep` (which defaults to "..." or b"...").

    `start_with_rep` and `end_with_rep` control where `rep` would go.
    """
    xlen = len(x)
    if xlen <= n:
        return x

    if rep is None:
        if isinstance(x, str):
            rep = "..."
        else:
            rep = b"..."
    replen = len(rep)

    if start_with_rep and end_with_rep:
        nrep = n - 2 * replen
        if nrep <= 0:
            return rep
        half = n // 2 - replen
        leftover = nrep - 2 * half
        halfx = xlen // 2
        return rep + x[halfx - half : halfx + half + leftover] + rep

    nrep = n - replen
    if nrep <= 0:
        return rep
    if start_with_rep:
        return rep + x[xlen - nrep :]
    if end_with_rep:
        return x[:nrep] + rep

    half = nrep // 2
    leftover = nrep - 2 * half
    return x[: half + leftover] + rep + x[xlen - half :]
