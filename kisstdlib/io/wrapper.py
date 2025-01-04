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

"""`MinimalIO` wrappers for file-like objects."""

import logging as _logging
import os as _os
import sys as _sys
import typing as _t

from .base import *

_logger = _logging.getLogger("kisstd")


class MinimalIOWrapper(MinimalIO):
    fobj: _t.Any
    fdno: FDNo | None

    def __init__(self, fobj: _t.Any) -> None:
        self.fobj = fobj
        # _socket.socket's fileno() will return -1 after
        # .close() and poll needs an actual value to unsubscribe
        # properly so we have to keep a copy here
        try:
            self.fdno = FDNo(fobj.fileno())
        except OSError:
            self.fdno = None
        _logger.debug("init %s", self)

    def __del__(self) -> None:
        _logger.debug("del %s", self)

    def __repr__(self) -> str:
        if self.fdno is not None:
            desc = "fd=" + str(self.fdno)
        else:
            desc = "obj=" + hex(id(self.fobj))
        return f"<{self.__class__.__name__} {hex(id(self))} {desc} closed={self.closed}>"

    def close(self) -> None:
        self.fobj.close()

    @property
    def closed(self) -> bool:
        return self.fobj.closed  # type: ignore

    def shutdown(self, what: ShutdownState) -> None:
        raise NotImplementedError("MinimalIOWrapper can't be shutdown")

    @property
    def shutdown_state(self) -> ShutdownState:
        if self.closed:
            return SHUT_BOTH
        return SHUT_NONE

    def __enter__(self) -> _t.Any:
        return self

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        self.close()

    def fileno(self) -> int:
        return self.fdno if self.fdno is not None else -1

    def isatty(self) -> bool:
        return self.fobj.isatty()  # type: ignore


class TIOWrapper(MinimalIOWrapper):
    def __init__(
        self, fobj: _t.Any, eol: bytes = b"\n", encoding: str = _sys.getdefaultencoding()
    ) -> None:
        super().__init__(fobj)
        self.encoding = encoding
        self.eol = eol


class TIOWrappedReader(TIOWrapper, MinimalIOReader):
    def read_some_bytes(self, size: int) -> bytes:
        return self.fobj.read(size)  # type: ignore


class TIOWrappedWriter(TIOWrapper, MinimalIOWriter):
    def write_some_bytes(self, data: ByteString) -> int:
        return self.fobj.write(data)  # type: ignore

    def flush(self) -> None:
        self.fobj.flush()

    def write_bytes_ln(self, data: ByteString) -> None:
        self.write_bytes(data)
        self.write_bytes(self.eol)

    def write_str(self, data: str) -> None:
        assert self.encoding is not None
        self.write_bytes(data.encode(self.encoding))

    def write_str_ln(self, data: str) -> None:
        self.write_str(data)
        self.write_bytes(self.eol)

    def write_strable(self, data: _t.Any) -> None:
        self.write_str(str(data))

    def write_strable_ln(self, data: _t.Any) -> None:
        self.write_strable(data)
        self.write_bytes(self.eol)

    def write(self, data: str | ByteString) -> None:
        if isinstance(data, str):
            self.write_str(data)
        else:
            self.write_bytes(data)

    def write_ln(self, data: str | ByteString) -> None:
        self.write(data)
        self.write_bytes(self.eol)

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        self.flush()
        self.close()
