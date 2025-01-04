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

"""`Exceptions` with printable and i18n-able descriptions."""

import typing as _t


class CatastrophicFailure(Exception):
    """An `Exception` with printable and i18n-able description."""

    info: list[tuple[str, tuple[_t.Any, ...]]]

    def __init__(self, what: _t.Any, *args: _t.Any) -> None:
        super().__init__()
        if isinstance(what, CatastrophicFailure):
            self.info = what.info
        else:
            self.info = [(what, args)]

    def get_message(self, gettext: _t.Callable[[str], str], separator: str = ": ") -> str:
        res = []
        for what, args in self.info:
            try:
                t = gettext(what) % args
            except Exception:
                t = f"{repr(what)} % {repr(args)}"
            res.append(t)
        res.reverse()
        return separator.join(res)

    def __str__(self) -> str:
        return self.get_message(lambda x: x)

    def elaborate(self, what: str, *args: _t.Any) -> _t.Any:
        self.info.append((what, args))
        return self


class Failure(CatastrophicFailure):
    """A non-catastrophic `CatastrophicFailure`."""
