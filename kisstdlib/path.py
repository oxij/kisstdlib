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

"""Filesystem walking."""

import errno as _errno
import os as _os
import os.path as _op
import stat as _stat
import typing as _t

IncludeFilesFunc = _t.Callable[[_t.AnyStr], bool]
IncludeDirectoriesFunc = _t.Callable[[_t.AnyStr, bool, list[tuple[_t.AnyStr, bool]]], bool | None]


def walk_orderly(
    path: _t.AnyStr,
    *,
    include_files: bool | IncludeFilesFunc[_t.AnyStr] = True,
    include_directories: bool | IncludeDirectoriesFunc[_t.AnyStr] = True,
    follow_symlinks: bool = True,
    ordering: bool | None = True,
    handle_error: _t.Callable[..., None] | None = None,
    path_is_file_maybe: bool = True,
) -> _t.Iterable[tuple[_t.AnyStr, bool]]:
    """Similar to `os.walk`, but produces an iterator over paths, allows
    non-directories as input (which will just output a single element), and
    the output is guaranteed to be ordered if `ordering` is not `None`.
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

    if ordering is not None:
        elements.sort(reverse=not ordering)

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
                ordering=ordering,
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


def not_empty_directories(
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


def not_empty_leaf_directories(
    path: _t.AnyStr, complete: bool, elements: list[tuple[_t.AnyStr, bool]]
) -> bool:
    """`walk_orderly(..., include_directories, ...)` filter that makes it print only non-empty leaf directories, i.e. non-empty directories without sub-directories"""
    if not_empty_directories(path, complete, elements) and leaf_directories(
        path, complete, elements
    ):
        return True
    return False
