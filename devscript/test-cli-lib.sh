#!/usr/bin/env bash
#
# A little shell library for testing CLI programs.
#
# This mainly exists for testing that given programs produce the same output
# between test invocations. I.e., mainly, for testing that given programs
# produce the same output at different versions.
#
# I.e., this is like integration tests, but for making sure the program plays
# well with itself across versions.

errors=0
task_errors=0

error() {
    echo -e "\e[1;31m" >&2
    echo -n "$*" >&2
    echo -e "\e[0m" >&2
    ((errors+=1))
    ((task_errors+=1))
}

die() {
    error "$*"
    exit 1
}

task_started=0
start() {
    echo -n "## $1"
    task_started=$(date +%s)
    task_errors=0
}

end() {
    local now=$(date +%s)
    echo ": $task_errors errors, $((now-task_started)) seconds"
}

finish() {
    echo "total: $errors errors"
    if ((errors > 0)); then
        exit 1
    fi
}

win32path() {
    sed 's%/%\\%g; s%^%Z:%' <<< "$1"
}

win32path0_many() {
    sed -z 's%/%\\%g; s%^%Z:%'
}

equal_file() {
    if ! diff -U 0 "$1" "$2"; then
        error "equal_file \`$1\` \`$2\` failed"
    fi
}

equal_dir() {
    if ! diff -U 0 <(describe-subtree "$1") <(describe-subtree "$2"); then
        error "equal_dir \`$1\` \`$2\` failed"
    fi
}

fixed_file() {
    local src="$1"
    local got="$2"
    shift 2
    local bn="$(basename "$got")"
    local expected="$src.$bn"

    if ! [[ -e "$expected" ]]; then
        cp "$got" "$expected"
        echo " created \`$bn\` at \`$expected\`"
    elif ! diff -U 0 "$expected" "$got" ; then
        cp "$got" "$expected.new"
        error "fixed_file \`$bn\` failed"
    else
        rm -f "$expected.new"
    fi
}

fixed_dir() {
    describe-subtree "$2" > "$2.describe-dir"
    fixed_file "$1" "$2.describe-dir"
}

ok() {
    "$@"
    code=$?
    if ((code != 0)); then
        die "$*: return code $code"
    fi
}

ok_stdio2() {
    local dst="$1"
    shift 1

    "$@" &> "$dst"
    code=$?
    if ((code != 0)); then
        cat "$dst" >&2
        die "$*: return code $code"
    fi
}

ok_no_stderr() {
    local tmp=$(mktemp --tmpdir test-cli-lib-stderr-XXXXXXXX)

    ok "$@" > /dev/null 2> "$tmp"
    if [[ -s "$tmp" ]]; then
        cat "$tmp" >&2
        error "$*: stderr is not empty"
    fi
    rm -r "$tmp"
}

# temp dir
tmpdir=
# temp pid
tmppid=

set_tmpdir() {
    tmpdir=$(mktemp --tmpdir -d test-cli-lib-dir-XXXXXXXX)
    tmpdir=$(readlink -f "$tmpdir")
}

atexit_cleanup() {
    [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"
    [[ -n "$tmppid" ]] && kill -9 "$tmppid"
}

umask 077
trap atexit_cleanup 0
