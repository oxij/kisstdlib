#!/usr/bin/env bash

#set -x

. ./devscript/test-cli-lib.sh

usage() {
    cat << EOF
# usage: $0 [--help] [--wine]

Check that all \`kisstdlib/example/*.py\` are fixed-output.
EOF
}

if [[ "$1" == "--help" ]]; then
    usage
    exit 0
fi

export PYTHONPATH="$PWD:$PYTHONPATH"

in_wine=
py() {
    if [[ -z "$in_wine" ]]; then
        echo -n | python3 "$@"
    else
        echo -n | wine python "$@"
    fi
}

set_tmpdir

OPWD="$PWD"
cd "$tmpdir"

check() {
    local out=$1
    local script=$2
    local file="$OPWD/example/$script"
    shift 2

    start "$script"
    ok_stdio2 "$out" py "$file" "$@"
    sed -i "s/0x[0-9a-f]\+/0xdeadbeef/g" "$out"
    sed -i 's/\(File "\)[^"]*\(", line \)[0-9]\+\(, in .module.\)/\1FILE\2NUM\3/g' "$out"
    fixed_file "$file" "$out"
    end
}

echo "# Testing fixed-outputness of example/*.py ..."

touch "foo.py"
touch "bar.py"
touch "nya.py"
mkdir "leaf"
mkdir "notleaf"
mkdir "notleaf/leaf"
check "out" fs_iter_subtree.py

check "out" sqlite3_ext.py

check "ansi.out" tty_io.py --no-interactive --ansi
check "noansi.out" tty_io.py --no-interactive --no-ansi

check "out" stop_gently.py --no-interactive
