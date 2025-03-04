# Copyright (c) 2023-2025 Jan Malakhovski <oxij@oxij.org>
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

"""Extensions for the standard `getpass` module."""

import sys as _sys
import subprocess as _subprocess

from getpass import *

from .failure import RuntimeFailure as _RuntimeFailure


def getpass_pinentry(
    desc: str | None = None, prompt: str | None = None, encoding: str = _sys.getdefaultencoding()
) -> str:
    try:
        with _subprocess.Popen(["pinentry"], stdin=_subprocess.PIPE, stdout=_subprocess.PIPE) as p:

            def check(beginning: str) -> str:
                res = p.stdout.readline().decode(encoding)  # type: ignore
                if not res.endswith("\n") or not res.startswith(beginning):
                    raise _RuntimeFailure("`pinentry` conversation failed")
                return res[len(beginning) : -1]

            check("OK ")

            def opt(what: str, beginning: str) -> str:
                p.stdin.write(what.encode(encoding) + b"\n")  # type: ignore
                p.stdin.flush()  # type: ignore
                return check(beginning)

            if desc is not None:
                opt("SETDESC " + desc, "OK")
            if prompt is not None:
                opt("SETPROMPT " + prompt, "OK")
            pin = opt("GETPIN", "D ")
            return pin
    except FileNotFoundError as exc:
        raise _RuntimeFailure("`pinentry` not found") from exc
