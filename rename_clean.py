"""
Utility to replace undesirable characters with underscores in Linux file names.
Undesirable characters are any that are not ASCII alphanumeric (`0-9`, `a-z`,
`A-Z`), underscore (`_`), hyphen (`-`), or dot (`.`). If characters are
replaced by underscores, then repeated underscores are also reduced to a single
underscore and trimmed from the file name stem and suffix, or from the
directory name. A unique name is always created by appending a number on the
name stem if necessary.
"""

# Author: Mark Blakeney, Jul 2025.
from __future__ import annotations

import io
import itertools
import os
import re
import string
import sys
from os.path import lexists
from pathlib import Path

from argparse_from_file import ArgumentParser, Namespace

NAME_MAX = 255  # Maximum length of a file name in bytes
ALPHANUMS = set(string.ascii_letters + string.digits)


def print_err(*args, **kwargs):
    "Print to stderr"
    print(*args, file=sys.stderr, **kwargs)


class Renamer:
    def __init__(self, args: Namespace):
        self.args = args
        self.valids = ALPHANUMS.copy()
        self.valids.update('-_.', args.add, args.character)
        self.rexp = f'{re.escape(args.character)}+'
        self.err_count = 0
        self.assigned = set()
        self.words = 'Would rename' if args.dryrun else 'Renamed'

    def make_new_name(self, path: Path, is_dir: bool) -> Path | None:
        "Make a new path name by replacing characters"
        if not (name := path.name):
            return None

        args = self.args
        char = args.character
        newname = ''.join((c if c in self.valids else char) for c in name)

        if newname == name and not args.more_aggressive:
            return None

        def trim(name: str) -> str:
            "Trim repeated replacement chars from within, and then from start and end"
            return re.sub(self.rexp, char, name).strip(char)

        if is_dir:
            stem = trim(newname) or char
            suffix = ''
        else:
            stem, suffix = os.path.splitext(newname)
            stem = trim(stem) or char
            if suffix := trim(suffix[1:]):
                suffix = '.' + suffix

        newname = stem + suffix

        while newname in ('.', '..'):
            newname = f'{newname}{char}'

        # If the name is unchanged, return None
        if newname == name:
            return None

        if stem != char:
            stem += char

        # Ensure a new name that does not already exist or is not already assigned
        for n in itertools.count(2):
            newpath = path.with_name(newname)
            if not lexists(newpath) and newpath not in self.assigned:
                break

            newname = f'{stem}{n}{suffix}'

        # Check file name lengths
        if len(os.fsencode(newpath.name)) > NAME_MAX:
            print_err(f'Error: new name too long: {newpath.name}')
            self.err_count += 1
            return None

        return newpath

    def rename_paths(self, paths: list[Path]) -> int:
        "Rename files and directories for the given paths"
        args = self.args
        for path in paths:
            if not lexists(path):
                print_err(f'Path does not exist: {path}')
                self.err_count += 1
                continue

            if args.ignore_hidden and path.name.startswith('.'):
                continue

            if args.symlinks_remove and path.is_symlink():
                try:
                    path.unlink()
                except OSError as e:
                    print_err(f'Error: {e}')
                    self.err_count += 1
                else:
                    if not args.quiet:
                        print(f'Removed symlink: "{path}"')
                continue

            if newpath := self.make_new_name(path, is_dir := path.is_dir()):
                if not args.quiet:
                    add = '/' if is_dir else ''
                    print(f'{self.words} "{path}{add}" -> "{newpath}{add}"')

                ok = True
                if not args.dryrun:
                    try:
                        path.rename(newpath)
                    except OSError as e:
                        print_err(f'Error: {e}')
                        self.err_count += 1
                        ok = False
                    else:
                        path = newpath

                if ok:
                    self.assigned.add(newpath)

            if args.recurse and (is_dir and not path.is_symlink()):
                try:
                    children = list(path.iterdir())
                except OSError as e:
                    print_err(f'Error: {e}')
                    self.err_count += 1
                else:
                    self.rename_paths(children)

        return self.err_count


def main() -> int:
    "Main code"
    # Process command line options
    opt = ArgumentParser(description=__doc__)
    opt.add_argument(
        '-r',
        '--recurse',
        action='store_true',
        help='recurse through all sub directories (not including symlinks)',
    )
    opt.add_argument(
        '-d',
        '--dryrun',
        action='store_true',
        help='do not rename, just show what would be done',
    )
    opt.add_argument('-q', '--quiet', action='store_true', help='do not report changes')
    opt.add_argument(
        '-i',
        '--ignore-hidden',
        action='store_true',
        help='ignore hidden files and directories (those starting with ".")',
    )
    opt.add_argument(
        '-m',
        '--more-aggressive',
        action='store_true',
        help='replace repeated underscores even if there are no other replacements',
    )
    opt.add_argument(
        '-s',
        '--symlinks-remove',
        action='store_true',
        help='remove symlinks instead of renaming them, to avoid potentially '
        'leaving broken links',
    )
    opt.add_argument(
        '-c',
        '--character',
        default='_',
        help='character to replace undesirable characters with, default = "%(default)s"',
    )
    opt.add_argument(
        '-a',
        '--add',
        default='',
        help='additional characters to allow in names, e.g. "-a=+%%" '
        '(default: only alphanumeric, "_", "-", and ".")',
    )
    opt.add_argument(
        'path',
        nargs='*',
        help='one or more file or directory names to rename, or "-" to read names from stdin. '
        'Default is all files in current directory if no path given.',
    )

    args = opt.parse_args()
    for fp in (sys.stdin, sys.stdout, sys.stderr):
        if isinstance(fp, io.TextIOWrapper):
            fp.reconfigure(errors='backslashreplace')

    if len(args.character) != 1:
        opt.error('-c/--character must be a single character.')

    if args.character in ALPHANUMS:
        opt.error('-c/--character cannot be plain alphanumeric.')

    if args.character in (os.sep, '.', '\\') or args.character.isspace():
        opt.error(f'-c/--character cannot be "{args.character}".')

    if args.dryrun:
        args.quiet = False

    # Get top level paths to rename
    if not args.path:
        try:
            paths = list(Path('.').iterdir())
        except OSError as e:
            sys.exit(f'Error: {e}')
    else:
        paths = []
        for path in args.path:
            if path == '-':
                paths.extend(
                    Path(ln)
                    for ls in sys.stdin
                    if (ln := ls.rstrip('\r\n')) and ln.strip()
                )
            else:
                paths.append(Path(path))

        # Remove duplicates while preserving order
        paths = list(dict.fromkeys(paths))

    renamer = Renamer(args)

    if (err_count := renamer.rename_paths(paths)) > 0:
        s = 's' if err_count > 1 else ''
        print_err(f'{err_count} error{s} occurred.')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
