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

Produce a recursive deterministic textual description of given input files
and/or directories.

I.e., given an input directory, this will produce an easily `diff`able output
describing what the input consists of, e.g.:

```
. dir mode 700 mtime [2025-01-01 00:00:00]
afile.jpg reg mode 600 mtime [2025-01-01 00:01:00] size 4096 sha256
0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
content dir mode 700 mtime [2025-01-01 00:03:00]
content/afile-hardlink.jpg => ../afile.jpg
content/afile-symlink.jpg lnk mode 777 mtime [2025-01-01 00:59:59] ->
../afile.jpg
content/zfile-hardlink.jpg reg mode 600 mtime [2025-01-01 00:02:00] size 256
sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
unix-socket ??? mode 600 mtime [2025-01-01 01:00:00] size 0
zfile.jpg => content/zfile-hardlink.jpg
```

(For hardlinks, the first file encountered in lexicographic walk order is
taken as the "original", while all others are rendered as hardlinks.)

Most useful for making fixed-output tests for programs that produces
filesystem trees.

- positional arguments:
  - `PATH`
  : input directories

- options:
  - `-h, --help`
  : show this help message and exit
  - `--no-mode`
  : ignore file modes
  - `--no-mtime`
  : ignore mtimes
  - `--precision MTIME_PRECISION`
  : time precision (as a power of 10); default: `0`
