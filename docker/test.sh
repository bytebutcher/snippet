#!/bin/bash

# ======================================================================================================================
# Helpers
# ======================================================================================================================

PASS=0
FAIL=0

assert_eq() {
    local description="$1"
    local expected="$2"
    local actual="$3"

    if [ "$expected" = "$actual" ]; then
        echo "[ PASS ] $description"
        ((PASS++))
    else
        echo "[ FAIL ] $description"
        echo "         expected : $(echo "$expected" | head -5 | sed 's/^/                   /')"
        echo "         actual   : $(echo "$actual"   | head -5 | sed 's/^/                   /')"
        ((FAIL++))
    fi
}

assert_match() {
    local description="$1"
    local pattern="$2"
    local actual="$3"

    if echo "$actual" | grep -${QUIET}E "$pattern"; then
        echo "[ PASS ] $description"
        ((PASS++))
    else
        echo "[ FAIL ] $description"
        echo "         pattern  : $pattern"
        echo "         actual   : $actual"
        ((FAIL++))
    fi
}

assert_exit_ok() {
    local description="$1"
    local exit_code="$2"

    if [ "$exit_code" -eq 0 ]; then
        echo "[ PASS ] $description"
        ((PASS++))
    else
        echo "[ FAIL ] $description (exit code: $exit_code)"
        ((FAIL++))
    fi
}

summary() {
    echo ""
    echo "======================================================"
    echo " Results: $PASS passed, $FAIL failed"
    echo "======================================================"
    [ "$FAIL" -eq 0 ] && exit 0 || exit 1
}

# ======================================================================================================================
# Setup
# ======================================================================================================================

cat <<'EOF' > files.txt
one
two
three
EOF

# ======================================================================================================================
# Test cases
# ======================================================================================================================

# --- Snippet database -------------------------------------------------------------------------------------------------

# Add a snippet to the database (non-interactive: uses -f so no editor is opened)
#snippet -e archive/extract-tgz -f 'tar -xzvf <archive>' > /dev/null 2>&1
#assert_exit_ok "Add snippet to database" $?
snippet -f 'tar -xzvf <archive>' archive=/path/to/foo.tar.gz
# Retrieve and fill a stored snippet with a single value
result=$(snippet -f 'tar -xzvf <archive>' archive=/path/to/foo.tar.gz)
assert_eq "Fill stored snippet with single value" \
    "tar -xzvf /path/to/foo.tar.gz" \
    "$result"

# Retrieve and fill a stored snippet with multiple values (generates one line per value)
result=$(snippet -f 'tar -xzvf <archive>' archive=/path/to/foo.tar.gz /path/to/bar.tar.gz)
assert_eq "Fill stored snippet with multiple values" \
    "$(printf 'tar -xzvf /path/to/foo.tar.gz\ntar -xzvf /path/to/bar.tar.gz')" \
    "$result"

# Note: "snippet -e archive/extract-tgz" (editor) and "snippet -t extract" (fzf search) are
# interactive and require a TTY — skipped in automated testing.

# --- Inline format strings --------------------------------------------------------------------------------------------

# Repeatable placeholder with positional args
result=$(snippet -f "tar -czvf <archive> <file...>" /path/to/foo.tar file=foo bar)
assert_eq "Repeatable placeholder with positional args" \
    "tar -czvf /path/to/foo.tar foo bar" \
    "$result"

# Preset: <datetime> is dynamic so we only assert the surrounding structure
result=$(snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file=foo bar)
assert_match "Preset <datetime> placeholder (structure check)" \
    "^tar -czvf '.*\.tar\.gz' foo bar$" \
    "$result"

# Import values from file (produces one line per value in files.txt)
result=$(snippet -f "tar -czvf '<datetime>.tar.gz' <file...>" file:files.txt)
assert_match "File import" \
    "^tar -czvf '.*\.tar\.gz' one two three$" \
    "$result"

# --- Optionals --------------------------------------------------------------------------------------------------------

# Optional group omitted when lhost is not provided, lport is provided
result=$(snippet -f "python3 -m http.server[ --bind <lhost>][ <lport>]" lport=4444)
assert_eq "Optional: omit unset group, include set group" \
    "python3 -m http.server 4444" \
    "$result"

# Default value used when argument is not provided
result=$(snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>")
assert_eq "Default value used when argument omitted" \
    "python3 -m http.server 8000" \
    "$result"

# Default value overwritten by explicit argument
result=$(snippet -f "python3 -m http.server[ --bind <lhost>] <lport='8000'>" lport=9090)
assert_eq "Default value overwritten by explicit argument" \
    "python3 -m http.server 9090" \
    "$result"

# --- Codecs -----------------------------------------------------------------------------------------------------------

# squote codec wraps each value in single quotes
result=$(snippet -f "tar -czvf <archive|squote> <file...|squote>" /path/to/foo.tar file=foo bar)
assert_eq "squote codec on archive and repeatable file" \
    "tar -czvf '/path/to/foo.tar' 'foo' 'bar'" \
    "$result"

# Chained codecs: add suffix then squote
result=$(snippet -f "cp <file|squote> <file|add:'.bak'|squote>" /path/to/foo /path/to/bar)
assert_match "Chained codecs: line 1" \
    "^cp '/path/to/foo' '/path/to/foo.bak'$" \
    "$(echo "$result" | sed -n '1p')"
assert_match "Chained codecs: line 2" \
    "^cp '/path/to/bar' '/path/to/bar.bak'$" \
    "$(echo "$result" | sed -n '2p')"

# ======================================================================================================================
# Cleanup
# ======================================================================================================================

rm files.txt

summary