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

from .base import POSIX as _POSIX, identity as _identity
from .io.base import *
from .string_ext import escape_path as _escape_path
from .time import Timestamp as _Timestamp

sep = _op.sep
sepb = _os.fsencode(_op.sep)


def dirname_dot(path: _t.AnyStr) -> tuple[_t.AnyStr, bool]:
    """Apply `os.path.dirname` to the given argument, but if it's empty, return "." instead.
    The second element of the tuple is `False` if the above replacement was performed, `True` otherwise.
    """
    path = _os.path.dirname(path)
    if isinstance(path, bytes):
        if path == b"":
            return b".", False
        return path, True
    if path == "":
        return ".", False
    return path, True


def realdir(path: _t.AnyStr, strict: bool = False) -> _t.AnyStr:
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


def file_data_equals(path: str | bytes, data: bytes) -> bool:
    """Check if contents of the given file `path` is equal to `data`."""
    try:
        with open(path, "rb") as f:
            return fileobj_data_equals(f, data)
    except FileNotFoundError:
        return False


def same_file_data(path1: str | bytes, path2: str | bytes) -> bool:
    """Check if two given files have exactly the same content."""
    with open(path1, "rb") as f1:
        with open(path2, "rb") as f2:
            return same_fileobj_data(f1, f2)


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


IncludeFilesFunc = _t.Callable[[_t.AnyStr], bool]
IncludeDirectoriesFunc = _t.Callable[
    [_t.AnyStr, _t.AnyStr, bool, list[tuple[_t.AnyStr, _t.AnyStr, bool]]], bool | None
]


class WalkOrder(_enum.Enum):
    NONE = 0
    SORT = 1
    REVERSE = 2


def iter_subtree(
    path: _t.AnyStr,
    *,
    include_files: bool | IncludeFilesFunc[_t.AnyStr] = True,
    include_directories: bool | IncludeDirectoriesFunc[_t.AnyStr] = True,
    follow_symlinks: bool = True,
    order: WalkOrder = WalkOrder.SORT,
    handle_error: _t.Callable[..., None] | None = None,
    path_sep: _t.AnyStr | None = None,
) -> _t.Iterator[tuple[_t.AnyStr, _t.AnyStr, bool]]:
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
    elements: list[tuple[_t.AnyStr, _t.AnyStr, bool]] = []

    with scandir_it:
        while True:
            try:
                entry: _os.DirEntry[_t.AnyStr] = next(scandir_it)
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

                epath_sep: _t.AnyStr = entry.path
                if entry_is_dir:
                    if isinstance(epath_sep, str):
                        epath_sep += sep
                    else:
                        epath_sep += sepb
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


def as_include_directories(f: IncludeFilesFunc[_t.AnyStr]) -> IncludeDirectoriesFunc[_t.AnyStr]:
    """`convert iter_subtree(..., include_files, ...)` filter to `include_directories` filter"""

    def func(
        path: _t.AnyStr,
        _path_sep: _t.AnyStr,
        _complete: bool,
        _elements: list[tuple[_t.AnyStr, _t.AnyStr, bool]],
    ) -> bool:
        return f(path)

    return func


