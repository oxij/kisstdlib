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

"""Re-exports allowing to simply use `from kisstdlib import *` in most simple programs."""

import os.path as _op
import sys as _sys
import typing as _t

from gettext import gettext, ngettext

from .base import *
from .failure import *
from .string_ext import *
from .itertools_ext import *
from .io.stdio import *
from .logging_ext import *
from .signal_ext import *

from .fs import setup_fs as _setup_fs


def setup_kisstdlib(
    prog: str | None = None,
    *,
    do_setup_stdio: bool = True,
    do_setup_delay_signals: bool = True,
    do_setup_fs: bool = True,
    **kwargs: _t.Any,
) -> tuple[LogCounter, ANSILogHandler]:
    """Run all `setup_*` functions of all other `kisstdlib.*` modules and setup
    everything they configure to play well with each other.
    """
    if prog is None:
        prog = _op.basename(_sys.argv[0])
    if do_setup_stdio:
        setup_stdio()
    setup_delay_signal_messages(prog + ": ")
    if do_setup_delay_signals:
        setup_delay_signals()
    if do_setup_fs:
        _setup_fs(prog)
    res = setup_logging(prog, **kwargs)
    return res


def run_kisstdlib_main(
    setup_logging_result: tuple[LogCounter, ANSILogHandler],
    func: _t.Callable[AParamSpec, None],
    /,
    *args: AParamSpec.args,
    **kwargs: AParamSpec.kwargs,
) -> None:
    """Run given function with given arguments under `with no_signals()` block while
    properly handling all exceptions in `ExceptionGroup`s,
    `CatastrophicFailure`s, `Exception`s, etc it raises by turning them into
    `logging.error`s. Then, flush `stdio`, report warning and error counts, and
    call `sys.exit` with a non-zero exit code if the function itself
    `sys.exit`ed with a non-zero code, or if it `raise`d any exceptions, or
    logged any errors via `logging`.

    I.e., this functions abstracts away all the boilerplate code you need to
    write to build a proper UNIXy CLI program.

    `setup_logging_result` argument should be supplied from the result of
    `setup_logging` or `setup_kisstdlib`.
    """
    counter, logger = setup_logging_result
    exit_code: int = 0

    try:
        try:
            with no_signals():
                func(*args, **kwargs)
        except SystemExit as exc:
            code = exc.code
            if code is not None:
                if isinstance(code, str):
                    critical("%s", code)
                else:
                    exit_code = code
    except* (SignalInterrupt, KeyboardInterrupt):
        critical(gettext("Interrupted!"))
    except* CatastrophicFailure as excs:
        ce: CatastrophicFailure
        for ce in flat_exceptions(excs):
            critical("%s", ce.get_message(gettext))
    except* BaseException as excs:
        be: BaseException
        for be in flat_exceptions(excs):
            critical(gettext("Uncaught exception: %s"), str(be), exc_info=be)

    try:
        logger.flush()
    except BrokenPipeError:
        pass
    try:
        stdout.flush()
    except BrokenPipeError:
        pass
    try:
        stderr.flush()
    except BrokenPipeError:
        pass

    num_warnings = counter.warnings
    num_errors = counter.errors

    if num_warnings > 0:
        warning(
            ngettext("There was %d warning!", "There were %d warnings!", num_warnings),
            num_warnings,
        )
    if num_errors > 0:
        error(
            ngettext("There was %d error!", "There were %d errors!", num_errors),
            num_errors,
        )
        if exit_code == 0:
            exit_code = 1

    _sys.exit(exit_code)
