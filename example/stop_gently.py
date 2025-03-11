#!/usr/bin/env python3
#
# Copyright (c) 2025 Jan Malakhovski <oxij@oxij.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""An example showing off `kisstdlib.signal_ext` module and related APIs.

Say, you want to write a piece of code which should not be interrupted by
`SIGINT` (`KeyboardInterrupt`), `SIGTERM`, and/or other signals at random points
in the program. Instead, you might want to delay processing of signals until
specific places in your program.

Yes, your program can still be `SIGKILL`ed or the whole machine can still crash,
so you should handle that case properly anyway. But, usually, a gentle program
termination request can help immensely if your program is then allowed to finish
currently running operation gracefully. E.g., if your program can save a
partially finished computation to disk, submit a partial request to a remote
server, commit an intermediate state it to a database, etc.

This example demonstrates `kisstdlib` can help you do this.
"""

import os
import signal
import sys

from kisstdlib import *

if __name__ == "__main__":
    # run with `--no-simulate` to play around with it yourself
    interactive = True
    simulate = True
    for e in sys.argv[1:]:
        if e == "--no-interactive":
            interactive = False
        if e == "--no-simulate":
            simulate = False

    timeout = (0.1 if interactive else 0.01) if simulate else 1
    num = 2 if simulate else 1

    # Prepare everything, this will setup signal handlers.
    setup_kisstdlib("program-name")

    printf_err("### In short")

    # The short version is that, after `setup_delay_signals` (called by the
    # `setup_kisstdlib` above), inside a `with no_signals()` block, `raise`ing
    # of interrupts gets delayed to the end of `no_signals` block, or until the
    # program enters a `with yes_signals()` block instead. The delayed signals
    # get raised as single `SignalInterrupt` `BaseException`, when a single
    # signal gets recieved:
    pid = os.getpid()
    try:
        try:
            with no_signals():
                os.kill(pid, signal.SIGINT)
            printf_err("won't ever execute")
        except* SignalInterrupt as excs:
            printf_err("Got: except* %s", repr(excs), color=ANSIColor.YELLOW)
    except BaseException as exc:
        printf_err("Top %s!", repr(exc), color=ANSIColor.YELLOW)

    # or as `BaseExceptionGroup`s of them, when the process recieves a bunch of
    # them:
    try:
        try:
            with no_signals():
                os.kill(pid, signal.SIGINT)
                os.kill(pid, signal.SIGTERM)
                with yes_signals():
                    printf_err("won't ever execute")
            printf_err("won't ever execute")
        except* SignalInterrupt as excs:
            printf_err("Got: except* %s", repr(excs), color=ANSIColor.YELLOW)
    except BaseException as exc:
        printf_err("Top: %s!", repr(exc), color=ANSIColor.YELLOW)

    forget_delayed_signals()

    # This allows you to do things like the following.
    #
    # Imagine "Work" performs changes in a `sqlite3` database, while "Commit"
    # and "Rollback" then commit or rollback them.
    #
    # Hitting ^C once inside the following `with no_signals()` block will not
    # raise anything. Instead, a delayed `GentleSignalInterrupt(signal.SIGINT)`
    # will be raised the moment the programs exits that block.
    #
    # However, if the instruction pointer is outside of that block or if you hit
    # ^C twice while it is inside, `SignalInterrupt(signal.SIGINT, forced=True)`
    # will be raised immediately.
    for n in range(0, num):
        printf_err("\n### Usage 1: %d", n)

        try:
            for i in range(0, 10):
                with no_signals():
                    # This part, ideally, should not be interrupted.
                    printf_err("Work on batch %d, atomically", i)
                    for j in range(0, 10):
                        printf_err("  ... element %d", j)
                        sleep(timeout)

                        if simulate:
                            # pretend signal were sent at these points
                            if n == 0 and i == 1 and j == 3:
                                os.kill(pid, signal.SIGINT)
                            elif n == 1 and i == 2 and j == 5:
                                os.kill(pid, signal.SIGINT)
                                os.kill(pid, signal.SIGINT)
                    printf_err("Commit batch %d.", i, color=ANSIColor.GREEN)
        except BaseException as exc:
            printf_err("Top: %s! Rollback!", repr(exc), color=ANSIColor.YELLOW)

        forget_delayed_signals()

    # Alternatively, you can call `raise_first_delayed_signal` at specific
    # program points under `no_signals` explicitly:

    for n in range(0, num):
        printf_err("\n### Usage 2: %d", n)

        i = 0
        try:
            with no_signals():
                for i in range(0, 10):
                    # Check if the user wants us to stop
                    try:
                        raise_first_delayed_signal()
                    except SignalInterrupt:
                        printf_err("Finished %d batches.", i, color=ANSIColor.GREEN)
                        break

                    # This part, ideally, should not be interrupted.
                    printf_err("Work on batch %d, atomically", i)
                    for j in range(0, 10):
                        printf_err("  ... element %d", j)
                        sleep(timeout)

                        if simulate:
                            # pretend signal were sent at these points
                            if n == 0 and i == 1 and j == 3:
                                os.kill(pid, signal.SIGINT)
                            elif n == 1 and i == 2 and j == 5:
                                os.kill(pid, signal.SIGINT)
                                os.kill(pid, signal.SIGINT)
                printf_err("Commit everything.", color=ANSIColor.GREEN)
        except BaseException as exc:
            printf_err("Top: %s! Rollback!", repr(exc), color=ANSIColor.YELLOW)

        forget_delayed_signals()

    # Alternatively, you can call catch `GentleSignalInterrupt` instead:

    for n in range(0, num):
        printf_err("\n### Usage 3: %d", n)

        i = 0
        try:
            with no_signals():
                for i in range(0, 10):
                    raise_first_delayed_signal()

                    # This part, ideally, should not be interrupted.
                    printf_err("Work on batch %d, atomically", i)
                    for j in range(0, 10):
                        printf_err("  ... element %d", j)
                        sleep(timeout)

                        if simulate:
                            # pretend signal were sent at these points
                            if n == 0 and i == 1 and j == 3:
                                os.kill(pid, signal.SIGINT)
                            elif n == 1 and i == 2 and j == 5:
                                os.kill(pid, signal.SIGINT)
                                os.kill(pid, signal.SIGINT)
                printf_err("Commit everything.", color=ANSIColor.GREEN)
        except GentleSignalInterrupt as exc:
            # raised by `raise_first_delayed_signal`
            printf_err("Commit %d finished batches.", i, color=ANSIColor.GREEN)
        except SignalInterrupt as exc:
            # raised by force-interrupting
            printf_err("Rollback %d unfinished batches.", i + 1, color=ANSIColor.YELLOW)
        except BaseException as exc:
            printf_err("Top: %s! Rollback!", repr(exc), color=ANSIColor.YELLOW)

        forget_delayed_signals()

    # If your program is a daemon that does some work and then sleeps, and that
    # sleep is the place where the program should be interrupted, then you can
    # also do this:

    for n in range(0, num):
        printf_err("\n### Usage: Sleeping: %d", n)

        try:
            with no_signals():
                for i in range(0, 10):
                    printf_err("Maybe sleeping...")
                    # `time.sleep` inside `yes_signals`, but raises
                    # `GentleSignalInterrupt(...)` regardless
                    soft_sleep(timeout * 5)

                    # This part, ideally, should not be interrupted.
                    try:
                        printf_err("Work on batch %d, atomically", i)
                        for j in range(0, 10):
                            printf_err("  ... element %d", j)
                            sleep(timeout)

                            if simulate:
                                # pretend signal were sent at these points
                                if n == 0 and i == 1 and j == 3:
                                    os.kill(pid, signal.SIGINT)
                                elif n == 1 and i == 2 and j == 5:
                                    os.kill(pid, signal.SIGINT)
                                    os.kill(pid, signal.SIGINT)
                        printf_err("Commit.", color=ANSIColor.GREEN)
                    except BaseException as exc:
                        printf_err("Got: %s! Rollback!", type(exc).__name__, color=ANSIColor.YELLOW)
                        raise
        except BaseException as exc:
            printf_err("Top: %s!", repr(exc), color=ANSIColor.YELLOW)
