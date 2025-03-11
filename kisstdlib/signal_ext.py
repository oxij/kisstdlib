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

"""Extensions for the standard `signal` module.

This module implements some infrastructure that can temporarily disable some
signals and then allow you to process them synchronously at later, specific,
code points.

I.e., this module helps with writing programs that can be terminated gracefully,
not just `KeyboardInterrupt`ed at random places in the program, forcing you to
try and pick up program pieces afterwards.

In OS-kernel-terms, this module implements soft interrupts. In POSIX-terms, it
implements signal blocking and delayed pending signal processing.

This is similar to signal blocking via `sigblock` and later processing via
`sigpending`, but unlike those, this infrastructure still allows programs's user
to interrupt the program forcefully without going for `SIGKILL`, which allows
parts of the program higher on the call stack to gracefully handle bugs and/or
forced user interrupts in parts lower on the call stack.

The latter part is most useful when the program stores its state in an ACID data
structure, like `sqlite3` database, which allows for rollbacks.

See `../example/stop_gently.py` for some usage examples.
"""

import dataclasses as _dc
import collections as _c
import signal as _signal
import sys as _sys
import typing as _t

from time import sleep
from contextlib import contextmanager as _contextmanager
from gettext import gettext as _gettext

from .io.stdio import printf_err as _printf_err


@_dc.dataclass(order=True, slots=True)
class SignalInterrupt(BaseException):
    """Like `KeyboardInterrupt`, but for arbitrary signals."""

    # signal number
    signum: int
    # was this signal raised forcefully?
    forced: bool = _dc.field(default=True)

    def __post_init__(self) -> None:
        BaseException.__init__(self)


class GentleSignalInterrupt(SignalInterrupt):
    """Unforced `SignalInterrupt`."""

    def __init__(self, signum: int) -> None:
        super().__init__(signum, False)


delay_signal_message: dict[int, str] = {}
delay_signal_message_default = "Interrupting, gently."

interrupt_signal_message: dict[int, str] = {}
interrupt_signal_message_default = "Interrupting, forcefully!"


def setup_delay_signal_messages(
    prefix: str = "",
    delaying: dict[int, str] = {
        _signal.SIGINT: "Gently finishing up... Press ^C again to forcefully interrupt.",
    },
    delaying_default: str = "Gently finishing up... Send this signal again to forcefully interrupt.",
    interrupting: dict[int, str] = {},
    interrupting_default: str = "Forcefully interrupting!",
) -> None:
    """Setup pretty default messages to be be printed to `stderr` by
    `delay_signal_handler`.
    """
    global delay_signal_message, delay_signal_message_default
    delay_signal_message = {}
    for signum, message in delaying.items():
        delay_signal_message[signum] = prefix + _gettext(message)
    delay_signal_message_default = prefix + _gettext(delaying_default)

    global interrupt_signal_message, interrupt_signal_message_default
    interrupt_signal_message = {}
    for signum, message in interrupting.items():
        interrupt_signal_message[signum] = prefix + _gettext(message)
    interrupt_signal_message_default = prefix + _gettext(interrupting_default)


_delay_signals_state: tuple[bool, bool | str] = True, True
_delayed_signals: _c.OrderedDict[int, int] = _c.OrderedDict()


def delay_signal_handler(signum: int, _frame: _t.Any) -> None:
    """If programs' instruction pointer is outside of `no_signals` block, inside
    `yes_signals` block, or if this functions was previously fired for the same
    `signum`, print `interrupt_signal_message*` to `stderr` and raise
    `SignalInterrupt(signum, True)`. Otherwise, just remember that this `signum`
    was received and print `delay_signal_message*` to `stderr`.

    I.e., this signal handled delays raising of `SignalInterrupt(signum)` until
    the end of the current `no_signals` block or the start of the next
    `yes_signals` block.
    """

    num = _delayed_signals.get(signum, 0) + 1

    enabled, verbose = _delay_signals_state
    if isinstance(verbose, str):
        _printf_err("%s", verbose, start="\n", color=1)
        verbose = False

    if enabled or num > 1:
        if verbose:
            _printf_err(
                "%s",
                interrupt_signal_message.get(signum, interrupt_signal_message_default),
                start="\n",
                color=1,
            )
        try:
            del _delayed_signals[signum]
        except KeyError:
            pass
        raise SignalInterrupt(signum)

    _delayed_signals[signum] = num

    if verbose:
        _printf_err(
            "%s",
            delay_signal_message.get(signum, delay_signal_message_default),
            start="\n",
            color=1,
        )


def setup_delay_signals(signals: list[str] | frozenset[str] | set[str] | None = None) -> None:
    """Bind given signal names to `delay_signal_handler`. Unavailable signal names
    will be ignored.

    Leaving `signals` unset will bind `SIGTERM`, `SIGINT`, and `SIGBREAK` (if
    available).

    This functions exists purely as a syntax sugar for:

    ```
    for name in signals:
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), delay_signal_handler)
    ```

    to help with code portability.

    Note, however, that at the moment this function does not check that given
    signal name exists on at least one platform, so typos in signal names will
    be silently ignored.

    You need to call this function or call `signal.signal(signum,
    delay_signal_handler)` manually for this module to start working.
    """
    if signals is None:
        signals = frozenset(["SIGTERM", "SIGINT", "SIGBREAK"])
    elif isinstance(signals, list):
        signals = frozenset(signals)

    for name in signals:
        try:
            signum = getattr(_signal, name)
        except AttributeError:
            pass
        else:
            _signal.signal(signum, delay_signal_handler)


