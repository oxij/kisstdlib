# Copyright (c) 2023-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Extensions for the standard `logging` module."""

import logging as _logging
import os.path as _op
import sys as _sys
import time as _time
import typing as _t

from gettext import ngettext as _ngettext

from logging import (  # pylint: disable=unused-import
    debug,
    info,
    warning,
    error,
    exception,
    critical,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
)

from .base import Number as _Number
from .io.stdio import (
    TIOWrappedWriter as _TIOWrappedWriter,
    ANSIColor as _ANSIColor,
    stderr as _stderr,
    printf as _printf,
)


class LogCounter(_logging.Handler):
    """A trivial `logging.Handler` that simply counts how many messages of each type
    were logged.

    Messages with levels below `INFO` are counted as `debugs`, in `[INFO,
    WARNING)` as `infos`, in `[WARNING, ERROR)` as `warnings`, over `ERROR` as
    `errors`.
    """

    errors: int
    warnings: int
    infos: int
    debugs: int

    def __init__(self, level: int = _logging.DEBUG) -> None:
        super().__init__(level)
        self.errors = 0
        self.warnings = 0
        self.infos = 0
        self.debugs = 0

    def handle(self, record: _logging.LogRecord) -> bool:
        if record.levelno >= _logging.ERROR:
            self.errors += 1
        elif record.levelno >= _logging.WARNING:
            self.warnings += 1
        elif record.levelno >= _logging.INFO:
            self.infos += 1
        else:
            self.debugs += 1
        return True


