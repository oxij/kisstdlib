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

    info: list[tuple[str, tuple[_t.Any, ...]] | list[_t.Self]]

    def __init__(self, what: str | _t.Self | list[_t.Self], *args: _t.Any) -> None:
        super().__init__()
        if isinstance(what, str):
            self.info = [(what, args)]
        elif isinstance(what, list):
            self.info = [what]
        else:
            self.info = what.info

    def get_message(
        self, gettext: _t.Callable[[str], str], separator: str = ":", indent: int = 0
    ) -> str:
        res = []
        for i in self.info:
            if isinstance(i, list):
                res.append(
                    separator
                    + "\n"
                    + "".join(
                        map(
                            lambda x: (" " * indent)
                            + x.get_message(gettext, separator, indent + 1)
                            + "\n",
                            i,
                        )
                    )
                )
            else:
                what, args = i
                try:
                    t = gettext(what) % args
                except Exception:
                    t = f"{repr(what)} % {repr(args)}"
                res.append(t)
        res.reverse()
        return (separator + " ").join(res)

    def __str__(self) -> str:
        return self.get_message(lambda x: x)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {repr(str(self))}>"

    def elaborate(self, what: str, *args: _t.Any) -> _t.Self:
        self.info.append((what, args))
        return self

    def subsume(self, excs: list[_t.Self]) -> _t.Self:
        self.info.append(excs)
        return self


class Failure(CatastrophicFailure):
    """A non-catastrophic `CatastrophicFailure`."""


class AssertionFailure(CatastrophicFailure, AssertionError):
    """`AssertionError`-equivalent `CatastrophicFailure`."""


class RuntimeFailure(Failure, RuntimeError):
    """`RuntimeError`-equivalent `Failure`."""


class ParsingFailure(Failure, ValueError):
    """A `Failure` of parsing something."""
