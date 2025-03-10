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

"""Produce a plain-text recursive deterministic `find`/`ls`/`stat`-like description of given file and/or directory inputs.

The output format is designed to be descriptive and easily `diff`able while also producing minimally dissimilar outputs for similar inputs, even when those inputs contain lots of symlinks and/or hardlinks.
I.e., essentially, this is an alternative to `ls -lR` and/or `find . -exec ls -l {} \\;` which generates outputs that change very little when files with multiple symlinks and/or hardlinks change.

This is most useful for testing code that produces filesystem trees.

The most verbose output format this program can produce, for a single input file

```bash
describe-forest --full path/to/README.md
```

looks as follows:

```
. reg mode 644 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Note how both the path to and the name of the file do not appear in the output.
This is what you would want for doing things like

```bash
if ! diff -U 0 <(describe-forest --full v1/path/to/README.md) <(describe-forest --full v2/path/to/README.md) ; then
    echo "output changed between versions!" >&2
    exit 1
fi
```

which this program is designed for.

For a single input directory

```bash
describe-forest --full path/to/dir
```

the output looks similar to this:

```
. dir mode 700 mtime [2025-01-01 00:00:00]
afile.jpg reg mode 600 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
sub dir mode 700 mtime [2025-01-01 00:03:00]
sub/afile-hardlink.jpg ref ==> afile.jpg
sub/afile-symlink.jpg sym mode 777 mtime [2025-01-01 00:59:59] -> ../afile.jpg
sub/zfile-hardlink.jpg reg mode 600 mtime [2025-01-01 00:02:00] size 256 sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
unix-socket ??? mode 600 mtime [2025-01-01 01:00:00] size 0
zfile.jpg ref ==> sub/zfile-hardlink.jpg
```

Hardlinks, which are denoted by `ref`s above, are processed as follows:

- each new file encountered in lexicographic walk is rendered fully,
- files with repeated dev+inode numbers are rendered by emitting `ref ==> ` followed by the full path (or `ref => ` followed by the relative path, with `--relative-hardlink`) to the previously encountered element.

This way, renaming a file in the input changes at most two lines.

Symlinks are rendered by simply emitting the path they store, unless `--follow-symlinks` is given, in which case the targets they point to get rendered instead.

Multiple inputs get named by numbering them starting from "0".
Thus, for instance, running this program with the same input file given twice

```bash
describe-forest --full path/to/README.md path/to/README.md
```

produces something like:

```
0 reg mode 600 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
1 ref ==> 0
```

And giving the same directory with that file inside twice produces:

```
0 dir mode 700 mtime [2025-01-01 00:00:00]
0/afile.jpg reg mode 600 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
1 dir mode 700 mtime [2025-01-01 00:00:00]
1/afile.jpg ref ==> 0/afile.jpg
```

In its default output format, though, the program emits only `size`s and `sha256`s, when appropriate:

```
. dir
afile.jpg reg size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

which is what you would usually want for writing tests.
Though, if you are testing `rsync` or some such, feel free to use other options described below.

See `devscript` directory in `kisstdlib`'s repository for examples of some shell machinery that uses this to implement arbitrary-program fixed-output tests, which is a nice and simple way to test programs by testing their outputs against outputs of different versions of themselves.

Also, internally, this programs is actually a thin wrapper over `describe_forest` function of `kisstdlib.fs` Python module, which can be used with `pytest` or some such.
"""

import sys as _sys
from gettext import gettext

from kisstdlib.argparse_ext import *
from kisstdlib.fs import describe_forest


def main() -> None:
    _ = gettext

    # fmt: off
    parser = BetterArgumentParser(
        prog="describe-forest",
        description=__doc__,
        add_version = True,
        version = "1.0",
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
    del cargs.full

    for desc in describe_forest(**cargs.__dict__):
        print(*desc)


if __name__ == "__main__":
    main()
