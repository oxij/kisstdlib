# Copyright (c) 2024-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Parsing of `str`ings and `bytes`."""

import re as _re
import typing as _t

from itertools import islice as _islice

from .failure import ParsingFailure


# A state transition function, see `BytesTransformer` below.
ByteTransitions: _t.TypeAlias = _t.Callable[[int, int], tuple[int, bytes] | None]


def LF2CRLF(_s: int, c: int) -> tuple[int, bytes] | None:
    "Map all LF to CR LF."
    if c == 10:
        # LF
        return 0, b"\r\n"
    return None


def CRLF2LF(s: int, c: int) -> tuple[int, bytes] | None:
    "Map all CR LF sequences to LF."
    if s == 0:
        if c == 13:
            # CR
            return 1, b""
        return None

    if c == 10:
        # CR LF
        return 0, b"\n"
    if c == 13:
        # CR CR
        return 1, b"\r"
    if c == -1:
        # CR EOF
        return 0, b"\r"

    # CR other
    return 0, bytes([13, c])


class BytesTransformer:
    """Transform some `bytes` using a given `ByteTransitions` somewhat similarly to
    `bytearray.transform`, but with more expressive power.

    This class implements the same `update` + `finalize` API as most cryptographic libraries.

    `ByteTransitions` is a function from old state number (the first `int`) and a char (the second
    `int`) to new state number and generated `bytes` output. The `None` result means "keep the same
    state, output the input byte". The initial state is `0`, EOF is represented by a `-1` byte.

    See, e.g. `UNIX2DOS*` and `DOS2UNIX*` in `kisstdlib.io.adapter` for example usages.
    """

    def __init__(self, transitions: ByteTransitions) -> None:
        self._transitions = transitions
        self._stateno = 0

    def update(self, data: bytes) -> bytes:
        i = 0
        dlen = len(data)

        stateno = self._stateno
        tf = self._transitions

        c: int
        t: tuple[int, bytes] | None

        # skip noops
        while i < dlen:
            c = data[i]
            t = tf(stateno, c)
            if t is None:
                i += 1
                continue
            # nstateno, nout = t
            # if nstateno == stateno and len(nout) == 0 and nout[0] == c:
            #     i += 1
            #     continue
            break
        else:
            return data

        if i == dlen:
            # there were only noops
            return data

        # copy the noop part
        res = bytearray(_islice(data, i))

        # update on the current char
        stateno, nout = t
        res.extend(nout)
        i += 1

        # update on the rest
        while i < dlen:
            c = data[i]
            t = tf(stateno, c)
            if t is None:
                res.append(c)
            else:
                stateno, nout = t
                res.extend(nout)
            i += 1

        self._stateno = stateno
        return bytes(res)

    def finalize(self) -> bytes:
        t = self._transitions(self._stateno, -1)
        if t is None:
            self._stateno, nout = 0, b""
        else:
            self._stateno, nout = t

        # ensure it gets reset properly
        assert self._stateno == 0

        return nout


word_re = _re.compile(r"(\S+)")
natural_re = _re.compile(r"([0-9]+)")
integer_re = _re.compile(r"(-?[0-9]+)")
decimal_re = _re.compile(r"(-?[0-9]+(.[0-9]+)?)")
whitespace_re = _re.compile(r"\s+")
opt_whitespace_re = _re.compile(r"(\s*)")


ParsedValueType = _t.TypeVar("ParsedValueType")
ParserParamSpec = _t.ParamSpec("ParserParamSpec")


