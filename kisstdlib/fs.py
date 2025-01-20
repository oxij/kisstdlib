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

from .io.base import *
from .io.base import _POSIX
from .time import Timestamp as _Timestamp


def fsdecode_maybe(x: str | bytes) -> str:
    """Apply `os.fsdecode` if `bytes`."""
    if isinstance(x, bytes):
        return _os.fsdecode(x)
    return x


def fsencode_maybe(x: str | bytes) -> bytes:
    """Apply `os.fsencode` if `str`."""
    if isinstance(x, str):
        return _os.fsencode(x)
    return x


def dirname_dot(x: _t.AnyStr) -> tuple[_t.AnyStr, bool]:
    """Apply `os.path.dirname` to the given argument, but if it's empty, return "." instead.
    The second element of the tuple is `False` if the above replacement was performed, `True` otherwise.
    """
    x = _os.path.dirname(x)
    if isinstance(x, bytes):
        if x == b"":
            return b".", False
        return x, True
    if x == "":
        return ".", False
    return x, True


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


IncludeFilesFunc = _t.Callable[[_t.AnyStr], bool]
IncludeDirectoriesFunc = _t.Callable[[_t.AnyStr, bool, list[tuple[_t.AnyStr, bool]]], bool | None]


class WalkOrder(_enum.Enum):
    NONE = 0
    SORT = 1
    REVERSE = 2


