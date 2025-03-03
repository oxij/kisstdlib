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

"""`MinimalIO` wrappers for file-like objects."""

import enum as _enum
import logging as _logging
import os as _os
import sys as _sys
import textwrap as _textwrap
import typing as _t

from .base import *

_logger = _logging.getLogger("kisstdlib")

# this value is cached for performance reasons and so that changes to the
# environment won't make things unpredictable
_COLOR = _os.getenv("NO_COLOR", "") != "1"


class MinimalIOWrapper(MinimalIO):
    fobj: _t.Any
    fdno: FDNo | None

    def __init__(self, fobj: _t.Any) -> None:
        self.fobj = fobj
        # _socket.socket's fileno() will return -1 after
        # .close() and poll needs an actual value to unsubscribe
        # properly so we have to keep a copy here
        try:
            self.fdno = FDNo(fobj.fileno())
        except OSError:
            self.fdno = None
        _logger.debug("init %s", self)

    def __del__(self) -> None:
        _logger.debug("del %s", self)

    def __repr__(self) -> str:
        if self.fdno is not None:
            desc = "fdno=" + str(self.fdno)
        else:
            desc = "fobj=" + hex(id(self.fobj))
        return f"<{self.__class__.__name__} {hex(id(self))} {desc} closed={self.closed}>"

    def close(self) -> None:
        self.fobj.close()

    @property
    def closed(self) -> bool:
        return self.fobj.closed  # type: ignore

    def shutdown(self, what: ShutdownState) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} can't be shutdown")

    @property
    def shutdown_state(self) -> ShutdownState:
        if self.closed:
            return ShutdownState.SHUT_BOTH
        return ShutdownState.SHUT_NONE

    def __enter__(self) -> _t.Any:
        return self

    def __exit__(self, exc_type: _t.Any, exc_value: _t.Any, exc_tb: _t.Any) -> None:
        self.close()

    def fileno(self) -> int:
        return self.fdno if self.fdno is not None else -1

    def isatty(self) -> bool:
        return self.fobj.isatty()  # type: ignore


class TIOWrapper(MinimalIOWrapper):
    def __init__(
        self,
        fobj: _t.Any,
        *,
        encoding: str = _sys.getdefaultencoding(),
        eol: str | bytes = b"\n",
    ) -> None:
        super().__init__(fobj)
        self.encoding = encoding
        self.eol = eol


class TIOWrappedReader(TIOWrapper, MinimalIOReader):
    def read_some_bytes(self, size: int) -> bytes:
        return self.fobj.read(size)  # type: ignore


class ANSIColor(_enum.IntEnum):
    """ANSI TTY colors.
    Use `n + 8` for `n != -1` for "bright" versions.
    """

    RESET = -1
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7


class ANSIMode(_enum.IntEnum):
    """ANSI TTY text modes."""

    RESET = 0
    BOLD = 1
    BRIGHT = 1
    DIM = 2
    FAINT = 2
    ITALIC = 3
    UNDERLINE = 4
    BLINK = 5
    INVERT = 7
    HIDE = 8
    STRIKE = 9

    # These are rarely supported.
    BLINK2 = 6
    DEFAULT_FONT = 10
    # FONT(n) = DEFAULT_FONT + n
    GOTHIC = 20
    UNDERLINE2 = 21
    PROPORTIONAL = 26
    FRAME = 51
    ENCIRCLE = 52
    OVERLINE = 53
    SUPERSCRIPT = 73
    SUBSCRIPT = 74


