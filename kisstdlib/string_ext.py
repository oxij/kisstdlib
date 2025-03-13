# Copyright (c) 2020-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Extensions for the standard `string` (and a bit of `stringprep`) modules.

Notably, this implements

- `escape` and `unescape`, which do `lex`-like string escapes, escaping
  requested characters with backslashes and unescaping them back;

- `url_quote` and `url_unquote`, which replace `quote`, `unquote`, `quote_plus`,
  and `unquote_plus` of `urllib.parse` with more general and more efficient
  versions;

- a general `StringLexer` class, which can do all of the above and more.
"""

import typing as _t

from string import *
from stringprep import in_table_c21_c22 as _in_table_c21_c22

from .failure import ParsingFailure as _ParsingFailure


def abbrev(
    x: _t.AnyStr,
    n: int,
    /,
    start_with_rep: bool = False,
    end_with_rep: bool = True,
    rep: _t.AnyStr | None = None,
) -> _t.AnyStr:
    """Abbreviate a `str`ing or `bytes` to length `n` with the abbreviated
    part replaced with optionsal `rep` (which defaults to "..." or b"...").

    `start_with_rep` and `end_with_rep` control where `rep` would go.
    """
    xlen = len(x)
    if xlen <= n:
        return x

    if rep is None:
        if isinstance(x, str):
            rep = "..."
        else:
            rep = b"..."
    replen = len(rep)

    if start_with_rep and end_with_rep:
        nrep = n - 2 * replen
        if nrep <= 0:
            return rep
        half = n // 2 - replen
        leftover = nrep - 2 * half
        halfx = xlen // 2
        return rep + x[halfx - half : halfx + half + leftover] + rep

    nrep = n - replen
    if nrep <= 0:
        return rep
    if start_with_rep:
        return rep + x[xlen - nrep :]
    if end_with_rep:
        return x[:nrep] + rep

    half = nrep // 2
    leftover = nrep - 2 * half
    return x[: half + leftover] + rep + x[xlen - half :]


def hex_quote(prefix: _t.AnyStr, data: bytes) -> _t.AnyStr:
    """Hex-quote given `data`, prepending each hex literal with a `prefix`."""
    res = []
    if isinstance(prefix, str):  # pylint: disable=no-else-return
        for b in data:
            res.append(prefix)
            res.append(f"{b:02X}")
        return "".join(res)
    else:
        for b in data:
            res.append(prefix)
            res.append(f"{b:02X}".encode("ascii"))
        return b"".join(res)


class StringLexer(_t.Generic[_t.AnyStr]):
    """A very simple string lexer which can escape, unescape, quote, and unquote
    `str`ings or `bytes`.

    This can generate and parse both `lex`-style and `url_quote`-style strings.
    """

    def __init__(
        self,
        escape_char: _t.AnyStr,
        hex_quote_char: _t.AnyStr | None,
        special: dict[str, str] | dict[int, int] | str,
        escape_special: bool,
        safe: _t.Callable[[str | int], bool],
        encoding: str = "utf-8",
    ) -> None:
        """`escape_char` is the main escape character, e.g., "\\" for `lex`, "%" for
        `url_quote`.

        `hex_quote_char` is the prefix used for hex-quoted literals, i.e., `"x"`
        for `lex` style and `None` for `url_quote` formatting.

        `special` is a mapping of characters that should be remapped in a
        special way. `escape_special` denotes if `special` characters should be
        escaped too, which is `True` for `lex`-style and `False` for
        `url_quote`.

        `safe` is a predicate which, for each character, decides if it's safe to
        output it without hex-escaping.

        The type of `escape_char` determines whether this object will be
        processing `str`ings or `bytes`.

        If `special` is a `str`ing, then each of its characters will be mapped
        to itself.

        Note that `url_quote` is a special case of escaping, with
        `escape_char="%"`, `hex_quote_char=None`, which will hex-quote all
        not-`safe` characters.

        `special` is usually empty in this case, but not always, like in case of
        `quote_plus`, in which case `escape_special=False` is required.
        """
        assert len(escape_char) == 1
        assert hex_quote_char is None or len(hex_quote_char) == 1

        self.escape_str: _t.AnyStr = escape_char
        self.escape_int = escape_int = (
            ord(escape_char) if isinstance(escape_char, str) else escape_char[0]
        )
        self.escape_special = escape_special
        self.hex_quote_string: _t.AnyStr = (
            ("" if isinstance(escape_char, str) else b"")
            if hex_quote_char is None
            else hex_quote_char
        )
        self.hex_quote_char: str | int | None = (
            None
            if hex_quote_char is None
            else (hex_quote_char if isinstance(hex_quote_char, str) else hex_quote_char[0])
        )
        self.safe = safe
        self.encoding = encoding

        fwd: dict[int, _t.AnyStr] = {}
        rev: dict[int, _t.AnyStr] = {}

        if hex_quote_char is not None:
            fwd[escape_int] = escape_char + escape_char
            rev[escape_int] = escape_char
        elif isinstance(escape_char, str):
            fwd[escape_int] = hex_quote(escape_char, escape_char.encode(encoding))
        else:
            fwd[escape_int] = hex_quote(escape_char, escape_char)

        a: str | int
        b: str | int
        if isinstance(escape_char, str):
            if isinstance(special, dict):
                for a, b in special.items():
                    aa = a if isinstance(a, int) else ord(a)
                    bb = b if isinstance(b, int) else ord(b)
                    fwd[aa] = escape_char + chr(bb) if escape_special else chr(bb)
                    rev[bb] = chr(aa)
            else:
                for c in special:
                    fwd[ord(c)] = escape_char + c
                    rev[ord(c)] = c
        elif isinstance(escape_char, bytes):
            if isinstance(special, dict):
                for a, b in special.items():
                    aa = a if isinstance(a, int) else ord(a)
                    bb = b if isinstance(b, int) else ord(b)
                    fwd[aa] = escape_char + bb.to_bytes() if escape_special else bb.to_bytes()
                    rev[bb] = aa.to_bytes()
            else:
                for c in special:
                    cc = c.encode("ascii")
                    fwd[ord(c)] = escape_char + cc if escape_special else cc
                    rev[ord(c)] = cc
        else:
            assert False
        self._fwd: dict[int, _t.AnyStr] = fwd
        self._rev: dict[int, _t.AnyStr] = rev

    def escape(self, data: _t.AnyStr, errors: str = "strict") -> _t.AnyStr:
        """Escape/quote given `data` using the configured settings.

        Turns all `special` characters into `{escape_char}{special(char)}`
        sequences, hex-quotes any not-`safe` characters, leaves everything else
        as-is.
        """

        safe = self.safe
        encoding = self.encoding
        prefix: _t.AnyStr = self.escape_str + self.hex_quote_string
        fwd = self._fwd

        res: list[_t.AnyStr] = []
        if isinstance(data, str):  # pylint: disable=no-else-return
            fwdc: dict[str, str] = {}
            for c in data:
                try:
                    res.append(fwdc[c])
                except KeyError:
                    pass
                else:
                    continue
                ci = ord(c)
                try:
                    m = fwd[ci]
                except KeyError:
                    pass
                else:
                    fwdc[c] = m
                    res.append(m)
                    continue
                if safe(c):
                    res.append(c)
                    continue
                fwdc[c] = fwd[ci] = ec = hex_quote(prefix, c.encode(encoding, errors=errors))
                res.append(ec)
            return "".join(res)
        else:
            fwdi: dict[int, bytes] = {}
            for c in data:
                try:
                    res.append(fwdi[c])
                except KeyError:
                    pass
                else:
                    continue
                try:
                    m = fwd[c]
                except KeyError:
                    pass
                else:
                    fwdi[c] = m
                    res.append(m)
                    continue
                if safe(c):
                    res.append(c.to_bytes())
                    continue
                fwdi[c] = fwd[c] = ec = hex_quote(prefix, c.to_bytes())
                res.append(ec)
            return b"".join(res)

    def unescape(self, data: _t.AnyStr, errors: str = "replace") -> _t.AnyStr:
        """Unescape/unquote given `data` using the configured settings."""

        encoding = self.encoding
        raw_special = not self.escape_special
        hex_quote_char = self.hex_quote_char
        rev = self._rev

        res = []
        i = 0
        datalen = len(data)
        if isinstance(data, str):  # pylint: disable=no-else-return
            escape_str = self.escape_str
            undecoded: list[int] = []

            def undecode() -> list[int]:
                if undecoded:
                    res.append(bytes(undecoded).decode(encoding, errors=errors))
                    return []
                return undecoded

            if raw_special:

                def normal(c: str) -> None:
                    try:
                        res.append(rev[ord(c)])
                    except KeyError:
                        res.append(c)

            else:

                def normal(c: str) -> None:
                    res.append(c)

            while i < datalen:
                c = data[i]
                i += 1
                if c != escape_str:
                    undecoded = undecode()
                    normal(c)
                    continue
                if i >= datalen:
                    raise _ParsingFailure("unexpected EOF while parsing %s", repr(data))
                if hex_quote_char is not None:
                    c1 = data[i]
                    i += 1
                    if c1 != hex_quote_char:
                        undecoded = undecode()
                        try:
                            res.append(rev[ord(c1)])
                        except KeyError:
                            normal(c1)
                        continue
                if i + 1 >= datalen:
                    raise _ParsingFailure("unexpected EOF while parsing %s", repr(data))
                hx = data[i : i + 2]
                i += 2
                undecoded.append(int(hx, 16))
            undecoded = undecode()
            return "".join(res)
        else:
            escape_int = self.escape_int

            if raw_special:

                def normali(ci: int) -> None:
                    try:
                        res.append(rev[ci])
                    except KeyError:
                        res.append(ci.to_bytes())

            else:

                def normali(ci: int) -> None:
                    res.append(ci.to_bytes())

            while i < datalen:
                ci = data[i]
                i += 1
                if ci != escape_int:
                    normali(ci)
                    continue
                if i >= datalen:
                    raise _ParsingFailure("unexpected EOF while parsing %s", repr(data))
                if hex_quote_char is not None:
                    ci1 = data[i]
                    i += 1
                    if ci1 != hex_quote_char:
                        try:
                            res.append(rev[ci1])
                        except KeyError:
                            normali(ci1)
                        continue
                if i + 1 >= datalen:
                    raise _ParsingFailure("unexpected EOF while parsing %s", repr(data))
                hx = data[i : i + 2]
                i += 2
                res.append(int(hx, 16).to_bytes())
                continue
            return b"".join(res)


### `lex`-like escaping

_lexers: dict[
    tuple[str | bytes, str | bytes | None, str | int, bool, int, str], StringLexer[_t.Any]
] = {}

# Escape sequences used by `printf` of C
ASCII_CONTROL_MAP = {
    "\x00": "0",
    "\a": "a",
    "\b": "b",
    "\t": "t",
    "\n": "n",
    "\v": "v",
    "\f": "f",
    "\r": "r",
    "\x1b": "e",
}

_safe_chars: dict[tuple[str, str], _t.Callable[[int | str], bool]] = {}


def safe_char(safe: str, unsafe: str) -> _t.Callable[[int | str], bool]:
    """Given known `safe` and `unsafe` characters, returns a predicate anwering a
    question of "Is this character safe to be printed raw?"

    The predicate returns `False` for all `unsafe` characters and `True` for all
    `safe` ones (that are not also `unsafe`). Otherwise, returns `False` for all
    ASCII and UNICODE control characters. Otherwise, returns `True`.
    """
    key = (safe, unsafe)
    try:
        return _safe_chars[key]
    except KeyError:
        pass

    safe_set = frozenset([ord(c) for c in safe])
    unsafe_set = frozenset([ord(c) for c in unsafe])

    def pred(char: str | int, /) -> bool:
        ichar = ord(char) if isinstance(char, str) else char
        if ichar in unsafe_set:
            return False
        if ichar in safe_set:
            return True
        if isinstance(char, str):
            return not _in_table_c21_c22(char)
        return not _in_table_c21_c22(chr(char))

    _safe_chars[key] = pred
    return pred


def escaper(
    escape_char: _t.AnyStr,
    special: dict[str, str] | dict[int, int] | str = ASCII_CONTROL_MAP,
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", ""),
    encoding: str = "utf-8",
) -> StringLexer[_t.AnyStr]:
    """Get an `StringLexer` instance usable for escaping, configured with given
    parameters.

    This function caches and reuses `StringLexer`s that use the same parameters
    since making several `StringLexer`s using the same parameters is wasteful.

    The type of `escape_char` determines whether the `StringLexer` will be
    processing `str`ings or `bytes`.
    """
    if isinstance(safe, tuple):
        safe = safe_char(*safe)
    sid: str | int = special if isinstance(special, str) else id(special)
    hex_quote_char: _t.AnyStr = "x" if isinstance(escape_char, str) else b"x"
    key = (escape_char, hex_quote_char, sid, True, id(safe), encoding)
    try:
        return _lexers[key]
    except KeyError:
        _lexers[key] = res = StringLexer(escape_char, hex_quote_char, special, True, safe, encoding)
    return res


def escape(
    x: _t.AnyStr,
    /,
    special: dict[str, str] | dict[int, int] | str = ASCII_CONTROL_MAP,
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", ""),
    encoding: str = "utf-8",
    errors: str = "strict",
) -> _t.AnyStr:
    """Escape all `special` and `safe` characters/bytes in `x` using `"\\"` as an
    escape character. See `StringLexer` for more info.
    """
    return escaper(b"\\" if isinstance(x, bytes) else "\\", special, safe, encoding).escape(
        x, errors
    )


def unescape(
    x: _t.AnyStr,
    /,
    special: dict[str, str] | dict[int, int] | str = ASCII_CONTROL_MAP,
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", ""),
    encoding: str = "utf-8",
    errors: str = "replace",
) -> _t.AnyStr:
    """Inverse of `escape` with the same parameters."""
    return escaper(b"\\" if isinstance(x, bytes) else "\\", special, safe, encoding).unescape(
        x, errors
    )


### Path escaping

path_escaper: StringLexer[str] = escaper("\\")
escape_path = path_escaper.escape
unescape_path = path_escaper.unescape


### URL-quoting

_safe_url_chars: dict[tuple[str, str], _t.Callable[[int | str], bool]] = {}

URL_ALLWAYS_SAFE = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~")


def safe_url_char(safe: str, unsafe: str) -> _t.Callable[[int | str], bool]:
    """Given known `safe` and `unsafe` characters, returns a predicate anwering a
    question of "Is this character safe to be used raw in URLs?"

    The predicate returns `False` for all `unsafe` characters and `True` for all
    `safe` ones (that are not also `unsafe`). Otherwise, returns `True` for all
    `URL_ALLWAYS_SAFE` characters. Otherwise, returns `False`.
    """
    key = (safe, unsafe)
    try:
        return _safe_url_chars[key]
    except KeyError:
        pass

    safe_set = frozenset([ord(c) for c in safe])
    unsafe_set = frozenset([ord(c) for c in unsafe])

    def pred(char: str | int, /) -> bool:
        ichar = ord(char) if isinstance(char, str) else char
        if ichar in unsafe_set:
            return False
        if ichar in safe_set or ichar in URL_ALLWAYS_SAFE:
            return True
        return False

    _safe_url_chars[key] = pred
    return pred


def quoter(
    escape_char: _t.AnyStr,
    special: dict[str, str] | dict[int, int] | str = "",
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", "/"),
    encoding: str = "utf-8",
) -> StringLexer[_t.AnyStr]:
    """Get an `StringLexer` instance usable for quouting, configured with given
    parameters.

    This function caches and reuses `StringLexer`s that use the same parameters
    since making several `StringLexer`s using the same parameters is wasteful.

    The type of `escape_char` determines whether the `StringLexer` will be
    processing `str`ings or `bytes`.
    """
    if isinstance(safe, tuple):
        safe = safe_url_char(*safe)
    sid: str | int = special if isinstance(special, str) else id(special)
    key = (escape_char, None, sid, False, id(safe), encoding)
    try:
        return _lexers[key]
    except KeyError:
        _lexers[key] = res = StringLexer(escape_char, None, special, False, safe, encoding)
    return res


URL_QUOTE_PLUS_MAP = {
    " ": "+",
}


def url_quote(
    x: _t.AnyStr,
    /,
    plus: bool = False,
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", "/"),
    encoding: str = "utf-8",
    errors: str = "strict",
) -> _t.AnyStr:
    """URL-quote all not-`safe` characters/bytes in `x` using `"%"` as an escape
    character. See `StringLexer` for more info.
    """
    return quoter(
        b"%" if isinstance(x, bytes) else "%",
        URL_QUOTE_PLUS_MAP if plus else "",
        safe,
        encoding,
    ).escape(x, errors)


def url_unquote(
    x: _t.AnyStr,
    /,
    plus: bool = False,
    safe: _t.Callable[[str | int], bool] | tuple[str, str] = ("", "/"),
    encoding: str = "utf-8",
    errors: str = "replace",
) -> _t.AnyStr:
    """Inverse of `url_quote` with the same parameters."""
    return quoter(
        b"%" if isinstance(x, bytes) else "%",
        URL_QUOTE_PLUS_MAP if plus else "",
        safe,
        encoding,
    ).unescape(x, errors)
