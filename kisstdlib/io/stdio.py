# Copyright (c) 2018-2025 Jan Malakhovski <oxij@oxij.org>
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

"""`TIOWrapped*`s for `stdin`, `stdout`, and `stderr`."""

import os as _os
import sys as _sys
import typing as _t

from .wrapper import *

stdin = TIOWrappedReader(_sys.stdin.buffer)
stdout = TIOWrappedWriter(_sys.stdout.buffer)
stderr = TIOWrappedWriter(_sys.stderr.buffer)


def setup_stdio() -> None:
    """Make `kisstdlib.io.stdio` play nicely with `print` and manual writes to
    `sys.stdout` and `sys.stderr`, at the cost of some performance.
    """
    _sys.stdout.reconfigure(write_through=True)  # type: ignore
    _sys.stderr.reconfigure(write_through=True)  # type: ignore


def _numlines(x: str | bytes) -> int:
    if isinstance(x, str):
        return x.count("\n")
    return x.count(b"\n")


def printf(
    pattern: _t.AnyStr,
    /,
    *args: _t.Any,
    start: _t.AnyStr | None = None,
    indent: _t.AnyStr | None = None,
    prefix: _t.AnyStr | None = None,
    suffix: _t.AnyStr | None = None,
    end: str | bytes | None = None,
    file: TIOWrappedWriter | None = None,
    width: int = 80,
    flush: bool | None = None,
    **kwargs: _t.Any,
) -> int:
    """`libc` `printf`-look-alike with Python `print`'s `end`, `file`, `flush`
    arguments.

    Note that unlike `libc`'s `printf` this prints `file.eol` at the end by
    default.

    It also has `indent` and `prefix` arguments, the values of which get
    prepended to each line, `suffix` which gets appended to it, and `start`
    which gets printed before the first line, similarly to how `end` gets
    printed after the last one.

    It also supports all `kwargs` of `ANSIEscape.set_attrs`, so you can set ANSI
    TTY text modes and colors right here.

    Colors get applied to `prefix`, rendered `pattern`, and `suffix`, but not to
    `indent` and `end`, so that, e.g., `printf(..., indent=" " * 4`,
    background=1)` produces an indented background-colored block.
    """
    if file is None:
        file = stdout
    empty = "" if isinstance(pattern, str) else b""
    if indent is None:
        indent = empty
    if prefix is None:
        prefix = empty
    if suffix is None:
        suffix = empty
    if end is None:
        end = file.eol

    data = pattern % args
    extra = len(prefix) + len(indent) + len(suffix)

    lines = 0
    implicit_eol = False
    if start:
        file.write(start)
        lines += _numlines(start)
    for line in data.splitlines(True):
        w = len(line) + extra
        if indent:
            file.write(indent)
            lines += _numlines(indent)
        if line[-1:] in ("\n", b"\n"):
            file.write_ln(prefix + line[:-1] + suffix, **kwargs)
            lines += 1
            w -= 1
        else:
            file.write(prefix + line + suffix, **kwargs)
        lines += w // width
        implicit_eol = w > 0 and w % width == 0
    if end:
        file.write(end)
        lines += max(0, _numlines(end) - 1) if implicit_eol else _numlines(end)
    if flush is True or flush is None and file.isatty():
        file.flush()
    return lines


def printf_err(pattern: str, /, *args: _t.Any, **kwargs: _t.Any) -> None:
    """`printf` to `stderr` with `flush=True`."""
    printf(
        pattern,
        *args,
        file=stderr,
        flush=True,
        **kwargs,
    )
