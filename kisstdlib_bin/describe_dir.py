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

import sys as _sys

import kisstdlib.argparse.better as _argparse
from kisstdlib.fs import describe_walks


def main() -> None:
    parser = _argparse.BetterArgumentParser(
        prog="describe-dir",
        description=__doc__,
        add_help=True,
        formatter_class=_argparse.MarkdownBetterHelpFormatter,
    )
    # fmt: off
    parser.add_argument("--no-mode", dest="show_mode", action="store_false", help="ignore file modes")
    parser.add_argument("--no-mtime", dest="show_mtime", action="store_false", help="ignore mtimes")
    parser.add_argument("--precision", dest="mtime_precision", type=int, default=0,
        help="time precision (as a power of 10); default: `0`",
    )
    parser.add_argument("paths", metavar="PATH", nargs="*", type=str, help="input directories")
    # fmt: on

    args = parser.parse_args(_sys.argv[1:])

    for desc in describe_walks(hash_len=64, **args.__dict__):
        print(*desc)


if __name__ == "__main__":
    main()
