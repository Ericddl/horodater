#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later

# The single source of truth for the installed command and release archives.
HORODATER_VERSION='0.1.0'

usage() {
    printf '%s\n' \
        'Usage: horodater [--dry-run] [--] FILE...' \
        '       horodater --help | --version' \
        '' \
        'Prefix regular filenames with the local date (YYYYMMDD_).' \
        'Existing destinations, directories and symbolic links are refused.' \
        'Names already starting with eight digits and _ are left unchanged.' \
        '' \
        '  -n, --dry-run  Show planned renames without changing files' \
        '  -h, --help     Show this help' \
        '  -V, --version  Show the version' \
        '' \
        'Exit status: 0 success, 1 operation failed, 2 invalid usage.'
}

dry_run=false
while [ "$#" -gt 0 ]; do
    case $1 in
        -n|--dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        -V|--version) printf 'horodater %s\n' "$HORODATER_VERSION"; exit 0 ;;
        --) shift; break ;;
        -*)
            printf 'horodater: unknown option: %s (use -- before filenames)\n' "$1" >&2
            exit 2
            ;;
        *) break ;;
    esac
done

if [ "$#" -eq 0 ]; then
    usage >&2
    exit 2
fi

# Compute once per invocation. Do not rename anything if the clock fails.
if ! today=$(LC_ALL=C date '+%Y%m%d'); then
    printf '%s\n' 'horodater: cannot determine the current date' >&2
    exit 1
fi
case $today in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
    *) printf '%s\n' 'horodater: date returned an invalid YYYYMMDD value' >&2; exit 1 ;;
esac

status=0
for operand do
    if [ -z "$operand" ]; then
        printf '%s\n' 'horodater: empty filename' >&2
        status=1
        continue
    fi

    # Every external command receives an absolute or ./-prefixed pathname.
    # Shell expansions also preserve trailing newlines, unlike $(basename ...).
    case $operand in
        /*) source=$operand ;;
        *) source=./$operand ;;
    esac

    if [ -L "$source" ] || [ ! -f "$source" ]; then
        printf 'horodater: not a regular file (or is a symbolic link): %s\n' "$operand" >&2
        status=1
        continue
    fi

    name=${source##*/}
    directory=${source%/*}
    case $name in
        [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_*) continue ;;
    esac
    destination=$directory/${today}_$name

    if [ -e "$destination" ] || [ -L "$destination" ]; then
        printf 'horodater: destination already exists: %s\n' "$destination" >&2
        status=1
        continue
    fi

    if [ "$dry_run" = true ]; then
        printf '%s -> %s\n' "$source" "$destination"
        continue
    fi

    # -i with closed input also refuses a file created after the check above.
    # Portable mv cannot guarantee the destination's type against concurrent
    # directory changes; shared directories require external coordination.
    if mv -i "$source" "$destination" < /dev/null; then
        if [ -e "$source" ] || [ -L "$source" ] ||
            [ ! -f "$destination" ] || [ -L "$destination" ]; then
            printf 'horodater: rename did not complete as expected: %s\n' "$operand" >&2
            status=1
        fi
    else
        printf 'horodater: cannot rename: %s\n' "$operand" >&2
        status=1
    fi
done
exit "$status"
