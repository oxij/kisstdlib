# Table of Contents
<details><summary>(Click me to see it.)</summary>
<ul>
<li><a href="#what-is-kisstdlib" id="toc-what-is-kisstdlib">What is <code>kisstdlib</code>?</a></li>
<li><a href="#parts-and-pieces" id="toc-parts-and-pieces">Parts and pieces</a></li>
<li><a href="#usage" id="toc-usage">Usage</a>
<ul>
<li><a href="#describe-forest" id="toc-describe-forest">describe-forest</a></li>
</ul></li>
<li><a href="#development-.test-example.sh---help---wine" id="toc-development-.test-example.sh---help---wine">Development: <code>./test-example.sh [--help] [--wine]</code></a></li>
</ul>
</details>

# What is `kisstdlib`?

`kisstdlib` is a set of modules for the [Python](https://www.python.org/) programming language, designed mostly for system programming with a touch of everything else, that aims to enhance the standard experience while keeping everything it does conceptually and algebraically simple.

This library borrows heavily from the [Haskell](https://www.haskell.org/) programming language, where appropriate.
(The Python's bundled modules do that too in many places, but `kisstdlib` borrows more.)

In short, `kisstdlib` mostly implements useful extensions for Python's bundled modules, keeping the APIs backward compatible and naming things in the same style.
The only exception to this is, yet unpublished, `io.loop` module, which implements Free-Monad-based IO.

At the moment, `kisstdlib` is an alpha work in progress software with an unstable API.

# <span id="pieces"/>Parts and pieces

`kisstdlib` consists of:

- a bunch of Python modules under [./kisstdlib](./kisstdlib);

  they are pretty well-documented there, though there's no generated `sphinx` docs yet;

- a bunch of human-readable [examples](./example) using those modules;

- some useful thin-wrapper programs over `kisstdlib` functions, useful for writing whole-program and/or fixed-output/extensional-equality tests;

  the documentation of which gets rendered into the following "Usage" section;

- as well as some testing-related infrastructure built on top of this, in [./devscript](./devscript).

# Usage

## describe-forest

Produce a plain-text recursive deterministic `find`/`ls`/`stat`-like description of given file and/or directory inputs.

The output format is designed to be descriptive and easily `diff`able while also producing minimally dissimilar outputs for similar inputs, even when those inputs contain lots of symlinks and/or hardlinks.
I.e., essentially, this is an alternative to `ls -lR` and/or `find . -exec ls -l {} \;` which generates outputs that change very little when files with multiple symlinks and/or hardlinks change.

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

- positional arguments:
  - `PATH`
  : input directories

- options:
  - `--version`
  : show program's version number and exit
  - `-h, --help`
  : show this help message and exit
  - `--markdown`
  : show `--help` formatted in Markdown
  - `--numbers`
  : emit number prefixes even with a single input `PATH`
  - `--literal`
  : emit paths without escaping them even when they contain special symbols
  - `--modes`
  : emit file modes
  - `--mtimes`
  : emit file mtimes
  - `--no-sizes`
  : do not emit file sizes
  - `--full`
  : an alias for `--mtimes --modes`
  - `--relative, --relative-hardlinks`
  : emit relative paths when emitting `ref`s
  - `-L, --dereference, --follow-symlinks`
  : follow all symbolic links; replaces all `sym` elements of the output with description of symlink targets
  - `--time-precision INT`
  : time precision (as a negative power of 10); default: `0`, which means seconds, set to `9` for nanosecond precision
  - `--hash-length INT`
  : cut hashes by taking their prefixes of this many characters; default: print them whole

# Development: `./test-example.sh [--help] [--wine]`

Check that all `kisstdlib/example/*.py` are fixed-output.
