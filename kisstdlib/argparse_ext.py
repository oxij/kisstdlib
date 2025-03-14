# Copyright (c) 2022-2025 Jan Malakhovski <oxij@oxij.org>
#
# This file is a part of `kisstdlib` project.
#
# This file can be distributed under the terms of the MIT-style license given
# below or Python Software Foundation License version 2 (PSF-2.0) as published
# by Python Software Foundation.
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

"""Extensions for the standard `argparse` module."""

import shutil as _shutil
import sys as _sys
import textwrap as _textwrap
import typing as _t

from argparse import *
from gettext import gettext as _gettext

from .base import identity as _identity
from .io.stdio import stdout as _stdout, stderr as _stderr
from .logging_ext import die as _die


class BetterHelpFormatter(HelpFormatter):
    """Like `argparse.HelpFormatter`, but with better formatting. Also, adds
    `add_code` function.
    """

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: int | None = None,
    ):
        if width is None:
            width = _shutil.get_terminal_size(fallback=(65536, 20)).columns - 2
        super().__init__(prog, indent_increment, max_help_position, width)

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        res = []
        for line in text.splitlines():
            if line == "":
                res.append(line)
                continue

            for sub in _textwrap.wrap(line, width - len(indent)):
                sub = indent + sub
                res.append(sub)
        return "\n".join(res)

    def _split_lines(self, text: str, width: int) -> list[str]:
        res = []
        for line in text.splitlines():
            res += _textwrap.wrap(line, width)
        return res

    def add_code(self, text: str) -> None:
        self.add_text(text.strip())


class MarkdownBetterHelpFormatter(BetterHelpFormatter):
    """`BetterHelpFormatter` that outputs stuff formatted in Markdown"""

    def add_code(self, text: str) -> None:
        self.add_text("```\n" + text.strip() + "\n```")

    def _format_usage(
        self, usage: str | None, actions: _t.Any, groups: _t.Any, prefix: str | None
    ) -> str:
        if prefix is None:
            prefix = _gettext("usage: ")

        if usage is not None:
            usage = usage % {"prog": self._prog}
        elif usage is None and not actions:
            usage = self._prog
        elif usage is None:
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)
            action_usage = self._format_actions_usage(optionals + positionals, groups)
            usage = " ".join([s for s in [self._prog, action_usage] if s])

        return f"{prefix}{usage}\n\n"

    def _format_action(self, action: _t.Any) -> str:
        # determine the required width and the entry label
        action_header = self._format_action_invocation(action)

        action_header = f"{' ' * self._current_indent}- `{action_header}`\n"

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add it
        if action.help and action.help.strip():
            first = True
            for line in self._expand_help(action).splitlines():
                if first:
                    parts.append(f"{' ' * self._current_indent}: {line}\n")
                else:
                    parts.append(f"{' ' * self._current_indent}  {line}\n")
                first = False

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith("\n"):
            parts.append("\n")

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    class _Section(HelpFormatter._Section):  # pylint: disable=protected-access
        def format_help(self) -> str:
            if self.parent is not None:
                self.formatter._indent()  # pylint: disable=protected-access
            join = self.formatter._join_parts  # pylint: disable=protected-access
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()  # pylint: disable=protected-access

            # return nothing if the section was empty
            if not item_help:
                return ""

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                heading = f"{' ' * self.formatter._current_indent}- {self.heading}:\n"  # pylint: disable=protected-access
            else:
                heading = ""

            # join the section-initial newline, the heading and the help
            return join(["\n", heading, item_help, "\n"])