def walk_orderly(
    path: _t.AnyStr,
    *,
    include_files: bool | IncludeFilesFunc[_t.AnyStr] = True,
    include_directories: bool | IncludeDirectoriesFunc[_t.AnyStr] = True,
    follow_symlinks: bool = True,
    order: WalkOrder = WalkOrder.SORT,
    handle_error: _t.Callable[..., None] | None = None,
    path_is_file_maybe: bool = True,
) -> _t.Iterable[tuple[_t.AnyStr, bool]]:
    """Similar to `os.walk`, but produces an iterator over paths, allows
    non-directories as input (which will just output a single
    element), provides convenient filtering and error handling, and
    the output is guaranteed to be ordered if `order` is not `NONE`.
    """

    if path_is_file_maybe:
        try:
            fstat = _os.stat(path, follow_symlinks=follow_symlinks)
        except OSError as exc:
            if handle_error is not None:
                eno = exc.errno
                handle_error(
                    "failed to stat `%s`: [Errno %d, %s] %s: %s",
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
            yield path, False
            return

    try:
        scandir_it = _os.scandir(path)
    except OSError as exc:
        if handle_error is not None:
            eno = exc.errno
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
    elements: list[tuple[_t.AnyStr, bool]] = []

    with scandir_it:
        while True:
            try:
                entry: _os.DirEntry[_t.AnyStr] = next(scandir_it)
            except StopIteration:
                break
            except OSError as exc:
                if handle_error is not None:
                    eno = exc.errno
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
                        eno = exc.errno
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

                elements.append((entry.path, entry_is_dir))

    if order != WalkOrder.NONE:
        elements.sort(reverse=order == WalkOrder.REVERSE)

    if isinstance(include_directories, bool):
        if include_directories:
            yield path, True
    else:
        inc = include_directories(path, complete, elements)
        if inc is None:
            return
        if inc:
            yield path, True

    for epath, eis_dir in elements:
        if eis_dir:
            yield from walk_orderly(
                epath,
                include_files=include_files,
                include_directories=include_directories,
                follow_symlinks=follow_symlinks,
                order=order,
                handle_error=handle_error,
                path_is_file_maybe=False,
            )
            continue
        if isinstance(include_files, bool):
            if not include_files:
                continue
        elif not include_files(epath):
            continue
        yield epath, False


def as_include_directories(f: IncludeFilesFunc[_t.AnyStr]) -> IncludeDirectoriesFunc[_t.AnyStr]:
    """`convert walk_orderly(..., include_files, ...)` filter to `include_directories` filter"""

    def func(path: _t.AnyStr, _complete: bool, _elements: list[tuple[_t.AnyStr, bool]]) -> bool:
        return f(path)

    return func


def with_extension_in(exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[_t.AnyStr]:
    """`walk_orderly(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that have one of the given extensions"""

    def pred(path: _t.AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext in exts

    return pred


def with_extension_not_in(exts: _cabc.Collection[str | bytes]) -> IncludeFilesFunc[_t.AnyStr]:
    """`walk_orderly(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that do not have any of the given extensions"""

    def pred(path: _t.AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext not in exts

    return pred


def nonempty_directories(
    _path: _t.AnyStr, complete: bool, elements: list[tuple[_t.AnyStr, bool]]
) -> bool:
    """`walk_orderly(..., include_directories, ...)` filter that makes it print only non-empty directories"""
    if len(elements) == 0:
        return not complete
    return True


def leaf_directories(
    _path: _t.AnyStr, complete: bool, elements: list[tuple[_t.AnyStr, bool]]
) -> bool:
    """`walk_orderly(..., include_directories, ...)` filter that makes it print leaf directories only, i.e. only directories without sub-directories"""
    if complete and all(map(lambda x: not x[1], elements)):
        return True
    return False


def nonempty_leaf_directories(
    path: _t.AnyStr, complete: bool, elements: list[tuple[_t.AnyStr, bool]]
) -> bool:
    """`walk_orderly(..., include_directories, ...)` filter that makes it print only non-empty leaf directories, i.e. non-empty directories without sub-directories"""
    if nonempty_directories(path, complete, elements) and leaf_directories(
        path, complete, elements
    ):
        return True
    return False


def _quote_path(x: str) -> str:
    return x.replace("\\", "\\\\").replace("\n", "\\n")


def _hex_sha256_of(path: str | bytes) -> str:
    BUFFER_SIZE = 8 * MiB
    with open(path, "rb") as f:
        fhash = _hashlib.sha256()
        while True:
            data = f.read(BUFFER_SIZE)
            if len(data) == 0:
                break
            fhash.update(data)
        return fhash.hexdigest()


def describe_walks(
    paths: list[_t.AnyStr],
    show_mode: bool = True,
    show_mtime: bool = True,
    mtime_precision: int = 9,
    hash_len: int = 64,
) -> _t.Iterator[list[str]]:
    """Produce a simple description of walks of given `paths`.
    See `describe-dir` script.
    """
    seen: dict[tuple[int, int], tuple[_t.AnyStr, int, str]] = {}
    for i, dirpath in enumerate(paths):
        for fpath, _ in walk_orderly(dirpath, follow_symlinks=False):
            abs_path = _op.abspath(fpath)
            rpath = _op.relpath(fpath, dirpath)
            apath: str = _quote_path(
                (str(i) + _op.sep if len(paths) > 1 else "") + fsdecode_maybe(rpath)
            )

            stat = _os.lstat(abs_path)
            ino = (stat.st_dev, stat.st_ino)
            try:
                habs_path, hi, hapath = seen[ino]
            except KeyError:
                seen[ino] = (abs_path, i, apath)
            else:
                if hi == i:
                    # within the same `dirpath`
                    dirname = _op.dirname(abs_path)
                    target = _quote_path(fsdecode_maybe(_op.relpath(habs_path, dirname)))
                    yield [apath, "ref", "=>", target]
                else:
                    yield [apath, "ref", "==>", hapath]
                continue

            if show_mtime:
                mtime = [
                    "mtime",
                    "["
                    + _Timestamp.from_ns(stat.st_mtime_ns).format(
                        precision=mtime_precision, utc=True
                    )
                    + "]",
                ]
            else:
                mtime = []
            size = stat.st_size
            if show_mode:
                mode = ["mode", oct(_stat.S_IMODE(stat.st_mode))[2:]]
            else:
                mode = []
            if _stat.S_ISDIR(stat.st_mode):
                yield [apath, "dir"] + mode + mtime
            elif _stat.S_ISREG(stat.st_mode):
                sha256 = _hex_sha256_of(abs_path)[:hash_len]
                yield [apath, "reg"] + mode + mtime + ["size", str(size), "sha256", sha256]  # fmt: skip
            elif _stat.S_ISLNK(stat.st_mode):
                symlink = _os.readlink(abs_path)
                arrow = "->"
                if (
                    isinstance(symlink, bytes)
                    and symlink.startswith(b"/")
                    or isinstance(symlink, str)
                    and symlink.startswith("/")
                ):
                    # absolute symlink
                    symlink = _op.realpath(abs_path)
                    arrow = "/->"
                yield [apath, "sym"] + mode + mtime + [arrow, _quote_path(fsdecode_maybe(symlink))]  # fmt: skip
            else:
                yield [apath, "???"] + mode + mtime + ["size", str(size)]


def describe_path(path: _t.AnyStr) -> _t.Iterator[list[str]]:
    """Produce a very simple description of walks of given `paths`, suitable for tests."""
    return describe_walks([path], False, False, 0, 8)


def unlink_maybe(path: str | bytes) -> None:
    """Try to `os.unlink` and ignore errors."""
    try:
        _os.unlink(path)
    except Exception:
        pass


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


def fsync_path(path: str | bytes, flags: int = 0) -> None:
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


def unlink_many_paths(
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
            if exceptions is not None:
                exceptions.append(exc)
            left.append(path)
    return left


def fsync_many_paths(
    paths: _t.Iterable[_t.AnyStr], flags: int = 0, exceptions: list[Exception] | None = None
) -> list[_t.AnyStr]:
    """`os.fsync` many paths, optionally collecting exceptions.
    Returns the paths for which `os.fsync` failed.
    """
    left = []
    for path in paths:
        try:
            fsync_path(path, flags)
        except Exception as exc:
            if exceptions is not None:
                exceptions.append(exc)
            left.append(path)
    return left


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
        makedirs &= nondot

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


DeferredRename = tuple[_t.AnyStr, _t.AnyStr, bool, _t.AnyStr, _t.AnyStr]


class DeferredSync(_t.Generic[_t.AnyStr]):
    """Deferred file system `replace`s, `rename`s, `unlink`s, and `fsync`s.

    Basically, this exists to defer `os.replace`, `os.rename`, `os.unlink`, and
    `os.fsync` calls into the future, thus allowing the OS sync file data at its
    own pace in the meantime and batching directory updates together.

    Doing this can improve disk performance considerably.
    """

    tmp_file: set[_t.AnyStr]
    unlink_file: set[_t.AnyStr]
    fsync_file: set[_t.AnyStr]
    fsync_dir: set[_t.AnyStr]
    fsync_dir2: set[_t.AnyStr]
    rename_file: _c.deque[DeferredRename[_t.AnyStr]]

    # if all of the above succeed, also do these
    _after: _t.Optional["DeferredSync[_t.AnyStr]"]

    def __init__(self) -> None:
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

    @property
    def after(self) -> "DeferredSync[_t.AnyStr]":
        if self._after is None:
            self._after = DeferredSync()
        return self._after

    def copy(self) -> "DeferredSync[_t.AnyStr]":
        """Return a shallow copy of this object (elements describing operations are not
        copied, only the structure is).
        """
        res: DeferredSync[_t.AnyStr] = DeferredSync()
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
            unlink_many_paths(self.tmp_file)
        self.reset()

    def commit(
        self, strict: bool = True, simulate: list[list[str]] | None = None
    ) -> list[Exception]:
        """Perform all deferred operations and return a list of raised exceptions.

        Operations that fail will be left sitting in the corresponding fields.

        With `simulate` argument set, this function instead simulates the
        `commit` and writes the log of things it would do into that argument.
        """
        exceptions: list[Exception] = []

        if simulate is not None:
            simulate += [["unlink", fsdecode_maybe(f)] for f in sorted(self.unlink_file)]
            self.unlink_file = set()
        elif self.unlink_file:
            self.unlink_file = set(unlink_many_paths(sorted(self.unlink_file), exceptions))

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
                simulate += [["fsync", fsdecode_maybe(f)] for f in sorted(self.fsync_file)]
                self.fsync_file = set()
            elif self.fsync_file:
                fsync_file_left.update(fsync_many_paths(sorted(self.fsync_file), 0, exceptions))
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
                            simulate.append(["replace" if allow_overwrites else "rename", fsdecode_maybe(src_path), fsdecode_maybe(dst_path)])  # fmt: skip
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
                simulate += [["fsync_win", fsdecode_maybe(f)] for f in sorted(self.fsync_file)]
                self.fsync_file = set()
            elif self.fsync_file:
                fsync_file_left.update(fsync_many_paths(sorted(self.fsync_file), 0, exceptions))
                self.fsync_file = set()

            if simulate is not None:
                simulate += [["fsync_dir", fsdecode_maybe(f)] for f in sorted(self.fsync_dir)]
                self.fsync_dir = set()
            elif self.fsync_dir:
                if _POSIX:
                    fsync_dir_left.update(fsync_many_paths(sorted(self.fsync_dir), _os.O_DIRECTORY, exceptions))  # fmt: skip
                self.fsync_dir = set()

            if simulate is not None:
                simulate += [["fsync_dir", fsdecode_maybe(f)] for f in sorted(self.fsync_dir2)]
                self.fsync_dir2 = set()
            elif self.fsync_dir2:
                if _POSIX:
                    fsync_dir2_left.update(fsync_many_paths(sorted(self.fsync_dir2), _os.O_DIRECTORY, exceptions))  # fmt: skip
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
            excs = self._after.commit(strict, simulate)
            if len(excs) > 0:
                exceptions += excs
            else:
                self._after = None

        return exceptions

    def finish(self, strict: bool = True) -> None:
        """Like `commit` but raises collected exceptions as an exception group and calls
        `.clear` in that case.
        """
        try:
            excs = self.commit(strict)
            if len(excs) > 0:
                raise ExceptionGroup("failed to sync", excs)
        finally:
            self.clear()


def atomic_rename(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool,
    *,
    makedirs: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Atomically rename a file, performing all necesary `fsync`s."""

    src_dir, _ = dirname_dot(src_path)
    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)

    if dsync is not None:
        dsync.rename_file.append((src_path, dst_path, allow_overwrites, src_dir, dst_dir))
        return

    rename(src_path, dst_path, allow_overwrites, makedirs=False, dst_dir=dst_dir)

    if _POSIX:
        fsync_path(dst_dir, _os.O_DIRECTORY)
        if src_dir != dst_dir:
            fsync_path(src_dir, _os.O_DIRECTORY)
    else:
        # on Windows, some docs claim, this helps
        fsync_path(dst_path)


def make_file(
    make_dst: _t.Callable[[_t.AnyStr, bool], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    makedirs: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Create a file using a given `make_dst` function."""

    if not allow_overwrites and _os.path.lexists(dst_path):
        # fail early
        raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)
    make_dst(dst_path, dsync is None)

    if dsync is not None:
        dsync.fsync_file.add(dst_path)
        dsync.fsync_dir.add(dst_dir)
        return

    if _POSIX:
        fsync_path(dst_dir, _os.O_DIRECTORY)


def atomic_make_file(
    make_dst: _t.Callable[[_t.AnyStr, bool], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    makedirs: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
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
        tmp_path = dst_path + ".part"
    else:
        tmp_path = dst_path + b".part"

    dst_dir, nondot = dirname_dot(dst_path)

    if makedirs and nondot:
        _os.makedirs(dst_dir, exist_ok=True)
    make_dst(tmp_path, dsync is None)

    if dsync is not None:
        dsync.tmp_file.add(tmp_path)
        dsync.fsync_file.add(tmp_path)
        dsync.rename_file.append((tmp_path, dst_path, allow_overwrites, dst_dir, dst_dir))
        return

    try:
        rename(tmp_path, dst_path, allow_overwrites, dst_dir=dst_dir)
    except Exception:
        unlink_maybe(tmp_path)
        raise

    if _POSIX:
        fsync_path(dst_dir, _os.O_DIRECTORY)
        # NB: src_dir == dst_dir


def atomic_copy2(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
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
    atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)


def atomic_link(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Atomically hardlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_path: _t.AnyStr, _fsync_immediately: bool) -> None:
        _os.link(src_path, dst_path, follow_symlinks=follow_symlinks)

    # _os.link is atomic, so non-atomic make_file is ok
    if allow_overwrites:
        atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)
    else:
        make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)


def atomic_symlink(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Atomically symlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_path: _t.AnyStr, _fsync_immediately: bool) -> None:
        _os.symlink(src_path, dst_path)

    # _os.symlink is atomic, so non-atomic make_file is ok
    if allow_overwrites:
        atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)
    else:
        make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)


def atomic_link_or_copy2(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Atomically hardlink or copy `src_path` to `dst_path`."""

    try:
        atomic_link(
            src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, dsync=dsync
        )
    except OSError as exc:
        if exc.errno != _errno.EXDEV:
            raise
        atomic_copy2(
            src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, dsync=dsync
        )


def atomic_move(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = False,
    dsync: DeferredSync[_t.AnyStr] | None = None,
) -> None:
    """Atomically move `src_path` to `dst_path`.

    Note that `follow_symlinks` is set to `False` by default for this function
    so that the result would be similar to that of `mv(1)` util.
    """

    src_dir, _ = dirname_dot(src_path)

    atomic_link_or_copy2(
        src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, dsync=dsync
    )

    if dsync is not None:
        after = dsync.after
        after.unlink_file.add(src_path)
        after.fsync_dir.add(src_dir)
        return

    _os.unlink(src_path)

    if _POSIX:
        fsync_path(src_dir, _os.O_DIRECTORY)


def atomic_write(
    data: bytes,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    dsync: DeferredSync[_t.AnyStr] | None = None,
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

    atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)
