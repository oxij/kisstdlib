#!/bin/sh -e

echo '$table-of-contents$' > toc.template
for i in 0 1; do
{
    echo "# Table of Contents"
    echo "<details><summary>(Click me to see it.)</summary>"
    pandoc --wrap=none --toc --template=toc.template --metadata title=toc -f markdown -t html README.md \
        | sed '/Table of Contents/ d; s%<span id="[^"]*"/>%%'
    echo "</details>"
    echo

    sed -n "/# What is/,/# Usage/ p" README.md
    echo

    python3 -m kisstdlib_bin.describe_forest --help --markdown | sed '
s/^\(#\+\) /#\1 /
s/^\(#\+\) \(describe-forest[^A-Z[({]*\) [A-Z[({].*/\1 \2/
'

    echo

    ./test-example.sh --help | sed '
s/^# usage: \(.*\)$/# Development: `\1`/
'
} > README.new
mv README.new README.md
done
pandoc -s -V pagetitle=README -f markdown -t html README.md > README.html