def with_extension_in(exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[_t.AnyStr]:
    """`iter_subtree(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that have one of the given extensions"""

    def pred(path: _t.AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext in exts

    return pred


def with_extension_not_in(exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[_t.AnyStr]:
    """`iter_subtree(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that do not have any of the given extensions"""

    def pred(path: _t.AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext not in exts

    return pred


def nonempty_directories(
    _path: _t.AnyStr,
    _path_sep: _t.AnyStr,
    complete: bool,
    elements: list[tuple[_t.AnyStr, _t.AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print only non-empty directories"""
    if len(elements) == 0:
        return not complete
    return True


def leaf_directories(
    _path: _t.AnyStr,
    _path_sep: _t.AnyStr,
    complete: bool,
    elements: list[tuple[_t.AnyStr, _t.AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print leaf directories only, i.e. only directories without sub-directories"""
    if complete and all(map(lambda x: not x[2], elements)):
        return True
    return False


def nonempty_leaf_directories(
    path: _t.AnyStr,
    path_sep: _t.AnyStr,
    complete: bool,
    elements: list[tuple[_t.AnyStr, _t.AnyStr, bool]],
) -> bool:
    """`iter_subtree(..., include_directories, ...)` filter that makes it print only non-empty leaf directories, i.e. non-empty directories without sub-directories"""
    if nonempty_directories(path, path_sep, complete, elements) and leaf_directories(
        path, path_sep, complete, elements
    ):
        return True
    return False


def describe_forest(
    paths: list[_t.AnyStr],
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
    seen: dict[tuple[int, int], tuple[_t.AnyStr, int, str]] = {}
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
                    + _Timestamp.from_ns(stat.st_mtime_ns).format(
                        precision=time_precision, utc=True
                    )
                    + "]",
                ]
                if mtimes
                else []
            )
            esize = ["size", str(stat.st_size)] if sizes else []
            emode = ["mode", oct(_stat.S_IMODE(stat.st_mode))[2:]] if modes else []
            if _stat.S_ISDIR(stat.st_mode):
                yield [epath + sep, "dir"] + emode + emtime
            elif _stat.S_ISREG(stat.st_mode):
                sha256 = sha256_file(abs_path).hex()
                if hash_length is not None:
                    sha256 = sha256[:hash_length]
                yield [epath, "reg"] + emode + emtime + esize + ["sha256", sha256]  # fmt: skip
            elif _stat.S_ISLNK(stat.st_mode):
                esymlink = escape(fsdecode(_os.readlink(abs_path)))
                yield [epath, "sym"] + emode + emtime + ["->", esymlink]
            else:
                yield [epath, "???"] + emode + emtime + esize


DeferredRename = tuple[_t.AnyStr, _t.AnyStr, bool, _t.AnyStr, _t.AnyStr]


class DeferredSync(_t.Generic[_t.AnyStr]):
    """Deferred file system `replace`s, `rename`s, `unlink`s, and `fsync`s.

    Basically, this exists to defer `os.replace`, `os.rename`, `os.unlink`, and
    `os.fsync` calls into the future, thus allowing the OS sync file data at its
    own pace in the meantime and batching directory updates together.

    Doing this can improve disk performance considerably.
    """

    defer: bool
    tmp_file: set[_t.AnyStr]
    unlink_file: set[_t.AnyStr]
    fsync_file: set[_t.AnyStr]
    fsync_dir: set[_t.AnyStr]
    fsync_dir2: set[_t.AnyStr]
    rename_file: _c.deque[DeferredRename[_t.AnyStr]]

    # if all of the above succeed, also do these
    _after: _t.Optional["DeferredSync[_t.AnyStr]"]

    def __init__(self, defer: bool) -> None:
        self.defer = defer
        self.reset()

    def reset(self) -> None:
        """Forget everything."""
        self.tmp_file = set()
        self.unlink_file = set()
        self.fsync_file = set()
        self.fsync_dir = set()
        self.fsync_dir2 = set()
        self.rename_file = _c.deque()
        self._after = None

    @property
    def after(self) -> "DeferredSync[_t.AnyStr]":
        if self._after is None:
            self._after = DeferredSync(self.defer)
        return self._after

    def __repr__(self) -> str:
        return (
            f"""<{self.__class__.__name__}
tmp={self.tmp_file!r}
unlink={self.unlink_file!r}
fsync_file={self.fsync_file!r}
fsync_dir={self.fsync_dir!r}
fsync_dir2={self.fsync_dir2!r}
rename_file={self.rename_file!r}
after="""
            + repr(self._after)
            + ">"
        )

    def copy(self) -> "DeferredSync[_t.AnyStr]":
        """Return a shallow copy of this object (elements describing operations are not
        copied, only the structure is).
        """
        res: DeferredSync[_t.AnyStr] = DeferredSync(self.defer)
        res.tmp_file = set(self.tmp_file)
        res.unlink_file = set(self.unlink_file)
        res.fsync_file = set(self.fsync_file)
        res.fsync_dir = set(self.fsync_dir)
        res.fsync_dir2 = set(self.fsync_dir2)
        res.rename_file = _c.deque(self.rename_file)
        if self._after is not None:
            res._after = self._after.copy()  # pylint: disable=protected-access
        return res

    def clear(self) -> None:
        """Forget all currently deferred operations and unlink all temporary files."""
        if self._after is not None:
            self._after.clear()
        if self.tmp_file:
            unlink_many(self.tmp_file)
        self.reset()

    def sync(self, strict: bool = True, simulate: list[list[str]] | None = None) -> list[Exception]:
        """Perform all deferred operations and return a list of raised exceptions.

        Operations that fail will be left sitting in the corresponding fields.

        With `simulate` argument set, this function instead simulates the
        `sync` and writes the log of things it would do into that argument.
        """
        exceptions: list[Exception] = []

        if simulate is not None:
            simulate += [["unlink", fsdecode(f)] for f in sorted(self.unlink_file)]
            self.unlink_file = set()
        elif self.unlink_file:
            self.unlink_file = set(unlink_many(sorted(self.unlink_file), exceptions))

        if strict and exceptions:
            return exceptions

        fsync_file_left: set[_t.AnyStr] = set()
        fsync_dir_left: set[_t.AnyStr] = set()
        fsync_dir2_left: set[_t.AnyStr] = set()
        rename_file_left: _c.deque[DeferredRename[_t.AnyStr]] = _c.deque()

        def done() -> None:
            self.fsync_file.update(fsync_file_left)
            self.fsync_dir.update(fsync_dir_left)
            self.fsync_dir2.update(fsync_dir2_left)
            rename_file_left.extend(self.rename_file)
            self.rename_file = rename_file_left

        while self.fsync_file or self.fsync_dir or self.fsync_dir2 or self.rename_file:
            if simulate is not None:
                simulate += [["fsync", fsdecode(f)] for f in sorted(self.fsync_file)]
                self.fsync_file = set()
            elif self.fsync_file:
                fsync_file_left.update(fsync_many_files(sorted(self.fsync_file), 0, exceptions))
                self.fsync_file = set()

            if strict and exceptions:
                done()
                return exceptions

            if self.rename_file:
                while self.rename_file:
                    el = self.rename_file.popleft()
                    src_path, dst_path, allow_overwrites, src_dir, dst_dir = el
                    cross = src_dir != dst_dir
                    if dst_dir in self.fsync_dir2 or cross and src_dir in self.fsync_dir:
                        # One of the previous renames moved files from our
                        # dst_dir or had our src_dir as destination. Delay this
                        # rename until previous operations sync.
                        #
                        # I.e., essentially, we force ordered FS mode, because,
                        # technically, rename(2) is allowed to loose the file
                        # when moving between different directories and fsyncing
                        # out of order. Consider this:
                        #
                        # rename(src, dst) (== overwrite_link(src, dst) -> unlink(src))
                        # -> fsync(src_dir) -> (OS crashes) -> fsync(dst_dir)
                        self.rename_file.appendleft(el)
                        if simulate is not None:
                            simulate.append(["barrier"])
                        break

                    try:
                        if simulate is not None:
                            simulate.append(["replace" if allow_overwrites else "rename", fsdecode(src_path), fsdecode(dst_path)])  # fmt: skip
                        else:
                            rename(src_path, dst_path, allow_overwrites, makedirs=False, dst_dir=dst_dir)  # fmt: skip
                    except Exception as exc:
                        exceptions.append(exc)
                        rename_file_left.append(el)
                    else:
                        self.tmp_file.discard(src_path)
                        for s in (self.fsync_file, fsync_file_left):
                            # if queued for fsyncing there, rename
                            try:
                                s.remove(src_path)
                            except KeyError:
                                pass
                            else:
                                s.add(dst_path)
                        self.fsync_dir.add(dst_dir)
                        if cross:
                            self.fsync_dir2.add(src_dir)
                        if not _POSIX or simulate is not None:
                            # on Windows, some docs claim, this helps
                            self.fsync_file.add(dst_path)

                    if strict and exceptions:
                        done()
                        return exceptions

            if simulate is not None:
                simulate += [["fsync_win", fsdecode(f)] for f in sorted(self.fsync_file)]
                self.fsync_file = set()
            elif self.fsync_file:
                fsync_file_left.update(fsync_many_files(sorted(self.fsync_file), 0, exceptions))
                self.fsync_file = set()

            if simulate is not None:
                simulate += [["fsync_dir", fsdecode(f)] for f in sorted(self.fsync_dir)]
                self.fsync_dir = set()
            elif self.fsync_dir:
                if _POSIX:
                    fsync_dir_left.update(fsync_many_files(sorted(self.fsync_dir), _os.O_DIRECTORY, exceptions))  # fmt: skip
                self.fsync_dir = set()

            if simulate is not None:
                simulate += [["fsync_dir", fsdecode(f)] for f in sorted(self.fsync_dir2)]
                self.fsync_dir2 = set()
            elif self.fsync_dir2:
                if _POSIX:
                    fsync_dir2_left.update(fsync_many_files(sorted(self.fsync_dir2), _os.O_DIRECTORY, exceptions))  # fmt: skip
                self.fsync_dir2 = set()

            if strict and exceptions:
                done()
                return exceptions

        if strict and self.tmp_file:
            exceptions.append(AssertionError("`tmp_file` set is not empty"))

        if exceptions:
            done()
            return exceptions

        if self._after is not None:
            excs = self._after.sync(strict, simulate)
            if len(excs) > 0:
                exceptions += excs
            else:
                self._after = None

        return exceptions

    def flush(self, strict: bool = True) -> None:
        """Like `sync` but raises collected exceptions as an exception group and calls
        `.clear` in that case.
        """
        try:
            excs = self.sync(strict)
            if len(excs) > 0:
                raise ExceptionGroup("failed to sync", excs)
        finally:
            self.clear()


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


def fsync_file(path: str | bytes, flags: int = 0) -> None:
    """Run `os.fsync` on a given `path`."""
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


def fsync_many_files(
    paths: _t.Iterable[_t.AnyStr], flags: int = 0, exceptions: list[Exception] | None = None
) -> list[_t.AnyStr]:
    """`os.fsync` many paths, optionally collecting exceptions.
    Returns the paths for which `os.fsync` failed.
    """
    left = []
    for path in paths:
        try:
            fsync_file(path, flags)
        except Exception as exc:
            if exceptions is None:
                raise
            left.append(path)
            exceptions.append(exc)
    return left


def unlink_maybe(path: str | bytes) -> None:
    """Try to `os.unlink` and ignore `Exception`s."""
    try:
        _os.unlink(path)
    except Exception:
        pass


def unlink_many(
    paths: _t.Iterable[_t.AnyStr], exceptions: list[Exception] | None = None
) -> list[_t.AnyStr]:
    """`os.unlink` many paths, optionally collecting exceptions.
    Returns the paths for which `os.unlink` failed.
    """
    left = []
    for path in paths:
        try:
            _os.unlink(path)
        except Exception as exc:
            if exceptions is None:
                raise
            left.append(path)
            exceptions.append(exc)
    return left


def atomic_unlink(
    path: _t.AnyStr,
    *,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically unlink `path`."""

    dirname, _ = dirname_dot(path)

    if isinstance(sync, DeferredSync) and sync.defer:
        sync.unlink_file.add(path)
        sync.fsync_dir.add(dirname)
        return

    _os.unlink(path)

    if isinstance(sync, DeferredSync):
        sync.fsync_dir.add(dirname)
        return

    if sync and _POSIX:
        fsync_file(dirname, _os.O_DIRECTORY)


def rename(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool,
    *,
    makedirs: bool = True,
    dst_dir: _t.AnyStr | None = None,
) -> None:
    if dst_dir is None:
        dst_dir, nondot = dirname_dot(dst_path)
        makedirs = makedirs and nondot

    if makedirs:
        _os.makedirs(dst_dir, exist_ok=True)

    if allow_overwrites:
        _os.replace(src_path, dst_path)
    elif _POSIX:
        with Directory(dst_dir) as d:
            d.flock()
            # this is now atomic
            if _os.path.lexists(dst_path):
                raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)
            _os.rename(src_path, dst_path)
    else:
        # this is both atomic and fails with `FileExistsError` on Windows
        _os.rename(src_path, dst_path)


def atomic_rename(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool,
    *,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically rename a file, performing all necesary `fsync`s."""

    src_dir, _ = dirname_dot(src_path)
    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)

    if isinstance(sync, DeferredSync) and sync.defer:
        sync.rename_file.append((src_path, dst_path, allow_overwrites, src_dir, dst_dir))
        return

    rename(src_path, dst_path, allow_overwrites, makedirs=False, dst_dir=dst_dir)

    if isinstance(sync, DeferredSync):
        sync.fsync_dir.add(dst_dir)
        return

    if sync:
        if _POSIX:
            fsync_file(dst_dir, _os.O_DIRECTORY)
            if src_dir != dst_dir:
                fsync_file(src_dir, _os.O_DIRECTORY)
        else:
            # on Windows, some docs claim, this helps
            fsync_file(dst_path)


def make_file(
    make_dst: _t.Callable[[_t.AnyStr, bool], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Create a file using a given `make_dst` function."""

    if not allow_overwrites and _os.path.lexists(dst_path):
        # fail early
        raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)
    make_dst(dst_path, isinstance(sync, bool))

    if isinstance(sync, DeferredSync):
        sync.fsync_file.add(dst_path)
        sync.fsync_dir.add(dst_dir)
        return

    if sync and _POSIX:
        fsync_file(dst_dir, _os.O_DIRECTORY)


_dot_part = ".part"
_dot_partb = b".part"


def atomic_make_file(
    make_dst: _t.Callable[[_t.AnyStr, bool], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically create a file using a given `make_dst` function. This
    runs `make_dst` on a `.part` path first, `fsync`s it, then does
    `os.rename` or `os.replace` to `dst_path` (on POSIX, `flock`ing
    the target directory, to make it truly atomic), then `fsync`s the
    target directory.
    """

    if not allow_overwrites and _os.path.lexists(dst_path):
        # fail early
        raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    if isinstance(dst_path, str):
        tmp_path = dst_path + _dot_part
    else:
        tmp_path = dst_path + _dot_partb

    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)
    make_dst(tmp_path, isinstance(sync, bool) and sync)

    if isinstance(sync, DeferredSync) and sync.defer:
        sync.tmp_file.add(tmp_path)
        sync.fsync_file.add(tmp_path)
        sync.rename_file.append((tmp_path, dst_path, allow_overwrites, dst_dir, dst_dir))
        return

    try:
        if sync:
            fsync_file(tmp_path)
        rename(tmp_path, dst_path, allow_overwrites, dst_dir=dst_dir)
    except Exception:
        unlink_maybe(tmp_path)
        raise

    if isinstance(sync, DeferredSync):
        sync.fsync_dir.add(dst_dir)
        return

    if sync and _POSIX:
        fsync_file(dst_dir, _os.O_DIRECTORY)
        # NB: src_dir == dst_dir


def atomic_write(
    data: bytes,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically write given `data` to `dst_path`."""

    def make_dst(tmp_path: _t.AnyStr, fsync_immediately: bool) -> None:
        try:
            with open(tmp_path, "xb") as fdst:
                fdst.write(data)
                fdst.flush()
                if fsync_immediately:
                    _os.fsync(fdst.fileno())
        except Exception:
            unlink_maybe(tmp_path)
            raise

    atomic_make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)


def atomic_copy2(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically copy `src_path` to `dst_path`."""

    def make_dst(tmp_path: _t.AnyStr, fsync_immediately: bool) -> None:
        try:
            if not follow_symlinks and _os.path.islink(src_path):
                _os.symlink(_os.readlink(src_path), tmp_path)
                _shutil.copystat(src_path, tmp_path, follow_symlinks=False)
            else:
                with open(src_path, "rb") as fsrc:
                    with open(tmp_path, "xb") as fdst:
                        _shutil.copyfileobj(fsrc, fdst)
                        fdst.flush()
                        _shutil.copystat(src_path, tmp_path, follow_symlinks=follow_symlinks)
                        if fsync_immediately:
                            _os.fsync(fdst.fileno())
        except Exception:
            unlink_maybe(tmp_path)
            raise

    # always use the atomic version here, like rsync does,
    # since copying can be interrupted in the middle
    atomic_make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)


def atomic_link(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically hardlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_path: _t.AnyStr, _fsync_immediately: bool) -> None:
        _os.link(src_path, dst_path, follow_symlinks=follow_symlinks)

    # _os.link is atomic, so non-atomic make_file is ok
    if allow_overwrites or (isinstance(sync, DeferredSync) and sync.defer):
        atomic_make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)
    else:
        make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)


def atomic_symlink(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically symlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_path: _t.AnyStr, _fsync_immediately: bool) -> None:
        _os.symlink(src_path, dst_path)

    # _os.symlink is atomic, so non-atomic make_file is ok
    if allow_overwrites or (isinstance(sync, DeferredSync) and sync.defer):
        atomic_make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)
    else:
        make_file(make_dst, dst_path, allow_overwrites, makedirs=makedirs, sync=sync)


def atomic_link_or_copy2(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically hardlink or copy `src_path` to `dst_path`."""

    try:
        atomic_link(src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, makedirs=makedirs, sync=sync)  # fmt: skip
    except OSError as exc:
        if exc.errno != _errno.EXDEV:
            raise
        atomic_copy2(src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, makedirs=makedirs, sync=sync)  # fmt: skip


def atomic_move(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = False,
    makedirs: bool = True,
    sync: DeferredSync[_t.AnyStr] | bool = True,
) -> None:
    """Atomically move `src_path` to `dst_path`.

    Note that `follow_symlinks` is set to `False` by default for this function
    so that the result would be similar to that of `mv(1)` util.
    """

    src_dir, _ = dirname_dot(src_path)

    atomic_link_or_copy2(src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, makedirs=makedirs, sync=sync)  # fmt: skip

    if isinstance(sync, DeferredSync):
        after = sync.after
        after.unlink_file.add(src_path)
        after.fsync_dir.add(src_dir)
        return

    _os.unlink(src_path)

    if sync and _POSIX:
        fsync_file(src_dir, _os.O_DIRECTORY)


def setup_fs(prog: str | None = None, ext: str = ".part", add_pid: bool = True) -> None:
    """Setup temporary files prefix."""
    if prog is None:
        prog = _op.basename(_sys.argv[0])

    global _dot_part, _dot_partb
    pid = f"{_os.getpid()}." if add_pid else ""
    _dot_part = f".{pid}{prog}{ext}"
    _dot_partb = _dot_part.encode("ascii")
