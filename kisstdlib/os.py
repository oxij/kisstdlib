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

import dataclasses as _dc
import enum as _enum
import errno as _errno
import io as _io
import os as _os
import os.path as _op
import shutil as _shutil
import stat as _stat
import sys as _sys
import typing as _t


_have_fcntl = False
try:
    import fcntl as _fcntl
except ImportError:
    pass
else:
    _have_fcntl = True


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
        else:
            yield epath, False


def as_include_directories(f: IncludeFilesFunc[_t.AnyStr]) -> IncludeDirectoriesFunc[_t.AnyStr]:
    """`convert walk_orderly(..., include_files, ...)` filter to `include_directories` filter"""

    def func(path: _t.AnyStr, _complete: bool, _elements: list[tuple[_t.AnyStr, bool]]) -> bool:
        return f(path)

    return func


def with_extension_in(exts: list[str | bytes] | set[str | bytes]) -> IncludeFilesFunc[_t.AnyStr]:
    """`walk_orderly(..., include_files, ...)` (or `include_directories`) filter that makes it only include files that have one of the given extensions"""

    def pred(path: _t.AnyStr) -> bool:
        _, ext = _op.splitext(path)
        return ext in exts

    return pred


def with_extension_not_in(
    exts: list[str | bytes] | set[str | bytes],
) -> IncludeFilesFunc[_t.AnyStr]:
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
    fd = _os.open(path, _os.O_RDONLY | flags)
    try:
        _os.fsync(fd)
    finally:
        _os.close(fd)


class DeferredSync:
    """Deferred file system fsyncs, replaces/renames and unlinks."""

    replaces: list[tuple[str | bytes, str | bytes]]
    files: set[str | bytes]
    dirs: set[str | bytes]
    unlinks: set[str | bytes]

    def __init__(self) -> None:
        self.replaces = []
        self.files = set()
        self.dirs = set()
        self.unlinks = set()

    def sync(self) -> None:
        if len(self.replaces) > 0:
            for path, _ in self.replaces:
                fsync_path(path)

            for ffrom, fto in self.replaces:
                _os.replace(ffrom, fto)
            self.replaces = []

        if len(self.files) > 0:
            for path in self.files:
                fsync_path(path)
            self.files = set()

        if len(self.dirs) > 0:
            for path in self.dirs:
                fsync_path(path, _os.O_DIRECTORY)
            self.dirs = set()

    def finish(self) -> None:
        self.sync()

        if len(self.unlinks) > 0:
            for path in self.unlinks:
                try:
                    _os.unlink(path)
                except Exception:
                    pass
            self.unlinks = set()


def make_file(
    make_dst: _t.Callable[[_t.AnyStr], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    dsync: DeferredSync | None = None,
) -> None:
    """Create a file using a given `make_dst` function."""

    if not allow_overwrites and _os.path.lexists(dst_path):
        # fail early
        raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    dirname = _os.path.dirname(dst_path)

    _os.makedirs(dirname, exist_ok=True)
    make_dst(dst_path)

    if dsync is None:
        fsync_path(dst_path)
        fsync_path(dirname, _os.O_DIRECTORY)
    else:
        dsync.files.add(dst_path)
        dsync.dirs.add(dirname)


def atomic_make_file(
    make_dst: _t.Callable[[_t.AnyStr], None],
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically, create a file using a given `make_dst` function. This
    will run `make_dst` on a `.part` path first, then `fsync` it, and
    then `os.replace` it to `dst_path` while also `flock`ing the
    target directory, if possible.
    """

    if not allow_overwrites and _os.path.lexists(dst_path):
        # fail early
        raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

    dirname = _os.path.dirname(dst_path)
    if isinstance(dst_path, str):
        dst_part = dst_path + ".part"
    else:
        dst_part = dst_path + b".part"

    _os.makedirs(dirname, exist_ok=True)
    make_dst(dst_part)

    if _have_fcntl:
        dirfd = _os.open(dirname, _os.O_RDONLY | _os.O_DIRECTORY)
        _fcntl.flock(dirfd, _fcntl.LOCK_EX)

    try:
        # this is now atomic on POSIX
        if not allow_overwrites and _os.path.lexists(dst_path):
            raise FileExistsError(_errno.EEXIST, _os.strerror(_errno.EEXIST), dst_path)

        if dsync is None:
            fsync_path(dst_part)
            _os.replace(dst_part, dst_path)
            if _have_fcntl:
                _os.fsync(dirfd)
        else:
            dsync.replaces.append((dst_part, dst_path))
            if _have_fcntl:
                dsync.dirs.add(dirname)
    finally:
        if _have_fcntl:
            _fcntl.flock(dirfd, _fcntl.LOCK_UN)
            _os.close(dirfd)


def atomic_copy2(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically copy `src_path` to `dst_path`."""

    def make_dst(dst_part: _t.AnyStr) -> None:
        if not follow_symlinks and _os.path.islink(src_path):
            _os.symlink(_os.readlink(src_path), dst_part)
        else:
            with open(src_path, "rb") as fsrc:
                try:
                    with open(dst_part, "xb") as fdst:
                        _shutil.copyfileobj(fsrc, fdst)
                except Exception:
                    try:
                        _os.unlink(dst_part)
                    except Exception:
                        pass
                    raise
        _shutil.copystat(src_path, dst_part, follow_symlinks=follow_symlinks)

    # always use the atomic version here, like rsync does,
    # since copying can be interrupted in the middle
    atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)


def atomic_link(
    src_path: _t.AnyStr,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    follow_symlinks: bool = True,
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically hardlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_part: _t.AnyStr) -> None:
        _os.link(src_path, dst_part, follow_symlinks=follow_symlinks)

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
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically symlink `src_path` to `dst_path`."""

    if follow_symlinks and _os.path.islink(src_path):
        src_path = _os.path.realpath(src_path)

    def make_dst(dst_part: _t.AnyStr) -> None:
        _os.symlink(src_path, dst_part)

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
    dsync: DeferredSync | None = None,
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
    follow_symlinks: bool = True,
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically move `src_path` to `dst_path`."""

    atomic_link_or_copy2(
        src_path, dst_path, allow_overwrites, follow_symlinks=follow_symlinks, dsync=dsync
    )
    if dsync is None:
        _os.unlink(src_path)
    else:
        dsync.unlinks.add(src_path)


def atomic_write(
    data: bytes,
    dst_path: _t.AnyStr,
    allow_overwrites: bool = False,
    *,
    dsync: DeferredSync | None = None,
) -> None:
    """Atomically write given `data` to `dst_path`."""

    def make_dst(dst_part: _t.AnyStr) -> None:
        with open(dst_part, "xb") as f:
            f.write(data)

    atomic_make_file(make_dst, dst_path, allow_overwrites, dsync=dsync)
