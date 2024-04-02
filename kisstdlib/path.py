# Copyright (c) 2018-2024 Jan Malakhovski <oxij@oxij.org>
#
# This file is a part of kisstdlib project.
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

import logging as _logging
import os as _os
import stat as _stat
import typing as _t

def walk_orderly(path : _t.AnyStr,
                 *,
                 include_directories : bool = True,
                 follow_symlinks : bool = True,
                 ordering : bool | None = True,
                 handle_error : _t.Callable[..., None] | None = _logging.error) -> _t.Iterable[_t.AnyStr]:
    """Similar to os.walk, but produces an iterator over plain file paths, allows
       non-directories as input (which will just output a single element), and
       the output is guaranteed to be ordered if `ordering` is not `None`.
    """

    try:
        fstat = _os.stat(path, follow_symlinks = follow_symlinks)
    except OSError:
        if handle_error is not None:
            handle_error("failed to stat: %s", path)
            return
        raise

    if not _stat.S_ISDIR(fstat.st_mode):
        yield path
        return

    try:
        scandir_it = _os.scandir(path)
    except OSError:
        if handle_error is not None:
            handle_error("failed to scandir: %s", path)
            return
        raise

    elements : list[_t.AnyStr] = []

    with scandir_it:
        while True:
            try:
                entry : _t.Any = next(scandir_it)
            except StopIteration:
                break
            except OSError:
                if handle_error is not None:
                    handle_error("failed in scandir: %s", path)
                    return
                raise
            else:
                try:
                    is_dir = entry.is_dir(follow_symlinks = follow_symlinks)
                except OSError:
                    if handle_error is not None:
                        handle_error("failed to stat: %s", entry.path)
                        return
                    raise

                if is_dir:
                    if isinstance(entry.path, bytes):
                        elements.append(entry.path + b"/") # type: ignore
                    else:
                        elements.append(entry.path + "/")
                else:
                    elements.append(entry.path)

    if ordering is not None:
        elements.sort(reverse=not ordering)

    for path in elements:
        lchar : _t.AnyStr = path[-1:]
        if lchar == "/" or lchar == b"/":
            if include_directories:
                yield path
            yield from walk_orderly(path,
                                    include_directories=include_directories,
                                    follow_symlinks=follow_symlinks,
                                    ordering=ordering,
                                    handle_error=handle_error)
        else:
            yield path
