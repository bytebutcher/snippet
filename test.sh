#!/bin/bash

# Setting up test files
# ---------------------
cat<<'EOF' > files.txt
one
two
three
EOF

# Executing test cases
# --------------------

# Add a new snippet to the database
snippet -e archive/extract-tgz -f 'tar -xzvf <archive>'

# Edit a snippet (will open vim)
snippet -e archive/extract-tgz

# Search a snippet which include the term "extract" (will open fzf)
snippet -t extract

# Fill snippet with a value
snippet -t archive/extract-tgz /path/to/foo.tar.gz

# Fill snippet with multiple values
snippet -t archive/extract-tgz /path/to/foo.tar.gz /path/to/bar.tar.gz

# Fill snippet with multiple values while using repeatable placeholders (e.g. <file...>)
snippet -f "tar -czvf <archive> <file...>" /path/to/foo.tar file=foo bar

# Using presets (e.g. '<datetime>' to include current datetime)
snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file=foo bar

# Import values from file
snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file:files.txt

# Using optionals
snippet -f "python3 -m http.server[ --bind <lhost>][ <lport>]" lport=4444

# Using defaults
snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>"

# Overwriting defaults
snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>" lport=9090

# Using codecs
snippet -f "tar -czvf <archive|squote> <file...|squote>" /path/to/foo.tar file=foo bar

# Using multiple codecs with arguments
snippet -f "cp <file|squote> <file...|add:'.bak'|squote>" /path/to/foo /path/to/bar

# Cleaning up
# -----------
rm files.txt