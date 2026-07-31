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
from functools import update_wrapper as _update_wrapper

from .string_ext import abbrev as _abbrev
from .failure import AssertionFailure as _AssertionFailure, ParsingFailure


# A state transition function, see `BytesTransformer` below.
type ByteTransitions = _t.Callable[[int, int], tuple[int, bytes] | None]


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
whitespace_re = _re.compile(r"(\s+)")
optional_whitespace_re = _re.compile(r"(\s*)")

type ParserFunc[**PPS, PT] = _t.Callable[_t.Concatenate["Parser", PPS], PT]
type BareParserFunc[**PPS, PT] = _t.Callable[_t.Concatenate[str, int, PPS], tuple[PT, int]]


class Parser:
    """Parsec-like parser combinator."""

    buf: str
    pos: tuple[int, int, int]

    def __init__(self, data: str, i: int = 0) -> None:
        self.buf = data
        self.pos = (i, 1, 0)

    def leftovers(self) -> str:
        """Return what's left in the buffer."""
        return self.buf[self.pos[0] :]

    def _tail(self) -> str:
        return repr(_abbrev(self.buf[self.pos[0] : self.pos[0] + 36], 32))

    def move_to(self, i: int) -> None:
        """Move to `i`th position in the buffer, updating caret's line and character positions as required."""
        buf = self.buf
        buflen = len(buf)
        if i < 0 or i > buflen:
            raise IndexError()

        istart, line, char = self.pos
        if istart == i:
            pass
        elif istart < i:
            r = buf.rfind("\n", istart, i)
            if r == -1:
                # a move within the same line
                char += i - istart
            else:
                # a move to a different line
                line += buf.count("\n", istart, r) + 1
                char = i - r - 1
        else:
            ni = istart - i
            if ni <= char:
                # a move within the same line
                char -= ni
            else:
                # a move to a different line
                line -= buf.count("\n", i, istart)
                char = i - buf.rfind("\n", 0, i) - 1
        self.pos = (i, line, char)

    def advance(self, n: int) -> int:
        """Advance `n` characters forward (or backward) and return `n`."""
        self.move_to(self.pos[0] + n)
        return n

    # Simple parsers

    def fail(self, what: str, *args: _t.Any) -> _t.Never:
        """Raise `ParsingFailure` with given arguments, elaborated with current positional information."""
        raise ParsingFailure(what, *args).elaborate("at %d:%d", self.pos[1], self.pos[2])

    def at_eof(self) -> bool:
        """Return `True` if we at the end of the buffer."""
        return self.pos[0] >= len(self.buf)

    def eof(self) -> None:
        """Raise `ParsingFailure` if we are not at the end of the buffer."""
        if self.at_eof():
            return
        self.fail("expected EOF, got %s", self._tail())

    def at_has_more(self, n: int) -> bool:
        """Return `True` if we have `n` more characters in the buffer."""
        return self.pos[0] + n <= len(self.buf)

    def has_more(self, n: int) -> None:
        """Raise `ParsingFailure` if we have less than `n` more characters in the buffer."""
        start = self.pos[0]
        end = start + n
        buflen = len(self.buf)
        if end > buflen:
            self.fail(
                "expected %d more characters, but got only %d characters left",
                n,
                buflen - start,
            )

    def take(self, n: int) -> str:
        """Advance `n` characters forward in the buffer. Then, return a string that was jumped over."""
        old_i = self.pos[0]
        new_i = old_i + n
        self.move_to(new_i)
        return self.buf[old_i:new_i]

    def at_string(self, s: str) -> bool:
        """Return `True` if the rest of the buffer starts with `s`."""
        return self.buf.startswith(s, self.pos[0])

    def optional_string(self, s: str) -> str | None:
        """If the rest of the buffer starts with `s`, advance `len(s)` characters and return `s`. Otherwise,
        return `None`.
        """
        if self.at_string(s):
            self.advance(len(s))
            return s
        return None

    def string(self, s: str) -> str:
        """If the rest of the buffer starts with `s`, advance `len(s)` characters and return `s`. Otherwise,
        raise `ParsingFailure`.
        """
        res = self.optional_string(s)
        if res is None:
            self.fail(
                "expected %s, got %s",
                repr(s),
                self._tail(),
            )
        return res

    def at_string_in(self, ss: _t.Iterable[str]) -> bool:
        """Return `True` if the rest of the buffer starts with one of `ss`."""
        for s in ss:
            if self.buf.startswith(s, self.pos[0]):
                return True
        return False

    def optional_string_in(self, ss: _t.Iterable[str]) -> str | None:
        """If the rest of the buffer starts with one of `ss`, advance the length of and return the matching
        string. Otherwise, return `None`.
        """
        for s in ss:
            if self.at_string(s):
                self.advance(len(s))
                return s
        return None

    def string_in(self, ss: _t.Iterable[str]) -> str:
        """If the rest of the buffer starts with one of `ss`, advance the length of and return the matching
        string. Otherwise, raise `ParsingFailure`.
        """
        res = self.optional_string_in(ss)
        if res is None:
            self.fail(
                "expected one of %s, got %s",
                repr(ss),
                self._tail(),
            )
        return res

    def run_regex[D1, D2](
        self,
        pattern: _re.Pattern[str],
        unmatched: _t.Callable[[], D1],
        matched: _t.Callable[[int, int, _re.Match[str]], D2],
        allow_empty: bool = False,
    ) -> D1 | D2:
        """If the rest of the buffer starts with regular expression `pattern`, match it and supply
        the result to `matched`. Otherwise, return `unmatched`.

        Note that, when `allow_empty` is set, which is the default, this and related functions raise
        `AssertionFailure` when `pattern` matches an empty string. This is very much on purpose as
        this behavior frequently helps with parsing expression bug discovery.

        This is the most general version of all `Parser.*_regex` operations.
        """
        istart = self.pos[0]
        m = pattern.match(self.buf, istart)
        if m is None:
            return unmatched()
        iend = m.span()[1]
        if not allow_empty and iend == istart:
            raise _AssertionFailure(
                "pattern %s matched an empty string",
                repr(_abbrev(pattern.pattern, 32)),
            )
        self.move_to(iend)
        return matched(istart, iend, m)

    def at_regex(self, pattern: _re.Pattern[str], allow_empty: bool = False) -> bool:
        """Return `True` if the rest of the buffer starts with regular expression `pattern`."""
        return self.run_regex(pattern, lambda: False, (lambda istart, iend, m: True), allow_empty)

    def skip_optional_regex(self, pattern: _re.Pattern[str], allow_empty: bool = False) -> int:
        """If the rest of the buffer starts with regular expression `pattern`, skip it and return the number
        of characters that were skipped. Otherwise, return `0`.
        """
        return self.run_regex(
            pattern, lambda: 0, (lambda istart, iend, m: iend - istart), allow_empty
        )

    def optional_regex(
        self, pattern: _re.Pattern[str], allow_empty: bool = False
    ) -> tuple[str | None, ...] | None:
        """If the rest of the buffer starts with regular expression `pattern`, advance the length of and
        return the groups of the match. Otherwise, return `None`.
        """
        return self.run_regex(pattern, lambda: None, (lambda _a, _b, m: m.groups()), allow_empty)

    def regex(self, pattern: _re.Pattern[str], allow_empty: bool = False) -> tuple[str | None, ...]:
        """If the rest of the buffer starts with regular expression `pattern`, advance the length of and
        return the groups of the match. Otherwise, raise `ParsingFailure`.
        """
        res = self.optional_regex(pattern, allow_empty)
        if res is None:
            self.fail(
                "expected to match re %s, got %s",
                repr(_abbrev(pattern.pattern, 32)),
                self._tail(),
            )
        return res

    def lexeme_regex(
        self, pattern: _re.Pattern[str], whitespace: _re.Pattern[str] = whitespace_re
    ) -> tuple[str | None, ...]:
        self.skip_optional_regex(whitespace)
        res = self.regex(pattern)
        self.skip_optional_regex(whitespace)
        return res

    def skip_optional_whitespace(self) -> int:
        """Skip over whitespace and return the number of characters that were skipped."""
        return self.skip_optional_regex(whitespace_re)

    def optional_whitespace(self) -> str:
        """Advance over whitespace and return what was skipped over, if anything."""
        return _t.cast(str, self.regex(optional_whitespace_re, True)[0])

    def whitespace(self) -> str:
        """Parse one or more whitespace characters and return what was parsed."""
        return _t.cast(str, self.regex(whitespace_re)[0])

    def take_until_ex[**PS, T, D](
        self,
        f: ParserFunc[PS, T],
        default: _t.Callable[[], D],
        *args: PS.args,
        **kwargs: PS.kwargs,
    ) -> tuple[str, T | D]:
        """Advance forward one character at a time, including up to EOF, while `f` raises
        `ParsingFailure`s. Return the result of `f` as soon as `f` succeeds.

        Returns a tuple of: the string that was jumped over, the result of `f` or `default()`.

        The first element of the result could include all of the rest of the buffer up to EOF if `f`
        never succeeded.

        This is the most general version of all `Parser.take_until*` operations.
        """
        res: T | D
        ok = False

        istart = self.pos[0]
        buflen = len(self.buf)
        while self.pos[0] < buflen:
            pos = self.pos
            try:
                res = f(self, *args, **kwargs)
            except ParsingFailure:
                self.pos = pos
                self.advance(1)
                continue
            ok = True
            break

        iend = self.pos[0]
        return self.buf[istart:iend], (res if ok else default())

    def take_until_optional[**PS, T](
        self,
        f: ParserFunc[PS, T],
        *args: PS.args,
        **kwargs: PS.kwargs,
    ) -> tuple[str, T | None]:
        """Advance forward one character at a time, until `f` succeeds or EOF is reached.

        Returns a tuple of: the string that was jumped over, the result of `f` or `None`.
        """
        return self.take_until_ex(f, lambda: None, *args, **kwargs)[0:2]

    def take_until[**PS](
        self,
        pred: ParserFunc[PS, bool],
        *args: PS.args,
        **kwargs: PS.kwargs,
    ) -> str:
        """Advance forward one character at a time until `pred` returns `True` or EOF is reached.

        Returns a string that was jumped over.
        """

        def inner(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> None:
            if not pred(p, *args, **kwargs):
                raise ParsingFailure("False")

        return self.take_until_ex(inner, lambda: None, *args, **kwargs)[0]

    def take_until_at_string(self, s: str) -> str:
        """`Parser.take_until` with with `Parser.at_string`."""
        return self.take_until(lambda p: p.at_string(s))

    def take_until_at_string_in(self, ss: _t.Iterable[str]) -> str:
        """`Parser.take_until` with with `Parser.at_string_in`."""
        return self.take_until(lambda p: p.at_string_in(ss))

    def take_until_at_regex(self, pattern: _re.Pattern[str], allow_empty: bool = False) -> str:
        """`Parser.take_until_true` with with `Parser.at_regex`."""
        return self.take_until(lambda p: p.at_regex(pattern, allow_empty))

    def run_bare_parser[**PS, T](
        self, f: BareParserFunc[PS, T], name: str | None, *args: PS.args, **kwargs: PS.kwargs
    ) -> T:
        """Apply `f: BareParserFunc` to `self`, elaborating raised `ParsingFailures` with `name` or `f.__name__`.."""
        try:
            res, iend = f(self.buf, self.pos[0], *args, **kwargs)
            self.move_to(iend)
            return res
        except ParsingFailure as exc:
            raise exc.elaborate("in <%s>", f.__name__ if name is None else name)

    @staticmethod
    def mk_bare_parser[**PS, T](
        name: str | None = None,
    ) -> _t.Callable[[BareParserFunc[PS, T]], ParserFunc[PS, T]]:
        """Decorator version of `Parser.run_bare`."""

        def inner(f: BareParserFunc[PS, T], /) -> ParserFunc[PS, T]:
            def inner2(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> T:
                return p.run_bare_parser(f, name, *args, **kwargs)

            _update_wrapper(inner2, f)
            return inner2

        return inner

    def run[**PS, T](self, f: ParserFunc[PS, T], *args: PS.args, **kwargs: PS.kwargs) -> T:
        """Apply `f: ParserFunc` to `self`. I.e. `p.run(f, ...)` is exactly `f(p, ...)`, the latter of
        which is should be used in most use cases.

        This method exists so that you could write `(p.run if required else p.optional)(f)` and
        similar.
        """
        return f(self, *args, **kwargs)

    def run_named[**PS, T](
        self, f: ParserFunc[PS, T], name: str | None, *args: PS.args, **kwargs: PS.kwargs
    ) -> T:
        """Apply `f: ParserFunc` to `self`, elaborating raised `ParsingFailures` with `name` or `f.__name__`."""
        try:
            return f(self, *args, **kwargs)
        except ParsingFailure as exc:
            raise exc.elaborate("in <%s>", f.__name__ if name is None else name)

    @staticmethod
    def mk_named[**PS, T](
        name: str | None = None,
    ) -> _t.Callable[[ParserFunc[PS, T]], ParserFunc[PS, T]]:
        """Decorator version of `Parser.run_parser`."""

        def inner(f: ParserFunc[PS, T]) -> ParserFunc[PS, T]:
            def inner2(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> T:
                return p.run_named(f, name, *args, **kwargs)

            _update_wrapper(inner2, f)
            return inner2

        return inner

    def optional[**PS, T](
        self, f: ParserFunc[PS, T], *args: PS.args, **kwargs: PS.kwargs
    ) -> T | None:
        """Apply `f: ParserFunc` to `self`, backtracking and returning `None` if it raises `ParsingFailure`."""
        pos = self.pos
        try:
            res = f(self, *args, **kwargs)
        except ParsingFailure:
            self.pos = pos
            return None
        return res

    @staticmethod
    def mk_optional[**PS, T](f: ParserFunc[PS, T]) -> ParserFunc[PS, T | None]:
        """Decorator version of `Parser.optional`."""

        def inner(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> T | None:
            return p.optional(f, *args, **kwargs)

        # NB: no _update_wrapper(inner, f)
        return inner

    def choice[**PS, T](
        self, fs: _t.Iterable[ParserFunc[PS, T]], *args: PS.args, **kwargs: PS.kwargs
    ) -> T:
        """Try parsing `self.buf` with given `ParserFunc`s, in order, backtracking after each failure and
        raising a `ParsingFailure` only if all of `fs` raise `ParsingFailure`s.
        """
        excs = []
        pos = self.pos
        for f in fs:
            try:
                res = f(self, *args, **kwargs)
            except ParsingFailure as exc:
                self.pos = pos
                excs.append(exc)
            else:
                return res
        raise ParsingFailure(excs)

    @staticmethod
    def mk_choice[**PS, T](*fs: ParserFunc[PS, T]) -> ParserFunc[PS, T]:
        """Decorator version of `Parser.choice`."""

        def inner(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> T:
            return p.choice(fs, *args, **kwargs)

        # NB: no _update_wrapper(inner, ?)
        return inner

    def repeat[**PS, T](
        self,
        f: ParserFunc[PS, T],
        no_less: int,
        no_more: int | None,
        *args: PS.args,
        **kwargs: PS.kwargs,
    ) -> _t.Generator[T]:
        """Repeatedly apply `f` to `self` until `f` raises `ParsingFailure` or until `no_more` iterations
        are reached.

        Each time `f` succeeds, yield its result.

        If `f` raises `ParsingFailure` before `no_less` iterations are reached, re-raise that
        `ParsingFailure` too.
        """
        pos = self.pos
        n = 0
        while no_more is None or n < no_more:
            try:
                res = f(self, *args, **kwargs)
            except ParsingFailure:
                if n < no_less:
                    raise
                break
            npos = self.pos
            if npos == pos:
                raise _AssertionFailure(
                    "parser <%s> succeeded without advancing forward", f.__name__
                )
            pos = npos
            n += 1
            yield res

    @staticmethod
    def mk_repeat[**PS, T](
        f: ParserFunc[PS, T],
        no_less: int = 0,
        no_more: int | None = None,
    ) -> ParserFunc[PS, _t.Generator[T]]:
        """Decorator version of `Parser.repeat`."""

        def inner(p: Parser, /, *args: PS.args, **kwargs: PS.kwargs) -> _t.Generator[T]:
            yield from p.repeat(f, no_less, no_more, *args, **kwargs)

        return inner


# Utility functions


def run_parser[**PS, T](
    f: ParserFunc[PS, T],
    eof: bool,
    data: str,
    *args: PS.args,
    **kwargs: PS.kwargs,
) -> tuple[T, Parser]:
    p = Parser(data)
    try:
        res = f(p, *args, **kwargs)
        if eof:
            p.eof()
    except ParsingFailure as exc:
        raise exc.elaborate("while parsing `%s`", _abbrev(data, 64))
    return res, p
