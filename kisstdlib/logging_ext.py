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


class CounterHandler(_logging.NullHandler):
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
        elif record.levelno >= _logging.DEBUG:
            self.debugs += 1
        return True
