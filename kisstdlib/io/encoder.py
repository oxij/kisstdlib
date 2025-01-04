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

"""Most basic types and definitions."""

import sys as _sys
import typing as _t

from .wrapper import *


class TIOEncoder(TIOWrappedWriter):
    default: _t.Callable[[_t.Any, _t.Any], None]

    def __init__(  # pylint: disable=dangerous-default-value
        self,
        fobj: _t.Any,
        eol: bytes = b"\n",
        encoding: str = _sys.getdefaultencoding(),
        encoders: dict[type[_t.Any], _t.Callable[[_t.Any, _t.Any], None]] = {},
        default: _t.Callable[[_t.Any, _t.Any], None] | None = None,
    ) -> None:
        super().__init__(fobj, eol, encoding)
        self.encoders = encoders.copy()
        if default is None:
            self.default = TIOEncoder.not_implemented
        else:
            self.default = default

    def not_implemented(self, obj: _t.Any) -> None:
        raise NotImplementedError("don't know how to encode %s", type(obj))

    def _find_encoder(self, obj_type: _t.Any) -> _t.Any:
        for typ, enc in self.encoders.items():
            if issubclass(obj_type, typ):
                return enc
        return self.default

    def encode(self, obj: _t.Any) -> None:
        typ = type(obj)
        try:
            enc = self.encoders[typ]
        except KeyError:
            enc = self._find_encoder(typ)
            self.encoders[typ] = enc
        enc(self, obj)


tio_default_encoders: dict[type[_t.Any], _t.Callable[[TIOWrappedWriter, _t.Any], None]] = {
    bool: TIOEncoder.write_strable,
    int: TIOEncoder.write_strable,
    float: TIOEncoder.write_strable,
    str: TIOEncoder.write_str,
    bytes: TIOEncoder.write_bytes,
}

tio_default_encoders_ln: dict[type[_t.Any], _t.Callable[[TIOWrappedWriter, _t.Any], None]] = {
    bool: TIOEncoder.write_strable_ln,
    int: TIOEncoder.write_strable_ln,
    float: TIOEncoder.write_strable_ln,
    str: TIOEncoder.write_str_ln,
    bytes: TIOEncoder.write_bytes_ln,
}
