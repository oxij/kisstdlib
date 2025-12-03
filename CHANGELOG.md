# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Also, at the bottom of this file there is a [TODO list](#todo) with planned future changes.

## [v0.0.12] - 2025-12-03

### Fixed

- `kisstdlib/fs.py`: `realdir`: Fixed `realdir(".")` to work as expected.

- `kisstdlib/itertools_ext.py`: `nth`: Fixed a bug.

### Added

- `kisstdlib/parsing.py`, `kisstdlib/io/adapter.py`: Implemented `BytesTransformer` and its IO-adapter friends.

- `test/test_basics.py`: Added better tests for `nth`.

- `test/test_parsing.py`, `test/test_io.py`: Added tests for `BytesTransformer` adapters.

### Changed

- `kisstdlib/io/adapter.py`: `UpdateFinalizeReader`: Reordered arguments a bit.

- `kisstdlib/sqlite3_ext.py`: Improved debug messages.

## [v0.0.11] - 2025-03-30

### Added

- `kisstdlib.fs`:  introduced `realdir`.

- `kisstdlib.io.adapter`: imported from `hoardy-adb/hoardy_adb/__main__.py`, improved a bit.

### Removed

- `kisstdlib.argparse_ext`: Removed `store_map` and `append_map`.

  These can be implemented with mainstream `argparse` by simply setting `type=func`.

### Changed

- Updated for `mypy v1.14.1`.

- `kisstdlib.fs`: `setup_fs`: put `pid` in front of `prog`.

## [v0.0.10] - 2025-03-17

### Added

- `kisstdlib.signal_ext`: Introduced `GentleSignalInterrupt` simplifying the API usage a bit.

- `kisstdlib.base`: Now re-exports `partial` and `partialmethod`.

- `kisstdlib.string_ext`: Introduced `path_escaper` and related singletons.

- `kisstdlib.logging_ext:ANSILogHandler`: Simplified the API by merging `rollback` functionality into `flush`.

- `kisstdlib.fs`:

  - Introduced `atomic_unlink`.

  - Introduced `setup_fs`, making temp file suffixes configurable.

    Also, `kisstdlib:setup_kisstdlib` now runs this function too.

### Fixed

- `kisstdlib.signal_ext`: From now on, `delay_signal_handler` will flush delayed signals when raising `SignalInterrupt`.

  This prevents `raise_first_delayed_signal` and `raise_delayed_signals` from raising them again, which was a bug.

- `kisstdlib.io.stdio`: Fixed `printf` to count implicit eols properly.

- `kisstdlib.fs`:

  - `iter_subtree`: Fixed error format.

  - `atomic_make_file`: Added `fsync` before `rename`, which should have been there.

- `kisstdlib:run_kisstdlib_main`: Now handles `BrokenPipeError`s when finishing up.

### Changed

- `devscript/test-cli-lib.sh`: Improved a bit.

- `kisstdlib.argparse_ext.py`:

  - Renamed and registered `OptionallyMarkdownHelpAction` as `help_omd`, similarly to how `argparse` does it.

  - Introduced `store_map` and `append_map` actions.

    Which do the same thing as `store` and `append`, but map values with a given function.

- `kisstdlib.fs`:

  - Replace `fsdecode_maybe` and `fsencode_maybe` with imports from `os`.

    Those functions have this functionality too.

  - `DeferredSync`:

    - Renamed `commit` -\> `sync`, `finish` -\> `flush`.

    - Action deference can now be optional, i.e. `DeferredSync` can now be used to only defer the `fsync` alone.

  - `atomic_*`:

    - Renamed `dsync` arguments -\> `sync`, now allowing them to be `bool`s.

      I.e., added no-`fsync`/async mode to all of those functions.

    - Added `prog` program name and its `pid` to temp file suffixes.

      Though, it's configurable via `setup_fs`.

- `kisstdlib:setup_kisstdlib`: Simplified the API a bit.

  Users should now call `setup_delay_signals` themselves if they need non-default `signals`.

## [v0.0.9] - 2025-03-10

### Changed (1)

- Renamed `kisstdlib.argparse.better` module -\> `kisstdlib.argparse_ext`.

- Renamed `kisstdlib.util` module -\> `kisstdlib.base`.

- Renamed `kisstdlib.logging` module -\> `kisstdlib.logging_ext`.

- `kisstdlib.base`:

  - Renamed `(In|Out|Extra)Type` -\> `(A|B|E)Type`.
  - Added more placeholder types, similarly named.
  - Re-imported `Decimal` here.
  - Moved `NumericType` here.
  - Renamed `NumericType` -\> `AnyNumber`.
  - Moved `BytesLike` and byte sizes here.
  - Renamed `str_Exception` -\> `get_traceback`, generalized it a bit.
  - Renamed `map_optionals` -\> `map_optional2list`.
  - Generalized `compose_*calls` into a single `compose_pipe`.
  - Switched to using positional-only parameters where appropriate.