class Parser:
    """Parsec-like parser combinator with regexes."""

    def __init__(self, data: str) -> None:
        self.buffer = data
        self.pos = 0

    def unread(self, data: str) -> None:
        self.buffer = self.buffer[: self.pos] + data + self.buffer[self.pos :]

    @property
    def leftovers(self) -> str:
        return self.buffer[self.pos :]

    def at_eof(self) -> bool:
        return self.pos >= len(self.buffer)

    def eof(self) -> None:
        if self.at_eof():
            return
        raise ParsingFailure(
            "while parsing %s: expected EOF, got %s", repr(self.buffer), repr(self.leftovers)
        )

    def chomp(
        self,
        parser: _t.Callable[_t.Concatenate[str, ParserParamSpec], tuple[ParsedValueType, str]],
        *args: ParserParamSpec.args,
        **kwargs: ParserParamSpec.kwargs,
    ) -> ParsedValueType:
        if self.pos == 0:
            res, leftovers = parser(self.buffer, *args, **kwargs)
        else:
            res, leftovers = parser(self.buffer[self.pos :], *args, **kwargs)
            self.pos = 0
        self.buffer = leftovers
        return res

    def have_at_least(self, n: int) -> bool:
        return self.pos + n <= len(self.buffer)

    def ensure_have(self, n: int) -> None:
        if self.have_at_least(n):
            return
        raise ParsingFailure(
            "while parsing %s: expected %d more characters, got EOF", repr(self.buffer), n
        )

    def skip(self, n: int) -> None:
        self.ensure_have(n)
        self.pos += n

    def take(self, n: int) -> str:
        self.ensure_have(n)
        old_pos = self.pos
        new_pos = old_pos + n
        self.pos = new_pos
        return self.buffer[old_pos:new_pos]

    def at_string(self, s: str) -> bool:
        return self.buffer.startswith(s, self.pos)

    def opt_string(self, s: str) -> bool:
        if self.at_string(s):
            self.pos += len(s)
            return True
        return False

    def string(self, s: str) -> None:
        if self.opt_string(s):
            return
        raise ParsingFailure(
            "while parsing %s: expected %s, got %s",
            repr(self.buffer),
            repr(s),
            repr(self.leftovers),
        )

    def at_string_in(self, ss: list[str]) -> bool:
        for s in ss:
            if self.buffer.startswith(s, self.pos):
                return True
        return False

    def opt_string_in(self, ss: list[str]) -> bool:
        for s in ss:
            if self.at_string(s):
                self.pos += len(s)
                return True
        return False

    def string_in(self, ss: list[str]) -> None:
        if self.opt_string_in(ss):
            return
        raise ParsingFailure(
            "while parsing %s: expected one of %s, got %s",
            repr(self.buffer),
            repr(ss),
            repr(self.leftovers),
        )

    def take_until_p(self, p: _t.Callable[[_t.Any], bool]) -> str:
        start = self.pos
        blen = len(self.buffer)
        while self.pos < blen:
            if p(self):
                break
            self.pos += 1
        return self.buffer[start : self.pos]

    def take_until_string(self, s: str) -> str:
        return self.take_until_p(lambda p: p.at_string(s))

    def take_until_string_in(self, ss: list[str]) -> str:
        return self.take_until_p(lambda p: p.at_string_in(ss))

    def at_regex(self, regexp: _re.Pattern[str]) -> bool:
        m = regexp.match(self.buffer, self.pos)
        return m is not None

    def regex(
        self, regexp: _re.Pattern[str], allow_empty: bool = False
    ) -> tuple[str | _t.Any, ...]:
        m = regexp.match(self.buffer, self.pos)
        if m is None:
            raise ParsingFailure(
                "while parsing %s: expected %s, got %s",
                repr(self.buffer),
                repr(regexp),
                repr(self.leftovers),
            )
        pos = m.span()[1]
        if pos == self.pos and not allow_empty:
            raise ParsingFailure(
                "while parsing %s: matched nothing via %s, buffer is %s",
                repr(self.buffer),
                repr(regexp),
                repr(self.leftovers),
            )
        self.pos = pos
        return m.groups()

    def opt_regex(self, regexp: _re.Pattern[str]) -> tuple[str | _t.Any, ...]:
        return self.regex(regexp, True)

    def whitespace(self) -> str:
        grp = self.regex(whitespace_re)
        return grp[0]

    def opt_whitespace(self) -> tuple[str | _t.Any, ...]:
        return self.opt_regex(opt_whitespace_re)

    def lexeme(self, body_re: _re.Pattern[str]) -> str:
        self.opt_whitespace()
        grp = self.regex(body_re)
        self.opt_whitespace()
        return grp[0]
