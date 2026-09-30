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

"""Extensions for the standard `os` and `shutil` modules."""

import collections as _c
import collections.abc as _cabc
import dataclasses as _dc
import enum as _enum
import errno as _errno
import hashlib as _hashlib
import io as _io
import os as _os
import os.path as _op
import shutil as _shutil
import stat as _stat
import sys as _sys
import typing as _t

from os import fsencode, fsdecode

from .base import (
    POSIX as _POSIX,
    WINDOWS as _WINDOWS,
    raise_one as _raise_one,
    identity as _identity,
    partial as _partial,
)
from .failure import AssertionFailure as _AssertionFailure
from .logging_ext import log_exception_warning as _log_exception_warning
from .io.base import *
from .string_ext import escape_path as _escape_path
from .time import TimeStamp as _TimeStamp


def fsreencode[AnyStr: (str, bytes)](src_path: str | bytes, dst_path: AnyStr) -> AnyStr:
    """Apply `fsencode` or `fsdecode` to `src_path` so that the type would match that of `dst_path`."""
    if isinstance(src_path, str):
        if isinstance(dst_path, bytes):
            return fsencode(src_path)
    elif isinstance(dst_path, str):
        return fsdecode(src_path)
    return src_path


def equal_path(path1: str | bytes, path2: str | bytes) -> bool:
    if path1 == path2:
        return True
    is_str1 = isinstance(path1, str)
    is_str2 = isinstance(path2, str)
    if is_str1 == is_str2:
        return False
    if is_str1:
        return fsencode(path1) == path2
    return path1 == fsencode(path2)


def unchanged_stat(stat1: _os.stat_result, stat2: _os.stat_result) -> bool:
    """Like `os.path.samestat`, but also checks that `stat_result`s have the same `size` and `mtime`."""
    if (
        _op.samestat(stat1, stat2)
        and stat1.st_size == stat2.st_size
        and stat1.st_mtime_ns == stat2.st_mtime_ns
    ):
        return True
    return False


sep = _op.sep
sepb = _os.fsencode(_op.sep)


def dirname_dot[AnyStr: (str, bytes)](path: AnyStr) -> tuple[AnyStr, bool]:
    """Apply `os.path.dirname` to the given argument, but if it's empty, return "." instead.
    The second element of the tuple is `False` if the above replacement was performed, `True` otherwise.
    """
    path = _op.dirname(path)
    if isinstance(path, bytes):
        if path == b"":
            return b".", False
        return path, True
    if path == "":
        return ".", False
    return path, True


def realdir[AnyStr: (str, bytes)](path: AnyStr, strict: bool = False) -> AnyStr:
    """Apply `os.path.realpath` to the `dirname` part of `path`.

    Essentially, this returns the canonical path of the inode the `path` points to, even when that
    inode is a symlink.
    """
    dn, bn = _op.split(_op.abspath(path))
    return _op.join(_op.realpath(dn, strict=strict), bn)


