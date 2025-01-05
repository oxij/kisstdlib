#!/usr/bin/env python3
#
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

"""Produce a recursive deterministic textual description of given input files and/or directories.

I.e., given an input directory, this will produce an easily `diff`able output describing what the input consists of, e.g.:

```
. dir mode 700 mtime [2025-01-01 00:00:00]
afile.jpg reg mode 600 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
content dir mode 700 mtime [2025-01-01 00:03:00]
content/afile-hardlink.jpg => ../afile.jpg
content/afile-symlink.jpg lnk mode 777 mtime [2025-01-01 00:59:59] -> ../afile.jpg
content/zfile-hardlink.jpg reg mode 600 mtime [2025-01-01 00:02:00] size 256 sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
unix-socket ??? mode 600 mtime [2025-01-01 01:00:00] size 0
zfile.jpg => content/zfile-hardlink.jpg
```

(For hardlinks, the first file encountered in lexicographic walk order is taken as the "original", while all others are rendered as hardlinks.)

Most useful for making fixed-output tests for programs that produces filesystem trees."""

import hashlib as _hashlib
import os as _os
import os.path as _op
import stat as _stat
import sys as _sys
import typing as _t

import kisstdlib.argparse.better as _argparse
import kisstdlib.os as _kos
import kisstdlib.time as _ktime

from kisstdlib.io.stdio import *


def any_to_bytes(s: _t.Any) -> bytes:
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return _os.fsencode(s)
    try:
        return _os.fsencode(str(s))
    except Exception:
        pass
    return _os.fsencode(repr(s))


def printbin(*ls: _t.Any) -> None:
    res = b" ".join(map(any_to_bytes, ls)).replace(b"\\", b"\\\\").replace(b"\n", b"\\n")
    stdout.write_bytes_ln(res)


BUFFER_SIZE = 4 * 1024 * 1024


def hex_sha256_of(path: bytes) -> str:
    with open(path, "rb") as f:
        fhash = _hashlib.sha256()
        while True:
            data = f.read(BUFFER_SIZE)
            if len(data) == 0:
                break
            fhash.update(data)
        return fhash.hexdigest()


def main() -> None:
    parser = _argparse.BetterArgumentParser(
        prog="describe-dir",
        description=__doc__,
        add_help=True,
        formatter_class=_argparse.MarkdownBetterHelpFormatter,
    )
    parser.add_argument("--no-mtime", dest="mtime", action="store_false", help="ignore mtimes")
    parser.add_argument(
        "--precision", type=int, default=0, help="time precision (as a power of 10); default: `0`"
    )
    parser.add_argument("path", metavar="PATH", nargs="*", type=str, help="input directories")
    args = parser.parse_args(_sys.argv[1:])

    argvb = [_os.fsencode(a) for a in args.path]
    argvb.sort()

    seen: dict[tuple[int, int], tuple[bytes, int, bytes]] = {}
    for i, dirpath in enumerate(argvb):
        for fpath, _ in _kos.walk_orderly(dirpath):
            abs_path = _op.abspath(fpath)
            rpath = _op.relpath(fpath, dirpath)
            apath = _op.join(_os.fsencode(str(i)), rpath) if len(argvb) > 1 else rpath

            stat = _os.lstat(abs_path)
            ino = (stat.st_dev, stat.st_ino)
            try:
                habs_path, hi, hapath = seen[ino]
            except KeyError:
                seen[ino] = (abs_path, i, apath)
            else:
                if hi == i:
                    # within the same root `dirpath`
                    printbin(apath, "=>", _op.relpath(habs_path, abs_path))
                else:
                    printbin(apath, "==>", hapath)
                continue

            if args.mtime:
                mtime = (
                    "["
                    + _ktime.Timestamp.from_ns(stat.st_mtime_ns).format(
                        precision=args.precision, utc=True
                    )
                    + "]"
                )
            else:
                mtime = "no"
            size = stat.st_size
            mode = oct(_stat.S_IMODE(stat.st_mode))[2:]
            if _stat.S_ISDIR(stat.st_mode):
                printbin(apath, "dir", "mode", mode, "mtime", mtime)
            elif _stat.S_ISREG(stat.st_mode):
                sha256 = hex_sha256_of(abs_path)
                printbin(apath, "reg", "mode", mode, "mtime", mtime, "size", size, "sha256", sha256)
            elif _stat.S_ISLNK(stat.st_mode):
                symlink = _os.readlink(abs_path)
                arrow = "->"
                if symlink.startswith(b"/"):
                    # absolute symlink
                    symlink = _op.relpath(_op.realpath(abs_path), abs_path)
                    arrow = "/->"
                printbin(apath, "lnk", "mode", mode, "mtime", mtime, arrow, symlink)
            else:
                printbin(apath, "???", "mode", mode, "mtime", mtime, "size", size)


if __name__ == "__main__":
    main()
