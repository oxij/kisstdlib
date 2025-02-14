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

"""Most basic things."""

import abc as _abc
import enum as _enum
import io as _io
import logging as _logging
import os as _os
import sys as _sys
import typing as _t

from ..base import POSIX as _POSIX, BytesLike, KiB, MiB, GiB  # pylint: disable=unused-import

if _POSIX:
    import fcntl as _fcntl

_logger = _logging.getLogger("kisstdlib")

# file descriptor number
FDNo = _t.NewType("FDNo", int)


class ShutdownState(_enum.Flag):
    """`.shutdown` state"""

    SHUT_NONE = 0
    SHUT_READ = 1
    SHUT_WRITE = 2
    SHUT_BOTH = 3


# incomplete operation results
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


def read_as_much_as(read_func: _t.Callable[[int], bytes | None], size: int) -> bytes:
    """Use `read_func` to read as much as `size` bytes of data."""
    data: list[bytes] = []
    total = 0
    while total < size:
        res = read_func(size - total)
        if not res:
            return b"".join(data)
        data.append(res)
        total += len(res)
    return b"".join(data)


def read_exactly(read_func: _t.Callable[[int], bytes | None], size: int) -> bytes:
    """Use `read_func` to read exactly `size` bytes of data, raise `IncompleteResultError` if that fails."""
    res = read_as_much_as(read_func, size)
    if len(res) < size:
        raise IncompleteReadError(res)
    return res


def write_all(write_func: _t.Callable[[BytesLike], int | None], data: BytesLike) -> None:
    """Use `write_func` to write all of given `data`, raise `IncompleteWriteError` if that fails."""
    view = memoryview(data)
    done = 0
    datalen = len(data)
    while done < datalen:
        res = write_func(view[done:])
        if not res:
            raise IncompleteWriteError(data[done:])
        done += res


def same_fileobj_data(a: _io.IOBase, b: _io.IOBase, chunk_size: int = 8 * MiB) -> bool:
    """Check if content data of two `io.IOBase` objects are equal.
    The result is unspecified if either argument is in non-blocking mode.
    """
    a_read = a.read
    b_read = b.read
    while True:
        ares = read_as_much_as(a_read, chunk_size)
        bres = read_as_much_as(b_read, chunk_size)
        if ares != bres:
            return False
        if len(ares) == 0:
            return True


def fileobj_data_equals(f: _io.IOBase, data: bytes) -> bool:
    """Check if content data of the given `io.IOBase` object is equal to `data`."""
    buf = _io.BytesIO(data)
    return same_fileobj_data(f, buf)


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


class MinimalIOReader(MinimalIO):
    @_abc.abstractmethod
    def read_some_bytes(self, size: int) -> bytes:
        raise NotImplementedError()

    def read_all_bytes(self, chunk_size: int = 8 * MiB) -> bytes:
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
        return read_exactly(self.read_some_bytes, size)


class MinimalIOWriter(MinimalIO):
    @_abc.abstractmethod
    def write_some_bytes(self, data: BytesLike) -> int:
        raise NotImplementedError()

    def write_bytes(self, data: BytesLike) -> None:
        return write_all(self.write_some_bytes, data)

    @_abc.abstractmethod
    def flush(self) -> None:
        raise NotImplementedError()


class MinimalFDWrapper(MinimalIO):
    fdno: FDNo | None = None
    closed: bool = False
    flocked: bool = False

    def __init__(self, fdno: FDNo | None) -> None:
        self.fdno = fdno
        _logger.debug("init %s", self)

    def __del__(self) -> None:
        _logger.debug("del %s", self)
        self.close()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {hex(id(self))} fdno={self.fdno}>"

    def close(self) -> None:
        if not self.closed and self.fdno is not None:
            _os.close(self.fdno)
        self.closed = True
        self.flocked = False

    def shutdown(self, what: ShutdownState) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} can't be shutdown")

    @property
    def shutdown_state(self) -> ShutdownState:
        if self.closed:
            return ShutdownState.SHUT_BOTH
        return ShutdownState.SHUT_NONE

    def flock(self) -> None:
        assert not self.closed
        if self.fdno is not None and _POSIX:
            _fcntl.flock(self.fdno, _fcntl.LOCK_EX)
        self.flocked = True

    def unflock(self) -> None:
        assert not self.closed
        assert self.flocked
        if self.fdno is not None and _POSIX:
            _fcntl.flock(self.fdno, _fcntl.LOCK_UN)
        self.flocked = False

    def __enter__(self) -> _t.Any:
        return self

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        self.close()


class Directory(MinimalFDWrapper):
    path: str | bytes

    def __init__(self, path: str | bytes) -> None:
        self.path = _os.path.abspath(path)
        if _POSIX:
            super().__init__(FDNo(_os.open(path, _os.O_RDONLY | _os.O_CLOEXEC | _os.O_DIRECTORY)))
        else:
            super().__init__(None)
