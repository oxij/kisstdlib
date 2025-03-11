#!/bin/sh -e

black $1 .
mypy
pytest -k 'not slow'
pylint .
./update-readme.sh
if [[ "$1" == "--check" ]]; then
    ./test-example.sh
fi