class ANSIBorder:
    SINGLE = ("┌─┐", "└─┘", "│", "│")
    ROUNDED = ("╭─╮", "╰─╯", "│", "│")

    HEAVY = ("┏━┓", "┗━┛", "┃", "┃")
    HEAVY_SINGLE = ("┍━┑", "┕━┙", "│", "│")
    SINGLE_HEAVY = ("┎─┒", "┖─┚", "┃", "┃")

    DOUBLE = ("╔═╗", "╚═╝", "║", "║")
    DOUBLE_SINGLE = ("╒═╕", "╘═╛", "│", "│")
    SINGLE_DOUBLE = ("╓─╖", "╙─╜", "║", "║")

    OUTER_BLOCK = ("▛▀▜", "▙▄▟", "▌", "▐")
    OUTER_BLOCK_B = ("▞▀▚", "▚▄▞", "▌", "▐")
    INNER_BLOCK = ("▗▄▖", "▝▀▘", "▐", "▌")

    LIGHT_SHADE = ("░░░", "░░░", "░", "░")
    MEDIUM_SHADE = ("▒▒▒", "▒▒▒", "▒", "▒")
    DARK_SHADE = ("▓▓▓", "▓▓▓", "▓", "▓")

    DOTTED23 = ("┌╌┐", "└╌┘", "┆", "┆")
    DOTTED23_HEAVY = ("┏╍┓", "┗╍┛", "┇", "┇")

    DOTTED34 = ("┌┄┐", "└┄┘", "┊", "┊")
    DOTTED34_HEAVY = ("┏┅┓", "┗┅┛", "┋", "┋")

    DOTTED2 = ("┌╌┐", "└╌┘", "╎", "╎")
    DOTTED2_HEAVY = ("┏╍┓", "┗╍┛", "╏", "╏")

    DOTTED3 = ("┌┄┐", "└┄┘", "┆", "┆")
    DOTTED3_HEAVY = ("┏┅┓", "┗┅┛", "┇", "┇")

    DOTTED4 = ("┌┈┐", "└┈┘", "┊", "┊")
    DOTTED4_HEAVY = ("┏┉┓", "┗┉┛", "┋", "┋")


