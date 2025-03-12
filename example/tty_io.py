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

"""An example showing off how to do TTY IO, color outputs, draw boxes, etc using
`kisstdlib`.
"""

import sys
from kisstdlib import *

if __name__ == "__main__":
    interactive = True
    for e in sys.argv[1:]:
        if e == "--no-interactive":
            interactive = False
        elif e == "--ansi":
            stdout.ansi = stderr.ansi = True
        elif e == "--no-ansi":
            stdout.ansi = stderr.ansi = False

    speed = 2 if interactive else 0.1

    print("# The basics")

    # Set everything up.

    counter, lhnd = setup_kisstdlib("the-program", level=DEBUG)

    # `setup_kisstdlib` calls `setup_stdio`, which sets things up in such a way
    # that all the standard things will work as usual and the standard `print`
    # will play well with `kisstdlib`'s things.

    print("print: Hello, World!")
    stdout.write_str_ln("write_str_ln: Hello, World!")
    printf("printf: Hello, %s!", "World")
    stdout.flush()

    print("print to stderr: Hello, World!", file=stderr)
    printf_err("printf_err: Hello, World!")

    printf("\n# Logging", flush=True)

    # `kisstdlib.logging_ext` module implements some nice `logging.Handler`s
    # that add a couple of useful features to the standard `logging` facilities.

    # The above `setup_kisstdlib` sets it all up, but without that line you can
    # also do it explicitly via
    #
    # counter, lhnd = setup_logging("the-program", level=DEBUG)
    #
    # These `setup_kisstdlib` or `setup_logging` calls should replace
    # `logging.basicConfig` calls in your code.

    # Firstly, `lhnd: ANSILogHandler` does nicely formatted, and optionally
    # colored (when on a TTY), output:

    # Show it off.
    debug("Debug message.")
    info("Multiline\ninfo message.")
    warning("Multiline\nwarning.")
    warning("Multiline\nwarning.")
    warning("Multiline\nwarning.")
    error("Multiline\nerror.")
    try:
        raise AssertionError()
    except Exception:
        exception("Oops!")

    print("Nice, isn't it?")
    print()

    # Secondly, `counter: LogCounter` counts all logging messages:

    printf(
        "So far: %d debugs, %d infos, %d warnings, %d errors",
        counter.debugs,
        counter.infos,
        counter.warnings,
        counter.errors,
    )

    # Thirdly, `ANSILogHandler` can do ephemeral and frequency-limited logging on a TTY:

    printf("\n# Ephemeral logging", color=ANSIColor.RED, flush=True)

    def step1(frac: int | float = 1) -> None:
        sleep(speed * frac)

    # enable ephemeral logging for messages below WARNING
    lhnd.ephemeral_below = WARNING
    # no more frequently than once per second
    lhnd.ephemeral_timeout = speed

    info(
        "This line will be ephemeral, i.e. it will be printed, but then replaced by the latter messages."
    )
    step1(0.5)
    info(
        "This line will not be printed at all, since it gets logged less than a {speed} seconds later."
    )
    step1(1)
    info("This one will replace the previous one.")
    step1(1)
    info("And then replace it with\nmultiline.")
    step1(1)
    info("And replace it all again.")
    step1(1)
    info("The next two won't be printed.")
    step1(0.5)
    info("Sneaky.")
    step1(0.1)
    info("But after the next `update`, this one will be.")
    step1(1)
    lhnd.update()
    step1(1)

    info("This will be shown, but the next ones won't be until `update`.")
    info("Sneaky.")
    info("Sneaky.")
    info("Sneaky.")
    step1(2)
    lhnd.update()
    step1(1)

    info("This will be shown and then removed on `flush`.")
    step1(1)
    lhnd.flush()

    # a test for implicit eols
    for k in range(0, 3):
        columns = stdout.terminal_size.columns * k
        for n in range(columns - 20, columns - 15):
            s = "!"
            for i in range(0, n):
                s += chr(48 + i % 10)
            info(s)
            lhnd.update()
            step1(1)

    lhnd.ephemeral_below = 0
    info("This will not be ephemeral anymore.")

    # `kisstdlib.io` primitives also support ANSI TTY escape codes
    printf("\n# ANSI TTY coloring", color=ANSIColor.RED, flush=True)

    if interactive:
        print("(Press 'Enter' to continue.)")
        stdin.read_some_bytes(1)

    # Text `color`, `background`, and/or `modes` can be set set (and then
    # immediately reset) directly from the usual writing primitives.
    printf("This is green with everything else reset to %s.", "default", color=ANSIColor.GREEN)
    stdout.write_str_ln("Similarly, but cyan.", color=ANSIColor.CYAN)
    # Note how the previous settings do not persist.
    stdout.write_str_ln("Blinking, with default color.", modes=ANSIMode.BLINK)
    stdout.write_str_ln(
        "This is bold yellow on red.",
        color=ANSIColor.YELLOW,
        background=ANSIColor.RED,
        modes=ANSIMode.BOLD,
    )

    # Coloring an indented block can be archived via
    stdout.write_str(" " * 8)
    stdout.write_str_ln("Indented.", background=ANSIColor.RED)
    # or via using `start` of `printf`
    printf("Similarly.", indent=" " * 8, prefix="note: ", background=ANSIColor.RED)
    # Note how `prefix` gets colored, while # `start` does not.

    # The `logging.Handler` set in `setup_logging` above uses this to color
    # things properly.

    # You can also use `.ansi_*` functions yourself
    stdout.ansi_reset()
    stdout.ansi_set(ANSIColor.BLUE)
    stdout.write_str_ln("This is now blue.")
    stdout.ansi_set(ANSIColor.RED, modes=ANSIMode.UNDERLINE)
    stdout.write_str_ln("This is underlined red.")
    stdout.ansi_set(modes=ANSIMode.BLINK)
    stdout.write_str_ln("Still underlined red, now also blinking.")
    stdout.ansi_set(ANSIColor.RED, modes=ANSIMode.UNDERLINE, reset=True)
    stdout.write_str_ln("Still underlined red, no longer blinking.")
    stdout.ansi_set(ANSIColor.WHITE)
    stdout.write_str_ln("Still underlined, now white.")

    # Which makes it easy to demonstrate why the above high-level function
    # perform resets before each newline symbol. After all, without them, this
    # happens:
    stdout.ansi_reset()
    stdout.ansi_set(ANSIColor.BLACK, ANSIColor.WHITE)
    stdout.write_str("On most terminals ")
    stdout.write_str_ln("background color becomes sticky")
    stdout.write_str_ln("after a newline.")
    stdout.write_str_ln("Sticky!")
    stdout.write_str("And then it will persist", color=ANSIColor.RED, background=ANSIColor.BLACK)
    print(" even after you reset it.")
    print("Until a newline after that.")
    print("Which is why `write_str*` functions reset everything immediately.")
    stdout.flush()

    printf(
        "\n# Box drawing, cursor movement, and overwrite damage", color=ANSIColor.RED, flush=True
    )
    # Just a little demo of what can be done with this

    if interactive:
        print("(Press 'Enter' to continue.)")
        stdin.read_some_bytes(1)

    def step2(message: str, frac: int | float = 1) -> None:
        stdout.ansi_move_to(0, 25)
        stdout.ansi_reset()
        stdout.write_str(message)
        stdout.ansi_clear_line(False)
        stdout.write_str_ln("")
        stdout.flush()
        if interactive:
            sleep(speed * frac)

    stdout.ansi_clear()
    stdout.ansi_set(ANSIColor.BLACK, ANSIColor.WHITE, reset=True)

    stdout.ansi_rect("░▒▓", 0, 0, 80, 25)
    step2("Drew a rect...")

    stdout.ansi_rect("░▒▓", 0, 0, 80, 25, 1)
    step2("Drew a shifted rect...")

    stdout.ansi_move_to(0, 0)
    stdout.ansi_set(background=ANSIColor.WHITE)
    for i in range(0, 25):
        stdout.ansi_move(4)
        stdout.ansi_set(ANSIColor.BLUE)
        stdout.write_str("a little wall of text, ")
        stdout.ansi_set(ANSIColor.YELLOW)
        stdout.write_str("nothing sinister, ")
        stdout.ansi_set(ANSIColor.GREEN)
        stdout.write_str("just a demonstration ")
        stdout.ansi_set(ANSIColor.MAGENTA)
        stdout.write_str_ln("nano desu")

    step2("Filled it with text...")

    n = 1
    i = 0
    for name, border in ANSIBorder.__dict__.items():
        if name.startswith("_"):
            continue
        stdout.ansi_set((n - 1) % 16, n % 16)
        stdout.ansi_box(border, i, i, 80 - i, 25 - i)
        step2(f"Drew a {name} box...", 0.1)
        n += 1
        i += 1
        if i >= 10:
            i = 0

    stdout.ansi_set(ANSIColor.BLACK, ANSIColor.GREEN)
    stdout.ansi_box(("  =  ", "  =  ", "│", "│"), 0, 0, 80, 25, 2, 1)

    step2("Drew an ASCII double-vertical-width box...")

    txt = "\n".join([str(i) + ": " + __doc__ for i in range(0, 30)])

    frames, scroll = stdout.make_ansi_scroll_box(txt, ANSIBorder.SINGLE, 3, 3, 77, 22, color=ANSIColor.YELLOW, border_background=ANSIColor.BLUE)  # fmt: skip
    frames2, scroll2 = stdout.make_ansi_scroll_box(txt, ANSIBorder.SINGLE, 10, 5, 70, 20, color=ANSIColor.BLUE, border_background=ANSIColor.GREEN)  # fmt: skip

    scroll(0)
    scroll2(0)
    step2("Drew boxes with text.")

    for i in range(1, frames):
        scroll(i)
        step2("Scroll the big box...", 0.1)

    for i in range(frames - 1, -1, -1):
        scroll(i)
        scroll2(0)
        step2("Scroll the big box in background...", 0.1)

    for i in chain(range(1, frames2)):
        scroll2(i)
        step2("Scroll the small box...", 0.1)

    stdout.ansi_set(ANSIColor.RED, reset=True)
    stdout.ansi_move_to(1, 1)
    stdout.write_str("0: move_to 1,1")

    stdout.ansi_move(39, 0, True)
    stdout.write_str("1: move_to 39")

    stdout.ansi_move_to(1, 1)
    stdout.ansi_move(10, 10)
    stdout.write_str("2: move 11,11 rel!")

    stdout.ansi_move_to(12, 12)
    stdout.write_str("3: move 12,12 abs")

    stdout.ansi_move_to(1, 1)
    stdout.ansi_move(23, 23)
    stdout.write_str("4: move 24,24 rel (will be overwritten!)")

    step2("Damaged it a bit....")

    stdout.ansi_set(ANSIColor.RED)
    stdout.ansi_move_to(24, 24)
    stdout.write_str("5: move 24,24 abs")

    step2("Damaged it a bit more...")

    stdout.ansi_set(ANSIColor.RED)
    stdout.ansi_move_to(17, 3)
    stdout.ansi_clear_line()
    stdout.write_str("6: clear_line")

    stdout.ansi_move_to(17, 4)
    stdout.ansi_clear_line(before=False)
    stdout.write_str("7: clear_line after")

    stdout.ansi_move_to(17, 5)
    stdout.ansi_clear_line(after=False)
    stdout.write_str("8: clear_line before")

    step2("And some more.")

    print()
    print("The end.")

    # Also, note how with disabled ANSI TTY features, with `--no-ansi` option
    # here, or when the output is redirected to a non-TTY destination, or with
    # `NO_COLOR=1` in the environment, the whole generated output is kept
    # human-readable, even though the program uses those ANSI calls. With ANSI
    # mode disabled all of them fallback to plain-text gracefully.
    #
    # Which also makes `ANSILogHandler`'s output quite nice when redirected to a
    # screen reader, for example.
