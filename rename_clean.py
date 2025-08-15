#!/usr/bin/env python3
"""
Utility to replace undesirable characters with underscores in Linux file names.
Undesirable characters are any that are not ASCII alphanumeric (`0-9`, `a-z`,
`A-Z`), underscore (`_`), hyphen (`-`), or dot (`.`). If characters are
replaced, then repeated underscores are also reduced to a single underscore and
trimmed from the name stem and suffix. A unique name is always created by
appending a number on the name stem if necessary.
"""

# Author: Mark Blakeney, Jul 2025.
from __future__ import annotations

import itertools
import re
import shlex
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Iterable

from platformdirs import user_config_path

PROG = Path(sys.argv[0]).stem
CNFFILE = user_config_path() / f'{PROG}-flags.conf'


class REMAPPER:
    def __init__(self, args: Namespace):
        # Save options from command line arguments
        self.recurse = args.recurse
        self.dryrun = args.dryrun
        self.quiet = args.quiet
        self.recurse_symlinks = args.recurse_symlinks
        self.ignore_hidden = args.ignore_hidden
        self.more_aggressive = args.more_aggressive
        self.character = args.character

        self.map = re.compile(r'[^-.\w' + self.character + args.add + ']+', re.ASCII)
        self.reduce = re.compile('\\' + self.character + '+')

        if self.map.match(args.character):
            sys.exit(
                f'Error: -c/--character "{args.character}" is one of the undesirable characters.'
            )

    def make_new_name(self, path: Path) -> Path | None:
        "Make a new path name by replacing characters"
        if not (pname := path.name):
            return None

        # Replace undesirable characters with an underscore.
        name = self.map.sub(self.character, pname)
        if name == pname and not self.more_aggressive:
            return None

        # Remove multiple underscores
        name = self.reduce.sub(self.character, name)

        # Remove leading and trailing underscores on stem and suffix
        newpath = Path(name)
        stem = newpath.stem.strip(self.character) or self.character
        if (suffix := newpath.suffix.strip(self.character)) == '.':
            suffix = ''

        # If the name is unchanged, return None
        if (name := (stem + suffix)) == pname:
            return None

        # Ensure a new name that does not already exist
        for n in itertools.count(2):
            newpath = path.with_name(name)
            if not newpath.exists():
                return newpath

            name = f'{stem}{self.character}{n}{suffix}'

        return None

    def rename_paths(self, dirs: Iterable[Path], top: bool = True) -> None:
        "Rename files and directories for the given paths"
        for path in dirs:
            if self.ignore_hidden and path.name.startswith('.'):
                continue

            if not (is_dir := path.is_dir()) and top and not path.exists():
                print(f'Path does not exist: {path}', file=sys.stderr)
                continue

            if newpath := self.make_new_name(path):
                if not self.quiet:
                    add = '/' if is_dir else ''
                    print(f'Renaming "{path}{add}" -> "{newpath}{add}"')

                if not self.dryrun:
                    path.rename(newpath)
                    path = newpath

            if is_dir and (
                top
                or (self.recurse and (not path.is_symlink() or self.recurse_symlinks))
            ):
                self.rename_paths(path.iterdir(), False)


def main() -> None:
    "Main code"
    # Process command line options
    opt = ArgumentParser(
        description=__doc__, epilog=f'Note you can set default options in {CNFFILE}'
    )
    opt.add_argument(
        '-r',
        '--recurse',
        action='store_true',
        help='recurse through all sub directories',
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
        '-s',
        '--recurse-symlinks',
        action='store_true',
        help='recurse into symbolic directory links, default is to rename a link but not recurse into it',
    )
    opt.add_argument(
        '-m',
        '--more-aggressive',
        action='store_true',
        help='Replace underscores even if deletions have not been done',
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
        help='additional characters to allow in names, e.g. "+%%" '
        '(default: only alphanumeric, "_", "-", and ".")',
    )
    opt.add_argument(
        'path',
        nargs='*',
        default=['.'],
        help='one or more file or directory names to rename, or "-" to read names from stdin. '
        'Default is all files in current directory if no path given.',
    )

    # Merge in default args from user config file. Then parse the
    # command line.
    if CNFFILE.exists():
        with CNFFILE.open() as fp:
            lines = [re.sub(r'#.*$', '', line).strip() for line in fp]
        cnflines = ' '.join(lines).strip()
    else:
        cnflines = ''

    args = opt.parse_args(shlex.split(cnflines) + sys.argv[1:])

    if args.dryrun:
        args.quiet = False

    if len(args.character) != 1:
        opt.error('Error: -c/--character must be a single character.')

    # Read stdin if single dash is given as path
    if len(paths := args.path) == 1 and paths[0] == '-':
        if args.recurse:
            opt.error('Error: -r/--recurse cannot be used with stdin input.')

        paths = [ln.rstrip('\r\n') for ln in sys.stdin]

    if paths:
        REMAPPER(args).rename_paths(Path(a) for a in paths)


if __name__ == '__main__':
    main()