class TIOWrappedWriter(TIOWrapper, MinimalIOWriter):
    """A nice wrapper over writable IOBase, which supports both `str` and `bytes`
    writing, and can do ANSI TTY escape sequence generation.

    On the latter, see <https://en.wikipedia.org/wiki/ANSI_escape_code> and
    <https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797> for more
    info.
    """

    ansi: bool

    def __init__(
        self,
        fobj: _t.Any,
        *,
        ansi: bool | None = None,
        encoding: str = _sys.getdefaultencoding(),
        eol: str | bytes = b"\n",
    ) -> None:
        """Initialize this object.

        Explitily specifying `ansi` argument force-enables or force-disables
        ANSI TTY mode. By default, `ansi` gets enabled if underlying `fobj` is a
        TTY and environment variables do not set `NO_COLOR=1`.
        """
        super().__init__(fobj, encoding=encoding, eol=eol)
        self.ansi = ansi if ansi is not None else _COLOR and self.isatty()

    def write_some_bytes(self, data: BytesLike) -> int:
        return self.fobj.write(data)  # type: ignore

    def flush(self) -> None:
        self.fobj.flush()

    def write_bytes(
        self,
        data: BytesLike,
        color: int | None = None,
        background: int | None = None,
        modes: int | list[int] | None = None,
    ) -> None:
        coloring = False
        if self.ansi and (color is not None or background is not None or modes is not None):
            self.ansi_set(color, background, modes, True)
            coloring = True
        MinimalIOWriter.write_bytes(self, data)
        if coloring:
            self.ansi_reset()

    def write_str(self, data: str, **kwargs: _t.Any) -> None:
        self.write_bytes(data.encode(self.encoding), **kwargs)

    def write(self, data: str | BytesLike, **kwargs: _t.Any) -> None:
        if isinstance(data, str):
            self.write_str(data, **kwargs)
        else:
            self.write_bytes(data, **kwargs)

    def write_bytes_ln(self, data: BytesLike, **kwargs: _t.Any) -> None:
        self.write_bytes(data, **kwargs)
        self.write(self.eol)

    def write_str_ln(self, data: str, **kwargs: _t.Any) -> None:
        self.write_str(data, **kwargs)
        self.write(self.eol)

    def write_ln(self, data: str | BytesLike, **kwargs: _t.Any) -> None:
        self.write(data, **kwargs)
        self.write(self.eol)

    def write_strable(self, data: _t.Any) -> None:
        self.write_str(str(data))

    def write_strable_ln(self, data: _t.Any) -> None:
        self.write_strable(data)
        self.write(self.eol)

    ### Terminal size

    @property
    def terminal_size(self) -> _os.terminal_size:
        fdno = self.fdno
        if fdno is not None:
            try:
                return _os.get_terminal_size(fdno)
            except OSError:
                pass
        return _os.terminal_size((80, 24))

    ### ANSI escape codes

    def ansi_reset(self) -> None:
        """Reset all ANSI TTY attributes to their default values.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        return self.write_str("\x1b[0m")

    def ansi_set(
        self,
        color: int | None = None,
        background: int | None = None,
        modes: int | list[int] | None = None,
        reset: bool = False,
    ) -> None:
        """Set ANSI TTY attributes.

        Unset parameters cause corresponding attributes to be left unchanged.

        Setting `color` and/or `background` to `-1` resets them to their default
        values.

        Setting `modes` to be equal to `-1` or `0`, or setting `reset=True`
        resets all attributes to their default values.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return

        if modes is None:
            modes = []
        elif isinstance(modes, int):
            if modes in (-1, 0):
                modes = []
                reset = True
            else:
                modes = [modes]

        res = []
        main = []

        if reset:
            main.append("0")
        for m in modes:
            assert m not in (-1, 0)  # set `reset=True` instead
            main.append(str(m))

        if color is None:
            pass
        elif color != -1:
            if color < 8:
                main.append(str(30 + color))
            elif color < 16:
                main.append(str(82 + color))
            else:
                res.append(f"\x1b[38;5;{color}m")
        elif not reset:
            main.append("39")  # "reset to default"

        if background is None:
            pass
        elif background != -1:
            if background < 8:
                main.append(str(40 + background))
            elif background < 16:
                main.append(str(92 + background))
            else:
                res.append(f"\x1b[48;5;{background}m")
        elif not reset:
            main.append("49")  # "reset to default"

        if main:
            res.insert(0, "\x1b[" + ";".join(main) + "m")

        self.write_str("".join(res))

    def ansi_save_cursor(self) -> None:
        """Save cursor position and attributes.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        return self.write_str("\x1b7")

    def ansi_restore_cursor(self) -> None:
        """Restore cursor position and attributes.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        return self.write_str("\x1b8")

    def ansi_clear(self) -> None:
        """Erase the whole screen and all history.

        With `self.ansi == False`, writes an empty line.
        """
        if not self.ansi:
            self.write_str_ln("")
            return
        return self.write_str("\x1bc")

    def ansi_clear_screen(self, before: bool = True, after: bool = True) -> None:
        """Erase the current screen. With `before=False`, erase only after cursor. With
        `after=False`, erase only before cursor.

        With `self.ansi == False`, writes an empty line.
        """
        if not self.ansi:
            self.write_str_ln("")
            return
        if before and after:
            return self.write_str("\x1b[2J")
        if before:
            return self.write_str("\x1b[1J")
        if after:
            return self.write_str("\x1b[0J")

    def ansi_clear_saved(self) -> None:
        """Erase saved screen lines. This is rarely supported, use `ansi_clear` instead.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        return self.write_str("\x1b[3J")

    def ansi_clear_line(self, before: bool = True, after: bool = True) -> None:
        """Erase current line. With `before=False`, erase only after cursor. With
        `after=False`, erase only before cursor.

        With `self.ansi == False`, writes an empty line.
        """
        if not self.ansi:
            self.write_str_ln("")
            return
        if before and after:
            return self.write_str("\x1b[2K")
        if before:
            return self.write_str("\x1b[1K")
        if after:
            return self.write_str("\x1b[0K")

    def ansi_scroll(self, lines: int = 0) -> None:
        """Scroll the screen `lines` up, adding `lines` empty lines to the bottom of the
        screen.

        Negative values are allowed, causing the screen to scroll down, adding
        previously saved screen lines to the top of the screen.

        Note that TTY emulators only ever save old lines at the top edge of the
        screen, meaning that `ansi_scroll(-n)` followed by `ansi_scroll(n)` will
        produce `n` empty lines at the bottom, erasing whatever was there.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        if lines > 0:
            self.write_str(f"\x1b[{lines}S")
        elif lines < 0:
            self.write_str(f"\x1b[{-lines}T")

    def ansi_shift(self, lines: int = 0) -> None:
        """Move the cursor `lines` down, scrolling the buffer if necessary.

        Negative values are allowed, causing the cursor to move up, also
        scrolling if necessary.

        This is different from `ansi_scroll` in that this does not scroll the
        buffer if the cursor is not at the edge of the screen.

        This is also different from `ansi_move` and `ansi_move_to` in that this
        does scroll the buffer when necessary.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        if lines > 0:
            self.write_str("\n" * lines)
        elif lines < 0:
            self.write_str("\x1bM" * (-lines))

    def ansi_move(self, columns: int = 0, lines: int = 0, abs_columns: bool = False) -> None:
        """Move the cursor `lines` down and `columns` to the right.

        Negative values are allowed and move up and to the left, respectively.

        With `abs_columns=True`, `columns` gets interpreted as an absolute
        value, starting from the beginning of line.

        If you want both `columns` and `lines` to be absolute, use
        `ansi_move_to` instead.

        Unlike `ansi_scroll` and `ansi_shift`, this won't scroll, this command
        is intended for semigraphics.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        if lines > 0:
            if abs_columns:
                self.write_str(f"\x1b[{lines}E")
            else:
                self.write_str(f"\x1b[{lines}B")
        elif lines < 0:
            if abs_columns:
                self.write_str(f"\x1b[{-lines}F")
            else:
                self.write_str(f"\x1b[{-lines}A")
        if abs_columns:
            if columns != 0:
                return self.write_str(f"\x1b[{columns + 1}G")
        elif columns > 0:
            self.write_str(f"\x1b[{columns}C")
        elif columns < 0:
            self.write_str(f"\x1b[{-columns}D")

    def ansi_move_to(self, column: int, line: int) -> None:
        """Move the cursor to specified screen-absolute `column` and `line`.

        Unlike `ansi_scroll` and `ansi_shift`, this won't scroll, this command
        is intended for semigraphics.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        return self.write_str(f"\x1b[{line + 1};{column + 1}H")

    def ansi_hline(
        self,
        fill: str,
        x: int,
        y: int,
        ex: int,
        n: int = 1,
        margin: int = 0,
        shift: int = 0,
    ) -> None:
        """Draw a horizontal line. Draws `n` lines `(x, y + i) -> (ex, y + i)` filled
        with `fill` shifted `shift` characters each new line.

        Setting `margin` draws first and last `margin` characters of `fill`
        without repetition, repeating and shifting only the middle.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        w = ex - x
        l = len(fill) - 2 * margin
        middle = margin
        if l < 0:
            l = 1
            middle = len(fill) // 2
        for j in range(0, n):
            self.ansi_move_to(x, y + j)
            res = []
            for i in range(0, margin):
                res.append(fill[(i + shift * j) % margin])
            for i in range(0, w - 2 * margin):
                res.append(fill[middle + (i + shift * j) % l])
            for i in range(0, margin):
                res.append(fill[-margin + (i + shift * j) % margin])
            self.write_str("".join(res))

    def ansi_vline(
        self,
        fill: str,
        x: int,
        y: int,
        ey: int,
        n: int = 1,
        margin: int = 0,
        shift: int = 0,
    ) -> None:
        """Draw a vertical line. Draws `n` lines `(x + i, y) -> (x + i, ey)` filled
        with `fill` shifted `shift` characters each new line.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        h = ey - y
        l = len(fill) - 2 * margin
        middle = margin
        if l < 0:
            l = 1
            middle = len(fill) // 2
        for i in range(0, margin):
            self.ansi_move_to(x, y + i)
            res = []
            for j in range(0, n):
                res.append(fill[(i + shift * j) % margin])
            self.write_str("".join(res))
        for i in range(0, h - margin):
            self.ansi_move_to(x, y + i + margin)
            res = []
            for j in range(0, n):
                res.append(fill[middle + (i + shift * j) % l])
            self.write_str("".join(res))
        for i in range(0, margin):
            self.ansi_move_to(x, ey - i)
            res = []
            for j in range(0, n):
                res.append(fill[-margin + (i + shift * j) % margin])
            self.write_str("".join(res))

    def ansi_rect(self, fill: str, x: int, y: int, ex: int, ey: int, shift: int = 0) -> None:
        """Draw a rectangle `(x, y) -> (ex, ey)` filled with `fill` shifted `shift`
        characters each new line.

        Setting `margin` draws first and last `margin` characters of `fill`
        without repetition, repeating and shifting only the middle.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        self.ansi_hline(fill, x, y, ex, ey - y, 0, shift)

    def ansi_box(
        self,
        border: tuple[str, str, str, str],
        x: int,
        y: int,
        ex: int,
        ey: int,
        n: int = 1,
        m: int = 1,
    ) -> None:
        """Draw a box `(x, y) -> (ex, ey)` with given `border` of `x`-width of `n` and
        `y`-height of `m`.

        With `self.ansi == False`, do nothing.
        """
        if not self.ansi:
            return
        self.ansi_hline(border[0], x, y, ex, m, n, 1)
        self.ansi_hline(border[1], x, ey - m, ex, m, n, 1)
        self.ansi_vline(border[2], x, y + m, ey - m, n, 0)
        self.ansi_vline(border[3], ex - n, y + m, ey - m, n, 0)

    def ansi_text(
        self,
        lines: _t.Iterable[str],
        x: int,
        y: int,
        width: int,
        fill: str = " ",
        center: bool = True,
    ) -> None:
        """Draw given text lines starting from `(x, y)`, filling them to `width` with
        `fill` character.

        With `self.ansi == False`, simply print `lines` as-is.
        """
        if not self.ansi:
            for line in lines:
                self.write_str_ln(line)
            return

        for i, line in enumerate(lines):
            self.ansi_move_to(x, y + i)
            if center:
                l = width - len(line)
                ld2 = l // 2
                self.write_str(fill * ld2 + line + fill * (l - ld2))
            else:
                self.write_str(line + fill * (width - len(line)))

    def make_ansi_scroll_box(
        self,
        text: str,
        border: tuple[str, str, str, str],
        x: int,
        y: int,
        ex: int,
        ey: int,
        n: int = 1,
        m: int = 1,
        fill: str = " ",
        center: bool = True,
        *,
        color: int = -1,
        background: int = -1,
        modes: int | list[int] = -1,
        border_color: int = -1,
        border_background: int = -1,
        border_modes: int | list[int] = -1,
    ) -> tuple[int, _t.Callable[[int], None]]:
        """Generate a function drawing an `ansi_box(border, x, y, ex, ey, n, m)` with
        `ansi_text` wrapping the `text` inside of it, as needed.

        Returns a tuple of `frames, render` where the first element is the
        number of scroll animation frames and the second is a function drawing
        those animation frames.

        I.e., if wrapped text is longer than box height, then the returned
        `frames` will be `> 1` and calling `render(n)` for `0 <= n < frames`
        will render `n`-th frame of an animation of the text being scrolled in
        the box.

        With `self.ansi == False`, simply print `text` as-is and return `0,
        lambda n: None`.
        """
        if not self.ansi:
            self.write_str_ln(text)
            return 0, lambda n: None

        width = ex - x - 2 * n
        height = ey - y - 2 * m
        lines = _textwrap.wrap(text, width)
        overflow = len(lines) - height

        def scroll(i: int) -> None:
            self.ansi_set(border_color, border_background, border_modes)
            self.ansi_box(border, x, y, ex, ey, n, m)
            self.ansi_set(color, background, modes)
            self.ansi_text(lines[i : height + i], x + n, y + m, width, fill, center)

        return max(0, overflow) + 1, scroll