class _OptionallyMarkdownHelpAction(Action):
    def __init__(
        self,
        option_strings: list[str],
        dest: str = SUPPRESS,
        default: _t.Any = SUPPRESS,
        **kwargs: _t.Any,
    ) -> None:
        super().__init__(
            option_strings=option_strings, dest=dest, default=default, nargs=0, **kwargs
        )

    def show_help(self, parser: "BetterArgumentParser", namespace: Namespace) -> None:
        if namespace._markdown:  # pylint: disable=protected-access
            parser.set_formatter_class(MarkdownBetterHelpFormatter)
            _stdout.write(parser.format_help())
        else:
            parser.print_help()
        parser.exit()

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | _t.Sequence[_t.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(parser, BetterArgumentParser):
            raise ArgumentError(
                None,
                _gettext("`OptionallyMarkdownHelpAction` needs `BetterArgumentParser`"),
            )
        parser.post_parse_args = self.show_help


class BetterArgumentParser(ArgumentParser):
    """Like `argparse.ArgumentParser`, but uses `BetterHelpFormatter` by default,
    and implements `format_help` that recurses into subcommands and appends
    `additional_sections` at the end.

    Also, this implements `add_version` option and disables `allow_abbrev` by
    default, since it's produces error-prone CLIs.
    """

    formatter_class: type[BetterHelpFormatter]

    def __init__(
        self,
        prog: str | None = None,
        *,
        allow_abbrev: bool = False,  # error-prone default in `ArgumentParser`
        add_version: bool = False,  # so that subparsers won't have this enabled
        version: str | None = None,
        add_help: bool = True,
        formatter_class: type[BetterHelpFormatter] = BetterHelpFormatter,
        additional_sections: list[_t.Callable[[BetterHelpFormatter], None]] = [],
        **kwargs: _t.Any,
    ) -> None:
        super().__init__(
            prog,
            allow_abbrev=allow_abbrev,
            add_help=False,
            formatter_class=formatter_class,
            **kwargs,
        )

        self.register("action", "help_omd", _OptionallyMarkdownHelpAction)

        self.add_version = add_version
        self.add_help = add_help
        self.additional_sections = additional_sections
        self.post_parse_args: _t.Callable[[BetterArgumentParser, Namespace], None] | None = None

        default_prefix = "-" if "-" in self.prefix_chars else self.prefix_chars[0]
        if add_version:
            if version is None:
                version = "dev"
                if prog is not None:
                    try:
                        import importlib.metadata as meta

                        try:
                            version = meta.version(prog)
                        except meta.PackageNotFoundError:
                            pass
                    except ImportError:
                        pass
            self.add_argument(
                default_prefix * 2 + "version", action="version", version="%(prog)s " + version
            )

        if add_help:
            self.add_argument(
                default_prefix + "h",
                default_prefix * 2 + "help",
                action="help_omd",
                default=SUPPRESS,
                help=_gettext("show this help message and exit"),
            )
            self.add_argument(
                default_prefix * 2 + "markdown",
                dest="_markdown",
                action="store_true",
                help=_gettext("show `--help` formatted in Markdown"),
            )

    def set_formatter_class(self, formatter_class: type[BetterHelpFormatter]) -> None:
        self.formatter_class = formatter_class
        if hasattr(self._subparsers, "_group_actions"):
            for grp in self._subparsers._group_actions:  # type: ignore # pylint: disable=protected-access
                for _choice, e in grp.choices.items():  # type: ignore
                    e.set_formatter_class(formatter_class)

    def format_help(self, depth: int = 1) -> str:
        # generate top-level thing, like the default `format_help` does
        formatter = self.formatter_class(prog=self.prog)

        formatter.add_usage(
            self.usage, self._actions, self._mutually_exclusive_groups, "#" * depth + " "
        )
        formatter.add_text(self.description)

        if hasattr(self, "_action_groups"):
            for action_group in self._action_groups:  # pylint: disable=protected-access
                formatter.start_section(action_group.title)
                formatter.add_text(action_group.description)
                formatter.add_arguments(
                    action_group._group_actions  # pylint: disable=protected-access
                )
                formatter.end_section()

        # add sub-sections for all subparsers
        if hasattr(self._subparsers, "_group_actions"):
            seen = set()
            for grp in self._subparsers._group_actions:  # type: ignore # pylint: disable=protected-access
                for _choice, e in grp.choices.items():  # type: ignore
                    if e in seen:
                        continue
                    seen.add(e)
                    formatter._add_item(  # pylint: disable=protected-access
                        e.format_help, [depth + 1]
                    )
                    formatter._add_item(lambda: "\n", [])  # pylint: disable=protected-access

        # add additional sections
        for gen in self.additional_sections:
            gen(formatter)

        # add epilog
        formatter.add_text(self.epilog)

        return formatter.format_help()

    def exit(self, status: int = 0, message: str | None = None) -> _t.NoReturn:
        if message:
            _stderr.write(message)
        _sys.exit(status)

    def error(self, message: str) -> _t.NoReturn:
        self.print_usage()
        _die("%s", message, code=2)

    def parse_args(  # type: ignore
        self,
        args: _t.Sequence[str] | None = None,
        namespace: Namespace | None = None,
        remake_parser: _t.Callable[["BetterArgumentParser"], "BetterArgumentParser"] = _identity,
        remake_subparser: _t.Callable[["BetterArgumentParser"], "BetterArgumentParser"] = _identity,
    ) -> Namespace:
        res: Namespace = super().parse_args(args, namespace)
        post = self.post_parse_args
        if post is not None:
            post(remake_parser(self), res)
        if hasattr(self._subparsers, "_group_actions"):
            for grp in self._subparsers._group_actions:  # type: ignore # pylint: disable=protected-access
                for _choice, e in grp.choices.items():  # type: ignore
                    post = e.post_parse_args
                    if post is not None:
                        post(remake_subparser(e), res)
        if self.add_help:
            del res._markdown
        return res


_AParamSpec = _t.ParamSpec("_AParamSpec")


def make_argparser_and_run(
    make_argparser: _t.Callable[[bool], BetterArgumentParser],
    func: _t.Callable[_t.Concatenate[Namespace, _AParamSpec], None],
    /,
    *args: _AParamSpec.args,
    **kwargs: _AParamSpec.kwargs,
) -> None:
    """Given `make_argparser` function that produces "real" and "fake"
    `BetterArgumentParser`s, run `parse_args` with on real one, but then, if
    `--help` was requested, run `show_help` with the fake one.

    I.e., allow the printed output of `--help` to differ from the real syntax
    one.

    This is useful for easily hiding whole blocks from `--help`, deduplicating
    similar groups between subcommands, making non-`--help` version cheaper to
    compute (by hiding complex generated help strings), etc.

    Suparsers' `--help`s will be left as-is, so that `subcommand --help` would
    show the real syntax.
    """
    parser = make_argparser(True)
    cargs = parser.parse_args(_sys.argv[1:], remake_parser=lambda x: make_argparser(False))
    func(cargs, *args, **kwargs)
