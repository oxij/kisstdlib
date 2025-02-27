#!/bin/sh -e

black $1 .
mypy
pytest -k 'not slow'
pylint .
./test-example.sh
./update-readme.sh