class ANSILogHandler(_logging.StreamHandler[_TIOWrappedWriter]):
    """A `logging.Handler` which

    - produces a prettier, more human-readable output than the default
      `logging.StreamHandler`;

    - prints "the previous message repeats <N> times" instead of repeating log
      lines;

    - supports ephemeral logging with rate-limiting,

      so that you could, e.g., set `level=DEBUG, ephemeral_below=WARNING,
      ephemeral_timeout=1` and let log messages with levels from `DEBUG` to
      `WARNING` also get printed to the TTY, but no more frequently than 1 per
      second (to reduce TTY IO), and with newer ephemeral messages replacing the
      older ones (to reduce TTY clutter);

    - updates the TTY incrementally, when possible.
    """

    def __init__(
        self,
        prog: str,
        formatter: _logging.Formatter,
        *,
        level: int = WARNING,
        ephemeral_below: int = 0,
        ephemeral_timeout: _Number = 0,
        debug_color: int = _ANSIColor.MAGENTA,
        info_color: int = _ANSIColor.BLUE,
        warning_color: int = _ANSIColor.YELLOW,
        error_color: int = _ANSIColor.RED,
        stream: _TIOWrappedWriter | None = None,
    ) -> None:
        if stream is None:
            stream = _stderr
        super().__init__(stream)
        self.prog = prog
        self.formatter = formatter
        self.level = level
        self.ephemeral_below = ephemeral_below
        self.ephemeral_timeout = ephemeral_timeout

        self.debug_color = debug_color
        self.info_color = info_color
        self.warning_color = warning_color
        self.error_color = error_color

        self.last: tuple[bool, int, str, str] | None = None
        self.repeats = 0
        self.last_printed = True
        self.repeats_printed = True
        self.last_lines = 0
        self.repeats_lines = 0
        self.updated_at: int | float = 0

    def reset(
        self,
        new: tuple[bool, int, str, str] | None = None,
        repeats: int = 0,
        completely: bool = True,
    ) -> None:
        """Reset internal state, using `new` as the last message.

        After a `reset` with default arguments:

        - If next `emit`s repeat the previous message, these repeats will will
          be counted separately.

        - If the last message was both ephemeral and printed, it will simply
          become pesistent.

        - Next `update` timeout for new ephemeral messages will be reset.
        """
        self.last = new
        self.repeats = repeats
        self.last_printed = False
        self.repeats_printed = False
        if completely:
            self.last_lines = 0
            self.repeats_lines = 0
            self.updated_at = 0

    def _rollback(self) -> None:
        """Remove the last printed message from view."""
        num = self.last_lines + self.repeats_lines
        if num > 0:
            stream = self.stream
            stream.ansi_shift(-num)
            stream.ansi_clear_screen(False)

    def update(self) -> None:
        """Print yet unprinted message, or update the previously printed one,
        incrementally. Similar to `flush`, but will display ephemeral state.

        Does nothing if there's nothing to do.
        """
        last = self.last
        if last is None:
            return

        stream = self.stream
        _ephemeral, color, prefix, message = last
        width = stream.terminal_size.columns

        if not self.last_printed:
            # rollback back everything
            self._rollback()

            # (re-)print
            self.last_lines = _printf(
                "%s",
                message,
                prefix=prefix,
                color=color,
                file=stream,
                width=width,
                flush=False,
            )
            self.repeats_lines = 0
            self.last_printed = True
            self.repeats_printed = False

        if not self.repeats_printed:
            # rollback only these
            if self.repeats_lines > 0:
                stream.ansi_shift(-self.repeats_lines)
                stream.ansi_clear_screen(False)

            # (re-)print
            repeats = self.repeats
            if repeats > 0:
                self.repeats_lines = _printf(
                    _ngettext(
                        "(the previous message repeats %d time)",
                        "(the previous message repeats %d times)",
                        repeats,
                    ),
                    repeats,
                    prefix=prefix,
                    color=color,
                    file=stream,
                    width=width,
                    flush=True,
                )
            else:
                self.repeats_lines = 0
                stream.flush()
            self.repeats_printed = True

    def flush(self) -> None:
        """Remove any ephemeral state from view and/or commit non-ephemeral state to
        view.

        I.e., if the last message was not ephemeral, `update` and `reset`.

        Otherwise, remove the last message from view, but don't forget about it,
        allowing it to be re-printed with `update`.

        If you want to commit the last ephemeral message to view, do `update`
        and `reset` manually.
        """
        last = self.last
        if last is not None and last[0]:
            # ephemeral
            self._rollback()
            self.stream.flush()
            self.reset(self.last, self.repeats)
        else:
            self.update()
            self.reset()

    def emit(self, record: _logging.LogRecord) -> None:
        """`logging.Handler` implementation."""
        levelno = record.levelno

        prefix_ = [self.prog, ":", record.levelname.lower(), ":"]
        if record.name != "root":
            prefix_.append(record.name)
            prefix_.append(":")
        prefix_.append(" ")
        prefix = "".join(prefix_)

        if levelno >= _logging.ERROR:
            color = self.error_color
        elif levelno >= _logging.WARNING:
            color = self.warning_color
        elif levelno >= _logging.INFO:
            color = self.info_color
        else:
            color = self.debug_color

        update = True
        ephemeral = levelno < self.ephemeral_below
        if ephemeral and self.ephemeral_timeout > 0:
            # limit update frequency
            now = _time.monotonic()
            update = now - self.updated_at >= self.ephemeral_timeout
            if update:
                self.updated_at = now

        message = self.format(record)
        data = ephemeral, color, prefix, message
        last = self.last

        if data == last:
            # the same message repeats
            self.repeats += 1
            self.repeats_printed = False
        else:
            # a new message
            self.reset(data, 0, not last[0] if last is not None else True)

        if update:
            self.update()


def die(pattern: str, /, *args: _t.Any, code: int = 1, **kwargs: _t.Any) -> _t.NoReturn:
    """Log a critical error and `sys.exit` with given `code`."""
    critical(pattern, *args, **kwargs)
    _sys.exit(code)


def setup_logging(
    prog: str | None = None,
    *,
    fmt: str | None = "%(message)s",
    datefmt: str | None = None,
    style: _t.Literal["%", "{", "$"] = "%",
    **kwargs: _t.Any,
) -> tuple[LogCounter, ANSILogHandler]:
    """Setup log message counting via `LogCounter` and pretty logging to `stderr`
    via `ANSILogHandler`, and then return both.
    """
    if prog is None:
        prog = _op.basename(_sys.argv[0])

    counter = LogCounter()
    lhnd = ANSILogHandler(prog, _logging.Formatter(fmt, datefmt, style), **kwargs)

    root = _logging.root
    root.addHandler(counter)
    root.addHandler(lhnd)
    root.setLevel(0)

    return counter, lhnd
