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
from gettext import gettext

from kisstdlib.argparse_ext import *
from kisstdlib.fs import describe_walks


def main() -> None:
    _ = gettext

    # fmt: off
    parser = BetterArgumentParser(
        prog="describe-subtree",
        description=__doc__,
        formatter_class=MarkdownBetterHelpFormatter,
    )
    parser.add_argument("-h", "--help", action="store_true",
        help=_("show this help message and exit"),
    )
    parser.add_argument("--markdown", action="store_true",
        help=_("show help messages formatted in Markdown"),
    )

    parser.add_argument("--numbers", dest="numbers", action="store_true",
        help="emit number prefixes even with a single input `PATH`",
    )
    parser.add_argument("--literal", dest="literal", action="store_true",
        help="emit paths without escaping them even when they contain special symbols",
    )
    parser.add_argument("--modes", dest="modes", action="store_true", help="emit file modes")
    parser.add_argument("--mtimes", dest="mtimes", action="store_true", help="emit file mtimes")
    parser.add_argument(
        "--no-sizes", dest="sizes", action="store_false", help="do not emit file sizes"
    )
    parser.add_argument("--full", dest="full", action="store_true", help="an alias for `--mtimes --modes`")
    parser.add_argument("--relative", "--relative-hardlinks", dest="relative_hardlinks", action="store_true",
        help="emit relative paths when emitting `ref`s",
    )
    parser.add_argument("-L", "--dereference", "--follow-symlinks", dest="follow_symlinks", action="store_true",
        help="follow all symbolic links; replaces all `sym` elements of the output with description of symlink targets",
    )
    parser.add_argument("--time-precision", metavar="INT", dest="time_precision", type=int, default=0,
        help="time precision (as a negative power of 10); default: `0`, which means seconds, set to `9` for nanosecond precision",
    )
    parser.add_argument("--hash-length", metavar="INT", dest="hash_length", type=int, default=None,
        help="cut hashes by taking their prefixes of this many characters; default: print them whole",
    )
    parser.add_argument("paths", metavar="PATH", nargs="*", type=str, help="input directories")
    # fmt: on

    cargs = parser.parse_args(_sys.argv[1:])

    if cargs.full:
        cargs.modes = True
        cargs.mtimes = True

    if cargs.help:
        if cargs.markdown:
            print(parser.format_help(8192))
        else:
            print(parser.format_help())
        _sys.exit(0)

    del cargs.full
    del cargs.help
    del cargs.markdown

    for desc in describe_walks(**cargs.__dict__):
        print(*desc)


if __name__ == "__main__":
    main()