- `kisstdlib.fs`:

  - Renamed `walk_orderly` -\> `iter_subtree`, improved its type.
  - Renamed `describe_walk` -\> `describe_forest`.
  - Improved and simplified the API of `describe_forest`.
  - Renamed `fsync_path` -\> `fsync_file`.
  - Renamed `fsync_many_paths` -\> `fsync_many_files`.
  - Renamed `unlink_many_paths` -\> `unlink_many`
  - Improved the behaviour of `unlink_many` and `fsync_many_files`.
  - Added `makedirs` arguments to all relevant functions.

- `kisstdlib.sorted:SortedIndex`:

 - Generalized it into an `AbstractSortedIndex` with the original `SortedIndex` as its implementation.
 - Renamed all internal API methods to `internal_*`.

- `kisstdlib.io.wrapper:TIOWrappedWriter`:

  - From now on, it allows `eol` to be `str`.
  - Improved it a bit.

- `kisstdlib.io.stdio`:

  - Edited it to play nicely with `sys.std(in|out|err)`.

- `kisstdlib.logging_ext`:

  - Renamed `CountHandler` -\> `LogCounter`.
  - In `LogCounter`:
      - Switched to inheriting from `Handler` instead, for thread safety.
      - From now on, it will count everything below `INFO` as `debugs`.

### Added (1)

- `kisstdlib.base`:

  - Introduced `Number` type with a bunch of operations for it.
  - Introduced some more constants.
  - Introduced `Missing` and `MISSING`.
  - Introduced `identity_`, `const`, `const_`.
  - Introduced `Maybe`, `maybe`, `map_maybe`, `map_maybe2list`.
  - Introduced `Either`, `either`, `map_left`, `map_right`.
  - Introduced `optional`, `optional2list`.
  - Introduced `fst`, `snd`.
  - Introduced `singleton`, `optlist`, `optslist`.
  - Introduced `first_def` and `first_ok`.
  - Introduced `flat_exceptions`.

- `kisstdlib.string_ext`:

  - Introduced the module.
  - Introduced `abbrev`.
  - Introduced `StringLexer`, which is a simple parser generator for simple string lexing syntaxes.
  - Introduced `escaper`, `escape`, `unescape`, which do `lex`-style string processing.
  - Introduced `quoter`, `url_quote`, `url_unquote`, which do what similar `urllib.parse` functions do, but faster, and with more options.
  - Introduced a bunch of related constants.

- `kisstdlib.fs`:

  - Introduced `same_file_data` and `same_symlink_data`.
  - Added `sep` and `sepb`.
  - Introduced `hash_file` and `sha256_file`.

- `kisstdlib.itertools_ext`:

  - Introduced the module with a bunch of commonly useful iteration-related stuff.
  - Introduced `diff_sorted`.

- `kisstdlib.time:Timestamp`

  - Implemented `__add__` and `__sub__`.

- `kisstdlib.sorted:AbstractSortedIndex`, `kisstdlib.sorted:SortedIndex`:

 - In `internal_from_to`:
     - Added support for reverse walking.
     - added support for inclusion and exclusion of bounds.

 - Introduced `internal_from_to_step` which adds `step`ping support to any `internal_from_to`.
 - Introduced `iter_range` which adds `predicate` support to `internal_from_to_step`.
 - Introduced a bunch of other convenience functions.

- `kisstdlib.sqlite3_ext`:

  - Introduced the module with a bunch of commonly useful `sqlite3`-related stuff.

- `kisstdlib.signal_ext`:

  - Introduced the module with a bunch of stuff useful for signal handling.

- `kisstdlib.getpass_ext`:

  - Introduced the module with a bunch `getpass`-related stuff.

- `kisstdlib.io.wrapper:TIOWrappedWriter`:

  - Implemented ANSI TTY Escape Sequences support, making a pretty nice API for it.
  - Added ANSI box and wrapped text drawing.
  - Introduced `terminal_size` API.

  Also, note that `TIOWrappedWriter`, by default, will automatically fallback to non-ANSI plain-text mode when the output is not a TTY of when `NO_COLOR=1` environment variable is set.

  Also, those newly introduced `ansi_*` API functions fallback to plain-text output when ANSI mode is disabled in a way that is designed to work pretty well with very little care taken in the code that uses them.

  I.e. you can just color things, draw boxes, scroll text around, and etc without care, and it will make the output readable in plain-text mode for you for free.

- `kisstdlib.io.stdio`:

  - Introduced `setup_stdio`.
  - Introduced `printf` and `printf_err` with ANSI TTY color support.

- `kisstdlib.logging_ext`:

  - Introduced `ANSILogHandler`, which use `printf` to render the log very prettily on an ANSI TTY.
  - Introduced `die`.
  - Introduced `setup_logging`.
  - Re-exported common logging things from `logging`.

### Removed

- `kisstdlib.fs`:

  - Removed `describe_path`, `describe_forest` is simple enough now.

- `kisstdlib.base`:

  - Replaced `first` with a more general version in `itertools_ext`.

### Fixed

