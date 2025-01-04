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

"""cbor2-style encoder for Pythonic Object Representation (repr)
"""

import io as _io
import typing as _t
import sys as _sys

from .io.encoder import TIOEncoder


class PyReprEncoder(TIOEncoder):
    def __init__(
        self,
        fobj: _io.BufferedIOBase,
        indent: int = 2,
        starting_indent: int = 0,
        width: int | None = None,
        encoding: str = _sys.getdefaultencoding(),
        encoders: dict[type[_t.Any], _t.Callable[[_t.Any, _t.Any], None]] | None = None,
        default: _t.Callable[[_t.Any, _t.Any], None] | None = None,
    ) -> None:
        super().__init__(
            fobj,
            b"\n",
            encoding,
            pyrepr_default_encoders if encoders is None else encoders,
            default,
        )
        self.indent = indent
        self.current = starting_indent
        self.width = width
        self.linelen = 0
        self.want_space = False
        self.want_ln = False

    def flush_line(self, force: bool = False) -> None:
        if self.linelen != 0:
            if force or self.want_ln or (self.width is not None and self.linelen > self.width):
                self.write_str_ln("")
                self.linelen = 0
                self.want_ln = False
                self.want_space = False

    def lnlexeme(self, token: str) -> None:
        token = " " * self.current + token
        self.write_str(token)
        self.linelen = len(token)

    def lexeme(self, token: str) -> None:
        self.flush_line()

        if self.linelen == 0:
            self.lnlexeme(token)
        elif self.want_space:
            if self.width is not None and self.linelen + len(token) + 1 > self.width:
                self.flush_line(True)
                self.lnlexeme(token)
            else:
                token = " " + token
                self.write_str(token)
                self.linelen += len(token)
        else:
            self.write_str(token)
            self.linelen += len(token)
        self.want_space = True

    def comment(self, token: str) -> None:
        self.lexeme("# " + token)
        self.flush_line(True)

    def start(self, token: str) -> None:
        self.lexeme(token)
        self.current += self.indent

    def delim(self, token: str) -> None:
        self.want_space = False
        self.lexeme(token)

    def stop(self, token: str) -> None:
        self.current -= self.indent
        self.lexeme(token)

    def encode_plain(self, obj: _t.Any) -> None:
        self.lexeme(str(obj))

    def encode_repr(self, obj: _t.Any) -> None:
        self.lexeme(repr(obj))

    def encode_list(self, obj: list[_t.Any]) -> None:
        large = len(obj) > 2
        self.start("[")
        self.want_ln = large
        first = True
        for o in obj:
            if not first:
                self.delim(",")
                self.want_ln = large
            first = False
            self.encode(o)
        self.want_ln = large
        self.stop("]")

    def encode_dict(self, obj: dict[_t.Any, _t.Any]) -> None:
        large = len(obj) > 1
        self.start("{")
        self.want_ln = large
        first = True
        for k in obj:
            if not first:
                self.delim(",")
                self.want_ln = large
            first = False

            self.lexeme(repr(k))
            self.delim(":")
            self.encode(obj[k])
        self.want_ln = large
        self.stop("}")


pyrepr_default_encoders: dict[type[_t.Any], _t.Callable[[PyReprEncoder, _t.Any], None]] = {
    bool: PyReprEncoder.encode_plain,
    int: PyReprEncoder.encode_plain,
    float: PyReprEncoder.encode_plain,
    str: PyReprEncoder.encode_repr,
    bytes: PyReprEncoder.encode_repr,
    type(None): PyReprEncoder.encode_repr,
    list: PyReprEncoder.encode_list,
    dict: PyReprEncoder.encode_dict,
}


def pyrepr_dumps(obj: _t.Any, *args: _t.Any, **kwargs: _t.Any) -> bytes:
    encoder = PyReprEncoder(_io.BytesIO(), *args, **kwargs)
    encoder.encode(obj)
    return encoder.fobj.getvalue()  # type: ignore
