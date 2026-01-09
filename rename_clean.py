#!/usr/bin/env python3
"""
Utility to replace undesirable characters with underscores in Linux file names.
Undesirable characters are any that are not ASCII alphanumeric (`0-9`, `a-z`,
`A-Z`), underscore (`_`), hyphen (`-`), or dot (`.`). If characters are
replaced, then repeated underscores are also reduced to a single underscore and
trimmed from the name stem and suffix. A unique name is always created by
appending a number on the name stem if necessary. If run from within a git
repository, `git mv` is used to rename tracked files/directories.
"""

# Author: Mark Blakeney, Jul 2025.
from __future__ import annotations

import itertools
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Sequence

from argparse_from_file import ArgumentParser, Namespace  # type: ignore[import]

PROG = Path(sys.argv[0]).stem

gitfiles = set()


def run(cmd: Sequence[str]) -> tuple[str, str]:
    "Run given command and return (stdout, stderr) strings"
    stdout = ''
    stderr = ''
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
    except Exception as e:
        stderr = str(e)
    else:
        if res.stdout:
            stdout = res.stdout.strip()
        if res.stderr:
            stderr = res.stderr.strip()

    return stdout, stderr


def rename(src: Path, dst: Path) -> bool:
    "Rename a file or directory, using git if possible"
    srcstr = str(src)
    if srcstr in gitfiles:
        out, err = run(('git', 'mv', '--', srcstr, str(dst)))
        if err:
            print(f'Git rename error: {err}', file=sys.stderr)
            return False
    else:
        src.rename(dst)

    return True


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
                    if rename(path, newpath):
                        path = newpath

            if is_dir and (
                top
                or (self.recurse and (not path.is_symlink() or self.recurse_symlinks))
            ):
                self.rename_paths(path.iterdir(), False)


def main() -> None:
    "Main code"
    # Process command line options
    opt = ArgumentParser(description=__doc__)
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
        help='replace repeated underscores even if there are no other replacements',
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
        '-G',
        '--no-git',
        dest='git',
        action='store_const',
        const=0,
        help='do not use git if invoked within a git repository',
    )
    opt.add_argument(
        '-g',
        '--git',
        dest='git',
        action='store_const',
        const=1,
        help='negate the --no-git option and DO use automatic git',
    )
    opt.add_argument(
        'path',
        nargs='*',
        default=['.'],
        help='one or more file or directory names to rename, or "-" to read names from stdin. '
        'Default is all files in current directory if no path given.',
    )

    args = opt.parse_args()

    if args.dryrun:
        args.quiet = False

    if len(args.character) != 1:
        opt.error('Error: -c/--character must be a single character.')

    if args.git != 0:
        out, giterr = run(('git', 'ls-files'))
        if giterr and args.git:
            print(f'Git invocation error: {giterr}', file=sys.stderr)
        if out:
            gitfiles.update(out.splitlines())

        if args.git and not gitfiles:
            opt.error('must be within a git repo to use -g/--git option')

    # Read stdin if single dash is given as path
    if len(paths := args.path) == 1 and paths[0] == '-':
        if args.recurse:
            opt.error('Error: -r/--recurse cannot be used with stdin input.')

        paths = [ln.rstrip('\r\n') for ln in sys.stdin]

    if paths:
        REMAPPER(args).rename_paths(Path(a) for a in paths)


if __name__ == '__main__':
    main()
