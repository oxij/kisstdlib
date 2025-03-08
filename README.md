# Table of Contents
<details><summary>(Click me to see it.)</summary>
<ul>
<li><a href="#what-is-kisstdlib" id="toc-what-is-kisstdlib">What is <code>kisstdlib</code>?</a></li>
<li><a href="#parts-and-pieces" id="toc-parts-and-pieces">Parts and pieces</a></li>
<li><a href="#usage" id="toc-usage">Usage</a>
<ul>
<li><a href="#describe-subtree" id="toc-describe-subtree">describe-subtree</a></li>
</ul></li>
</ul>
</details>

# What is `kisstdlib`?

`kisstdlib` is a [Python](https://www.python.org/) library that aims to enhance the Standard experience while Keeping It all very conceptually and algebraically Simple.

The design is very much informed by borrowing from [Haskell](https://www.haskell.org/) programming language, where appropriate.

# <span id="pieces"/>Parts and pieces

An Alpha Work In Progress software at the moment.

However, this project already provides some useful thin-wrapper programs over `kisstdlib` functions, which I use for writing tests in other programs, which are shown below.

# Usage

## describe-subtree

Produce a recursive deterministic self-descriptive `find .`+`stat`-like textual description of given files and/or directories.

I.e., given one or more inputs, this program produces an easily `diff`able output describing what the input consists of.
This is most useful for testing code that produces filesystem trees but it can also be used as a better alternative to `ls -lR` or `find . -exec ls -l {} \;`.

The most verbose output format this program can produce, for a single input file

```bash
describe-subtree --full path/to/README.md
```

looks as follows:

```
. reg mode 644 mtime [2025-01-01 00:01:00] size 4096 sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Note how both the path to and the name of the file do not appear in the output.
This is what you would want for doing things like

```bash
if ! diff -U 0 <(describe-subtree --full v1/path/to/README.md) <(describe-subtree --full v2/path/to/README.md) ; then
    echo "output changed between versions!" >&2
    exit 1
fi
```

which this program is designed for.

For a single input directory

```bash
describe-subtree --full path/to/dir
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
describe-subtree --full path/to/README.md path/to/README.md
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
