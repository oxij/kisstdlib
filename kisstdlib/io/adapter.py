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

"""Adapt almost any folding function into `IOBase` interface."""

import typing as _t

from zlib import compressobj as _compressobj, decompressobj as _decompressobj

from ..parsing import (
    BytesTransformer as _BytesTransformer,
    LF2CRLF as _LF2CRLF,
    CRLF2LF as _CRLF2LF,
)


class IOAdapter:
    def __init__(self, fobj: _t.Any) -> None:
        self._fobj = fobj

    def close(self) -> None:
        self._fobj.close()

    def flush(self) -> None:
        self._fobj.flush()

    def __enter__(self) -> _t.Any:
        return self

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        self.close()

    def fileno(self) -> int:
        return self._fobj.fileno()  # type: ignore

    @property
    def closed(self) -> bool:
        return self._fobj.closed  # type: ignore


class ReadAdapter(IOAdapter):
    def __init__(self, fobj: _t.Any, block_size: int) -> None:
        super().__init__(fobj)
        self._block_size = block_size
        self._buffer = b""
        self._eof = False

    def _handle_eof(self) -> bytes:
        raise NotImplementedError()

    def _handle_data(self, data: bytes) -> bytes:
        raise NotImplementedError()

    def read(self, size: int = -1) -> bytes:
        while not self._eof and (size == -1 or len(self._buffer) < size):
            data = self._fobj.read(self._block_size)
            if len(data) == 0:
                self._buffer += self._handle_eof()
                self._eof = True
            else:
                self._buffer += self._handle_data(data)

        if len(self._buffer) == 0:
            return self._buffer

        if size == -1 or len(self._buffer) == size:
            res = self._buffer
            self._buffer = b""
            return res

        res = self._buffer[:size]
        self._buffer = self._buffer[len(res) :]
        return res

    def tell(self) -> int:
        return self._fobj.tell()  # type: ignore


class UpdateFinalizeReader(ReadAdapter):
    def __init__(self, fobj: _t.Any, preprocessor: _t.Any, block_size: int = 4096) -> None:
        super().__init__(fobj, block_size)
        self._preprocessor = preprocessor

    def _handle_eof(self) -> bytes:
        return self._preprocessor.finalize()  # type: ignore

    def _handle_data(self, data: bytes) -> bytes:
        return self._preprocessor.update(data)  # type: ignore


class UpdateFinalizeWriter(IOAdapter):
    def __init__(self, fobj: _t.Any, preprocessor: _t.Any) -> None:
        super().__init__(fobj)
        self._preprocessor = preprocessor

    def write(self, data: bytes) -> None:
        self._fobj.write(self._preprocessor.update(data))

    def close(self) -> None:
        if not self.closed:
            self._fobj.write(self._preprocessor.finalize())
            self._fobj.close()


class DOS2UNIXReader(UpdateFinalizeReader):
    def __init__(self, fobj: _t.Any, block_size: int = 4096) -> None:
        super().__init__(fobj, _BytesTransformer(_CRLF2LF), block_size)


class UNIX2DOSReader(UpdateFinalizeReader):
    def __init__(self, fobj: _t.Any, block_size: int = 4096) -> None:
        super().__init__(fobj, _BytesTransformer(_LF2CRLF), block_size)


class DOS2UNIXWriter(UpdateFinalizeWriter):
    def __init__(self, fobj: _t.Any) -> None:
        super().__init__(fobj, _BytesTransformer(_CRLF2LF))


class UNIX2DOSWriter(UpdateFinalizeWriter):
    def __init__(self, fobj: _t.Any) -> None:
        super().__init__(fobj, _BytesTransformer(_LF2CRLF))


class ZlibDecompressor(ReadAdapter):
    def __init__(self, fobj: _t.Any, block_size: int, **kwargs: _t.Any) -> None:
        super().__init__(fobj, block_size)
        self._decompressor = _decompressobj(**kwargs)

    def _handle_eof(self) -> bytes:
        return self._decompressor.flush()

    def _handle_data(self, data: bytes) -> bytes:
        return self._decompressor.decompress(data)


class ZlibCompressor(IOAdapter):
    def __init__(self, fobj: _t.Any, **kwargs: _t.Any) -> None:
        super().__init__(fobj)
        self._compressor = _compressobj(**kwargs)

    def write(self, data: bytes) -> None:
        self._fobj.write(self._compressor.compress(data))

    def close(self) -> None:
        if not self.closed:
            self._fobj.write(self._compressor.flush())
            self._fobj.close()