def pop_delayed_signal() -> int | None:
    """Pop the first `signum` delayed by `delay_signal_handler` and return it, or
    `None` if no signals bound to `delay_signal_handler` were recieved.

    This function can be called repeatedly, in which case it will return
    `signum`s of each delayed signal in order they were received.
    """
    try:
        signum, _num = _delayed_signals.popitem(False)
    except KeyError:
        return None
    return signum


def raise_first_delayed_signal() -> None:
    """Raise `GentleSignalInterrupt(signum)` with the first `signum` delayed by
    `delay_signal_handler`, do nothing if no signals bound to
    `delay_signal_handler` were recieved.

    This function can be called repeatedly, in which case it will raise
    `GentleSignalInterrupt`s for each delayed signal in order they were
    received.
    """
    try:
        signum, _num = _delayed_signals.popitem(False)
    except KeyError:
        pass
    else:
        raise GentleSignalInterrupt(signum)


def raise_delayed_signals() -> None:
    """Like `raise_first_delayed_signal` but if two or more `signum`s were delayed,
    raise all of them together as a `BaseExceptionGroup`.
    """
    excs = []
    while len(_delayed_signals) > 0:
        signum, _num = _delayed_signals.popitem(False)
        excs.append(GentleSignalInterrupt(signum))
    if len(excs) == 0:
        return
    if len(excs) == 1:
        raise excs[0]
    raise BaseExceptionGroup("many delayed signals", excs)


def forget_delayed_signals() -> None:
    """Forget about all currently delayed `signum`s."""
    global _delayed_signals
    _delayed_signals = _c.OrderedDict()


@_contextmanager
def no_signals(*, do_raise: bool = True, verbose: bool | str = True) -> _t.Iterator[None]:
    """Use as `with no_signals(): ...`.

    Start delaying signals bound to `delay_signal_handler` inside this code block.

    When `do_raise` is set (which is the default), if this is the topmost
    `no_signals` block, or if the parent block is `yes_signals`, then
    `raise_delayed_signals` will be called right after this block finishes.
    I.e., any delayed `GentleSignalInterrupt`s will be raised immediately at
    exit from this block.

    You can also `raise` them at certain program points by calling
    `raise_first_delayed_signal` or `raise_delayed_signals` manually from inside
    this block, or process them without raising anything via
    `pop_delayed_signal`.

    `verbose` controls whether `delay_signal_handler` should print any messages
    to `stderr` while inside this block.

    You can also set `verbose` to a `str`ing, which is similar to `True`, but
    will also override the messages `delay_signal_handler` will print while
    inside this code block. I.e. using a `str`ing has the same effect as saving
    current values of `delay_signal_message*` and `interrupt_signal_message*`,
    resetting them all to the `str` value of `verbose`, running this block with
    `verbose=True`, and then restoring the old values.
    """
    global _delay_signals_state
    old = _delay_signals_state
    _delay_signals_state = False, verbose
    try:
        yield None
    except Exception:
        # pretend `GentleSignalInterrupt` was raised first
        if do_raise and old[0]:
            raise_delayed_signals()
        raise
    finally:
        _delay_signals_state = old

    if do_raise and old[0]:
        raise_delayed_signals()


@_contextmanager
def yes_signals(*, do_raise: bool = True, verbose: bool | str = False) -> _t.Iterator[None]:
    """Use as `with yes_signals(): ...`.

    Do not delay signals bound to `delay_signal_handler` inside this code block.

    When `do_raise` is set, `raise_delayed_signals` will be called right before
    block entry.

    `verbose` semantics is the same as of `no_signals`.
    """
    if do_raise:
        raise_delayed_signals()

    global _delay_signals_state
    old = _delay_signals_state
    _delay_signals_state = True, verbose
    try:
        yield None
    finally:
        _delay_signals_state = old


def soft_sleep(seconds: int | float, *, verbose: bool | str = False) -> None:
    """Start `yes_signals(verbose=verbose)` block, if doing that does not not
    trigger `raise_delayed_signals`, run `time.sleep` with the given argument,
    if the latter gets interrupted with a `SignalInterrupt`, raise
    `GentleSignalInterrupt` with the same `signum` instead.

    Note that you should probably use `try ... except*`, not simply `try ...
    except` with this, unless you know what you are doing.
    """
    # NB: there's no need to handle `BaseExceptionGroup` here since this these
    # `except` clauses will only be executed right after `delay_signal_handler`
    # `raise`s.
    try:
        with yes_signals(verbose=verbose):
            sleep(seconds)
    except GentleSignalInterrupt:
        raise
    except SignalInterrupt as exc:
        raise GentleSignalInterrupt(exc.signum) from exc
