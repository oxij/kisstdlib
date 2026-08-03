#!/bin/sh -e

black $1 .
mypy
LANG=C TZ=GMT pytest -k 'not slow'
LANG=pl_PL.UTF-8 TZ=GMT-2 pytest -k time
pylint .
./update-readme.sh
if [[ "$1" == "--check" ]]; then
    ./test-example.sh
fi
