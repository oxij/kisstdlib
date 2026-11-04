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

PACKAGE=cli
TAG=new
INPUT=default

errors=0
task_errors=0

error() {
    echo -en "\e[1;31merror: " >&2
    echo -n "$*" >&2
    echo -e "\e[0m" >&2
    ((errors+=1))
    ((task_errors+=1))
    return 1
}

die() {
    error "$*"
    exit 1
}

abbrev_file() {
    local len=$(cat "$1" | wc -l)
    if ((len <= 10)); then
        cat "$1"
    else
        head -n 5 "$1"
        echo "..."
        tail -n 5 "$1"
    fi
}

diff_files() {
    local tmp=$(mktemp --tmpdir "test-dir-$PACKAGE-$TAG-$INPUT-XXXXXXXX.diff")
    diff -U 0 "$1" "$2" > "$tmp"
    local code=$?
    if [[ $code != 0 ]]; then
        abbrev_file "$tmp" >&2
    fi
    rm -f "$tmp"
    return $code
}

task_started=0

end() {
    local now=$(date +%s)
    echo ": $task_errors errors, $((now-task_started)) seconds"
    task_started=0
}

begin() {
    if (($task_started > 0)); then
        end
    fi

    echo -n "## $*"
    task_started=$(date +%s)
    task_errors=0
}

TARGETS=()

start() {
    if (($task_started > 0)); then
        end
    fi

    local ok=1
    for t in "${TARGETS[@]}"; do
        if grep -E "$t" <<< "$*" &>/dev/null ; then
            ok=1
            break
        else
            ok=
        fi
    done
    if [[ -z "$ok" ]]; then
        return 1
    fi

    begin "$@"
}

finish() {
    if (($task_started > 0)); then
        end
    fi

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

make_regular() {
    local dst="$1"
    local time="$2"
    local content="$3"

    echo -n "$content" > "$dst.part"
    mv "$dst.part" "$dst"
    touch -d "$time" "$dst"
}

make_symlink() {
    local dst="$1"
    local time="$2"
    local target="$3"

    ln -s "$target" "$dst.part"
    mv "$dst.part" "$dst"
    touch -h -d "$time" "$dst"
}

set_subtree_dir_mtimes() {
    find "$1" -type d -exec touch -h -d "$2" {} \;
}

equal_file() {
    if ! diff_files "$1" "$2"; then
        error "equal_file $*: wrong file content"
    fi
}

equal_dir() {
    if ! diff_files <(describe-forest "$1") <(describe-forest "$2"); then
        error "equal_dir $*: wrong directory content"
    fi
}

fixed_file_quiet() {
    local src="$1"
    local got="$2"
    shift 2
    local bn="$(basename "$got")"
    local expected="$src.$bn"

    if ! [[ -e "$expected.$TAG" ]]; then
        cp -a "$got" "$expected.$TAG"
    elif ! diff "$expected.$TAG" "$got" &>/dev/null ; then
        mv --backup=numbered "$expected.$TAG" "$expected.$TAG.old"
        cp -a "$got" "$expected.$TAG"
    fi
    if ! [[ -e "$expected" ]] ; then
        ln "$expected.$TAG" "$expected"
    elif ! diff_files "$expected" "$expected.$TAG" ; then
        return 1
    fi
}

fixed_file() {
    if ! fixed_file_quiet "$@"; then
        error "fixed_file $*: wrong file content"
    fi
}

fixed_dir() {
    describe-forest "$2" > "$2.describe-dir"
    local code=$?
    if [[ $code != 0 ]]; then
        error "fixed_dir $*: describe-forest: expected return code 0, got $code"
    fi
    if ! fixed_file_quiet "$1" "$2.describe-dir"; then
        error "fixed_dir $*: wrong directory content"
    fi
}

retcode() {
    local ret=$1
    shift

    "$@"
    local code=$?
    if [[ $code != $ret ]]; then
        error "retcode $ret $*: expected return code $ret, got $code"
    fi
}

retcode_stdio() {
    local ret=$1
    local dst_="$2"
    local dst="$2.stdio"
    shift 2

    "$@" &> "$dst"
    local code=$?
    if [[ $code != $ret ]]; then
        abbrev_file "$dst" >&2
        error "retcode_stdio $ret $dst_ $*: expected return code $ret, got $code"
    fi
}

ok() {
    retcode 0 "$@"
}

ok_stdio() {
    retcode_stdio 0 "$@"
}

retcode_fixed_stdio() {
    local ret=$1
    local src="$2"
    local dst="$3"
    shift 3

    retcode_stdio $ret "$dst" "$@"
    local code=$?
    if [[ $? != 0 ]]; then
        error "retcode_fixed_stdio $ret $src $dst $*: retcode_stdio: expected return code 0, got $code"
    fi
    sed -i "s%$tmpdir/%./%g" "$dst.stdio"
    if ! fixed_file_quiet "$src" "$dst.stdio"; then
        error "retcode_fixed_stdio $ret $src $dst $*: wrong stdio content"
    fi
}

ok_fixed_stdio() {
    retcode_fixed_stdio 0 "$@"
}

ok_no_stdio() {
    local dst_="$1"
    local dst="$1.stdio"
    shift 1

    "$@" &> "$dst"
    local code=$?
    if [[ $code != 0 ]]; then
        abbrev_file "$dst" >&2
        error "ok_no_stdio $dst_ $*: expected return code 0, got $code"
    elif [[ -s "$dst" ]]; then
        abbrev_file "$dst" >&2
        error "ok_no_stdio $dst_ $*: stdio is not empty"
    fi
}

ok_no_stderr() {
    local dst_="$1"
    local dst="$1.stderr"
    shift 1

    "$@" > /dev/null 2> "$dst"
    local code=$?
    if [[ $code != 0 ]]; then
        abbrev_file "$dst" >&2
        error "ok_no_stderr $dst_ $*: expected return code 0, got $code"
    elif [[ -s "$dst" ]]; then
        abbrev_file "$dst" >&2
        error "ok_no_stderr $dst_ $*: stderr is not empty"
    fi
}

any_result() {
    local dst="$1.result"
    shift 1

    "$@" &> "$dst"
    local code=$?
    if [[ $code != 0 ]]; then
        echo "# \$? == $code" >> "$dst"
    fi
    return $code
}

# temp dir
tmpdir=
# temp pid
tmppid=

set_tmpdir() {
    tmpdir=$(mktemp --tmpdir -d "test-dir-$PACKAGE-$TAG-$INPUT-XXXXXXXX")
    tmpdir=$(readlink -f "$tmpdir")
}

atexit_cleanup() {
    [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"
    [[ -n "$tmppid" ]] && kill -9 "$tmppid"
}

umask 077
trap atexit_cleanup 0
