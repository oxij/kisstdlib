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

"""Most basic types and definitions."""

import abc as _abc
import sys as _sys
import typing as _t

# file descriptor number
FDNo = _t.NewType("FDNo", int)
# anything that can be `write`ed to
ByteString = _t.Union[bytes, bytearray, memoryview]

# ideally, this should be `_t.NewType("ShutdownState", int)`, but then `~` and
# `|` operations wouldn't work
ShutdownState = int
SHUT_NONE = ShutdownState(0)
SHUT_READ = ShutdownState(1)
SHUT_WRITE = ShutdownState(2)
SHUT_BOTH = ShutdownState(3)

MEGABYTE = 1024 * 1024


class MinimalIO(metaclass=_abc.ABCMeta):
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))}>"

    @_abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()

    @property
    @_abc.abstractmethod
    def closed(self) -> bool:
        raise NotImplementedError()

    @_abc.abstractmethod
    def shutdown(self, what: ShutdownState) -> None:
        raise NotImplementedError()

    @property
    @_abc.abstractmethod
    def shutdown_state(self) -> ShutdownState:
        raise NotImplementedError()


IncompleteResultType = _t.TypeVar("IncompleteResultType")


class IncompleteResultError(Exception, _t.Generic[IncompleteResultType]):
    """En `Exception` signifying an opeartion did not complete, but did
    produce a partial result.
    """

    def __init__(self, data: IncompleteResultType) -> None:
        super().__init__()
        self.data = data


class IncompleteReadError(IncompleteResultError[bytes]):
    """When a `read` operation was not complete. `.data` stores the chunk that was
    read successfully.
    """


class IncompleteWriteError(IncompleteResultError[bytes]):
    """When a `write` operation was not complete. `.data` stores the leftover
    unwritten chunk."""


class MinimalIOReader(MinimalIO):
    @_abc.abstractmethod
    def read_some_bytes(self, size: int) -> bytes:
        raise NotImplementedError()

    def read_all_bytes(self, chunk_size: int = MEGABYTE) -> bytes:
        data: list[bytes] = []
        while True:
            res = self.read_some_bytes(chunk_size)
            rlen = len(res)
            if rlen == 0:
                break
            data.append(res)
        return b"".join(data)

    def read_bytes(self, size: int | None = None) -> bytes:
        if size is None:
            return self.read_all_bytes()
        return self.read_some_bytes(size)

    def read_exactly_bytes(self, size: int) -> bytes:
        data: list[bytes] = []
        total = 0
        while total < size:
            res = self.read_some_bytes(size - total)
            rlen = len(res)
            if rlen == 0:
                raise IncompleteReadError(b"".join(data))
            data.append(res)
            total += rlen
        return b"".join(data)


class MinimalIOWriter(MinimalIO):
    @_abc.abstractmethod
    def write_some_bytes(self, data: ByteString) -> int:
        raise NotImplementedError()

    def write_bytes(self, data: ByteString) -> None:
        done = 0
        view = memoryview(data)
        datalen = len(data)
        while done < datalen:
            res = self.write_some_bytes(view[done:])
            if res == 0:
                raise IncompleteWriteError(data[done:])
            done += res

    @_abc.abstractmethod
    def flush(self) -> None:
        raise NotImplementedError()