def read_file_maybe(path: str | bytes) -> bytes | None:
    """Return contents of the given file path, or `None` if it does not exist."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def same_file_data(
    path1: str | bytes, path2: str | bytes, chunk_size: int = FILE_CHUNK_SIZE
) -> bool:
    """Check if two given files have exactly the same content."""
    with open(path1, "rb") as f1:
        with open(path2, "rb") as f2:
            return same_fileobj_data(f1, f2, chunk_size)


def file_data_equals(path: str | bytes, data: bytes, chunk_size: int = FILE_CHUNK_SIZE) -> bool:
    """Check if contents of the given file `path` is equal to `data`.

    Returns `False` if `path` does not exists.
    """
    try:
        with open(path, "rb") as f:
            return fileobj_data_equals(f, data, chunk_size)
    except FileNotFoundError:
        return False


def same_symlink_data(path1: str | bytes, path2: str | bytes) -> bool:
    """Check if two given symlinks have exactly the same content."""
    a = _os.readlink(fsencode(path1))
    b = _os.readlink(fsencode(path2))
    return a == b


HASH_BUFFER_SIZE = 16 * MiB


def hash_file(
    make_hasher: _t.Callable[[], _t.Any], path: str | bytes, buffer_size: int = HASH_BUFFER_SIZE
) -> bytes:
    """Use a `hashlib.Hash` factory to produce a hash digest of file contents."""
    with open(path, "rb") as f:
        hasher = make_hasher()
        while True:
            data = f.read(buffer_size)
            if len(data) == 0:
                break
            hasher.update(data)
        return hasher.digest()  # type: ignore


def sha256_file(path: str | bytes, buffer_size: int = HASH_BUFFER_SIZE) -> bytes:
    """Get `sha256` hash digest of file contents."""
    return hash_file(_hashlib.sha256, path, buffer_size)


type IncludeFilesFunc[_AnyStr] = _t.Callable[[_AnyStr], bool]
type IncludeDirectoriesFunc[_AnyStr] = _t.Callable[
    [_AnyStr, _AnyStr, bool, list[tuple[_AnyStr, _AnyStr, bool]]], bool | None
]


class WalkOrder(_enum.Enum):
    NONE = 0
    SORT = 1
    REVERSE = 2


def iter_subtree[AnyStr: (
    str,
    bytes,
)](
    path: AnyStr,
    *,
    include_files: bool | IncludeFilesFunc[AnyStr] = True,
    include_directories: bool | IncludeDirectoriesFunc[AnyStr] = True,
    follow_symlinks: bool = False,
    order: WalkOrder = WalkOrder.SORT,
    handle_error: _t.Callable[..., None] | None = None,
    path_sep: AnyStr | None = None,
) -> _t.Iterator[tuple[AnyStr, AnyStr, bool]]:
    """Similar to `os.walk`, but produces an iterator over

    `tuple[path, path + sep if is_dir else path, is_dir]`

    elements, allows non-directories as input (which will just output a single
    element), provides convenient filtering and error handling, and the output
    is guaranteed to be ordered if `order` is not `WalkOrder.NONE`.

    The output is sorted by the second element of the tuple. I.e., it respects
    the `sep` separator, i.e. directories are sorted as if they have it appended
    at the end:

    ```
    example*not
    example.dot
    example
    example/a
    example/aa
    example/b
    example/c
    ```

    and not

    ```
    example
    example/a
    example/aa
    example/b
    example/c
    example*not
    example.dot
    ```

    or

    ```
    example
    example*not
    example.dot
    example/a
    example/aa
    example/b
    example/c
    ```

    because otherwise `list(map(first, iter_subtree(..., include_directories=False)))`
    won't actually be sorted.
    """

    if path_sep is None:
        try:
            fstat = _os.stat(path, follow_symlinks=follow_symlinks)
        except OSError as exc:
            if handle_error is not None:
                eno = exc.errno or 0
                handle_error(
                    "failed to `stat`: [Errno %d, %s] %s: %s",
                    eno,
                    _errno.errorcode.get(eno, "?"),
                    _os.strerror(eno),
                    path,
                )
                return
            raise

        if not _stat.S_ISDIR(fstat.st_mode):
            if isinstance(include_files, bool):
                if not include_files:
                    return
            elif not include_files(path):
                return
            yield path, path, False
            return

        path_sep = path + (sep if isinstance(path, str) else sepb)

    try:
        scandir_it = _os.scandir(path)
    except OSError as exc:
        if handle_error is not None:
            eno = exc.errno or 0
            handle_error(
                "failed to `scandir`: [Errno %d, %s] %s: %s",
                eno,
                _errno.errorcode.get(eno, "?"),
                _os.strerror(eno),
                path,
            )
            return
        raise

    complete = True
    elements: list[tuple[AnyStr, AnyStr, bool]] = []

    with scandir_it:
        while True:
            try:
                entry: _os.DirEntry[AnyStr] = next(scandir_it)
            except StopIteration:
                break
            except OSError as exc:
                if handle_error is not None:
                    eno = exc.errno or 0
                    handle_error(
                        "failed in `scandir`: [Errno %d, %s] %s: %s",
                        eno,
                        _errno.errorcode.get(eno, "?"),
                        _os.strerror(eno),
                        path,
                    )
                    return
                raise
            else:
                try:
                    entry_is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
                except OSError as exc:
                    if handle_error is not None:
                        eno = exc.errno or 0
                        handle_error(
                            "failed to `stat`: [Errno %d, %s] %s: %s",
                            eno,
                            _errno.errorcode.get(eno, "?"),
                            _os.strerror(eno),
                            path,
                        )
                        # NB: skip errors here
                        complete = False
                        continue
                    raise

                epath_sep: AnyStr = entry.path
                if entry_is_dir:
                    epath_sep += sep if isinstance(epath_sep, str) else sepb
                elements.append((entry.path, epath_sep, entry_is_dir))

    if order != WalkOrder.NONE:
        elements.sort(key=lambda x: x[1], reverse=order == WalkOrder.REVERSE)

    if isinstance(include_directories, bool):
        if include_directories:
            yield path, path_sep, True
    else:
        inc = include_directories(path, path_sep, complete, elements)
        if inc is None:
            return
        if inc:
            yield path, path_sep, True

    for el in elements:
        epath, epath_sep, eis_dir = el
        if eis_dir:
            yield from iter_subtree(
                epath,
                include_files=include_files,
                include_directories=include_directories,
                follow_symlinks=follow_symlinks,
                order=order,
                handle_error=handle_error,
                path_sep=epath_sep,
            )
            continue
        if isinstance(include_files, bool):
            if not include_files:
                continue
        elif not include_files(epath):
            continue
        yield el


def as_include_directories[AnyStr: (
    str,
    bytes,
)](f: IncludeFilesFunc[AnyStr]) -> IncludeDirectoriesFunc[AnyStr]:
    """`convert iter_subtree(..., include_files, ...)` filter to `include_directories` filter"""

    def func(
        path: AnyStr,
        _path_sep: AnyStr,
        _complete: bool,
        _elements: list[tuple[AnyStr, AnyStr, bool]],
    ) -> bool:
        return f(path)

    return func


def with_extension_in[AnyStr: (
    str,
    bytes,
)](exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[AnyStr]:
    """`iter_subtree(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that have one of the given extensions"""

    def pred(path: AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext in exts

    return pred


def with_extension_not_in[AnyStr: (
    str,
    bytes,
)](exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[AnyStr]:
    """`iter_subtree(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that do not have any of the given extensions"""

    def pred(path: AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext not in exts

    return pred


def nonempty_directories[AnyStr: (
    str,
    bytes,
)](
    _path: AnyStr,
    _path_sep: AnyStr,
    complete: bool,
    elements: list[tuple[AnyStr, AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print only non-empty directories"""
    if len(elements) == 0:
        return not complete
    return True


def leaf_directories[AnyStr: (
    str,
    bytes,
)](
    _path: AnyStr,
    _path_sep: AnyStr,
    complete: bool,
    elements: list[tuple[AnyStr, AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print leaf directories only, i.e. only directories without sub-directories"""
    if complete and all(map(lambda x: not x[2], elements)):
        return True
    return False


def nonempty_leaf_directories[AnyStr: (
    str,
    bytes,
)](
    path: AnyStr,
    path_sep: AnyStr,
    complete: bool,
    elements: list[tuple[AnyStr, AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print only non-empty leaf directories, i.e. non-empty directories without sub-directories"""
    if nonempty_directories(path, path_sep, complete, elements) and leaf_directories(
        path, path_sep, complete, elements
    ):
        return True
    return False


def describe_file_type(stat: int, long: bool = True) -> str:
    if _stat.S_ISREG(stat):
        return "reg" if long else "r"
    if _stat.S_ISLNK(stat):
        return "sym" if long else "l"
    if _stat.S_ISDIR(stat):
        return "dir" if long else "d"
    if _stat.S_ISCHR(stat):
        return "chr" if long else "c"
    if _stat.S_ISBLK(stat):
        return "blk" if long else "b"
    if _stat.S_ISFIFO(stat):
        return "fifo" if long else "f"
    if _stat.S_ISSOCK(stat):
        return "sock" if long else "s"
    return "???" if long else "?"


def describe_forest[AnyStr: (
    str,
    bytes,
)](
    paths: list[AnyStr],
    *,
    numbers: bool | None = None,
    literal: bool = False,
    modes: bool = False,
    mtimes: bool = False,
    sizes: bool = True,
    relative_hardlinks: bool = False,
    follow_symlinks: bool = False,
    time_precision: int = 9,
    hash_length: int | None = None,
) -> _t.Iterator[list[str]]:
    """Produce a simple `find .`+`stat`-like description of walks of given `paths`.
    See `describe-forest` script for more info.
    """
    escape: _t.Callable[[str], str] = _identity if literal else _escape_path
    seen: dict[tuple[int, int], tuple[AnyStr, int, str]] = {}
    for i, dirpath in enumerate(paths):
        for fpath, _eps, _edir in iter_subtree(dirpath, follow_symlinks=follow_symlinks):
            abs_path = _op.abspath(fpath)
            rpath = fsdecode(_op.relpath(fpath, dirpath))
            epath: str
            if numbers is False or numbers is None and len(paths) == 1:
                epath = escape(rpath)
            else:
                epath = str(i)
                if rpath != ".":
                    epath += sep + escape(rpath)

            stat = _os.stat(abs_path, follow_symlinks=follow_symlinks)
            ino = (stat.st_dev, stat.st_ino)
            try:
                habs_path, hi, hepath = seen[ino]
            except KeyError:
                pass
            else:
                if relative_hardlinks and hi == i:
                    # within the same `dirpath`
                    dirname = _op.dirname(abs_path)
                    target = escape(fsdecode(_op.relpath(habs_path, dirname)))
                    yield [epath, "ref", "=>", target]
                else:
                    yield [epath, "ref", "==>", hepath]
                continue
            finally:
                seen[ino] = (abs_path, i, epath)

            emtime = (
                [
                    "mtime",
                    "["
                    + _TimeStamp.from_ns(stat.st_mtime_ns).format(precision=time_precision, tz=0)
                    + "]",
                ]
                if mtimes
                else []
            )
            esize = ["size", str(stat.st_size)] if sizes else []
            st_mode = stat.st_mode
            emode = ["mode", oct(_stat.S_IMODE(st_mode))[2:]] if modes else []
            if _stat.S_ISDIR(st_mode):
                yield [epath + sep, "dir"] + emode + emtime
            elif _stat.S_ISREG(st_mode):
                sha256 = sha256_file(abs_path).hex()
                if hash_length is not None:
                    sha256 = sha256[:hash_length]
                yield [epath, "reg"] + emode + emtime + esize + ["sha256", sha256]
            elif _stat.S_ISLNK(st_mode):
                esymlink = escape(fsdecode(_os.readlink(abs_path)))
                yield [epath, "sym"] + emode + emtime + ["->", esymlink]
            else:
                yield [epath, describe_file_type(st_mode)] + emode + emtime + esize


type DeferredMake[_AnyStr] = tuple[_t.Callable[[_t.Any, _AnyStr, bool], None], _t.Any, bool]
type DeferredRename[_AnyStr] = tuple[_AnyStr, bool | _os.stat_result, bool]


class Deferred[AnyStr: (str, bytes)]:
    """Deferred file system `write`s, `replace`s, `rename`s, `unlink`s, and `fsync`s.

    Basically, this exists to defer file writes, `os.replace`, `os.rename`, `os.unlink`, and
    `os.fsync` calls into the future, thus allowing the OS sync file data at its own pace in the
    meantime and batching directory updates together.

    Doing this can improve disk performance considerably.
    """

    defer: bool

    unsafe_make_file: dict[AnyStr, DeferredMake[AnyStr]]
    fsync_file: dict[AnyStr, int]
    rename_file: dict[AnyStr, DeferredRename[AnyStr]]
    unlink_file: dict[AnyStr, bool | _os.stat_result]
    fsync_dir: dict[AnyStr, int]
    fsync_dir2: dict[AnyStr, int]

    # if all of the above succeed, also do these
    _after: _t.Optional["Deferred[AnyStr]"]

    def __init__(self, defer: bool) -> None:
        self.defer = defer
        self.unsafe_make_file = {}
        self.fsync_file = {}
        self.rename_file = {}
        self.unlink_file = {}
        self.fsync_dir = {}
        self.fsync_dir2 = {}
        self._after = None

    def clear(self) -> None:
        """Forget everything."""
        self.unsafe_make_file.clear()
        self.fsync_file.clear()
        self.rename_file.clear()
        self.unlink_file.clear()
        self.fsync_dir.clear()
        self.fsync_dir2.clear()
        self._after = None

    def __len__(self) -> int:
        return (
            len(self.unsafe_make_file)
            + len(self.fsync_file)
            + len(self.rename_file)
            + len(self.unlink_file)
            + len(self.fsync_dir)
            + len(self.fsync_dir2)
            + (len(self._after) if self._after is not None else 0)
        )

    def copy(self) -> "Deferred[AnyStr]":
        """Return a shallow copy of this object (elements describing operations are not
        copied, only the structure is).
        """
        res: Deferred[AnyStr] = Deferred(self.defer)
        res.unsafe_make_file = dict(self.unsafe_make_file)
        res.fsync_file = dict(self.fsync_file)
        res.rename_file = dict(self.rename_file)
        res.unlink_file = dict(self.unlink_file)
        res.fsync_dir = dict(self.fsync_dir)
        res.fsync_dir2 = dict(self.fsync_dir2)
        if self._after is not None:
            res._after = self._after.copy()  # pylint: disable=protected-access
        return res

    def __repr__(self) -> str:
        return f"""<{self.__class__.__name__}
unsafe_make_file={self.unsafe_make_file!r}
fsync_file={self.fsync_file!r}
rename_file={self.rename_file!r}
unlink_file={self.unlink_file!r}
fsync_dir={self.fsync_dir!r}
fsync_dir2={self.fsync_dir2!r}
after={self._after!r}>"""

    @property
    def after(self) -> "Deferred[AnyStr]":
        if self._after is None:
            self._after = Deferred(self.defer)
        return self._after

    def flush(
        self,
        on_warning: _t.Callable[
            _t.Concatenate[Exception, AnyStr, str, ...], None
        ] = _log_exception_warning,
        on_error: _t.Callable[_t.Concatenate[Exception, AnyStr, str, ...], None] = _raise_one,
        simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
    ) -> None:
        """Perform all deferred operations.

        Operations that fail will be left sitting in the corresponding fields.

        With `simulate` argument set, this function instead simulates the
        `sync` and writes the log of things it would do into that argument.
        """

        made_dirs: set[AnyStr] = set()

        while (
            self.unsafe_make_file
            or self.fsync_file
            or self.rename_file
            or self.unlink_file
            or self.fsync_dir
            or self.fsync_dir2
        ):
            if self.unsafe_make_file:
                for dst_path in list(self.unsafe_make_file.keys()):
                    func, data, makedirs = self.unsafe_make_file[dst_path]
                    try:
                        unsafe_make_file(
                            func,
                            data,
                            dst_path,
                            makedirs=made_dirs if makedirs else False,
                            sync=self,
                            defer_defer=False,
                            simulate=simulate,
                        )
                    except Exception as exc:
                        on_error(exc, dst_path, "unsafe_make_file", func, data, makedirs)
                    del self.unsafe_make_file[dst_path]

            if self.fsync_file:
                for path, flags in sorted(self.fsync_file.items()):
                    try:
                        fsync_file(path, flags, simulate=simulate)
                    except Exception as exc:
                        on_warning(exc, path, "fsync_file", flags)
                    del self.fsync_file[path]

            if self.rename_file:
                for dst_path in list(self.rename_file.keys()):
                    src_path, allow_overwrites, makedirs = self.rename_file[dst_path]
                    try:
                        rename_file(
                            src_path,
                            dst_path,
                            allow_overwrites,
                            makedirs=made_dirs if makedirs else False,
                            sync=self,
                            defer_defer=False,
                            simulate=simulate,
                        )
                    except Exception as exc:
                        on_error(exc, dst_path, "rename_file", src_path, allow_overwrites, makedirs)
                    del self.rename_file[dst_path]
                    try:
                        del self.unlink_file[src_path]
                    except KeyError:
                        pass

            if self.unlink_file:
                for dst_path, exists in sorted(self.unlink_file.items()):
                    try:
                        unlink_file(
                            dst_path,
                            exists,
                            sync=self,
                            defer_defer=False,
                            simulate=simulate,
                        )
                    except Exception as exc:
                        on_error(exc, dst_path, "unlink_file", exists)
                    del self.unlink_file[dst_path]

            if self.fsync_dir:
                for path, flags in sorted(self.fsync_dir.items()):
                    try:
                        fsync_file(path, flags, simulate=simulate)
                    except Exception as exc:
                        on_warning(exc, path, "fsync_dir", flags)
                    del self.fsync_dir[path]

            if self.fsync_dir2:
                for path, flags in sorted(self.fsync_dir2.items()):
                    try:
                        fsync_file(path, flags, simulate=simulate)
                    except Exception as exc:
                        on_warning(exc, path, "fsync_dir", flags)
                    del self.fsync_dir2[path]

        if self._after is not None:
            self._after.flush(on_warning, on_error, simulate=simulate)
            if len(self._after) == 0:
                self._after = None


def fsync_maybe(fd: int) -> None:
    """Try to `os.fsync` and ignore `errno.EINVAL` errors."""
    try:
        _os.fsync(fd)
    except OSError as exc:
        if exc.errno == _errno.EINVAL:
            # EINVAL means fd is not attached to a file, so we
            # ignore this error
            return
        raise


def fsync_file[AnyStr: (
    str,
    bytes,
)](
    path: AnyStr,
    flags: int = 0,
    *,
    sync: bool | Deferred[AnyStr] = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Run `os.fsync` on a given `path`."""

    is_dir = flags & _os.O_DIRECTORY

    if isinstance(sync, Deferred):
        if is_dir:
            sync.fsync_dir[path] = flags
        else:
            sync.fsync_file[path] = flags
        return

    if simulate is not None:
        simulate("fsync", path, flags)
    elif is_dir and _WINDOWS:
        # On Windows, try fsyncing the first file instead.
        scandir_it = _os.scandir(path)
        with scandir_it:
            try:
                entry: _os.DirEntry[_t.Any] = next(scandir_it)
            except StopIteration:
                pass
            else:
                try:
                    fsync_file(entry.path, flags & ~_os.O_DIRECTORY)
                except OSError:
                    pass
    else:
        oflags = _os.O_RDONLY | _os.O_NOFOLLOW | _os.O_CLOEXEC if _POSIX else _os.O_RDWR
        try:
            fd = _os.open(path, oflags | flags)
        except OSError as exc:
            if exc.errno == _errno.ELOOP:
                # ignore symlinks; doing it this way insead of `stat`ing the path to
                # ensure atomicity
                return
            raise
        try:
            _os.fsync(fd)
        except OSError as exc:
            exc.filename = path
            raise exc
        finally:
            _os.close(fd)


def _fsync_file_barrier[AnyStr: (
    str,
    bytes,
)](
    path: AnyStr,
    fsyncs: dict[AnyStr, int],
    *,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    try:
        flags = fsyncs.pop(path)
    except KeyError:
        pass
    else:
        fsync_file(path, flags, simulate=simulate)


def unlink_file[AnyStr: (
    str,
    bytes,
)](
    path: AnyStr,
    exists: bool | _os.stat_result = True,
    *,
    dirname: AnyStr | None = None,
    sync: bool | Deferred[AnyStr] = True,
    defer_defer: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically unlink `path`."""

    if isinstance(sync, Deferred) and sync.defer and defer_defer:
        sync.unlink_file[path] = exists
        return

    if simulate is not None:
        simulate("unlink", path)
    else:
        if isinstance(exists, _os.stat_result) and not unchanged_stat(_os.lstat(path), exists):
            raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), path)
        try:
            _os.unlink(path)
        except FileNotFoundError:
            if exists:
                raise

    if sync is not False:
        if dirname is None:
            dirname, _ = dirname_dot(path)
        fsync_file(dirname, _os.O_DIRECTORY, sync=sync, simulate=simulate)


def rename_file[AnyStr: (
    str,
    bytes,
)](
    src_path: AnyStr,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    src_dir: AnyStr | None = None,
    dst_dir: AnyStr | None = None,
    sync: bool | Deferred[AnyStr] = True,
    defer_defer: bool = True,
    sync_files: bool = False,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically rename a file, performing all necesary `fsync`s."""

    if isinstance(sync, Deferred) and sync.defer and defer_defer:
        if not allow_overwrites and (
            dst_path in sync.unsafe_make_file
            or dst_path in sync.rename_file
            or _op.lexists(dst_path)
        ):
            raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)
        sync.rename_file[dst_path] = (src_path, allow_overwrites, makedirs is not False)
        return

    # if not allow_overwrites and _op.lexists(dst_path):
    #     raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    if src_dir is None:
        src_dir, _ = dirname_dot(src_path)

    if dst_dir is None:
        dst_dir, _ = dirname_dot(dst_path)

    cross = src_dir != dst_dir

    if isinstance(sync, Deferred):
        # (OrderedFSMode) Enforce ordered FS mode, because, technically, on POSIX, rename(2) can
        # loose files when moving between different directories and fsyncing out of order. For
        # example, consider the following unfortunate order of operations:
        #
        #   rename(src, dst) (== atomically: link(src, dst) -> unlink(src))
        #   -> fsync(src_dir)
        #   -> (OS crashes)
        #   -> fsync(dst_dir)
        #
        # This code prevents issues in such and similar situations.
        #
        # One of the previous writes wanted `src_path` to be synced.
        _fsync_file_barrier(src_path, sync.fsync_file, simulate=simulate)
        # One of the previous renames moved files from our `dst_dir`.
        _fsync_file_barrier(dst_dir, sync.fsync_dir2, simulate=simulate)
        if cross:
            # One of the previous renames had our `src_dir` as destination.
            _fsync_file_barrier(src_dir, sync.fsync_dir, simulate=simulate)
    elif sync and sync_files:
        fsync_file(src_path, 0, simulate=simulate)

    if dst_dir in (".", b"."):
        makedirs_ = False
    else:
        makedirs_ = dst_dir not in makedirs if isinstance(makedirs, set) else makedirs

    if makedirs_:
        if simulate is not None:
            simulate("makedirs", dst_dir)
        else:
            _os.makedirs(dst_dir, exist_ok=True)
        if isinstance(makedirs, set):
            makedirs.add(dst_dir)

    if simulate is not None:
        simulate("replace" if allow_overwrites else "rename", src_path, dst_path)
    elif allow_overwrites:
        if isinstance(allow_overwrites, _os.stat_result) and not unchanged_stat(
            _os.lstat(dst_path), allow_overwrites
        ):
            raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)
        _os.replace(src_path, dst_path)
    elif _POSIX:
        with Directory(dst_dir) as d:
            d.flock()
            # NB: this is now atomic
            if _op.lexists(dst_path):
                raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)
            _os.rename(src_path, dst_path)
    else:
        # NB: this is both atomic and fails with `FileExistsError` on Windows
        _os.rename(src_path, dst_path)

    if not sync_dirs:
        pass
    elif isinstance(sync, Deferred):
        sync.fsync_dir[dst_dir] = _os.O_DIRECTORY
        if cross:
            sync.fsync_dir2[src_dir] = _os.O_DIRECTORY
    elif sync:
        fsync_file(dst_dir, _os.O_DIRECTORY, simulate=simulate)
        if cross:
            fsync_file(src_dir, _os.O_DIRECTORY, simulate=simulate)


def unsafe_make_file[Data, AnyStr: (
    str,
    bytes,
)](
    func: _t.Callable[[Data, AnyStr, bool], None],
    data: Data,
    dst_path: AnyStr,
    *,
    makedirs: bool | set[AnyStr] = True,
    dst_dir: AnyStr | None = None,
    sync: bool | Deferred[AnyStr] = True,
    defer_defer: bool = True,
    sync_files: bool = False,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Create a file using the given `func` function, `os.unlink`ing any partial results."""

    if isinstance(sync, Deferred) and sync.defer and defer_defer:
        if dst_path in sync.unsafe_make_file or _op.lexists(dst_path):
            raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)
        sync.unsafe_make_file[dst_path] = func, data, makedirs is not False
        return

    # if _op.lexists(dst_path):
    #     raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    if dst_dir is None:
        dst_dir, _ = dirname_dot(dst_path)

    if dst_dir in (".", b"."):
        makedirs_ = False
    else:
        makedirs_ = dst_dir not in makedirs if isinstance(makedirs, set) else makedirs

    if makedirs_:
        if simulate is not None:
            simulate("makedirs", dst_dir)
        else:
            _os.makedirs(dst_dir, exist_ok=True)
        if isinstance(makedirs, set):
            makedirs.add(dst_dir)

    if simulate is not None:
        simulate("make", dst_path)
        if sync is True and sync_files:
            simulate("fsync", dst_path, 0)
    else:
        func(data, dst_path, sync is True and sync_files)

    if isinstance(sync, Deferred):
        sync.fsync_file[dst_path] = 0
        if sync_dirs:
            sync.fsync_dir[dst_dir] = _os.O_DIRECTORY
    elif sync and sync_dirs:
        # NB: `fsync(dst_path)` is done by `func`
        fsync_file(dst_dir, _os.O_DIRECTORY, simulate=simulate)


_dot_part = ".part"
_dot_partb = b".part"


def make_file[Data, AnyStr: (
    str,
    bytes,
)](
    func: _t.Callable[[Data, AnyStr, bool], None],
    data: Data,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Run `unsafe_make_file` into a temporary file and then `os.rename` or `os.replace` to `dst_path`."""

    tmp_path = dst_path + (_dot_part if isinstance(dst_path, str) else _dot_partb)

    dst_dir, _ = dirname_dot(dst_path)

    if isinstance(sync, Deferred) and sync.defer:
        sync.unlink_file[tmp_path] = False

    unsafe_make_file(
        func,
        data,
        tmp_path,
        makedirs=makedirs,
        dst_dir=dst_dir,
        sync=sync,
        sync_files=sync_files,
        sync_dirs=False,
        simulate=simulate,
    )

    try:
        rename_file(
            tmp_path,
            dst_path,
            allow_overwrites,
            makedirs=False,
            src_dir=dst_dir,
            dst_dir=dst_dir,
            sync=sync,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )
    except BaseException:
        if isinstance(sync, Deferred):
            try:
                del sync.fsync_file[tmp_path]
            except KeyError:
                pass
            if sync.defer:
                try:
                    del sync.unlink_file[tmp_path]
                except KeyError:
                    pass
        try:
            _os.unlink(tmp_path)
        except Exception:
            pass
        raise


def unsafe_write_file[AnyStr: (
    str,
    bytes,
)](data: bytes | _io.IOBase, dst_path: AnyStr, fsync_immediately: bool = True) -> None:
    try:
        with open(dst_path, "xb") as fdst:
            if isinstance(data, bytes):
                fdst.write(data)
            else:
                _shutil.copyfileobj(data, fdst)
            fdst.flush()
            if fsync_immediately:
                _os.fsync(fdst.fileno())
    except FileExistsError:
        raise
    except BaseException:
        try:
            _os.unlink(dst_path)
        except Exception:
            pass
        raise


def write_file[AnyStr: (
    str,
    bytes,
)](
    data: bytes | _io.IOBase,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically write given `data` to `dst_path` via writing `data` to a temporary file first and then
    `rename`s it to `dst_path`.
    """

    make_file(
        unsafe_write_file,
        data,
        dst_path,
        allow_overwrites,
        makedirs=makedirs,
        sync=sync,
        sync_files=sync_files,
        sync_dirs=sync_dirs,
        simulate=simulate,
    )


def unsafe_copy_file(
    src_path: str | bytes, dst_path: str | bytes, fsync_immediately: bool = True
) -> None:
    with open(src_path, "rb") as fsrc:
        try:
            with open(dst_path, "xb") as fdst:
                _shutil.copyfileobj(fsrc, fdst)
                fdst.flush()
                _shutil.copystat(src_path, dst_path, follow_symlinks=True)
                if fsync_immediately:
                    _os.fsync(fdst.fileno())
        except FileExistsError:
            raise
        except BaseException:
            try:
                _os.unlink(dst_path)
            except Exception:
                pass
            raise


def copy_file[AnyStr: (
    str,
    bytes,
)](
    src_path: str | bytes,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically copy `src_path` to `dst_path`, following symlinks."""

    make_file(
        unsafe_copy_file,
        src_path,
        dst_path,
        allow_overwrites,
        makedirs=makedirs,
        sync=sync,
        sync_files=sync_files,
        sync_dirs=sync_dirs,
        simulate=simulate,
    )


def unsafe_symlink_file(
    src_path: str | bytes, dst_path: str | bytes, _fsync_immediately: bool = False
) -> None:
    # NB: this raises `FileExistsError` when `dst_path` exists
    _os.symlink(src_path, dst_path)
    # if fsync_immediately:
    #     fsync_file(dst_dir, _os.O_SYMLINK)


def symlink_file[AnyStr: (
    str,
    bytes,
)](
    src_path: str | bytes,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically symlink `src_path` to `dst_path`."""

    if allow_overwrites or (isinstance(sync, Deferred) and sync.defer):
        make_file(
            unsafe_symlink_file,
            src_path,
            dst_path,
            allow_overwrites,
            makedirs=makedirs,
            sync=sync,
            sync_files=sync_files,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )
    else:
        # `_os.symlink` is atomic, so non-atomic `unsafe_make_file` is ok in this case
        unsafe_make_file(
            unsafe_symlink_file,
            src_path,
            dst_path,
            makedirs=makedirs,
            sync=sync,
            sync_files=sync_files,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )


def unsafe_copy_symlink(
    src_path: str | bytes, dst_path: str | bytes, _fsync_immediately: bool = False
) -> None:
    data = _os.readlink(fsencode(src_path))
    _os.symlink(data, dst_path)
    _shutil.copystat(src_path, dst_path, follow_symlinks=False)
    # if fsync_immediately:
    #     fsync_file(dst_dir, _os.O_SYMLINK)


def unsafe_clone_file(
    src_path: str | bytes, dst_path: str | bytes, fsync_immediately: bool = True
) -> None:
    if _op.islink(src_path):
        unsafe_copy_symlink(src_path, dst_path, fsync_immediately)
        return
    unsafe_copy_file(src_path, dst_path, fsync_immediately)


def clone_file[AnyStr: (
    str,
    bytes,
)](
    src_path: str | bytes,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically copy `src_path` to `dst_path`, not following and preserving symlinks."""

    make_file(
        unsafe_clone_file,
        src_path,
        dst_path,
        allow_overwrites,
        makedirs=makedirs,
        sync=sync,
        sync_files=sync_files,
        sync_dirs=sync_dirs,
        simulate=simulate,
    )


def unsafe_link_file(
    src_path: str | bytes, dst_path: str | bytes, _fsync_immediately: bool = False
) -> None:
    # NB: this raises `FileExistsError` when `dst_path` exists
    _os.link(src_path, dst_path, follow_symlinks=False)


def link_file[AnyStr: (
    str,
    bytes,
)](
    src_path: str | bytes,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = False,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically hardlink `src_path` to `dst_path`."""

    if allow_overwrites or (isinstance(sync, Deferred) and sync.defer):
        make_file(
            unsafe_link_file,
            src_path,
            dst_path,
            allow_overwrites,
            makedirs=makedirs,
            sync=sync,
            sync_files=sync_files,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )
    else:
        # `_os.link` is atomic, so non-atomic `unsafe_make_file` is ok in this case
        unsafe_make_file(
            unsafe_link_file,
            src_path,
            dst_path,
            makedirs=makedirs,
            sync=sync,
            sync_files=sync_files,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )


def link_or_clone_file[AnyStr: (
    str,
    bytes,
)](
    src_path: str | bytes,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically hardlink or copy `src_path` to `dst_path`."""

    try:
        link_file(
            src_path,
            dst_path,
            allow_overwrites,
            makedirs=makedirs,
            sync=sync,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )
    except OSError as exc:
        if exc.errno != _errno.EXDEV:
            raise
        clone_file(
            src_path,
            dst_path,
            allow_overwrites,
            makedirs=makedirs,
            sync=sync,
            sync_files=sync_files,
            sync_dirs=sync_dirs,
            simulate=simulate,
        )


def move_file[AnyStr: (
    str,
    bytes,
)](
    src_path: AnyStr,
    dst_path: AnyStr,
    allow_overwrites: bool | _os.stat_result = False,
    *,
    unlink_safely: bool = True,
    makedirs: bool | set[AnyStr] = True,
    sync: bool | Deferred[AnyStr] = True,
    sync_files: bool = True,
    sync_dirs: bool = True,
    simulate: _t.Callable[_t.Concatenate[str, ...], None] | None = None,
) -> None:
    """Atomically move `src_path` to `dst_path`."""

    exists: bool | _os.stat_result = (
        _os.lstat(src_path)
        if unlink_safely
        and isinstance(sync, Deferred)
        and (not sync.defer or src_path in sync.unsafe_make_file or src_path in sync.rename_file)
        and simulate is None
        else True
    )

    link_or_clone_file(
        src_path,
        dst_path,
        allow_overwrites,
        makedirs=makedirs,
        sync=sync,
        sync_files=sync_files,
        sync_dirs=sync_dirs,
        simulate=simulate,
    )

    if isinstance(sync, Deferred):
        sync.after.unlink_file[src_path] = exists
        return

    unlink_file(src_path, sync=sync, simulate=simulate)


def setup_fs(prog: str | None = None, ext: str = ".part", add_pid: bool = True) -> None:
    """Setup temporary files prefix."""
    if prog is None:
        prog = _op.basename(_sys.argv[0])

    global _dot_part, _dot_partb
    pid = f"{_os.getpid()}." if add_pid else ""
    _dot_part = f".{pid}{prog}{ext}"
    _dot_partb = _dot_part.encode("ascii")