- `kisstdlib.fs:iter_subtree`:

  - From now on it will sort directories as if they have `os.path.sep` after their name.

    Otherwise, `list(map(first, iter_subtree(..., include_directories=False)))` won't be sorted.

    This was broken since 730b1422ea6714349693163f6ae9965a80c00c5d.

    Also, added those separators to the outputs of `describe_forest`.

- `kisstdlib.failure:CatastrophicFailure`:

  - Implemented `__repr__`.

- `kisstdlib.sorted`:

  - Fixed a bug in `internal_from_nearest` found by tests.

- `kisstdlib.argparse_ext`:

  - In `BetterArgumentParser`, fixed it to properly format subparser headers to arbitrary `depth`.

### Changed (2)

- `kisstdlib.argparse_ext`:

  - Switched to using `kisstdlib.io.stdio` and `kisstdlib.logging_ext`.
  - Improved and simplified Markdown formatting code.
  - Simplified `BetterArgumentParser.format_help`, make it play better with default `argparse` things.
  - Made `MarkdownBetterHelpFormatter` produce proper Markdown headers independent of `width`.
  - Improved `BetterArgumentParser` defaults.

### Added (2)

- `kisstdlib.argparse_ext`:

  - Introduced `OptionallyMarkdownHelpAction`.
  - Implemented `--help` and `--markdown` directly in `BetterArgumentParser`.
  - Introduced `make_argparser_and_run`.

- `kisstdlib`:

  - Introduced `setup_kisstdlib` and `run_kisstdlib_main`.
  - Re-exported all the commonly useful things.

- Examples:

  - Added a bunch of new examples.

- Tests:

  - Added a bunch more `./test/*` unit tests.
  - Added `./test-example.sh` with fixed-output tests testing that examples produce the same results between versions.

### Changed (3)

- Renamed `describe-dir` script -\> `describe-forest`.

- `describe-forest`:

  - Improved `describe-forest--help`.
  - Added `describe-forest --version`.
  - Added more command-line options.
  - Improved output format.

- `test-cli-lib.sh`:

  - Added a bunch more functions there.
  - Generalized and simplified it all.
  - Improved logging.

- `*`:

  - Improved documentation and docstrings.

## [v0.0.8] - 2025-01-22

### Changed

- Split tests into `test/*` directory to remove them from resulting installations.
- Greatly improved syncing behaviour of `DeferredSync` and its `atomic_*` friends.
- `atomic_move` now has `follow_symlinks = False` by default, like `mv(1)` does.

### Added

- Imported and generalized a bunch of stuff from `hoardy-web`.
- Added a tests for `DeferredSync` and its `atomic_*` friends.

### Fixed

- `walk_orderly`: fixed `include_files` filtering.

## [v0.0.7] - 2025-01-17

### Fixed

- Fixed `fsync`ing of directories on Linux.
  The previous Windows support fix broke it.

## [v0.0.6] - 2025-01-17 [YANKED]

### Changed

- Improved the API a bit.
- Improved error handling.

### Fixed

- Improved Windows support.

## [v0.0.5] - 2025-01-13

### Added

- Imported a bunch of code from `hoardy-*` projects.

### Changed

- Improved newly imported code quite a bit.
- Formatted code using `black`.
- Fixed issues found by `pylint`.
- Improved error handling.
- Improved the API a bit.

### Fixed

- Improved Windows support.

## [v0.0.4] - 2024-11-09

### Changed

- `walk_orderly`:

    - Improved the API a bit.
    - It works on Windows now.
    - Improved performance.

## [v0.0.3] - 2024-04-02

### Changed

- Improved the API a bit.

## [v0.0.2] - 2024-02-22

### Added

- `walk_orderly`:

  - Added `order_by` argument.

## [v0.0.1] - 2023-10-26

### Added

- Initial release.

[v0.0.12]: https://github.com/oxij/kisstdlib/compare/v0.0.11...v0.0.12
[v0.0.11]: https://github.com/oxij/kisstdlib/compare/v0.0.10...v0.0.11
[v0.0.10]: https://github.com/oxij/kisstdlib/compare/v0.0.9...v0.0.10
[v0.0.9]: https://github.com/oxij/kisstdlib/compare/v0.0.8...v0.0.9
[v0.0.8]: https://github.com/oxij/kisstdlib/compare/v0.0.7...v0.0.8
[v0.0.7]: https://github.com/oxij/kisstdlib/compare/v0.0.6...v0.0.7
[v0.0.6]: https://github.com/oxij/kisstdlib/compare/v0.0.5...v0.0.6
[v0.0.5]: https://github.com/oxij/kisstdlib/compare/v0.0.4...v0.0.5
[v0.0.4]: https://github.com/oxij/kisstdlib/compare/v0.0.3...v0.0.4
[v0.0.3]: https://github.com/oxij/kisstdlib/compare/v0.0.2...v0.0.3
[v0.0.2]: https://github.com/oxij/kisstdlib/compare/v0.0.1...v0.0.2
[v0.0.1]: https://github.com/oxij/kisstdlib/releases/tag/v0.0.1

# TODO

- Publish the rest of this.
